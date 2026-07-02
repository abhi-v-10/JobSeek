"""
Comprehensive tests for the Resume Optimizer Tool.

Validates:
- Deterministic ATS scoring consistency
- Identical inputs produce identical outputs
- Keyword gap analysis accuracy
- Skill optimization (no fabrication)
- Project optimization (no invention)
- Bullet point improvements (no exaggeration)
- Truthfulness guarantees
- Fallback behavior (no crashes)
- Formatter output validity
- Intent routing
- Section analysis
- Integration tests with/without target job
"""

import os
import sys
import re
from unittest.mock import patch

# Add parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.tools.resume_optimizer_tool import (
    calculate_ats_score,
    analyze_keyword_gaps,
    optimize_skills,
    optimize_projects,
    analyze_sections,
    optimize_resume,
    format_resume_optimization,
    _score_formatting,
    _score_keyword_coverage,
    _score_skills_section,
    _score_experience,
    _score_projects,
    _score_education,
    _score_technical_stack,
    _score_action_verbs,
    _score_achievement_quantification,
    _score_overall_structure,
    _detect_weak_bullets,
    _generate_fallback_bullet_improvements,
    _generate_fallback_recruiter_feedback,
    _generate_checklist,
    ResumeOptimizationResponse,
    ATSScore,
    KeywordGapAnalysis,
    SkillOptimization,
    RecruiterFeedback,
    BulletPointImprovement,
)
from app.core.skill_utils import (
    extract_skills_from_profile,
    fuzzy_skill_match,
    infer_skills_from_title,
    expand_skills_with_aliases,
    TECH_RE,
)
from app.core.scoring_utils import (
    calibrate_score,
    count_production_signals,
    count_project_signals,
)
from app.services.intent_service import detect_intent_rule


# ==============================================================================
# TEST DATA
# ==============================================================================

MOCK_RESUME_TEXT = (
    "AI Backend Developer with experience in Python, Django, FastAPI, "
    "REST APIs, PostgreSQL, MongoDB, Node.js, Express.js, GitHub Actions, "
    "Redis, Linux. Built production Django systems, FastAPI integrations, "
    "AI agent development with ElevenLabs integrations. "
    "Production debugging, deployed systems, CI/CD pipelines, "
    "Stripe payment integration, authentication systems, OAuth, JWT. "
    "Experience with Gemini API, prompt engineering, AI automation workflows.\n\n"
    "PROJECTS\n"
    "- MovieDB: Full-stack movie database application using Django, PostgreSQL, REST APIs\n"
    "- Scholaroid: AI-powered scholarship finder using FastAPI, OpenAI, PostgreSQL\n"
    "- AI Chrome Extension: Chrome extension with ElevenLabs AI voice integration\n"
    "- School Management System: CRUD application with authentication and role management\n\n"
    "EXPERIENCE\n"
    "- Worked on backend systems using Django and FastAPI\n"
    "- Helped with API integration and database management\n"
    "- Used Python for automation scripts\n"
    "- Developed authentication systems using JWT and OAuth\n\n"
    "EDUCATION\n"
    "Bachelor of Technology in Computer Science\n"
    "University of Technology, 2024\n\n"
    "SKILLS\n"
    "Python, Django, FastAPI, PostgreSQL, MongoDB, Redis, Node.js, REST APIs, Git"
)

MOCK_PROFILE = {
    "skills": [
        {"name": "Python"},
        {"name": "Django"},
        {"name": "FastAPI"},
        {"name": "REST APIs"},
        {"name": "PostgreSQL"},
        {"name": "MongoDB"},
        {"name": "Node.js"},
        {"name": "Express.js"},
        {"name": "GitHub Actions"},
        {"name": "Redis"},
    ],
    "parsed_resume": {
        "skills": ["Python", "Django", "FastAPI", "Redis", "Linux"],
        "technologies": ["Docker", "Git", "PostgreSQL"],
        "projects": [
            {"name": "MovieDB", "description": "Full-stack movie database with Django and PostgreSQL"},
            {"name": "Scholaroid", "description": "AI scholarship finder with FastAPI and OpenAI"},
            {"name": "AI Chrome Extension", "description": "Chrome extension with ElevenLabs AI"},
            {"name": "School Management System", "description": "CRUD app with auth"},
        ],
    },
    "resume_text": MOCK_RESUME_TEXT,
    "experience_years": 2,
    "full_name": "Test User",
    "github_url": "https://github.com/testuser",
    "target_role": "Backend Developer",
}

