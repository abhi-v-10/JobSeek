from typing import Optional

from app.core.ai_logger import log_agent_response, log_tool_call, log_user_message
from app.schemas.chat import AgentMessage, ChatResponse
from app.services.django_service import (
    fetch_user_profile,
    get_session_messages,
    save_message,
)
from app.services.intent_service import detect_intent
from app.services.openai_service import ask_ai, generate_chat_title
from app.tools import job_tool, resume_tool
from app.tools.personalized_job_recommender import recommend_jobs_for_user
from app.utils.file_parser import encode_image, extract_text_from_file
from fastapi import APIRouter, File, Form, Header, UploadFile

router = APIRouter()


# ---------------------------------------------------------------------------
# Title generation
# ---------------------------------------------------------------------------


@router.post("/title")
def get_title(payload: dict):
    """Generate a short title for a new chat session."""
    message = payload.get("message", "")
    title = generate_chat_title(message)
    return {"title": title}


# ---------------------------------------------------------------------------
# Main chat endpoint
# ---------------------------------------------------------------------------


@router.post("/", response_model=ChatResponse)
async def chat(
    session_id: str = Form(...),
    message: str = Form(...),
    file: Optional[UploadFile] = File(None),
    authorization: str = Header(None),
):
    """
    Handle a chat turn:
      1. Persist user message to Django.
      2. Detect intent.
      3. Dispatch to the correct tool or fallback to general AI.
      4. Persist and return the agent reply.

    All steps are logged to logs/ai.log.
    """

    # ── Log the incoming user message ────────────────────────────────────────
    log_user_message(session_id, message)

    # ── Parse any attached file ───────────────────────────────────────────────
    file_context: Optional[str] = None
    image_base64: Optional[str] = None

    if file:
        content = await file.read()
        ext = (file.filename or "").lower().split(".")[-1]
        if ext in ("jpg", "jpeg", "png", "webp"):
            image_base64 = encode_image(content)
        else:
            file_context = extract_text_from_file(content, file.filename)

    # ── Persist user message ──────────────────────────────────────────────────
    save_message(
        session_id=session_id,
        role="user",
        content=message,
        auth_token=authorization,
    )

    # ── Load conversation history ─────────────────────────────────────────────
    history_response = get_session_messages(session_id, auth_token=authorization)
    history = history_response.get("data", [])

    # ── Detect intent ─────────────────────────────────────────────────────────
    intent = detect_intent(message)

    # ── Dispatch ──────────────────────────────────────────────────────────────
    ai_reply: str = ""
    message_type: str = "text"
    job_data: Optional[list] = None

    if intent == "job_recommendation":
        ai_reply, message_type, job_data = _handle_job_recommendation(
            session_id=session_id,
            message=message,
            authorization=authorization,
        )

    elif intent == "job_search":
        log_tool_call(session_id, "job_search", f'query="{message[:60]}"')
        ai_reply, raw_jobs = job_tool.run_with_data(message)
        message_type = "jobs"
        job_data = raw_jobs or None

    elif intent == "resume_review":
        log_tool_call(session_id, "resume_review")
        ai_reply = resume_tool.run(auth_token=authorization)
        message_type = "resume_feedback"

    else:
        log_tool_call(session_id, "general_ai", f"intent={intent}")
        ai_reply = ask_ai(
            message,
            history,
            file_context=file_context,
            image_base64=image_base64,
        )
        message_type = "text"

    # ── Log the agent response ────────────────────────────────────────────────
    log_agent_response(session_id, message_type, ai_reply)

    # ── Persist agent reply ───────────────────────────────────────────────────
    save_message(
        session_id=session_id,
        role="assistant",
        content=ai_reply,
        message_type=message_type,
        metadata={"jobs": job_data} if job_data else {},
        auth_token=authorization,
    )

    return ChatResponse(
        success=True,
        session_id=session_id,
        message=AgentMessage(
            type=message_type,
            content=ai_reply,
            data=job_data,
        ),
    )


# ---------------------------------------------------------------------------
# Job recommendation handler
# ---------------------------------------------------------------------------


def _handle_job_recommendation(
    session_id: str,
    message: str,
    authorization: Optional[str],
) -> tuple[str, str, Optional[list]]:
    """
    Fetch the user's profile, run the personalized job recommender, and
    return (text_reply, message_type, job_data).

    Falls back to the general job_search tool if the recommender produces
    no results (e.g., the user has no profile data yet).

    Returns:
        (ai_reply: str, message_type: str, job_data: list | None)
    """
    # ── Fetch user profile (best-effort) ────────────────────────────────────
    user_profile: dict = {}
    if authorization:
        try:
            user_profile = fetch_user_profile(auth_token=authorization) or {}
        except Exception:
            pass  # Proceed with empty profile — recommender handles it gracefully

    skill_count = len(user_profile.get("skills") or [])
    log_tool_call(
        session_id,
        "job_recommender",
        f"skills={skill_count} has_resume={'yes' if user_profile.get('resume_text') else 'no'}",
    )

    # ── Run recommender ───────────────────────────────────────────────────────
    recommendations = recommend_jobs_for_user(
        user_profile=user_profile,
        resume_text=user_profile.get("resume_text"),
        user_query=message,
        limit=10,
    )

    # ── No matches — fall back to a plain job search ─────────────────────────
    if not recommendations.recommended_jobs:
        log_tool_call(session_id, "job_search", "fallback — no recommendations found")
        fallback_text, fallback_jobs = job_tool.run_with_data(message)
        # Prepend the recommender's helpful summary so the user knows why
        full_text = (
            f"{recommendations.summary}\n\n{fallback_text}"
            if fallback_text
            else recommendations.summary
        )
        return full_text, "jobs", fallback_jobs or None

    # ── Build the text reply ─────────────────────────────────────────────────
    text_lines: list[str] = [recommendations.summary]

    if recommendations.strategic_advice:
        text_lines.append("")
        for tip in recommendations.strategic_advice[:3]:
            text_lines.append(f"• {tip}")

    ai_reply = "\n".join(text_lines)

    # ── Map RecommendedJob → JobSearchResult format for the frontend ─────────
    job_data = [
        {
            "id": job.job_id,
            "title": job.title,
            "company_name": job.company,
            "location": job.location,
            "is_remote": job.is_remote,
            "job_type": "corporate",
            "skills": (", ".join(job.matching_skills + job.missing_skills) or None),
            "created_at": job.created_at,
        }
        for job in recommendations.recommended_jobs
    ]

    return ai_reply, "jobs", job_data
