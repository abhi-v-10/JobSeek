"""
Resume Intelligence Tool for SeekBot.

Fetches the user's parsed resume text from Django, sends it to OpenAI
for structured career analysis, and returns actionable insights.

Architecture:
    FastAPI (this tool) → Django API (resume text) → OpenAI (analysis)
    FastAPI never touches the DB directly.
"""

import logging

# from openai import OpenAI
from app.core.openai_client import generate_chat_completion

# from app.core.config import OPENAI_API_KEY
from app.services.django_service import fetch_user_resume

logger = logging.getLogger(__name__)

# client = OpenAI(api_key=OPENAI_API_KEY)
# client = InferenceClient(provider="hf-inference", api_key=HF_TOKEN)


# ---------------------------------------------------------------------------
# System prompt for resume analysis
# ---------------------------------------------------------------------------

RESUME_ANALYSIS_PROMPT = """
You are SeekBot, a modern AI career mentor for JobSeek.
You will be provided with the user's resume and their message.

If the user is asking for a general resume review or analysis, provide it using this exact structure (no headings):
1) Short conversational opening (1-2 lines).
2) Best-fit roles (2-4 roles).
3) Strengths (2-4 bullets).
4) Missing or improvable areas (2-4 bullets).
5) Next skills or projects (2-4 bullets).
6) Short final recommendation (1 line).

Formatting rules for general review:
- Plain text only. No markdown headings, no numbered headings, no emojis.
- Use short bullets for lists.
- Use direct second-person language ("you", "your").
- Keep tech names in plain text (no inline code formatting).

HOWEVER, if the user asks a specific question (e.g., "what projects do I have?", "do I know python?"), DO NOT provide the general analysis. Instead, just answer their specific question directly based on their resume. Keep it concise, conversational, and helpful.
"""


# ---------------------------------------------------------------------------
# Step 1 — Fetch resume from Django
# ---------------------------------------------------------------------------


def fetch_resume(auth_token: str = None) -> dict:
    """
    Call the Django API to get the user's parsed resume text.

    Args:
        auth_token: Bearer token forwarded from the user's request.

    Returns:
        Dict with 'success', 'resume_text', etc.
    """
    try:
        data = fetch_user_resume(auth_token=auth_token)
        return data
    except RuntimeError as exc:
        logger.error("Failed to fetch resume: %s", exc)
        return {
            "success": False,
            "message": "Could not connect to the resume service. Please try again later.",
        }
    except Exception as exc:
        logger.error("Unexpected error fetching resume: %s", exc)
        return {
            "success": False,
            "message": "Something went wrong while fetching your resume.",
        }


# ---------------------------------------------------------------------------
# Step 2 — Analyze resume with OpenAI
# ---------------------------------------------------------------------------


def analyze_resume(resume_text: str, user_message: str = None) -> str:
    """
    Send the resume text and user message to AI for analysis or Q&A.

    Args:
        resume_text: Plaintext content of the user's resume.
        user_message: The query the user asked.

    Returns:
        Formatted analysis string ready for chat display.
    """
    
    user_query = user_message or "Please analyze my resume."
    
    try:
        response = generate_chat_completion(
            messages=[
                {"role": "system", "content": RESUME_ANALYSIS_PROMPT},
                {
                    "role": "user",
                    "content": f"Here is the candidate's resume:\n\n{resume_text}\n\nUser Message: {user_query}",
                },
            ],
            temperature=0.3,
            max_tokens=1200,
        )
        return response.choices[0].message.content.strip()
    except Exception as exc:
        logger.error("OpenAI resume analysis failed: %s", exc)
        return (
            "I wasn't able to analyze your resume right now. "
            "Please try again in a moment."
        )


# ---------------------------------------------------------------------------
# Step 3 — Main entry point
# ---------------------------------------------------------------------------


def run(message: str = None, auth_token: str = None) -> str:
    """
    Main entry point for the resume analysis tool.

    Flow:
        1. Fetch parsed resume text from Django
        2. Validate resume exists and has content
        3. Analyze with OpenAI
        4. Return structured insights

    Args:
        auth_token: User's Bearer token for Django API auth.

    Returns:
        Formatted string with career insights or an error message.
    """
    # Step 1 — Fetch
    resume_data = fetch_resume(auth_token=auth_token)

    if not resume_data.get("success"):
        message = resume_data.get("message", "No resume found.")
        return (
            f"{message}\n\n"
            "To get a resume analysis, please upload your resume first "
            "from the Resume page."
        )

    # Step 2 — Validate
    resume_text = resume_data.get("resume_text", "").strip()

    if not resume_text:
        return (
            "Your resume file is uploaded but I couldn't extract any text from it. "
            "Please make sure your resume is a text-based PDF (not a scanned image) "
            "and try re-uploading."
        )

    # Step 3 — Analyze
    analysis = analyze_resume(resume_text, user_message=message)

    return analysis
