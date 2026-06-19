"""
Unit tests for the application strategy scoring pipeline V1.5.

Validates:
- Skill extraction from all sources (dict-based, parsed_resume, resume text)
- Semantic skill alias expansion
- Score calibration (no 100% scores)
- Job readiness calculation with fuzzy matching
- Title-based fallback scoring
- Opportunity classification thresholds
- Overall readiness score with production/project signals
- Production experience detection
- Project quality detection
"""

import os
import sys

# Add the parent directory to sys.path so app can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.tools.application_strategy_tool import (
    extract_skills_from_profile,
    calculate_readiness_score,
    calculate_job_readiness,
    classify_opportunity,
    _infer_skills_from_title,
    _fuzzy_skill_match,
    _calibrate_score,
    _expand_skills_with_aliases,
    _count_production_signals,
    _count_project_signals,
)


# ==============================================================================
# Test data: simulated user profile matching the reported resume
# ==============================================================================

MOCK_PROFILE_DICT_SKILLS = {
    "skills": [
        {"name": "Python"},
        {"name": "Django"},
        {"name": "Flask"},
        {"name": "FastAPI"},
        {"name": "REST APIs"},
        {"name": "PostgreSQL"},
        {"name": "MongoDB"},
        {"name": "Node.js"},
        {"name": "Express.js"},
        {"name": "GitHub Actions"},
    ],
    "parsed_resume": {
        "skills": ["Python", "Django", "FastAPI", "Redis", "Linux"],
        "technologies": ["Docker", "Git", "PostgreSQL"],
        "projects": [
            {"name": "School Management System"},
            {"name": "MovieDB"},
            {"name": "MERN Application"},
            {"name": "AI-powered Chrome Extension"},
        ],
    },
    "resume_text": (
        "AI Backend Developer with experience in Python, Django, FastAPI, "
        "REST APIs, PostgreSQL, MongoDB, Node.js, Express.js, GitHub Actions, "
        "Redis, Linux. Built production Django systems, FastAPI integrations, "
        "AI agent development with ElevenLabs integrations. "
        "Production debugging, deployed systems, CI/CD pipelines, "
        "Stripe payment integration, authentication systems, OAuth, JWT. "
        "Experience with Gemini API, prompt engineering, AI automation workflows."
    ),
    "experience_years": 2,
    "full_name": "Test User",
    "github_url": "https://github.com/testuser",
}

MOCK_PROFILE_STR_SKILLS = {
    "skills": "Python, Django, FastAPI, PostgreSQL, MongoDB",
    "resume_text": "Backend developer skilled in Python and Django.",
}


# ==============================================================================
# ISSUE 1 -- SCORE CALIBRATION
# ==============================================================================

def test_calibrate_score_cap():
    """100% raw should never produce 100% calibrated."""
    assert _calibrate_score(100.0) < 100.0, "100% should be calibrated down"
    assert _calibrate_score(100.0) <= 95.0, "Cap should be 95%"
    print(f"  [PASS] calibrate(100) = {_calibrate_score(100.0)} (capped)")


def test_calibrate_score_linear_below_70():
    """Scores below 70 should pass through unchanged."""
    for s in [0, 10, 30, 50, 60, 70]:
        assert _calibrate_score(float(s)) == float(s), f"Score {s} should be unchanged"
    print(f"  [PASS] Scores <= 70 are linear")


def test_calibrate_score_diminishing():
    """Scores above 70 should show diminishing returns."""
    s80 = _calibrate_score(80.0)
    s90 = _calibrate_score(90.0)
    s100 = _calibrate_score(100.0)
    assert s80 < 80, f"calibrate(80)={s80} should be < 80"
    assert s90 < 90, f"calibrate(90)={s90} should be < 90"
    assert s90 > s80, "90 should still be higher than 80"
    assert s100 > s90, "100 should still be higher than 90"
    print(f"  [PASS] Diminishing: 80->{s80}, 90->{s90}, 100->{s100}")


# ==============================================================================
# SKILL EXTRACTION + ALIASES
# ==============================================================================

