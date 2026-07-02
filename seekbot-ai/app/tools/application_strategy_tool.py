"""
Application Strategy Tool for SeekBot AI.

Determines application priorities, readiness, timing, and strategy.
This tool consumes output from the personalized job recommender and
builds a phased application plan with explainable, deterministic scoring.

Architecture:
    personalized_job_recommender -> application_strategy_tool -> AI explanation layer

Scoring is fully deterministic. AI is invoked ONLY for generating
human-readable explanations and strategic advice.
"""

import json
import logging
import os
import re
from typing import List, Optional, Dict, Any, Set
from pydantic import BaseModel, Field
import openai
from app.core.openai_client import generate_chat_completion
from app.core.skill_utils import (
    TECH_RE as _TECH_RE,
    SKILL_ALIASES as _SKILL_ALIASES,
    TITLE_SKILL_MAP as _TITLE_SKILL_MAP,
    expand_skills_with_aliases as _expand_skills_with_aliases,
    extract_skills_from_profile,
    fuzzy_skill_match as _fuzzy_skill_match,
    infer_skills_from_title as _infer_skills_from_title,
)
from app.core.scoring_utils import (
    PRODUCTION_INDICATORS as _PRODUCTION_INDICATORS,
    PROJECT_QUALITY_INDICATORS as _PROJECT_QUALITY_INDICATORS,
    calibrate_score as _calibrate_score,
    count_production_signals as _count_production_signals,
    count_project_signals as _count_project_signals,
)

# Configure logging
logger = logging.getLogger(__name__)

# ==============================================================================
# PYDANTIC MODELS (Structured Output)
# ==============================================================================

class SkillGap(BaseModel):
    skill: str = Field(..., description="Name of the missing or weak skill.")
    severity: str = Field(..., description="Severity of the gap: 'High', 'Medium', or 'Low'.")
    recommendation: str = Field(..., description="Actionable advice on how to acquire or improve the skill.")

class ApplicationOpportunity(BaseModel):
    job_id: Optional[int] = Field(None, description="The ID of the job, if available.")
    title: str = Field(..., description="Job title.")
    company: Optional[str] = Field(None, description="Company name.")
    match_score: float = Field(..., description="Overall match score (0-100).")
    readiness_score: float = Field(..., description="User's readiness score for this specific role (0-100).")
    application_priority: str = Field(..., description="'Apply Now', 'Strong Fit', 'Stretch Opportunity', or 'Delay Application'.")
    confidence_level: str = Field(..., description="'High', 'Medium', or 'Low' confidence in the recommendation.")
    why_recommended: str = Field(..., description="Recruiter-style explanation of why this job is a fit.")
    strengths_for_role: List[str] = Field(..., description="List of the user's strengths for this specific role.")
    skill_gaps: List[SkillGap] = Field(..., description="Identified skill gaps for this role.")
    required_next_steps: List[str] = Field(..., description="Immediate next steps before applying.")

class ApplicationStrategyPhase(BaseModel):
    phase_name: str = Field(..., description="Name of the phase, e.g., 'Phase 1: Immediate Applications'.")
    duration: str = Field(..., description="Estimated duration, e.g., 'Weeks 1-2'.")
    goal: str = Field(..., description="Primary goal of this phase.")
    actions: List[str] = Field(..., description="Specific actions to take during this phase.")

class ApplicationStrategyResponse(BaseModel):
    target_role: Optional[str] = Field(None, description="The primary target role for the strategy.")
    career_summary: str = Field(..., description="A brief, professional summary of the user's current standing.")
    overall_readiness_score: float = Field(..., description="Overall readiness score (0-100).")
    strongest_opportunities: List[ApplicationOpportunity] = Field(..., description="Jobs to apply to immediately.")
    stretch_opportunities: List[ApplicationOpportunity] = Field(..., description="Jobs that require some preparation.")
    jobs_to_delay: List[ApplicationOpportunity] = Field(..., description="Jobs to avoid for now due to major gaps.")
    application_strategy: List[ApplicationStrategyPhase] = Field(..., description="Strategic application phases.")
    strategic_advice: List[str] = Field(..., description="Actionable, recruiter-level advice.")
    final_recommendation: str = Field(..., description="Concluding recommendation from the career strategist.")