MOCK_JOB_DESCRIPTION = (
    "We are looking for a Backend Developer with experience in Python, Django, "
    "FastAPI, PostgreSQL, Redis, Docker, CI/CD, REST APIs, authentication, "
    "and microservices. Experience with AWS, Kubernetes, and system design "
    "is a plus."
)


# ==============================================================================
# ATS SCORING TESTS
# ==============================================================================

def test_ats_score_range():
    """ATS scores must always be between 0 and 100."""
    user_skills = extract_skills_from_profile(MOCK_PROFILE, MOCK_RESUME_TEXT)
    target_keywords = infer_skills_from_title("Backend Developer")
    ats = calculate_ats_score(MOCK_RESUME_TEXT, user_skills, target_keywords, MOCK_PROFILE)

    assert 0 <= ats.overall_score <= 100, f"Overall score out of range: {ats.overall_score}"
    assert 0 <= ats.potential_score <= 100, f"Potential score out of range: {ats.potential_score}"
    for cat in ats.categories:
        assert 0 <= cat.score <= 100, f"Category {cat.name} score out of range: {cat.score}"
    print(f"  [PASS] ATS scores in range: overall={ats.overall_score}, potential={ats.potential_score}")


def test_ats_score_deterministic():
    """Identical inputs must produce identical outputs."""
    user_skills = extract_skills_from_profile(MOCK_PROFILE, MOCK_RESUME_TEXT)
    target_keywords = infer_skills_from_title("Backend Developer")

    ats1 = calculate_ats_score(MOCK_RESUME_TEXT, user_skills, target_keywords, MOCK_PROFILE)
    ats2 = calculate_ats_score(MOCK_RESUME_TEXT, user_skills, target_keywords, MOCK_PROFILE)

    assert ats1.overall_score == ats2.overall_score, "ATS scores are not deterministic"
    assert ats1.potential_score == ats2.potential_score, "Potential scores are not deterministic"
    for c1, c2 in zip(ats1.categories, ats2.categories):
        assert c1.score == c2.score, f"Category {c1.name} is not deterministic"
    print(f"  [PASS] ATS scoring is deterministic: {ats1.overall_score}")


def test_ats_potential_higher_or_equal():
    """Potential ATS score must always be >= current score."""
    user_skills = extract_skills_from_profile(MOCK_PROFILE, MOCK_RESUME_TEXT)
    target_keywords = infer_skills_from_title("Backend Developer")
    ats = calculate_ats_score(MOCK_RESUME_TEXT, user_skills, target_keywords, MOCK_PROFILE)

    assert ats.potential_score >= ats.overall_score, (
        f"Potential ({ats.potential_score}) < current ({ats.overall_score})"
    )
    print(f"  [PASS] Potential ({ats.potential_score}) >= Current ({ats.overall_score})")


def test_ats_empty_resume():
    """Empty resume should produce low but valid ATS scores."""
    user_skills = set()
    target_keywords = infer_skills_from_title("Backend Developer")
    ats = calculate_ats_score("", user_skills, target_keywords, {})

    assert 0 <= ats.overall_score <= 100, "Score out of range for empty resume"
    assert ats.overall_score < 30, f"Empty resume should score low, got {ats.overall_score}"
    print(f"  [PASS] Empty resume score: {ats.overall_score}")


def test_ats_categories_have_explanations():
    """Every ATS category must have a non-empty explanation."""
    user_skills = extract_skills_from_profile(MOCK_PROFILE, MOCK_RESUME_TEXT)
    target_keywords = infer_skills_from_title("Backend Developer")
    ats = calculate_ats_score(MOCK_RESUME_TEXT, user_skills, target_keywords, MOCK_PROFILE)

    for cat in ats.categories:
        assert cat.explanation, f"Category {cat.name} has empty explanation"
    print(f"  [PASS] All {len(ats.categories)} categories have explanations")


