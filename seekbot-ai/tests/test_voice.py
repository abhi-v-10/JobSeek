"""
Voice and evidence-based-recommendation tests.

Plain script, matching this repo's test convention:
    python tests/test_voice.py

SeekBot talks TO the user, never ABOUT them, and never recommends a skill the
user demonstrably already has. Both rules are enforced deterministically
(prompt instructions alone are not reliable), so both are testable offline.
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.skill_utils import (  # noqa: E402
    canonical_skill_name,
    filter_demonstrated_skills,
    is_skill_demonstrated,
)
from app.core.voice import (  # noqa: E402
    VOICE_RULES,
    enforce_second_person,
    has_third_person_leak,
    strip_third_person,
)

USER = "Abhishyanth Vemula"

# The exact text SeekBot produced in the reported regression.
REPORTED_OUTPUT = (
    "Abhishyanth Vemula is a Computer Science Engineering student with strong backend "
    "development experience in Django, Flask, and REST APIs, complemented by AI integration "
    "projects (FastAPI, ElevenLabs, Gemini). His production-grade work at Nestafar, coupled "
    "with full-stack projects, positions him as a competitive candidate for Python-focused roles."
)


# ---------------------------------------------------------------------------
# Third-person detection
# ---------------------------------------------------------------------------


def test_reported_regression_is_detected():
    assert has_third_person_leak(REPORTED_OUTPUT, USER) is True


def test_report_voice_markers_are_detected():
    for text in (
        "The candidate demonstrates strong backend skills.",
        "This applicant has 3 years of experience.",
        "His experience suggests a backend focus.",
        "Their resume shows Django work.",
        "Abhishyanth has strong Django experience.",
    ):
        assert has_third_person_leak(text, USER) is True, text


def test_second_person_text_is_never_flagged():
    for text in (
        "Based on your resume, you already have strong Django experience.",
        "Your backend experience makes you a strong fit.",
        "You're in a good position to apply.",
        "I found 5 skills in your resume. Reply 'yes' and I'll add them.",
        "Lead with your Django work — it's your strongest asset.",
    ):
        assert has_third_person_leak(text, USER) is False, text


def test_detection_without_a_known_name():
    """The guard still works when the profile has no name on it."""
    assert has_third_person_leak("The candidate has strong Python skills.", None) is True
    assert has_third_person_leak("You have strong Python skills.", None) is False


# ---------------------------------------------------------------------------
# Repair
# ---------------------------------------------------------------------------


def test_reported_regression_is_repaired_into_second_person():
    repaired = enforce_second_person(REPORTED_OUTPUT, USER)

    assert not has_third_person_leak(repaired, USER), repaired
    assert "Abhishyanth" not in repaired
    assert " his " not in repaired.lower()
    assert " him " not in repaired.lower()
    assert repaired.startswith("You are"), repaired
    assert "Your production-grade work" in repaired, repaired


def test_repair_fixes_grammar_and_capitalisation():
    repaired = strip_third_person("Abhishyanth is a student. His work is strong.", USER)
    assert "you are a student" in repaired.lower()
    # Sentence after the period must be re-capitalised.
    assert ". Your work" in repaired, repaired


def test_repair_leaves_clean_text_untouched():
    clean = "Your Django experience is your strongest asset."
    assert enforce_second_person(clean, USER) == clean


def test_fallback_is_used_when_repair_cannot_fix_it():
    fallback = "Here's where you stand right now."
    # "the candidate" survives no repair path that also removes the pronoun soup.
    unfixable = "The candidate's peers, their mentors, and his or her managers agree."
    result = enforce_second_person(unfixable, USER, fallback=fallback)
    assert not has_third_person_leak(result, USER), result


def test_empty_input_is_safe():
    assert enforce_second_person("", USER) == ""
    assert enforce_second_person("", USER, fallback="fb") == "fb"
    assert has_third_person_leak("", USER) is False
    assert has_third_person_leak(None, USER) is False


def test_voice_rules_are_available_to_prompts():
    assert "SECOND PERSON" in VOICE_RULES
    assert "the candidate" in VOICE_RULES.lower()


# ---------------------------------------------------------------------------
# Evidence-based gap filtering
# ---------------------------------------------------------------------------

RESUME = (
    "Built an AI chat assistant with Google Gemini and ElevenLabs voice synthesis. "
    "Django REST APIs running in production with Redis caching."
)
SKILLS = {"python", "django", "fastapi", "gemini", "elevenlabs", "react", "rest", "redis"}


def test_genai_gap_is_suppressed_when_the_user_shipped_gemini():
    """
    The reported bug: SeekBot told a user whose resume features Gemini and
    ElevenLabs integrations that their biggest gap was "Generative AI (GenAI)".
    """
    assert is_skill_demonstrated("Generative AI (GenAI)", SKILLS, RESUME) is True
    assert is_skill_demonstrated("LLM", SKILLS, RESUME) is True

    kept = filter_demonstrated_skills(
        ["Generative AI (GenAI)", "Docker", "LLM", "AWS", "Vector Databases"], SKILLS, RESUME
    )
    assert kept == ["Docker", "AWS", "Vector Databases"], kept


def test_genuinely_missing_skills_survive_the_filter():
    for skill in ("Docker", "Kubernetes", "AWS", "Terraform"):
        assert is_skill_demonstrated(skill, SKILLS, RESUME) is False, skill


def test_direct_and_alias_evidence_both_count():
    # Direct.
    assert is_skill_demonstrated("Django", SKILLS, RESUME) is True
    # Alias — django implies python/sql/orm.
    assert is_skill_demonstrated("ORM", {"django"}, None) is True
    # Resume-text evidence only.
    assert is_skill_demonstrated("Redis", set(), "Used Redis for caching.") is True


def test_filter_handles_empty_input():
    assert filter_demonstrated_skills([], SKILLS, RESUME) == []
    assert filter_demonstrated_skills(None, SKILLS, RESUME) == []
    assert is_skill_demonstrated("", SKILLS, RESUME) is False


# ---------------------------------------------------------------------------
# Display names
# ---------------------------------------------------------------------------


def test_technology_names_are_not_mangled_by_title_case():
    cases = {
        "fastapi": "FastAPI",
        "css": "CSS",
        "ci/cd": "CI/CD",
        "node.js": "Node.js",
        "postgresql": "PostgreSQL",
        "aws": "AWS",
        "rest": "REST APIs",
        "elevenlabs": "ElevenLabs",
        "javascript": "JavaScript",
    }
    for raw, expected in cases.items():
        assert canonical_skill_name(raw) == expected, f"{raw} -> {canonical_skill_name(raw)}"


def test_unknown_skills_fall_back_to_title_case():
    assert canonical_skill_name("testing") == "Testing"
    assert canonical_skill_name("") == ""


def run_tests():
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    for test in tests:
        test()
        print(f"  ok  {test.__name__}")
    print(f"\nAll {len(tests)} voice tests passed.")


if __name__ == "__main__":
    run_tests()