# ==============================================================================
# CONSTANTS & SHARED UTILITIES
# ==============================================================================
# Constants and helper functions (_TECH_RE, _SKILL_ALIASES, _TITLE_SKILL_MAP,
# _calibrate_score, _expand_skills_with_aliases, _count_production_signals,
# _count_project_signals, extract_skills_from_profile, _fuzzy_skill_match,
# _infer_skills_from_title) are imported from app.core.skill_utils and
# app.core.scoring_utils at the top of this file.
# These shared modules were extracted to enable reuse across tools
# (resume_optimizer_tool, personalized_job_recommender, etc.)
# without tight coupling or circular imports.


def calculate_readiness_score(user_profile: dict, resume_text: Optional[str]) -> float:
    """
    Deterministically calculates an overall readiness score (0-100) based on
    skill depth, resume quality, experience level, experience quality,
    project relevance, and profile completeness.
    """
    score = 0.0
    breakdown = []

    # 1. Skill Depth (Max 25)
    skills = extract_skills_from_profile(user_profile, resume_text)
    skill_count = len(skills)
    skill_pts = 0.0
    if skill_count >= 15:
        skill_pts = 25
    elif skill_count >= 10:
        skill_pts = 22
    elif skill_count >= 7:
        skill_pts = 18
    elif skill_count >= 4:
        skill_pts = 12
    elif skill_count >= 1:
        skill_pts = 6
    score += skill_pts
    breakdown.append(f"+{skill_pts:.0f} Skill Depth ({skill_count} skills)")

    # 2. Resume Quality (Max 20)
    combined_resume = resume_text or user_profile.get("resume_text") or ""
    resume_len = len(combined_resume.strip())
    resume_pts = 0.0
    if resume_len > 1000:
        resume_pts = 20
    elif resume_len > 500:
        resume_pts = 16
    elif resume_len > 100:
        resume_pts = 10
    elif resume_len > 0:
        resume_pts = 5
    score += resume_pts
    breakdown.append(f"+{resume_pts:.0f} Resume Quality (len={resume_len})")

    # 3. Experience Level (Max 18)
    exp = user_profile.get("experience_years") or user_profile.get("years_of_experience") or 0
    parsed = user_profile.get("parsed_resume") or {}
    if isinstance(parsed, str):
        try:
            parsed = json.loads(parsed)
        except (json.JSONDecodeError, TypeError):
            parsed = {}
    if not exp and isinstance(parsed, dict):
        for key in ("experience_years", "total_experience", "years_of_experience"):
            val = parsed.get(key)
            if val is not None:
                try:
                    exp = int(float(str(val)))
                    break
                except (TypeError, ValueError):
                    pass
    exp_pts = 0.0
    if isinstance(exp, (int, float)):
        if exp >= 5:
            exp_pts = 18
        elif exp >= 3:
            exp_pts = 15
        elif exp >= 1:
            exp_pts = 12
        else:
            exp_pts = 5
    score += exp_pts
    breakdown.append(f"+{exp_pts:.0f} Experience Level ({exp} years)")

    # 4. Production Experience Quality (Max 15) -- ISSUE 6
    prod_signals = _count_production_signals(resume_text, user_profile)
    prod_pts = min(15.0, prod_signals * 3.0)
    score += prod_pts
    breakdown.append(f"+{prod_pts:.0f} Production Experience ({prod_signals} signals)")

    # 5. Project Relevance (Max 12) -- ISSUE 5
    project_signals = _count_project_signals(resume_text, user_profile)
    project_pts = min(12.0, project_signals * 2.0)
    score += project_pts
    breakdown.append(f"+{project_pts:.0f} Project Relevance ({project_signals} signals)")

    # 6. Profile Completeness (Max 10)
    profile_pts = 0.0
    if user_profile.get("skills"):
        profile_pts += 3
    if user_profile.get("parsed_resume"):
        profile_pts += 3
    if user_profile.get("full_name") or user_profile.get("username"):
        profile_pts += 1
    if user_profile.get("github_url") or user_profile.get("linkedin_url"):
        profile_pts += 3
    score += profile_pts
    breakdown.append(f"+{profile_pts:.0f} Profile Completeness")

    # ISSUE 1 & 3: Apply calibration and log the breakdown
    raw = min(100.0, score)
    final = _calibrate_score(raw)

    logger.info(
        "[STRATEGY] Overall readiness breakdown:\n  %s\n  Raw=%.1f -> Calibrated=%.1f/100",
        "\n  ".join(breakdown), raw, final,
    )
    return final


