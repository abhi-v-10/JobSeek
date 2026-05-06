"""
Resume Intelligence Tool for SeekBot.

Fetches the user's parsed resume text from Django, sends it to OpenAI
for structured career analysis, and returns actionable insights.

Architecture:
    FastAPI (this tool) → Django API (resume text) → OpenAI (analysis)
    FastAPI never touches the DB directly.
"""

import logging

from openai import OpenAI

from app.core.config import OPENAI_API_KEY
from app.services.django_service import fetch_user_resume

logger = logging.getLogger(__name__)

client = OpenAI(api_key=OPENAI_API_KEY)


# ---------------------------------------------------------------------------
# System prompt for resume analysis
# ---------------------------------------------------------------------------

RESUME_ANALYSIS_PROMPT = """
You are SeekBot, an elite AI Career Strategist. 

Your goal is to provide a sharp, compact, and high-impact analysis of the user's resume or provided document. 

Speak directly to the user. Keep paragraphs short (max 2-3 lines). Focus on "Job Readiness."

Structure your response exactly like this:

**1. The Verdict**
A 2-line high-level summary of who they are and their current market "heat" level.

**2. Tech Stack Extraction**
- **Core**: List primary languages/frameworks found.
- **Tools**: List dev tools/databases found.

**3. Project Impact**
- **[Project Name]**: 1-line summary of the "What" and "Result." (Limit to top 2).

**4. Job-Ready Checklist (CRITICAL)**
- Provide 3-4 specific, blunt improvements needed to make the profile "Job Ready."

**5. Market Level**
- **Level**: [Junior/Mid/Senior]
- **Verdict**: 1-line on why.

RULES:
- Be punchy. Use short sentences.
- NO HASHTAGS (#). Use **bold text** for all headers.
- Use `inline code` for technologies.
- Do not stop mid-sentence. Ensure the analysis is complete and conclusive.
- If the user provides an image or document, analyze it in the context of their career.
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


def analyze_resume(resume_text: str) -> str:
    """
    Send the resume text to OpenAI for structured career analysis.

    Args:
        resume_text: Plaintext content of the user's resume.

    Returns:
        Formatted analysis string ready for chat display.
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": RESUME_ANALYSIS_PROMPT},
                {
                    "role": "user",
                    "content": f"Here is the candidate's resume:\n\n{resume_text}",
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


def run(auth_token: str = None) -> str:
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
    analysis = analyze_resume(resume_text)

    return analysis