def test_ats_weights_sum_to_100():
    """ATS category weights must sum to exactly 100."""
    from app.tools.resume_optimizer_tool import ATS_WEIGHTS
    total = sum(ATS_WEIGHTS.values())
    assert total == 100.0, f"ATS weights sum to {total}, expected 100"
    print(f"  [PASS] ATS weights sum to {total}")


# ==============================================================================
# INDIVIDUAL SCORING FUNCTION TESTS
# ==============================================================================

def test_score_formatting():
    """Formatting score should be reasonable for well-structured resume."""
    score, explanation = _score_formatting(MOCK_RESUME_TEXT)
    assert 0 <= score <= 100, f"Formatting score out of range: {score}"
    assert explanation, "Formatting explanation is empty"
    print(f"  [PASS] Formatting score: {score} - {explanation[:50]}")


def test_score_action_verbs():
    """Action verb detection should find verbs in resume."""
    score, explanation = _score_action_verbs(MOCK_RESUME_TEXT)
    assert 0 <= score <= 100, f"Action verb score out of range: {score}"
    assert score > 0, "Should detect at least some action verbs"
    print(f"  [PASS] Action verbs score: {score} - {explanation[:50]}")


def test_score_education():
    """Education scoring should detect degree and field."""
    score, explanation = _score_education(MOCK_RESUME_TEXT)
    assert score >= 50, f"Should detect education, got score {score}"
    print(f"  [PASS] Education score: {score} - {explanation[:50]}")


def test_score_achievement_quantification():
    """Quantification scoring for resume without many numbers."""
    score, explanation = _score_achievement_quantification(MOCK_RESUME_TEXT)
    assert 0 <= score <= 100
    print(f"  [PASS] Achievement quantification score: {score}")


# ==============================================================================
# KEYWORD GAP ANALYSIS TESTS
# ==============================================================================

def test_keyword_gap_with_target_job():
    """Keyword analysis should identify present and missing keywords."""
    user_skills = extract_skills_from_profile(MOCK_PROFILE, MOCK_RESUME_TEXT)
    analysis = analyze_keyword_gaps(
        MOCK_RESUME_TEXT, user_skills, "Backend Developer", MOCK_JOB_DESCRIPTION, MOCK_PROFILE
    )

    assert analysis.keyword_match_percentage > 0, "Should have some keyword matches"
    assert len(analysis.present_keywords) > 0, "Should find present keywords"
    print(f"  [PASS] Keyword match: {analysis.keyword_match_percentage}% "
          f"({len(analysis.present_keywords)} present, {len(analysis.missing_keywords)} missing)")


def test_keyword_gap_no_target_job():
    """Without job description, should fall back to role-based inference."""
    user_skills = extract_skills_from_profile(MOCK_PROFILE, MOCK_RESUME_TEXT)
    analysis = analyze_keyword_gaps(
        MOCK_RESUME_TEXT, user_skills, "Backend Developer", None, MOCK_PROFILE
    )

    assert analysis.target_role == "Backend Developer"
    assert analysis.keyword_match_percentage > 0
    print(f"  [PASS] Fallback keyword match: {analysis.keyword_match_percentage}%")


def test_no_fabricated_skills_in_keywords():
    """Missing keywords must recommend learning, NOT adding."""
    user_skills = extract_skills_from_profile(MOCK_PROFILE, MOCK_RESUME_TEXT)
    analysis = analyze_keyword_gaps(
        MOCK_RESUME_TEXT, user_skills, "Backend Developer", MOCK_JOB_DESCRIPTION, MOCK_PROFILE
    )

    for kw in analysis.missing_keywords:
        assert "do NOT add" in kw.recommendation or "learn" in kw.recommendation.lower(), (
            f"Missing keyword '{kw.keyword}' should recommend learning, got: {kw.recommendation}"
        )
    print(f"  [PASS] All {len(analysis.missing_keywords)} missing keywords recommend learning, not adding")


# ==============================================================================
# SKILL OPTIMIZATION TESTS
# ==============================================================================