# _infer_skills_from_title and _fuzzy_skill_match are imported from
# app.core.skill_utils (see imports at top of file).


def calculate_job_readiness(
    user_skills: Set[str],
    job_reqs: Set[str],
    job_title: str = "",
) -> float:
    """
    Deterministically calculate how ready a user is for a specific job.
    Uses fuzzy substring matching, semantic aliases, and title-based fallback.
    Applies calibration to prevent unrealistic 100% scores.
    """
    # If no requirements listed, try title-based inference
    effective_reqs = job_reqs
    is_inferred = False
    if not effective_reqs:
        effective_reqs = _infer_skills_from_title(job_title)
        is_inferred = True

    if not effective_reqs:
        logger.info(
            "[STRATEGY] No requirements determinable for '%s' -- defaulting to 60%% readiness",
            job_title,
        )
        return 60.0  # Conservative default when we truly can't determine requirements

    # Fuzzy substring matching (same approach as job recommender)
    matched, missing = _fuzzy_skill_match(user_skills, effective_reqs)

    match_pct = (len(matched) / len(effective_reqs)) * 100 if effective_reqs else 0.0

    # Slight discount for inferred skills (less certainty)
    if is_inferred:
        match_pct = match_pct * 0.85

    # ISSUE 1: Apply calibration to prevent unrealistic 100%
    final = _calibrate_score(round(match_pct, 1))

    logger.info(
        "[STRATEGY] Job readiness for '%s': matched=%s, missing=%s, "
        "raw=%.1f%%, calibrated=%.1f%%, inferred=%s",
        job_title, matched, missing, match_pct, final, is_inferred,
    )
    return final


def classify_opportunity(match_score: float, readiness_score: float) -> str:
    """
    Categorizes job based on deterministic scoring metrics.

    match_score:     multi-factor score from recommender (0-100)
    readiness_score: skill overlap percentage from calculate_job_readiness (0-100)

    The match_score already incorporates experience, work-mode, and role alignment,
    so it's weighted more heavily than pure skill overlap.
    """
    combined = (match_score * 0.6) + (readiness_score * 0.4)

    if combined >= 75:
        category = "Apply Now"
    elif combined >= 58:
        category = "Strong Fit"
    elif combined >= 40:
        category = "Stretch Opportunity"
    else:
        category = "Delay Application"

    logger.info(
        "[STRATEGY] classify_opportunity: match=%.1f, readiness=%.1f, "
        "combined=%.1f -> %s",
        match_score, readiness_score, combined, category,
    )
    return category

# ==============================================================================
# FALLBACK BEHAVIOR (Guaranteed execution without AI)
# ==============================================================================


def _generate_fallback_reasoning(
    job_title: str,
    company: str,
    matched_skills: list,
    missing_skills: list,
    match_score: float,
    readiness: float,
) -> str:
    """
    Generate a recruiter-style recommendation reason from deterministic data.
    ISSUE 4: Specific, evidence-based reasoning instead of generic text.
    """
    parts = []

    if matched_skills:
        top = [s.title() for s in matched_skills[:4]]
        parts.append(
            f"Your experience with {', '.join(top)} directly aligns with "
            f"the requirements for this {job_title} role"
            + (f" at {company}" if company and company != "Unknown Company" else "")
            + "."
        )

    if readiness >= 75:
        parts.append(
            f"With a {readiness:.0f}% skill readiness, you cover the core technical "
            f"requirements and can contribute from day one."
        )
    elif readiness >= 50:
        parts.append(
            f"At {readiness:.0f}% readiness, you have a solid foundation and can "
            f"close the remaining gaps quickly."
        )

    if missing_skills and len(missing_skills) <= 2:
        gaps = [s.title() for s in missing_skills]
        parts.append(f"Minor gap in {', '.join(gaps)} -- addressable within 2-4 weeks.")

    if not parts:
        parts.append(
            f"Match score of {match_score:.0f}% with {len(matched_skills)} "
            f"overlapping skills for this role."
        )

    return " ".join(parts)


