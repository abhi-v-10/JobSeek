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
application_strategy
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
        "application_strategy",
        "general_chat",
    }

    return result if result in allowed else "general_chat"


def detect_intent_rule(message: str) -> str | None:
    text = message.lower().strip()

    # ── Application Strategy (must come before job_recommendation) ───────────
    strategy_triggers = [
        "what jobs should i apply for first",
        "which jobs should i prioritize",
        "which opportunities should i prioritize",
        "create an application strategy",
        "am i ready to apply",
        "what should i focus on before applying",
        "what jobs should i apply to this week",
        "realistic for me",
        "what should i learn before applying",
        "application priorities",
    ]
    if any(k in text for k in strategy_triggers):
        return "application_strategy"

    # ── Job recommendation (must come before job_search) ─────────────────
    recommendation_triggers = [
        "recommend",
        "suggest job",
        "jobs for me",
        "job for me",
        "what jobs should",
        "which jobs",
        "best fit",
        "suitable for me",
        "based on my",
        "my profile",
        "match my skill",
        "personalized",
        "highest chance",
        "chance of selection",
        "best match",
        "show"
    ]
    job_context = ["job", "jobs", "role", "position", "apply", "opening"]
    if any(k in text for k in recommendation_triggers) and any(
        k in text for k in job_context
    ):
        return "job_recommendation"

    job_keywords = [
        "job",
        "jobs",
        "internship",
        "intern",
        "apply",
        "vacancy",
        "hiring",
        "opening",
        "developer role",
    ]

    resume_keywords = [
        "resume",
        "cv",
        "ats",
        "improve my resume",
        "analyze my resume",
        "review my resume",
        "review my cv",
        "resume analysis",
        "resume review",
        "resume feedback",
        "what skills do i have",
        "my skills",
        "skill analysis",
        "career analysis",
        "rate my resume",
    ]

    roadmap_keywords = ["roadmap", "how do i become", "career path", "how can i become"]

    interview_keywords = [
        "interview",
        "mock interview",
        "questions",
        "prepare me",
        "interview prep",
        "prepare for",
        "practice interview",
        "conduct a technical interview",
    ]

    market_keywords = ["trend", "trending", "market", "salary", "demand"]

    skill_keywords = ["skill", "learn", "what should i learn"]

    project_keywords = ["project", "projects", "portfolio"]

    if any(k in text for k in interview_keywords):
        return "interview_prep"

    if any(k in text for k in job_keywords):
        return "job_search"

    if any(k in text for k in resume_keywords):
        return "resume_review"

    if any(k in text for k in roadmap_keywords):
        return "career_roadmap"

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

    if ai_result == "job_recommendation":
        return "job_recommendation"

    return ai_result


INTENTS = [
    "job_recommendation",
    "job_search",
    "resume_review",
    "career_roadmap",
    "interview_prep",
    "market_insights",
    "skill_guidance",
    "project_suggestions",
    "application_strategy",
    "general_chat",
]