def test_skill_grouping():
    """Skills should be organized into logical categories."""
    user_skills = extract_skills_from_profile(MOCK_PROFILE, MOCK_RESUME_TEXT)
    optimization = optimize_skills(user_skills, "Backend Developer")

    assert len(optimization.optimized_groups) > 0, "Should produce at least one group"
    assert len(optimization.current_skills) > 0, "Should list current skills"

    # Verify all groups have skills
    for group in optimization.optimized_groups:
        assert len(group.skills) > 0, f"Group '{group.category}' has no skills"

    print(f"  [PASS] {len(optimization.optimized_groups)} skill groups created")


def test_no_fabricated_skills_in_optimization():
    """Skill optimization must only reorganize, never create new skills."""
    user_skills = extract_skills_from_profile(MOCK_PROFILE, MOCK_RESUME_TEXT)
    optimization = optimize_skills(user_skills, "Backend Developer")

    # Collect all skills from optimized groups
    all_optimized = set()
    for group in optimization.optimized_groups:
        for skill in group.skills:
            all_optimized.add(skill.lower())

    # Every optimized skill must come from the user's actual skills
    for skill in all_optimized:
        assert skill in user_skills or skill.lower() in user_skills, (
            f"Fabricated skill detected in optimization: '{skill}'"
        )
    print(f"  [PASS] No fabricated skills in optimization ({len(all_optimized)} skills verified)")


# ==============================================================================
# PROJECT OPTIMIZATION TESTS
# ==============================================================================

def test_project_relevance_scoring():
    """Projects should be scored for relevance to target role."""
    user_skills = extract_skills_from_profile(MOCK_PROFILE, MOCK_RESUME_TEXT)
    optimizations = optimize_projects(MOCK_RESUME_TEXT, MOCK_PROFILE, user_skills, "Backend Developer")

    assert len(optimizations) > 0, "Should find projects to optimize"
    for proj in optimizations:
        assert 0 <= proj.relevance_score <= 100, f"Relevance score out of range for {proj.project_name}"
    print(f"  [PASS] {len(optimizations)} projects scored for relevance")


def test_no_invented_projects():
    """Project optimization must never create new projects."""
    user_skills = extract_skills_from_profile(MOCK_PROFILE, MOCK_RESUME_TEXT)
    optimizations = optimize_projects(MOCK_RESUME_TEXT, MOCK_PROFILE, user_skills, "Backend Developer")

    # Extract real project names from profile
    parsed = MOCK_PROFILE.get("parsed_resume", {})
    real_projects = {p["name"] for p in parsed.get("projects", []) if isinstance(p, dict)}

    for proj in optimizations:
        assert proj.project_name in real_projects, (
            f"Invented project detected: '{proj.project_name}'"
        )
    print(f"  [PASS] All {len(optimizations)} projects are real (no inventions)")


def test_project_recommended_positions():
    """Projects should have valid recommended positions."""
    user_skills = extract_skills_from_profile(MOCK_PROFILE, MOCK_RESUME_TEXT)
    optimizations = optimize_projects(MOCK_RESUME_TEXT, MOCK_PROFILE, user_skills, "Backend Developer")

    positions = [p.recommended_position for p in optimizations]
    assert sorted(positions) == list(range(1, len(positions) + 1)), (
        f"Recommended positions should be 1..N, got {positions}"
    )
    print(f"  [PASS] Project positions are valid: {positions}")


# ==============================================================================
# SECTION ANALYSIS TESTS
# ==============================================================================

def test_section_analysis_completeness():
    """Should analyze all major resume sections."""
    user_skills = extract_skills_from_profile(MOCK_PROFILE, MOCK_RESUME_TEXT)
    sections = analyze_sections(MOCK_RESUME_TEXT, user_skills, MOCK_PROFILE, "Backend Developer")

    section_names = {s.section_name for s in sections}
    required_sections = {"Summary / Objective", "Skills", "Projects", "Experience", "Education", "Certifications"}
    assert required_sections.issubset(section_names), (
        f"Missing sections: {required_sections - section_names}"
    )
    print(f"  [PASS] All {len(required_sections)} required sections analyzed")


def test_section_scores_in_range():
    """All section scores should be 0-100."""
    user_skills = extract_skills_from_profile(MOCK_PROFILE, MOCK_RESUME_TEXT)
    sections = analyze_sections(MOCK_RESUME_TEXT, user_skills, MOCK_PROFILE, "Backend Developer")

    for section in sections:
        assert 0 <= section.score <= 100, f"Section {section.section_name} score out of range: {section.score}"
    print(f"  [PASS] All section scores in range")


