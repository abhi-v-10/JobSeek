"""
SeekBot's conversational voice.

SeekBot talks TO the user, never ABOUT them. A reply should read like a
trusted mentor, not a recruiter report, an ATS printout, or a resume parser.

This module holds two things:

    1. VOICE_RULES — a prompt fragment every generative tool appends, so the
       instruction lives in one place instead of drifting across prompts.
    2. A deterministic leak guard — because prompt instructions alone are not
       reliable. Models slip back into third person ("Abhishyanth Vemula is a
       Computer Science student...") especially when the payload contains the
       user's name. The guard catches that after generation and repairs or
       replaces it, so a prompt regression can never reach the user.
"""

from __future__ import annotations

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Prompt fragment
# ---------------------------------------------------------------------------

VOICE_RULES: str = """
VOICE — non-negotiable:
- Write in SECOND PERSON. Address the user directly as "you"/"your".
- NEVER refer to the user by name, as "the candidate", "the user", "this applicant",
  or with he/she/they. You are speaking to them, not writing about them.
  WRONG: "Abhishyanth is a CS student with strong Django experience."
  RIGHT: "You've got strong Django experience."
- Sound like an experienced mentor talking to a junior engineer — warm, direct,
  concrete. Not a recruiter report, ATS analysis, or database summary.
- Never state a score or verdict without the reason behind it. Every number must
  feel earned: "around 82%, because you already have Django, REST APIs and
  production experience" — not "Readiness: 82%".
- Only name a gap the user genuinely lacks. If their resume already shows related
  work, do not recommend it. Recommending "learn GenAI" to someone who shipped a
  Gemini integration destroys trust.
- Be encouraging but honest. No "you're perfect", no "you have no chance".
- Prefer actions over observations. Not "You have Django" but "Lead with your
  Django work — it's your strongest asset for these roles."
"""


# ---------------------------------------------------------------------------
# Third-person leak detection
# ---------------------------------------------------------------------------

_THIRD_PERSON_MARKERS = re.compile(
    r"\b(the candidate|this candidate|the applicant|this applicant|the user|"
    r"his|her|hers|he's|she's|he is|she is|they are a|their experience|"
    r"their resume|their profile|their background)\b",
    re.IGNORECASE,
)

# "Name is a ...", "Name has ...", "Name demonstrates ..." — the classic
# resume-report opener.
_NAME_SUBJECT_RE_TEMPLATE = r"\b{name}\b\s+(is|was|has|have|holds|brings|demonstrates|possesses|shows)\b"


def _name_variants(full_name: Optional[str]) -> list[str]:
    """Full name plus individual name parts, longest first."""
    if not full_name or not isinstance(full_name, str):
        return []
    cleaned = full_name.strip()
    if not cleaned:
        return []
    parts = [p for p in re.split(r"\s+", cleaned) if len(p) > 2]
    variants = [cleaned] + parts
    # Longest first so "Abhishyanth Vemula" is matched before "Abhishyanth".
    return sorted({v for v in variants if v}, key=len, reverse=True)


def has_third_person_leak(text: str, user_name: Optional[str] = None) -> bool:
    """
    Detect whether generated text talks ABOUT the user instead of TO them.

    Args:
        text: The generated text to inspect.
        user_name: The user's name, if known — its presence as a sentence
            subject is the strongest signal of report voice.

    Returns:
        True if the text reads as third-person narration.
    """
    if not text or not isinstance(text, str):
        return False

    if _THIRD_PERSON_MARKERS.search(text):
        return True

    for variant in _name_variants(user_name):
        if re.search(_NAME_SUBJECT_RE_TEMPLATE.format(name=re.escape(variant)), text, re.IGNORECASE):
            return True
        # A bare name mention at the start of the text is also report voice.
        if re.match(rf"^\W*{re.escape(variant)}\b", text, re.IGNORECASE):
            return True

    return False


def strip_third_person(text: str, user_name: Optional[str] = None) -> str:
    """
    Best-effort rewrite of third-person narration into second person.

    Handles the common mechanical cases (name-as-subject, possessives,
    "the candidate"). This is a repair pass, not a rewriter — callers should
    use `has_third_person_leak` to decide whether a deterministic replacement
    is safer than a repair.
    """
    if not text:
        return text

    result = text

    for variant in _name_variants(user_name):
        pattern = re.escape(variant)
        result = re.sub(rf"\b{pattern}'s\b", "your", result, flags=re.IGNORECASE)
        result = re.sub(rf"\b{pattern}\b\s+(is|was)\b", "you are", result, flags=re.IGNORECASE)
        result = re.sub(rf"\b{pattern}\b\s+(has|have)\b", "you have", result, flags=re.IGNORECASE)
        result = re.sub(rf"\b{pattern}\b", "you", result, flags=re.IGNORECASE)

    replacements = [
        (r"\b(the|this) candidate's\b", "your"),
        (r"\b(the|this) applicant's\b", "your"),
        (r"\b(the|this) user's\b", "your"),
        (r"\b(the|this) candidate\b", "you"),
        (r"\b(the|this) applicant\b", "you"),
        (r"\b(the|this) user\b", "you"),
        (r"\btheir (experience|resume|profile|background|skills|work)\b", r"your \1"),
        (r"\bhis or her\b", "your"),
        (r"\b(his|her)\s+(?=\w)", "your "),
        # Subject / object pronouns. Only reached once a leak is confirmed, so
        # these are safe here even though they'd be too aggressive in detection
        # (a legitimate reply can say "I'll add them to your profile").
        (r"\b(he|she)\s+(is|was)\b", "you are"),
        (r"\b(he|she)\s+(has|have)\b", "you have"),
        (r"\b(he|she)\b", "you"),
        (r"\b(him|himself|herself)\b", "you"),
    ]
    for pattern, replacement in replacements:
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)

    # Tidy up grammar the substitutions can break.
    result = re.sub(r"\byou is\b", "you are", result, flags=re.IGNORECASE)
    result = re.sub(r"\byou has\b", "you have", result, flags=re.IGNORECASE)
    result = re.sub(r"\byour\s+your\b", "your", result, flags=re.IGNORECASE)
    result = re.sub(r"\s+([,.;:])", r"\1", result)
    result = re.sub(r"\s{2,}", " ", result).strip()

    # Re-capitalise sentence starts that a substitution lowercased.
    result = re.sub(
        r"(^|[.!?]\s+)([a-z])",
        lambda m: m.group(1) + m.group(2).upper(),
        result,
    )

    return result


def enforce_second_person(
    text: str,
    user_name: Optional[str] = None,
    fallback: Optional[str] = None,
) -> str:
    """
    Guarantee user-facing text is in second person.

    Repairs the text if it leaks third person; if a repair still leaks (or a
    caller-supplied `fallback` is preferred), returns the fallback instead.

    Args:
        text: Generated text.
        user_name: The user's name, if known.
        fallback: Deterministic replacement used when repair fails.

    Returns:
        Text safe to show the user.
    """
    if not text:
        return fallback or ""

    if not has_third_person_leak(text, user_name):
        return text

    logger.info("Third-person leak detected in generated copy — repairing")
    repaired = strip_third_person(text, user_name)

    if has_third_person_leak(repaired, user_name):
        logger.warning("Third-person repair incomplete — using deterministic fallback")
        return fallback or repaired

    return repaired