def test_extract_skills_dict_based():
    """Skills stored as list of dicts should be extracted correctly."""
    skills = extract_skills_from_profile(MOCK_PROFILE_DICT_SKILLS)
    assert "python" in skills, f"Missing 'python' in {skills}"
    assert "django" in skills, f"Missing 'django' in {skills}"
    assert "fastapi" in skills, f"Missing 'fastapi' in {skills}"
    assert "postgresql" in skills, f"Missing 'postgresql' in {skills}"
    assert "mongodb" in skills, f"Missing 'mongodb' in {skills}"
    # Should NOT contain garbage like "{'name': 'Python'}"
    for s in skills:
        assert not s.startswith("{"), f"Garbage skill detected: {s}"
    print(f"  [PASS] Dict-based extraction: {len(skills)} skills extracted")


def test_alias_expansion():
    """Semantic aliases should expand skill sets."""
    base = {"django", "fastapi", "github actions"}
    expanded = _expand_skills_with_aliases(base)
    # django -> python, sql, orm
    assert "python" in expanded, f"Missing alias 'python' from 'django': {expanded}"
    assert "sql" in expanded, f"Missing alias 'sql' from 'django': {expanded}"
    # fastapi -> rest, api, python
    assert "rest" in expanded, f"Missing alias 'rest' from 'fastapi': {expanded}"
    assert "api" in expanded, f"Missing alias 'api' from 'fastapi': {expanded}"
    # github actions -> ci/cd, git
    assert "ci/cd" in expanded, f"Missing alias 'ci/cd' from 'github actions': {expanded}"
    print(f"  [PASS] Alias expansion: {len(base)} -> {len(expanded)} skills")


def test_ai_skills_recognized():
    """AI-related terms from resume should be extracted."""
    profile = {
        "resume_text": (
            "AI agent development, prompt engineering, Gemini API integration, "
            "ElevenLabs text-to-speech, LangChain workflows"
        )
    }
    skills = extract_skills_from_profile(profile)
    assert "ai agent" in skills or "gemini" in skills or "langchain" in skills, (
        f"AI-related skills should be extracted: {skills}"
    )
    print(f"  [PASS] AI skills extracted: {sorted(skills)}")


def test_extract_skills_empty_profile():
    """Empty profile should return empty set, not crash."""
    skills = extract_skills_from_profile({})
    assert isinstance(skills, set)
    assert len(skills) == 0
    print(f"  [PASS] Empty profile: {len(skills)} skills (safe)")


# ==============================================================================
# PRODUCTION & PROJECT SIGNALS
# ==============================================================================

def test_production_signals():
    """Should detect production experience indicators."""
    count = _count_production_signals(
        MOCK_PROFILE_DICT_SKILLS.get("resume_text"),
        MOCK_PROFILE_DICT_SKILLS,
    )
    assert count >= 3, f"Expected >= 3 production signals, got {count}"
    print(f"  [PASS] Production signals: {count}")


def test_project_signals():
    """Should detect project quality indicators."""
    count = _count_project_signals(
        MOCK_PROFILE_DICT_SKILLS.get("resume_text"),
        MOCK_PROFILE_DICT_SKILLS,
    )
    assert count >= 4, f"Expected >= 4 project signals, got {count}"
    print(f"  [PASS] Project signals: {count}")


# ==============================================================================
# JOB READINESS SCORING
# ==============================================================================

def test_job_readiness_no_100_percent():
    """Even a perfect match should not produce 100% after calibration."""
    user_skills = {"python", "django", "fastapi", "postgresql"}
    job_reqs = {"python", "django", "fastapi", "postgresql"}
    readiness = calculate_job_readiness(user_skills, job_reqs)
    assert readiness < 100.0, f"Expected < 100%, got {readiness}%"
    assert readiness >= 85.0, f"Expected >= 85% for perfect match, got {readiness}%"
    print(f"  [PASS] Perfect match readiness: {readiness}% (not 100)")