# ==============================================================================
# BULLET POINT IMPROVEMENT TESTS
# ==============================================================================

def test_weak_bullet_detection():
    """Should detect weak bullet patterns."""
    weak = _detect_weak_bullets(MOCK_RESUME_TEXT)
    assert len(weak) > 0, "Should detect weak bullets in mock resume"
    print(f"  [PASS] Detected {len(weak)} weak bullets")


def test_fallback_bullet_improvements():
    """Fallback bullet improvements should provide valid replacements."""
    weak = _detect_weak_bullets(MOCK_RESUME_TEXT)
    improvements = _generate_fallback_bullet_improvements(weak)

    for bi in improvements:
        assert bi.original != bi.improved, f"Improvement should differ from original: '{bi.original}'"
        assert bi.reasoning, f"Improvement should have reasoning: '{bi.original}'"
    print(f"  [PASS] {len(improvements)} bullet improvements generated")


def test_bullet_improvements_no_exaggeration():
    """Bullet improvements must not add fabricated metrics."""
    weak = ["Worked on backend systems"]
    improvements = _generate_fallback_bullet_improvements(weak)

    for bi in improvements:
        # Should not contain invented percentages or numbers
        numbers = re.findall(r'\d+%', bi.improved)
        assert len(numbers) == 0, f"Fabricated metrics in improvement: '{bi.improved}'"
    print(f"  [PASS] No fabricated metrics in bullet improvements")


# ==============================================================================
# TRUTHFULNESS VALIDATION TESTS
# ==============================================================================

def test_truthfulness_no_invented_experience():
    """The optimizer must never invent work experience."""
    with patch("app.tools.resume_optimizer_tool._generate_ai_enhancements", side_effect=RuntimeError("mock")):
        result = optimize_resume(
            resume_text=MOCK_RESUME_TEXT,
            user_profile=MOCK_PROFILE,
            target_role="Backend Developer",
        )

    # Check recruiter feedback doesn't reference non-existent experience
    rf = result.recruiter_feedback
    if rf.biggest_strengths:
        for strength in rf.biggest_strengths:
            # Should not mention specific companies not in the resume
            assert "Google" not in strength and "Amazon" not in strength, (
                f"Invented company reference in strengths: '{strength}'"
            )
    print(f"  [PASS] No invented experience detected")


def test_truthfulness_keyword_recommendations():
    """Missing keyword recommendations must not suggest pretending."""
    user_skills = extract_skills_from_profile(MOCK_PROFILE, MOCK_RESUME_TEXT)
    analysis = analyze_keyword_gaps(
        MOCK_RESUME_TEXT, user_skills, "Backend Developer", MOCK_JOB_DESCRIPTION, MOCK_PROFILE
    )

    for kw in analysis.missing_keywords:
        recommendation = kw.recommendation.lower()
        assert "add" not in recommendation or "do not add" in recommendation, (
            f"Keyword '{kw.keyword}' recommends adding without evidence: {kw.recommendation}"
        )
    print(f"  [PASS] Truthfulness validated for keyword recommendations")


# ==============================================================================
# FALLBACK BEHAVIOR TESTS
# ==============================================================================

def test_fallback_on_missing_resume():
    """Should return valid response when no resume is available."""
    result = optimize_resume(
        resume_text="",
        user_profile={},
        target_role="Backend Developer",
    )

    assert isinstance(result, ResumeOptimizationResponse)
    assert result.summary.overall_recommendation
    print(f"  [PASS] Fallback for missing resume works")


def test_fallback_recruiter_feedback():
    """Fallback recruiter feedback should be complete and evidence-based."""
    user_skills = extract_skills_from_profile(MOCK_PROFILE, MOCK_RESUME_TEXT)
    feedback = _generate_fallback_recruiter_feedback(
        user_skills, MOCK_RESUME_TEXT, MOCK_PROFILE, "Backend Developer", 65.0
    )

    assert feedback.overall_impression, "Should have overall impression"
    assert feedback.shortlisting_probability in ("High", "Medium", "Low")
    assert len(feedback.biggest_strengths) > 0, "Should have at least one strength"
    print(f"  [PASS] Fallback recruiter feedback is complete: {feedback.shortlisting_probability}")


