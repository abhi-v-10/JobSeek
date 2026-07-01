"""
Resume text extraction utility.

Uses PyMuPDF (fitz) to extract plaintext from uploaded PDF resumes.
Falls back gracefully if the file is not a valid PDF.
"""

import logging
import re

import fitz  # PyMuPDF

logger = logging.getLogger(__name__)


def extract_resume_text(file_path: str) -> str:
    """
    Extract and clean plaintext from a PDF resume.

    Args:
        file_path: Absolute filesystem path to the PDF file.

    Returns:
        Cleaned text string extracted from the PDF.

    Raises:
        ValueError: If the file cannot be opened or contains no text.
    """
    try:
        doc = fitz.open(file_path)
    except Exception as exc:
        logger.error("Failed to open PDF: %s — %s", file_path, exc)
        raise ValueError(f"Could not open resume file: {exc}") from exc

    raw_pages: list[str] = []
    for page in doc:
        text = page.get_text("text")
        if text:
            raw_pages.append(text)
    doc.close()

    if not raw_pages:
        raise ValueError("Resume PDF contains no extractable text.")

    full_text = "\n".join(raw_pages)
    cleaned = _clean_text(full_text)

    if not cleaned.strip():
        raise ValueError("Resume text is empty after cleaning.")

    return cleaned


def _clean_text(text: str) -> str:
    """
    Remove excess whitespace, null bytes, and normalise line breaks
    while preserving paragraph structure.
    """
    # Remove null bytes
    text = text.replace("\x00", "")

    # Collapse multiple blank lines into at most two newlines
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Collapse multiple spaces/tabs into a single space per line
    text = re.sub(r"[^\S\n]+", " ", text)

    # Strip leading/trailing whitespace from each line
    lines = [line.strip() for line in text.splitlines()]
    text = "\n".join(lines)

    return text.strip()