def _generate_fallback_gap_analysis(missing_skills: list, job_title: str) -> List[SkillGap]:
    """
    Generate specific, actionable gap analysis instead of generic advice.
    ISSUE 2: Precise gaps with concrete learning recommendations.
    """
    gap_recommendations = {
        "aws": ("High", "Complete AWS Cloud Practitioner certification; deploy a side project on EC2 or Lambda."),
        "azure": ("Medium", "Explore Azure Fundamentals; deploy a web app using Azure App Service."),
        "gcp": ("Medium", "Try Google Cloud Skills Boost; deploy a Cloud Run service."),
        "docker": ("High", "Containerize one of your existing projects; learn Docker Compose for multi-service setups."),
        "kubernetes": ("Medium", "Complete a Kubernetes basics tutorial; deploy a Helm chart to a local cluster."),
        "terraform": ("Medium", "Write Terraform configs for your existing cloud infrastructure."),
        "machine learning": ("High", "Build an end-to-end ML pipeline with scikit-learn; deploy a model via FastAPI."),
        "deep learning": ("Medium", "Complete a PyTorch/TensorFlow project; train a model on a public dataset."),
        "langchain": ("Medium", "Build a RAG-powered chatbot using LangChain and your existing FastAPI skills."),
        "rag": ("Medium", "Implement a Retrieval-Augmented Generation pipeline with a vector database."),
        "vector database": ("Medium", "Set up Pinecone or ChromaDB; build a semantic search feature."),
        "llm": ("Medium", "Build an LLM-powered application using OpenAI or HuggingFace APIs."),
        "ci/cd": ("Medium", "Set up a GitHub Actions pipeline for automated testing and deployment."),
        "typescript": ("Low", "Migrate a small JavaScript project to TypeScript to learn the type system."),
        "graphql": ("Low", "Add a GraphQL endpoint to an existing REST API project."),
        "redis": ("Low", "Add caching with Redis to one of your Django/FastAPI projects."),
        "linux": ("Low", "Practice common sysadmin tasks; set up and manage a VPS."),
        "nginx": ("Low", "Configure Nginx as a reverse proxy for one of your deployed applications."),
    }

    gaps = []
    for skill in missing_skills[:5]:
        skill_lower = skill.lower()
        if skill_lower in gap_recommendations:
            severity, rec = gap_recommendations[skill_lower]
        else:
            severity = "Medium"
            rec = f"Study {skill} fundamentals through official documentation and build a small project demonstrating the skill."
        gaps.append(SkillGap(skill=skill, severity=severity, recommendation=rec))

    return gaps