def test_never_crashes_empty_input():
    """Optimizer should never crash, even with completely empty input."""
    result = optimize_resume()

    assert isinstance(result, ResumeOptimizationResponse)
    print(f"  [PASS] No crash on empty input")


def test_never_crashes_none_profile():
    """Optimizer should handle None profile gracefully."""
    result = optimize_resume(
        resume_text=MOCK_RESUME_TEXT,
        user_profile=None,
    )

    assert isinstance(result, ResumeOptimizationResponse)
    assert result.ats_score.overall_score >= 0
    print(f"  [PASS] No crash on None profile, ATS: {result.ats_score.overall_score}")


# ==============================================================================
# FORMATTER TESTS
# ==============================================================================

def test_formatter_produces_valid_output():
    """Formatter should produce non-empty markdown output."""
    with patch("app.tools.resume_optimizer_tool._generate_ai_enhancements", side_effect=RuntimeError("mock")):
        result = optimize_resume(
            resume_text=MOCK_RESUME_TEXT,
            user_profile=MOCK_PROFILE,
            target_role="Backend Developer",
        )
    formatted = format_resume_optimization(result)

    assert isinstance(formatted, str)
    assert len(formatted) > 100, "Formatted output is too short"
    assert "## Resume Optimization" in formatted, "Missing main header"
    assert "ATS" in formatted, "Missing ATS section"
    print(f"  [PASS] Formatter produces valid output ({len(formatted)} chars)")


def test_formatter_contains_key_sections():
    """Formatted output should contain all major sections."""
    with patch("app.tools.resume_optimizer_tool._generate_ai_enhancements", side_effect=RuntimeError("mock")):
        result = optimize_resume(
            resume_text=MOCK_RESUME_TEXT,
            user_profile=MOCK_PROFILE,
            target_role="Backend Developer",
        )
    formatted = format_resume_optimization(result)

    expected_sections = [
        "ATS Score:",
        "Top Strengths",
        "High-Impact Improvements",
        "Recruiter Verdict",
        "Today's Priority",
    ]
    for section in expected_sections:
        assert section in formatted, f"Missing section in formatted output: {section}"
    print(f"  [PASS] All key sections present in formatted output")


def test_formatter_no_raw_json():
    """Formatted output should not contain raw JSON."""
    with patch("app.tools.resume_optimizer_tool._generate_ai_enhancements", side_effect=RuntimeError("mock")):
        result = optimize_resume(
            resume_text=MOCK_RESUME_TEXT,
            user_profile=MOCK_PROFILE,
            target_role="Backend Developer",
        )
    formatted = format_resume_optimization(result)

    assert '{"' not in formatted, "Raw JSON detected in formatted output"
    assert '":{' not in formatted, "Raw JSON object detected in formatted output"
    print(f"  [PASS] No raw JSON in formatted output")


# ==============================================================================
# INTENT ROUTING TESTS
# ==============================================================================

def test_intent_routing_optimize():
    """'optimize my resume' should route to resume_optimization."""
    assert detect_intent_rule("optimize my resume") == "resume_optimization"
    assert detect_intent_rule("Optimize my resume for backend developer") == "resume_optimization"
    print(f"  [PASS] 'optimize my resume' routes correctly")


def test_intent_routing_ats():
    """ATS-related queries should route to resume_optimization."""
    assert detect_intent_rule("will my resume pass ats") == "resume_optimization"
    assert detect_intent_rule("what is my ats score") == "resume_optimization"
    print(f"  [PASS] ATS queries route correctly")


def test_intent_routing_tailor():
    """'tailor my resume' should route to resume_optimization."""
    assert detect_intent_rule("tailor my resume for this job") == "resume_optimization"
    assert detect_intent_rule("tailor my cv for Amazon") == "resume_optimization"
    print(f"  [PASS] 'tailor' queries route correctly")


def test_intent_routing_improve():
    """'how can I improve my resume' should route to resume_optimization."""
    assert detect_intent_rule("how can i improve my resume") == "resume_optimization"
    assert detect_intent_rule("get more interviews") == "resume_optimization"
    print(f"  [PASS] Improvement queries route correctly")