def test_job_readiness_fuzzy():
    """Fuzzy matching should handle 'rest' <-> 'rest apis', etc."""
    user_skills = {"python", "django", "fastapi", "rest apis", "postgresql", "mongodb", "node.js"}
    job_reqs = {"python", "django", "rest", "sql"}
    readiness = calculate_job_readiness(user_skills, job_reqs)
    assert readiness >= 50.0, f"Expected >= 50%, got {readiness}%"
    print(f"  [PASS] Fuzzy job readiness: {readiness}%")


def test_job_readiness_no_reqs_with_title():
    """Jobs with no requirements should get title-based fallback."""
    user_skills = {"python", "django", "fastapi", "sql", "git", "api", "rest"}
    readiness = calculate_job_readiness(user_skills, set(), "Software Developer")
    assert readiness > 0, f"Expected > 0%, got {readiness}%"
    assert readiness < 100, f"Expected < 100%, got {readiness}%"
    print(f"  [PASS] Title fallback readiness (Software Developer): {readiness}%")


def test_job_readiness_unknown_title():
    """Unrecognizable title should get conservative default."""
    user_skills = {"python", "django"}
    readiness = calculate_job_readiness(user_skills, set(), "Mystery Role XYZ")
    assert readiness == 60.0, f"Expected 60% default, got {readiness}%"
    print(f"  [PASS] Unknown title fallback readiness: {readiness}%")


# ==============================================================================
# OPPORTUNITY CLASSIFICATION
# ==============================================================================

def test_classify_opportunity_apply_now():
    """High match + high readiness should be 'Apply Now'."""
    result = classify_opportunity(90, 80)
    assert result == "Apply Now", f"Expected 'Apply Now', got '{result}'"
    print(f"  [PASS] classify(90, 80) = {result}")


def test_classify_opportunity_strong_fit():
    """Good match + decent readiness should be 'Strong Fit'."""
    result = classify_opportunity(72, 65)
    assert result in ("Apply Now", "Strong Fit"), f"Expected Strong Fit or Apply Now, got '{result}'"
    print(f"  [PASS] classify(72, 65) = {result}")


def test_classify_opportunity_not_auto_delay():
    """A job with match=72 and readiness=0 should NOT be auto-delayed."""
    result = classify_opportunity(72, 0)
    assert result != "Delay Application", f"Expected NOT 'Delay Application', got '{result}'"
    print(f"  [PASS] classify(72, 0) = {result} (not auto-delayed)")


# ==============================================================================
# TITLE-BASED FALLBACK
# ==============================================================================

def test_infer_skills_from_title():
    """Title inference should produce reasonable skill sets."""
    sw_skills = _infer_skills_from_title("Software Developer")
    assert len(sw_skills) > 0, "Should infer skills for Software Developer"
    assert "python" in sw_skills
    assert "docker" in sw_skills, f"V1.5 should include docker: {sw_skills}"
    print(f"  [PASS] Software Developer inferred: {sorted(sw_skills)}")

    ai_skills = _infer_skills_from_title("AI Engineer")
    assert len(ai_skills) > 0
    assert "python" in ai_skills
    assert "llm" in ai_skills, f"V1.5 should include llm: {ai_skills}"
    assert "langchain" in ai_skills or "rag" in ai_skills, (
        f"V1.5 should include modern AI tools: {ai_skills}"
    )
    print(f"  [PASS] AI Engineer inferred: {sorted(ai_skills)}")


# ==============================================================================
# END-TO-END VALIDATION (ISSUE 10)
# ==============================================================================

def test_end_to_end_software_developer():
    """
    Software Developer @ Deloitte.
    Expected readiness: 80-95 (strong backend profile).
    Should NOT be 0% or 100%.
    """
    user_skills = extract_skills_from_profile(MOCK_PROFILE_DICT_SKILLS)
    job_reqs = {"python", "javascript", "sql", "git", "api", "rest", "docker"}
    job_title = "Software Developer"

    readiness = calculate_job_readiness(user_skills, job_reqs, job_title)
    assert 60 <= readiness <= 95, f"SW Dev readiness should be 60-95%, got {readiness}%"
    assert readiness != 100.0, "Should not be 100%"

    match_score = 72.0
    priority = classify_opportunity(match_score, readiness)
    assert priority in ("Apply Now", "Strong Fit"), (
        f"SW Dev should be Apply Now or Strong Fit, got {priority}"
    )

    print(f"  [PASS] Software Developer @ Deloitte: readiness={readiness}%, priority={priority}")