def generate_fallback_strategy(
    user_profile: dict,
    recommended_jobs: list,
    readiness: float,
    target_role: str,
    resume_text: Optional[str] = None,
) -> ApplicationStrategyResponse:
    """
    Generates a safe, deterministic strategy if the AI fails or times out.
    ISSUE 4, 8, 9: Recruiter-quality reasoning and actionable strategies.
    """
    user_skills = extract_skills_from_profile(user_profile, resume_text)
    prod_signals = _count_production_signals(resume_text, user_profile)

    strongest = []
    stretch = []
    delay = []

    for job in (recommended_jobs or []):
        job_reqs = set(job.get("required_skills", []))
        job_title = job.get("title", "")
        company = job.get("company", "Unknown Company")
        job_readiness = calculate_job_readiness(user_skills, job_reqs, job_title)
        match_score = float(job.get("match_score", 50.0))

        priority = classify_opportunity(match_score, job_readiness)

        # Compute matched/missing with fuzzy matching for display
        effective_reqs = job_reqs if job_reqs else _infer_skills_from_title(job_title)
        matched_skills, missing_skill_list = _fuzzy_skill_match(user_skills, effective_reqs)

        # ISSUE 2: Specific gap analysis
        skill_gaps = _generate_fallback_gap_analysis(missing_skill_list, job_title)

        # ISSUE 4: Evidence-based reasoning
        why = _generate_fallback_reasoning(
            job_title, company, matched_skills, missing_skill_list,
            match_score, job_readiness,
        )

        strengths = [s.title() for s in matched_skills[:6]] if matched_skills else ["General background alignment"]

        # ISSUE 8: Specific next steps based on priority
        if priority in ("Apply Now", "Strong Fit"):
            next_steps = [
                f"Tailor your resume to emphasize {', '.join(s.title() for s in matched_skills[:3])}",
                f"Research {company}'s engineering culture and recent projects",
                "Prepare a brief cover letter highlighting your relevant project experience",
            ]
        elif priority == "Stretch Opportunity":
            gap_names = [g.skill for g in skill_gaps[:2]]
            next_steps = [
                f"Start building skills in {', '.join(gap_names)}" if gap_names else "Review the full job description",
                "Build a small project demonstrating the missing competencies",
                "Apply after 2-4 weeks of targeted preparation",
            ]
        else:
            next_steps = [
                "Focus on roles closer to your current skill set first",
                "Revisit this role after building foundational experience",
            ]

        # Confidence based on data quality
        confidence = "High" if job_reqs and len(matched_skills) >= 3 else "Medium"

        opp = ApplicationOpportunity(
            job_id=job.get("id"),
            title=job_title or "Unknown Role",
            company=company,
            match_score=match_score,
            readiness_score=job_readiness,
            application_priority=priority,
            confidence_level=confidence,
            why_recommended=why,
            strengths_for_role=strengths,
            skill_gaps=skill_gaps,
            required_next_steps=next_steps,
        )

        if priority in ["Apply Now", "Strong Fit"]:
            strongest.append(opp)
        elif priority == "Stretch Opportunity":
            stretch.append(opp)
        else:
            delay.append(opp)

    # Sort each bucket by readiness descending
    strongest.sort(key=lambda o: o.readiness_score, reverse=True)
    stretch.sort(key=lambda o: o.readiness_score, reverse=True)

    # ISSUE 8: Actionable execution phases
    phases = []
    if strongest:
        top_titles = [o.title for o in strongest[:3]]
        phases.append(ApplicationStrategyPhase(
            phase_name="Phase 1: Immediate Applications",
            duration="Weeks 1-2",
            goal=f"Submit tailored applications to {len(strongest)} high-match roles",
            actions=[
                f"Customize resume for: {', '.join(top_titles)}",
                "Write role-specific cover letters referencing your relevant projects",
                "Prepare for technical screening questions in your core stack",
                "Set up job alerts for similar positions at target companies",
            ],
        ))
    if stretch:
        gap_skills = set()
        for o in stretch[:3]:
            gap_skills.update(g.skill for g in o.skill_gaps[:2])
        gap_list = sorted(gap_skills)[:4]
        phases.append(ApplicationStrategyPhase(
            phase_name="Phase 2: Targeted Skill Building",
            duration="Weeks 3-6",
            goal="Close specific skill gaps to unlock stretch opportunities",
            actions=[
                f"Build a project demonstrating: {', '.join(gap_list)}" if gap_list else "Identify and address key skill gaps",
                "Complete relevant online courses or certifications",
                "Contribute to open-source projects in target technology areas",
                "Update resume and portfolio with new skills and projects",
            ],
        ))
    if delay:
        phases.append(ApplicationStrategyPhase(
            phase_name="Phase 3: Long-Term Career Growth",
            duration="Months 2-4",
            goal="Build towards aspirational roles through systematic upskilling",
            actions=[
                "Identify mentors or communities in your target role area",
                "Build 1-2 substantial portfolio projects showcasing advanced capabilities",
                "Consider relevant certifications (AWS, GCP, ML specializations)",
                "Network with professionals in target companies via LinkedIn",
            ],
        ))

    # ISSUE 9: Evidence-based recruiter insights
    strategic_advice = []
    if prod_signals >= 3:
        strategic_advice.append(
            "Your production experience (debugging, deployment, CI/CD) is a significant "
            "differentiator -- highlight it prominently in every application."
        )
    if len(user_skills) >= 12:
        strategic_advice.append(
            "Your broad technical skill set across multiple frameworks and databases "
            "makes you versatile -- tailor your resume to each role's specific stack."
        )
    if "ai agent" in user_skills or "llm" in user_skills or "langchain" in user_skills:
        strategic_advice.append(
            "Your AI/LLM integration experience is highly sought-after -- even for "
            "non-AI roles, mention this as a differentiator."
        )
    strategic_advice.extend([
        "Apply to your strongest matches first for momentum and interview practice.",
        "Follow up on applications within 5-7 business days with a brief, professional note.",
    ])

    # Career summary
    skill_areas = []
    if any(s in user_skills for s in ("django", "fastapi", "flask", "express")):
        skill_areas.append("backend development")
    if any(s in user_skills for s in ("react", "vue", "angular")):
        skill_areas.append("frontend frameworks")
    if any(s in user_skills for s in ("llm", "machine learning", "ai agent", "langchain")):
        skill_areas.append("AI/ML integration")
    if any(s in user_skills for s in ("docker", "kubernetes", "aws", "ci/cd")):
        skill_areas.append("DevOps practices")

    area_text = ", ".join(skill_areas) if skill_areas else "software development"

    return ApplicationStrategyResponse(
        target_role=target_role or "Your target role",
        career_summary=(
            f"With {len(user_skills)} identified technical competencies spanning "
            f"{area_text}, and {prod_signals} production-experience indicators, "
            f"you are well-positioned for targeted applications."
        ),
        overall_readiness_score=readiness,
        strongest_opportunities=strongest,
        stretch_opportunities=stretch,
        jobs_to_delay=delay,
        application_strategy=phases,
        strategic_advice=strategic_advice,
        final_recommendation=(
            f"You have {len(strongest)} strong opportunities ready for immediate "
            f"application and {len(stretch)} stretch roles worth preparing for. "
            f"Prioritize applying to your top matches this week while building "
            f"skills for stretch targets."
        ),
    )