def test_intent_routing_does_not_break_review():
    """Generic 'review my resume' should still route to resume_review."""
    assert detect_intent_rule("review my resume") == "resume_review"
    assert detect_intent_rule("analyze my resume") == "resume_review"
    print(f"  [PASS] resume_review routing is preserved")


# ==============================================================================
# INTEGRATION TESTS (Full Pipeline, No AI)
# ==============================================================================

def test_full_optimization_without_target_job():
    """Full optimization pipeline should work without a target job."""
    with patch("app.tools.resume_optimizer_tool._generate_ai_enhancements", side_effect=RuntimeError("mock")):
        result = optimize_resume(
            resume_text=MOCK_RESUME_TEXT,
            user_profile=MOCK_PROFILE,
        )

    assert isinstance(result, ResumeOptimizationResponse)
    assert result.ats_score.overall_score > 0
    assert result.target_role, "Should resolve a target role"
    assert len(result.section_feedback) >= 4, "Should analyze multiple sections"
    print(f"  [PASS] Full optimization without target job: ATS={result.ats_score.overall_score}")


def test_full_optimization_with_backend_job():
    """Full optimization for a Backend Developer role."""
    with patch("app.tools.resume_optimizer_tool._generate_ai_enhancements", side_effect=RuntimeError("mock")):
        result = optimize_resume(
            resume_text=MOCK_RESUME_TEXT,
            user_profile=MOCK_PROFILE,
            target_role="Backend Developer",
            job_description=MOCK_JOB_DESCRIPTION,
        )

    assert result.target_role == "Backend Developer"
    assert result.ats_score.overall_score > 0
    assert result.keyword_analysis.keyword_match_percentage > 0
    assert len(result.project_optimizations) > 0
    print(f"  [PASS] Backend Developer optimization: ATS={result.ats_score.overall_score}, "
          f"Keywords={result.keyword_analysis.keyword_match_percentage}%")


def test_full_optimization_with_ai_engineer_job():
    """Full optimization for an AI Engineer role."""
    ai_jd = (
        "Looking for an AI Engineer with Python, LLM, LangChain, RAG, "
        "vector databases, FastAPI, Docker, and prompt engineering experience."
    )
    with patch("app.tools.resume_optimizer_tool._generate_ai_enhancements", side_effect=RuntimeError("mock")):
        result = optimize_resume(
            resume_text=MOCK_RESUME_TEXT,
            user_profile=MOCK_PROFILE,
            target_role="AI Engineer",
            job_description=ai_jd,
        )

    assert result.target_role == "AI Engineer"
    assert result.ats_score.overall_score > 0
    print(f"  [PASS] AI Engineer optimization: ATS={result.ats_score.overall_score}")


def test_full_optimization_missing_resume():
    """Optimization with missing resume should degrade gracefully."""
    result = optimize_resume(
        resume_text="",
        user_profile={"target_role": "Backend Developer"},
    )

    assert isinstance(result, ResumeOptimizationResponse)
    assert result.summary.overall_recommendation
    assert "upload" in result.summary.overall_recommendation.lower() or \
           "resume" in result.summary.overall_recommendation.lower()
    print(f"  [PASS] Missing resume handled gracefully")


# ==============================================================================
# SHARED UTILITY TESTS (ensure refactoring didn't break anything)
# ==============================================================================

def test_shared_skill_extraction():
    """Skill extraction from shared utils works correctly."""
    skills = extract_skills_from_profile(MOCK_PROFILE, MOCK_RESUME_TEXT)
    assert "python" in skills, "Should extract Python"
    assert "django" in skills, "Should extract Django"
    assert "fastapi" in skills, "Should extract FastAPI"
    print(f"  [PASS] Shared skill extraction: {len(skills)} skills")


def test_shared_calibrate_score():
    """Calibration from shared utils works correctly."""
    assert calibrate_score(100.0) < 100.0, "100 should be calibrated down"
    assert calibrate_score(50.0) == 50.0, "50 should pass through"
    assert calibrate_score(0.0) == 0.0, "0 should remain 0"
    print(f"  [PASS] Shared calibration works: cal(100)={calibrate_score(100.0)}")


