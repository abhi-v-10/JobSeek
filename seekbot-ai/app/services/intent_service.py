import re
from app.services.openai_service import ask_ai




def detect_intent_ai(message: str) -> str:
    prompt = f"""
Classify the user message into ONLY one intent:

job_search
resume_review
resume_analysis
skill_analysis
career_roadmap
interview_prep
market_insights
skill_guidance
project_suggestions
general_chat

Message: {message}

Return only the intent name.
"""

    result = ask_ai(prompt).strip().lower()

    allowed = {
        "job_search",
        "resume_review",
        "resume_analysis",
        "skill_analysis",
        "career_roadmap",
        "interview_prep",
        "market_insights",
        "skill_guidance",
        "project_suggestions",
        "general_chat"
    }

    return result if result in allowed else "general_chat"

def detect_intent_rule(message: str) -> str | None:
    text = message.lower().strip()

    job_keywords = [
        "job", "jobs", "internship", "intern", "apply",
        "vacancy", "hiring", "opening", "developer role"
    ]

    resume_keywords = [
        "resume", "cv", "ats", "improve my resume",
        "analyze my resume", "review my resume", "review my cv",
        "resume analysis", "resume review", "resume feedback",
        "what skills do i have", "my skills", "skill analysis",
        "career analysis", "rate my resume",
    ]

    roadmap_keywords = [
        "roadmap", "how do i become", "career path",
        "how can i become"
    ]

    interview_keywords = [
        "interview", "mock interview", "questions"
    ]

    market_keywords = [
        "trend", "trending", "market", "salary", "demand"
    ]

    skill_keywords = [
        "skill", "learn", "what should i learn"
    ]

    project_keywords = [
        "project", "projects", "portfolio"
    ]

    if any(k in text for k in job_keywords):
        return "job_search"

    if any(k in text for k in resume_keywords):
        return "resume_review"

    if any(k in text for k in roadmap_keywords):
        return "career_roadmap"

    if any(k in text for k in interview_keywords):
        return "interview_prep"

    if any(k in text for k in market_keywords):
        return "market_insights"

    if any(k in text for k in skill_keywords):
        return "skill_guidance"

    if any(k in text for k in project_keywords):
        return "project_suggestions"

    return None

def detect_intent(message: str) -> str:
    rule_result = detect_intent_rule(message)

    if rule_result:
        return rule_result

    ai_result = detect_intent_ai(message)

    # Normalize resume-related intents to a single key
    if ai_result in ("resume_analysis", "skill_analysis"):
        return "resume_review"

    return ai_result

INTENTS = [
    "job_search",
    "resume_review",
    "career_roadmap",
    "interview_prep",
    "market_insights",
    "skill_guidance",
    "project_suggestions",
    "general_chat"
]