# ==============================================================================
# AI ANALYSIS ENGINE (Structured Outputs)
# ==============================================================================

def generate_strategy_with_ai(
    user_profile: dict,
    resume_text: Optional[str],
    recommended_jobs: list,
    roadmap_context: Optional[str],
    target_role: str,
    overall_readiness: float,
) -> ApplicationStrategyResponse:
    """
    Uses AI to analyze deterministic metrics and generate strategic,
    recruiter-level coaching. All scores are computed deterministically;
    the AI only generates explanations, advice, and phased strategies.
    """
    user_skills = extract_skills_from_profile(user_profile, resume_text)
    prod_signals = _count_production_signals(resume_text, user_profile)
    project_signals = _count_project_signals(resume_text, user_profile)

    job_context = []
    for job in (recommended_jobs or []):
        job_reqs = set(job.get("required_skills", []))
        job_title = job.get("title", "")
        job_readiness = calculate_job_readiness(user_skills, job_reqs, job_title)
        match_score = float(job.get("match_score", 50.0))
        priority = classify_opportunity(match_score, job_readiness)

        effective_reqs = job_reqs if job_reqs else _infer_skills_from_title(job_title)
        matched, missing = _fuzzy_skill_match(user_skills, effective_reqs)

        job_context.append({
            "job_id": job.get("id"),
            "title": job_title,
            "company": job.get("company"),
            "deterministic_match_score": match_score,
            "deterministic_readiness_score": job_readiness,
            "assigned_priority": priority,
            "required_skills": list(job_reqs),
            "matched_skills": matched,
            "missing_skills": missing,
        })

    # Sanitize inputs for prompt
    sanitized_profile = {
        k: v for k, v in user_profile.items()
        if k not in ["password", "secrets", "api_keys", "social_security"]
    }
    truncated_resume = resume_text[:3000] if resume_text else None

    prompt_payload = {
        "user_profile": sanitized_profile,
        "user_skills": sorted(user_skills),
        "resume_snippet": truncated_resume,
        "target_role": target_role,
        "overall_readiness": overall_readiness,
        "production_experience_signals": prod_signals,
        "project_quality_signals": project_signals,
        "pre_analyzed_jobs": job_context,
        "roadmap_context": roadmap_context,
    }

    schema_json = json.dumps(ApplicationStrategyResponse.model_json_schema(), indent=2)
    # ISSUE 4, 8, 9: Enhanced AI prompt for recruiter-grade output
    system_prompt = (
        "You are an elite Career Strategist, Senior Hiring Manager, and Technical Career Coach at JobSeek. "
        "You have 15+ years of experience in technical recruiting and career coaching.\n\n"
        "Your objective is to produce a HIGHLY PERSONALIZED, EVIDENCE-BASED application strategy.\n\n"
        "CRITICAL INSTRUCTIONS:\n"
        "1. Do NOT invent new jobs; strictly use the `pre_analyzed_jobs` provided.\n"
        "2. You MUST use the provided deterministic scores (`deterministic_match_score`, `deterministic_readiness_score`) "
        "and `assigned_priority` EXACTLY as given. Do NOT recalculate or override them.\n"
        "3. For `why_recommended`: Reference SPECIFIC skills, projects, and experience from the user's resume. "
        "Never write generic text like 'You are a strong fit.' Instead write evidence like "
        "'Your Django backend experience with production debugging and Redis caching directly aligns with this role.'\n"
        "4. For `skill_gaps`: Only list TRULY missing skills. If the user has related experience "
        "(e.g., AI agent development counts toward LLM/GenAI requirements), acknowledge partial coverage and "
        "suggest SPECIFIC advanced gaps (e.g., 'RAG architectures', 'vector databases', 'LLMOps') rather than broad categories.\n"
        "5. For `required_next_steps`: Be HIGHLY SPECIFIC and actionable. Instead of 'Learn AI', write "
        "'Build a RAG-powered chatbot using LangChain and PostgreSQL within 4 weeks.'\n"
        "6. For `strategic_advice`: Provide recruiter-level observations based on resume evidence. "
        "Example: 'Your combination of production backend work and AI integration is uncommon among early-career "
        "candidates -- emphasize this in every application.'\n"
        "7. For `career_summary`: Write a recruiter's assessment of the candidate, referencing specific strengths.\n"
        "8. For `application_strategy` phases: Include concrete, time-bound actions with specific technologies and projects.\n"
        f"9. Output a JSON object matching this schema:\n{schema_json}"
    )

    try:
        response = generate_chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": (
                    "Generate a comprehensive, recruiter-grade application strategy "
                    "based on this context:\n"
                    f"{json.dumps(prompt_payload)}"
                )},
            ],
            temperature=0.25,
            max_tokens=3000,
            response_format={"type": "json_object"},
        )

        raw_content = response.choices[0].message.content.strip()
        parsed_dict = json.loads(raw_content)
        return ApplicationStrategyResponse.model_validate(parsed_dict)

    except Exception as e:
        logger.error("AI strategy generation failed: %s", str(e))
        raise e