def test_shared_fuzzy_match():
    """Fuzzy matching from shared utils works correctly."""
    user = {"python", "django", "fastapi"}
    reqs = {"python", "django", "docker"}
    matched, missing = fuzzy_skill_match(user, reqs)
    assert "python" in matched
    assert "docker" in missing
    print(f"  [PASS] Shared fuzzy match: {len(matched)} matched, {len(missing)} missing")


# ==============================================================================
# CHECKLIST TESTS
# ==============================================================================

def test_checklist_has_priorities():
    """Checklist items should have valid priorities."""
    with patch("app.tools.resume_optimizer_tool._generate_ai_enhancements", side_effect=RuntimeError("mock")):
        result = optimize_resume(
            resume_text=MOCK_RESUME_TEXT,
            user_profile=MOCK_PROFILE,
            target_role="Backend Developer",
            job_description=MOCK_JOB_DESCRIPTION,
        )

    for item in result.optimization_checklist:
        assert item.priority in ("High", "Medium", "Low"), (
            f"Invalid priority: {item.priority}"
        )
        assert item.action, "Checklist item has no action"
    print(f"  [PASS] Checklist has {len(result.optimization_checklist)} valid items")


# ==============================================================================
# RUNNER
# ==============================================================================

if __name__ == "__main__":
    tests = [
        # ATS Scoring
        test_ats_score_range,
        test_ats_score_deterministic,
        test_ats_potential_higher_or_equal,
        test_ats_empty_resume,
        test_ats_categories_have_explanations,
        test_ats_weights_sum_to_100,
        # Individual Scorers
        test_score_formatting,
        test_score_action_verbs,
        test_score_education,
        test_score_achievement_quantification,
        # Keyword Gaps
        test_keyword_gap_with_target_job,
        test_keyword_gap_no_target_job,
        test_no_fabricated_skills_in_keywords,
        # Skill Optimization
        test_skill_grouping,
        test_no_fabricated_skills_in_optimization,
        # Project Optimization
        test_project_relevance_scoring,
        test_no_invented_projects,
        test_project_recommended_positions,
        # Section Analysis
        test_section_analysis_completeness,
        test_section_scores_in_range,
        # Bullet Improvements
        test_weak_bullet_detection,
        test_fallback_bullet_improvements,
        test_bullet_improvements_no_exaggeration,
        # Truthfulness
        test_truthfulness_no_invented_experience,
        test_truthfulness_keyword_recommendations,
        # Fallback
        test_fallback_on_missing_resume,
        test_fallback_recruiter_feedback,
        test_never_crashes_empty_input,
        test_never_crashes_none_profile,
        # Formatter
        test_formatter_produces_valid_output,
        test_formatter_contains_key_sections,
        test_formatter_no_raw_json,
        # Intent Routing
        test_intent_routing_optimize,
        test_intent_routing_ats,
        test_intent_routing_tailor,
        test_intent_routing_improve,
        test_intent_routing_does_not_break_review,
        # Integration
        test_full_optimization_without_target_job,
        test_full_optimization_with_backend_job,
        test_full_optimization_with_ai_engineer_job,
        test_full_optimization_missing_resume,
        # Shared Utils
        test_shared_skill_extraction,
        test_shared_calibrate_score,
        test_shared_fuzzy_match,
        # Checklist
        test_checklist_has_priorities,
    ]

    print(f"\n{'=' * 60}")
    print(f"  Resume Optimizer Tool — Test Suite ({len(tests)} tests)")
    print(f"{'=' * 60}\n")

    passed = 0
    failed = 0
    errors = []

    for test_fn in tests:
        try:
            test_fn()
            passed += 1
        except Exception as e:
            failed += 1
            errors.append((test_fn.__name__, str(e)))
            print(f"  [FAIL] {test_fn.__name__}: {e}")

    print(f"\n{'=' * 60}")
    print(f"  Results: {passed} passed, {failed} failed, {len(tests)} total")
    print(f"{'=' * 60}")

    if errors:
        print(f"\nFailed tests:")
        for name, err in errors:
            print(f"  - {name}: {err}")

    sys.exit(1 if failed else 0)