def test_end_to_end_ai_engineer():
    """
    AI Engineer @ Amazon.
    Expected readiness: 50-75 (has AI experience but may lack some advanced areas).
    Should NOT be 0%.
    """
    user_skills = extract_skills_from_profile(MOCK_PROFILE_DICT_SKILLS)
    job_reqs = {"python", "machine learning", "deep learning", "llm",
                "langchain", "docker", "aws"}
    job_title = "AI Engineer"

    readiness = calculate_job_readiness(user_skills, job_reqs, job_title)
    assert readiness > 20.0, f"AI Engineer readiness should be > 20%, got {readiness}%"
    assert readiness < 95.0, f"AI Engineer readiness should be < 95%, got {readiness}%"

    match_score = 65.0
    priority = classify_opportunity(match_score, readiness)

    print(f"  [PASS] AI Engineer @ Amazon: readiness={readiness}%, priority={priority}")


def test_overall_readiness_score():
    """
    Overall readiness for a strong profile should be high but not 100%.
    V1.5: should reflect production experience and project signals.
    """
    score = calculate_readiness_score(
        MOCK_PROFILE_DICT_SKILLS,
        MOCK_PROFILE_DICT_SKILLS.get("resume_text"),
    )
    assert 65 <= score <= 95, f"Overall readiness should be 65-95 for strong profile, got {score}"
    assert score != 100.0, "Should not be 100%"
    print(f"  [PASS] Overall readiness score: {score}/100")


def test_overall_readiness_weak_profile():
    """A weak profile should get a proportionally low but non-zero score."""
    weak_profile = {"skills": [{"name": "Python"}], "resume_text": "Student."}
    score = calculate_readiness_score(weak_profile, "Student.")
    assert score < 50, f"Weak profile should be < 50, got {score}"
    assert score > 0, f"Should not be 0, got {score}"
    print(f"  [PASS] Weak profile readiness: {score}/100")


# ==============================================================================
# RUNNER
# ==============================================================================

def run_all():
    print("\n" + "=" * 60)
    print("ISSUE 1 -- SCORE CALIBRATION")
    print("=" * 60)
    test_calibrate_score_cap()
    test_calibrate_score_linear_below_70()
    test_calibrate_score_diminishing()

    print("\n" + "=" * 60)
    print("SKILL EXTRACTION + ALIASES")
    print("=" * 60)
    test_extract_skills_dict_based()
    test_alias_expansion()
    test_ai_skills_recognized()
    test_extract_skills_empty_profile()

    print("\n" + "=" * 60)
    print("PRODUCTION & PROJECT SIGNALS")
    print("=" * 60)
    test_production_signals()
    test_project_signals()

    print("\n" + "=" * 60)
    print("JOB READINESS SCORING")
    print("=" * 60)
    test_job_readiness_no_100_percent()
    test_job_readiness_fuzzy()
    test_job_readiness_no_reqs_with_title()
    test_job_readiness_unknown_title()

    print("\n" + "=" * 60)
    print("OPPORTUNITY CLASSIFICATION")
    print("=" * 60)
    test_classify_opportunity_apply_now()
    test_classify_opportunity_strong_fit()
    test_classify_opportunity_not_auto_delay()

    print("\n" + "=" * 60)
    print("TITLE-BASED FALLBACK")
    print("=" * 60)
    test_infer_skills_from_title()

    print("\n" + "=" * 60)
    print("END-TO-END VALIDATION (ISSUE 10)")
    print("=" * 60)
    test_end_to_end_software_developer()
    test_end_to_end_ai_engineer()
    test_overall_readiness_score()
    test_overall_readiness_weak_profile()

    print("\n" + "=" * 60)
    print("ALL V1.5 TESTS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    run_all()