# ==============================================================================
# MAIN EXPORTED FUNCTION
# ==============================================================================

def generate_application_strategy(
    user_profile: dict,
    resume_text: Optional[str] = None,
    recommended_jobs: Optional[list] = None,
    roadmap_context: Optional[str] = None,
    target_role: Optional[str] = None,
) -> ApplicationStrategyResponse:
    """
    Analyzes the user's profile, resume, and job opportunities to generate
    a personalized strategic application plan.
    """
    logger.info("Initiating application strategy generation engine.")

    # 1. Input Validation & Defaults
    if not isinstance(user_profile, dict):
        user_profile = {}

    resolved_target_role = target_role or user_profile.get("target_role", "Your Ideal Role")
    safe_recommended_jobs = recommended_jobs if isinstance(recommended_jobs, list) else []

    try:
        # 2. Deterministic Scoring
        overall_readiness = calculate_readiness_score(user_profile, resume_text)
        logger.info("Calculated overall deterministic readiness score: %.1f", overall_readiness)

        # 3. AI Generation Strategy
        try:
            logger.info("Attempting to generate strategy via AI...")
            strategy_response = generate_strategy_with_ai(
                user_profile=user_profile,
                resume_text=resume_text,
                recommended_jobs=safe_recommended_jobs,
                roadmap_context=roadmap_context,
                target_role=resolved_target_role,
                overall_readiness=overall_readiness,
            )
            logger.info("AI application strategy generated successfully.")
            return strategy_response

        except Exception as ai_error:
            logger.warning(
                "Falling back to deterministic strategy engine due to AI failure: %s",
                str(ai_error),
            )
            return generate_fallback_strategy(
                user_profile=user_profile,
                recommended_jobs=safe_recommended_jobs,
                readiness=overall_readiness,
                target_role=resolved_target_role,
                resume_text=resume_text,
            )

    except Exception as e:
        logger.error("Critical error in generate_application_strategy core execution: %s", str(e))
        # Ultimate fail-safe to prevent application crash
        return ApplicationStrategyResponse(
            target_role=resolved_target_role,
            career_summary="We encountered an unexpected issue analyzing your full profile, but your career journey continues.",
            overall_readiness_score=0.0,
            strongest_opportunities=[],
            stretch_opportunities=[],
            jobs_to_delay=[],
            application_strategy=[],
            strategic_advice=["Keep your resume updated", "Focus on consistent learning and networking"],
            final_recommendation="Please try generating your strategy again later.",
        )

