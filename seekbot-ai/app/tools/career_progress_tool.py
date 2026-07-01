import logging
import json
from typing import Dict, Any, Optional

from app.services.openai_service import ask_ai
from app.services.django_service import (
    fetch_user_profile,
    fetch_application_dashboard,
    fetch_application_analytics,
    fetch_upcoming_interviews,
)
from app.tools import resume_tool, application_strategy_tool, interview_tool
from app.tools.personalized_job_recommender import recommend_jobs_for_user

logger = logging.getLogger(__name__)


def generate_career_progress(
    session_id: str, message: str, authorization: Optional[str]
) -> str:
    """
    Generate a comprehensive career progress dashboard by orchestrating data from:
    - Application Dashboard
    - Application Analytics
    - Upcoming Interviews
    - Resume Tool
    - Job Recommender Tool
    - Application Strategy Tool
    - Interview Tool
    """
    logger.info(f"[{session_id}] Starting career_progress_tool orchestration.")

    # 1. Fetch User Profile and Platform Data
    user_profile = {}
    app_dashboard = {}
    app_analytics = {}
    upcoming_interviews = []

    if authorization:
        try:
            user_profile = fetch_user_profile(auth_token=authorization) or {}
            app_dashboard = fetch_application_dashboard(auth_token=authorization) or {}
            app_analytics = fetch_application_analytics(auth_token=authorization) or {}
            interviews_res = fetch_upcoming_interviews(auth_token=authorization) or {}
            # Assuming upcoming-interviews returns a list or dict with a 'results' key
            if isinstance(interviews_res, dict) and "results" in interviews_res:
                upcoming_interviews = interviews_res["results"]
            elif isinstance(interviews_res, list):
                upcoming_interviews = interviews_res
        except Exception as e:
            logger.warning(f"Failed to fetch user data from Django: {e}")

    resume_text = user_profile.get("resume_text", "")
    target_role = user_profile.get("target_role") or "Software Engineer"
    experience_level = user_profile.get("experience_level")

    # 2. Fetch Resume Feedback (lightweight wrapper if available)
    resume_feedback = ""
    if resume_text:
        try:
            resume_feedback = resume_tool.run(
                message="evaluate my resume", auth_token=authorization
            )
        except Exception as e:
            logger.warning(f"Failed to run resume_tool: {e}")

    # 3. Fetch Job Recommendations (for Readiness & Strategy)
    recommended_jobs = []
    try:
        recommendations = recommend_jobs_for_user(
            user_profile=user_profile,
            resume_text=resume_text,
            user_query=target_role,
            limit=3,
        )
        recommended_jobs = [
            {
                "id": job.job_id,
                "title": job.title,
                "company": job.company,
                "match_score": job.match_score,
                "readiness_score": getattr(job, "readiness_score", job.match_score),
                "required_skills": job.matching_skills + job.missing_skills,
            }
            for job in recommendations.recommended_jobs
        ]
    except Exception as e:
        logger.warning(f"Failed to run job recommender: {e}")

    # 4. Fetch Application Strategy
    strategy_summary = ""
    if recommended_jobs:
        try:
            strategy = application_strategy_tool.generate_application_strategy(
                user_profile=user_profile,
                resume_text=resume_text,
                recommended_jobs=recommended_jobs,
                target_role=target_role,
            )
            strategy_summary = application_strategy_tool.format_application_strategy(
                strategy
            )
        except Exception as e:
            logger.warning(f"Failed to run application strategy tool: {e}")

    # 5. Fetch Interview Prep
    interview_summary = ""
    if target_role:
        try:
            interview_payload = interview_tool.prepare_interview(
                target_role=target_role,
                user_profile=user_profile,
                resume_text=resume_text,
                job_description=None,
                experience_level=experience_level,
                focus_area=None,
                question_count=3,
            )
            interview_summary = interview_payload.preparation_summary
        except Exception as e:
            logger.warning(f"Failed to run interview tool: {e}")

    # 6. Compose the exact orchestrator prompt for the LLM
    prompt = f"""
You are SeekBot, a Principal AI Career Architect and Mentor.
The user is asking about their career progress ("{message}").

Your objective is to generate a Personal AI Career Dashboard that feels like a premium SaaS dashboard generated specifically for the user.
Format the response beautifully using Markdown. Keep the response concise, easy to scan using bullets, and avoid repeating information. 
Do NOT use generic chatbot language. Never fabricate numbers or complain about missing data. If modules (interviews, offers) lack data, hide or display them gracefully using 'N/A' or '0'.
Always maintain positive, realistic coaching—act like a career mentor. Personalize advice by referencing the user's specific projects or skills.

LIVE PLATFORM DATA:
--------------------------------------------------
USER PROFILE: {json.dumps(user_profile, indent=2)}
APP DASHBOARD: {json.dumps(app_dashboard, indent=2)}
APP ANALYTICS: {json.dumps(app_analytics, indent=2)}
UPCOMING INTERVIEWS: {json.dumps(upcoming_interviews, indent=2)}
RESUME SUMMARY: {resume_feedback[:500]}...
JOB RECOMMENDATIONS (Readiness & Missing Skills): {json.dumps(recommended_jobs, indent=2)}
STRATEGY: {strategy_summary[:500]}...
INTERVIEW PREP: {interview_summary[:500]}...
--------------------------------------------------

YOUR RESPONSE MUST FOLLOW EXACTLY THIS DASHBOARD STRUCTURE:

### Executive Summary
[Start with a highly personalized, humanized opening summarizing their current position and next milestone. Answer their question immediately before showing details. Keep it concise.]

### 📊 Smart Dashboard
- **Applications:** [Count] Submitted
- **Interviews:** [Count] Scheduled
- **Offers:** [Count]
- **Current Stage:** [Current Stage]
- **Interview Rate:** [Rate% or "N/A (no interview opportunities yet)"]
- **Offer Rate:** [Rate% or "N/A until interviews exist"]

### 💼 Career Readiness
[For the top target role, display the score and explicitly SHOW EVIDENCE of WHY it received that score.
Example:
**[Role] Readiness:** [Score]/100
**Evidence:**
✓ [Found skill 1]
✓ [Found skill 2]
**Missing:**
- [Missing skill 1]]

### 🏢 Recent Application Context
[If applications exist, show the most recent one:
**Role:** [Role]
**Company:** [Company]
**Status:** [Status]
**Applied Date:** [Date]
**Next Expected Step:** [Expected Step]
If no applications exist, omit this section gracefully.]

### 📈 Progress Timeline
[Generate a visual career journey using ✓ for completed and ○ for upcoming milestones based on data.
Example:
✓ Resume Uploaded
✓ Resume Analyzed
✓ First Application Submitted
○ First Interview
○ First Offer]

### 💡 Placement Insights
[1-2 intelligent, concise, evidence-based observations. Personalize this using their actual projects or data from the user profile/resume. Use encouraging, realistic coaching tone.]

### 🎯 Smart Actions
**High Priority:**
- [Action based on platform data, referencing specific projects or skills]
**Medium Priority:**
- [Action]
**Low Priority:**
- [Action]

### 🏁 Next Milestone
[A single, specific career milestone representing their next immediate goal (e.g., "Prepare for your first technical interview.")]
"""

    try:
        final_response = ask_ai(prompt)
        return final_response
    except Exception as e:
        logger.error(f"AI synthesis failed: {e}")
        return "I encountered an issue while generating your career progress dashboard. Please try again later."