# ==============================================================================
# PRESENTATION FORMATTER
# ==============================================================================

def format_application_strategy(strategy: ApplicationStrategyResponse) -> str:
    """
    Formats the ApplicationStrategyResponse object into beautiful, conversational markdown
    ready for presentation by the SeekBot AI chat UI.
    """
    output = []

    # Header & Readiness Overview
    role_header = f" for {strategy.target_role}" if strategy.target_role else ""
    output.append(f"## Your Application Strategy{role_header}")
    output.append(f"**Overall Readiness Score:** `{strategy.overall_readiness_score}/100`")
    output.append(f"> _{strategy.career_summary}_\n")

    # Strong Opportunities (Apply Now)
    if strategy.strongest_opportunities:
        output.append("### High-Priority Applications")
        output.append("*(Jobs you should apply for immediately)*\n")
        for job in strategy.strongest_opportunities:
            output.append(f"#### **{job.title}** @ {job.company or 'Confidential'}")
            output.append(f"- **Match:** {job.match_score}% | **Readiness:** {job.readiness_score}%")
            output.append(f"- **Why You're a Fit:** {job.why_recommended}")
            if job.strengths_for_role:
                output.append(f"- **Your Strengths:** {', '.join(job.strengths_for_role[:5])}")
            if job.skill_gaps:
                gaps_text = ", ".join(g.skill for g in job.skill_gaps[:3])
                output.append(f"- **Minor Gaps:** {gaps_text}")
            if job.required_next_steps:
                output.append(f"- **Next Step:** {job.required_next_steps[0]}")
            output.append("")

    # Stretch Opportunities
    if strategy.stretch_opportunities:
        output.append("### Stretch Opportunities")
        output.append("*(Great jobs that require targeted preparation)*\n")
        for job in strategy.stretch_opportunities:
            output.append(f"#### **{job.title}** @ {job.company or 'Confidential'}")
            output.append(f"- **Match:** {job.match_score}% | **Readiness:** {job.readiness_score}%")
            if job.skill_gaps:
                for gap in job.skill_gaps[:3]:
                    output.append(f"- **Gap ({gap.severity}):** {gap.skill} -- {gap.recommendation}")
            if job.required_next_steps:
                output.append(f"- **Action:** {job.required_next_steps[0]}")
            output.append("")

    # Jobs to Delay
    if strategy.jobs_to_delay:
        output.append("### Hold Off For Now")
        output.append("*(Revisit after targeted upskilling)*\n")
        for job in strategy.jobs_to_delay:
            output.append(f"- **{job.title}** @ {job.company or 'Confidential'} (Readiness: {job.readiness_score}%)")
        output.append("")

    # Execution Phases
    if strategy.application_strategy:
        output.append("### Your Execution Plan")
        for phase in strategy.application_strategy:
            output.append(f"#### {phase.phase_name} -- _{phase.duration}_")
            output.append(f"**Goal:** {phase.goal}")
            for action in phase.actions:
                output.append(f"- [ ] {action}")
            output.append("")

    # Final Advice & Recommendation
    if strategy.strategic_advice:
        output.append("### Recruiter Insights")
        for advice in strategy.strategic_advice:
            output.append(f"- {advice}")
        output.append("")

    output.append("---")
    output.append(f"**Final Verdict:** {strategy.final_recommendation}")

    return "\n".join(output)
