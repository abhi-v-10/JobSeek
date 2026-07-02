"""
Resume Optimizer Tool for SeekBot AI.

An AI Resume Optimization Engine that compares the user's resume, profile,
skill data, resume analysis, and job match data to produce a truthful,
actionable optimization plan with deterministic ATS scoring, keyword gap
analysis, skill optimization, and recruiter-grade feedback.

Architecture:
    resume_tool -> skill_utils -> scoring_utils -> resume_optimizer_tool -> AI layer

This is an orchestration tool. It consumes outputs from existing tools
(resume_tool, application_strategy_tool, personalized_job_recommender)
and produces optimization recommendations. It does NOT duplicate resume
parsing, skill extraction, or job matching logic.

Scoring is fully deterministic. AI is invoked ONLY for generating
human-readable bullet improvements, recruiter feedback, and wording
suggestions. The tool never crashes — all AI failures fall back to
deterministic optimization.

SAFETY: This tool NEVER invents experience, skills, projects,
certifications, metrics, or achievements. All suggestions remain truthful.
If evidence is missing, the tool recommends learning — not pretending.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from pydantic import BaseModel, Field

from app.core.openai_client import generate_chat_completion
from app.core.skill_utils import (
    TECH_RE,
    TITLE_SKILL_MAP,
    extract_skills_from_profile,
    fuzzy_skill_match,
    infer_skills_from_title,
    expand_skills_with_aliases,
)
from app.core.scoring_utils import (
    PRODUCTION_INDICATORS,
    PROJECT_QUALITY_INDICATORS,
    calibrate_score,
    count_production_signals,
    count_project_signals,
)

logger = logging.getLogger(__name__)


# ==============================================================================
# PYDANTIC V2 MODELS
# ==============================================================================

class ATSScoreCategory(BaseModel):
    """Individual ATS scoring category."""
    name: str = Field(..., description="Category name (e.g., 'Keyword Coverage').")
    score: float = Field(..., description="Current score for this category (0-100).")
    max_score: float = Field(default=100.0, description="Maximum possible score.")
    weight: float = Field(..., description="Weight of this category in overall score.")
    explanation: str = Field(..., description="Why this score was given.")


class ATSScore(BaseModel):
    """Overall ATS scoring with category breakdown."""
    overall_score: float = Field(default=0.0, description="Current weighted ATS score (0-100).")
    potential_score: float = Field(default=0.0, description="Projected ATS score after optimization (0-100).")
    categories: List[ATSScoreCategory] = Field(default_factory=list, description="Per-category breakdown.")
    summary: str = Field(default="", description="Brief ATS score summary.")


class KeywordGap(BaseModel):
    """A single keyword with its match status."""
    keyword: str = Field(..., description="The keyword or technology.")
    status: str = Field(..., description="'present', 'missing', or 'recommended'.")
    source: str = Field(default="", description="Where found: 'resume', 'profile', 'skill_sync', or 'job_description'.")
    recommendation: str = Field(default="", description="Action for missing keywords.")


class KeywordGapAnalysis(BaseModel):
    """Full keyword comparison results."""
    target_role: str = Field(default="", description="The role keywords were matched against.")
    present_keywords: List[KeywordGap] = Field(default_factory=list)
    missing_keywords: List[KeywordGap] = Field(default_factory=list)
    recommended_keywords: List[KeywordGap] = Field(default_factory=list)
    keyword_match_percentage: float = Field(default=0.0, description="Percentage of target keywords present.")


class SkillGroup(BaseModel):
    """A logical grouping of related skills."""
    category: str = Field(..., description="Group name (e.g., 'Backend Development').")
    skills: List[str] = Field(default_factory=list, description="Skills in this group.")


class SkillOptimization(BaseModel):
    """Current vs. optimized skill organization."""
    current_skills: List[str] = Field(default_factory=list, description="Skills as currently listed.")
    optimized_groups: List[SkillGroup] = Field(default_factory=list, description="Optimized skill groupings.")
    visibility_suggestions: List[str] = Field(default_factory=list, description="Skills to make more prominent.")
    relevance_notes: List[str] = Field(default_factory=list, description="Notes about skill relevance to target.")


class ProjectOptimization(BaseModel):
    """Optimization recommendations for a single project."""
    project_name: str = Field(..., description="Name of the project.")
    relevance_score: float = Field(default=0.0, description="Relevance to target role (0-100).")
    current_position: int = Field(default=0, description="Current position in resume.")
    recommended_position: int = Field(default=0, description="Recommended position.")
    visibility: str = Field(default="keep", description="'highlight', 'keep', or 'deprioritize'.")
    suggestions: List[str] = Field(default_factory=list, description="Improvement suggestions.")


class BulletPointImprovement(BaseModel):
    """Before/after improvement for a bullet point."""
    original: str = Field(..., description="Original bullet text.")
    improved: str = Field(..., description="Improved bullet text.")
    reasoning: str = Field(default="", description="Why this improvement was suggested.")
    category: str = Field(default="", description="Improvement type: 'action_verb', 'quantification', 'specificity', 'technical_detail'.")


class ExperienceOptimization(BaseModel):
    """Optimization for a single experience entry."""
    role: str = Field(default="", description="Job title or role.")
    company: str = Field(default="", description="Company name.")
    bullet_improvements: List[BulletPointImprovement] = Field(default_factory=list)
    overall_suggestions: List[str] = Field(default_factory=list)


class ResumeSectionFeedback(BaseModel):
    """Feedback for a single resume section."""
    section_name: str = Field(..., description="Section name (e.g., 'Summary', 'Skills').")
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)
    priority: str = Field(default="Medium", description="'High', 'Medium', or 'Low'.")
    score: float = Field(default=0.0, description="Section quality score (0-100).")


class RecruiterFeedback(BaseModel):
    """Senior technical recruiter review."""
    overall_impression: str = Field(default="", description="Recruiter's first impression.")
    biggest_strengths: List[str] = Field(default_factory=list)
    biggest_weaknesses: List[str] = Field(default_factory=list)
    shortlisting_probability: str = Field(default="", description="'High', 'Medium', or 'Low'.")
    interview_readiness: str = Field(default="", description="Assessment of interview readiness.")
    portfolio_quality: str = Field(default="", description="Assessment of portfolio/projects.")
    ats_compatibility: str = Field(default="", description="ATS compatibility assessment.")
    key_recommendations: List[str] = Field(default_factory=list)


class OptimizationChecklistItem(BaseModel):
    """A single checklist item with priority."""
    priority: str = Field(..., description="'High', 'Medium', or 'Low'.")
    action: str = Field(..., description="The specific action to take.")
    category: str = Field(default="", description="Category: 'skills', 'projects', 'experience', 'formatting', 'keywords'.")


class OptimizationSummary(BaseModel):
    """Final optimization summary."""
    current_ats_score: float = Field(default=0.0)
    potential_ats_score: float = Field(default=0.0)
    resume_strength: str = Field(default="")
    top_improvements: List[str] = Field(default_factory=list)
    recruiter_verdict: str = Field(default="")
    overall_recommendation: str = Field(default="")


class ResumeOptimizationResponse(BaseModel):
    """
    Top-level response for the Resume Optimizer tool.
    Aggregates all optimization sub-analyses into a single response.
    Designed for future extensibility (versioning, tailoring, export).
    """
    target_role: str = Field(default="", description="Role the resume is being optimized for.")
    ats_score: ATSScore = Field(default_factory=ATSScore)
    keyword_analysis: KeywordGapAnalysis = Field(default_factory=KeywordGapAnalysis)
    skill_optimization: SkillOptimization = Field(default_factory=SkillOptimization)
    project_optimizations: List[ProjectOptimization] = Field(default_factory=list)
    experience_optimizations: List[ExperienceOptimization] = Field(default_factory=list)
    section_feedback: List[ResumeSectionFeedback] = Field(default_factory=list)
    recruiter_feedback: RecruiterFeedback = Field(default_factory=RecruiterFeedback)
    optimization_checklist: List[OptimizationChecklistItem] = Field(default_factory=list)
    summary: OptimizationSummary = Field(default_factory=OptimizationSummary)


# ==============================================================================
# CONSTANTS
# ==============================================================================

# Strong action verbs for bullet point evaluation.
ACTION_VERBS: Set[str] = {
    "developed", "built", "designed", "implemented", "created", "engineered",
    "architected", "deployed", "optimized", "integrated", "automated",
    "managed", "led", "established", "launched", "reduced", "increased",
    "improved", "streamlined", "configured", "maintained", "migrated",
    "refactored", "tested", "debugged", "resolved", "delivered",
    "orchestrated", "collaborated", "mentored", "spearheaded",
}

# Weak bullet patterns that should be improved.
WEAK_BULLET_PATTERNS: List[re.Pattern] = [
    re.compile(r"^(worked on|helped with|assisted|was responsible for|did)\b", re.IGNORECASE),
    re.compile(r"^(used|utilized|worked with)\b", re.IGNORECASE),
    re.compile(r"^(involved in|participated in|contributed to)\b", re.IGNORECASE),
]

# ATS category weights (must sum to 100).
ATS_WEIGHTS: Dict[str, float] = {
    "formatting": 10.0,
    "keyword_coverage": 20.0,
    "skills_section": 15.0,
    "experience": 15.0,
    "projects": 10.0,
    "education": 5.0,
    "technical_stack": 10.0,
    "action_verbs": 5.0,
    "achievement_quantification": 5.0,
    "overall_structure": 5.0,
}

# Skill category mapping for organized grouping.
SKILL_CATEGORIES: Dict[str, List[str]] = {
    "Backend Development": [
        "python", "django", "fastapi", "flask", "express", "nest.js",
        "spring", "laravel", "rails", "gin", "fiber", "rest", "api",
        "graphql", "grpc", "jwt", "oauth", "authentication",
    ],
    "Frontend Development": [
        "javascript", "typescript", "react", "vue", "angular", "next.js",
        "nuxt", "svelte", "remix", "html", "css", "sass", "tailwind",
        "bootstrap",
    ],
    "Databases": [
        "postgresql", "postgres", "mysql", "mongodb", "redis", "sqlite",
        "cassandra", "dynamodb", "elasticsearch", "supabase", "firebase",
        "sql", "nosql", "orm",
    ],
    "AI / Machine Learning": [
        "machine learning", "deep learning", "tensorflow", "pytorch",
        "scikit-learn", "pandas", "numpy", "langchain", "langgraph",
        "llm", "rag", "vector database", "huggingface", "transformers",
        "prompt engineering", "ai agent", "generative ai", "openai",
        "gemini", "elevenlabs", "bedrock", "pinecone", "weaviate", "chromadb",
    ],
    "Cloud & DevOps": [
        "aws", "azure", "gcp", "docker", "kubernetes", "k8s", "terraform",
        "ansible", "linux", "nginx", "vercel", "netlify", "heroku",
        "ci/cd", "github actions",
    ],
    "Data Engineering": [
        "spark", "hadoop", "kafka", "airflow",
    ],
    "Languages": [
        "java", "kotlin", "swift", "golang", "go", "rust", "c++", "c#",
        "php", "ruby", "scala", "dart",
    ],
    "Tools & Platforms": [
        "git", "github", "gitlab", "jira", "stripe", "websocket",
        "microservices", "ocr",
    ],
    "Runtime": [
        "node.js", "deno", "bun",
    ],
}


# ==============================================================================
# DETERMINISTIC ATS SCORING ENGINE
# ==============================================================================

def _score_formatting(resume_text: str) -> Tuple[float, str]:
    """Score resume formatting and structure (0-100)."""
    score = 0.0
    reasons = []

    length = len(resume_text.strip())
    if length >= 800:
        score += 30
    elif length >= 400:
        score += 20
        reasons.append("Resume could be more detailed")
    elif length > 0:
        score += 10
        reasons.append("Resume is too short for ATS")
    else:
        reasons.append("No resume text found")
        return 0.0, "; ".join(reasons) or "No content to evaluate"

    # Check for section headers
    section_keywords = ["experience", "education", "skills", "projects", "summary", "objective", "certification"]
    found_sections = sum(1 for kw in section_keywords if kw in resume_text.lower())
    if found_sections >= 4:
        score += 30
    elif found_sections >= 2:
        score += 20
        reasons.append(f"Only {found_sections} standard sections detected")
    else:
        score += 5
        reasons.append("Missing standard resume sections")

    # Check line structure (bullets, line breaks)
    lines = [l.strip() for l in resume_text.split("\n") if l.strip()]
    if len(lines) >= 15:
        score += 20
    elif len(lines) >= 8:
        score += 12
        reasons.append("Resume could use more structured bullet points")
    else:
        score += 5
        reasons.append("Very few structured lines")

    # Check for contact info patterns
    has_email = bool(re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", resume_text))
    has_phone = bool(re.search(r"\+?\d[\d\s\-()]{7,}", resume_text))
    has_link = bool(re.search(r"(github|linkedin|portfolio|http)", resume_text, re.IGNORECASE))
    contact_score = sum([has_email, has_phone, has_link]) * 7
    score += min(20, contact_score)
    if not has_email:
        reasons.append("No email detected")
    if not has_link:
        reasons.append("No portfolio/LinkedIn link detected")

    explanation = "; ".join(reasons) if reasons else "Good formatting and structure"
    return min(100.0, score), explanation


def _score_keyword_coverage(
    resume_text: str,
    user_skills: Set[str],
    target_keywords: Set[str],
) -> Tuple[float, str]:
    """Score keyword coverage against target role (0-100)."""
    if not target_keywords:
        return 60.0, "No target keywords available; defaulting to average"

    matched, missing = fuzzy_skill_match(user_skills, target_keywords)

    # Also check resume text directly for keywords
    resume_lower = resume_text.lower()
    for kw in missing[:]:
        if kw.lower() in resume_lower:
            matched.append(kw)
            missing.remove(kw)

    total = len(target_keywords)
    match_pct = (len(matched) / total * 100) if total > 0 else 0

    if missing:
        explanation = f"{len(matched)}/{total} target keywords present; missing: {', '.join(missing[:5])}"
    else:
        explanation = f"All {total} target keywords present"

    return min(100.0, match_pct), explanation


def _score_skills_section(
    resume_text: str,
    user_skills: Set[str],
) -> Tuple[float, str]:
    """Score the skills section quality (0-100)."""
    score = 0.0
    reasons = []

    skill_count = len(user_skills)
    if skill_count >= 15:
        score += 40
    elif skill_count >= 10:
        score += 32
    elif skill_count >= 6:
        score += 22
    elif skill_count >= 3:
        score += 12
    elif skill_count > 0:
        score += 5
    else:
        return 0.0, "No skills detected"

    # Check for skill grouping (category headers in resume)
    grouping_keywords = ["backend", "frontend", "database", "cloud", "devops", "tools", "languages", "frameworks"]
    grouped = sum(1 for kw in grouping_keywords if kw in resume_text.lower())
    if grouped >= 2:
        score += 30
    elif grouped >= 1:
        score += 15
        reasons.append("Skills could be better organized into categories")
    else:
        score += 5
        reasons.append("Skills listed without categorization")

    # Check for modern tech stack
    modern_tech = {"fastapi", "react", "docker", "kubernetes", "langchain", "llm", "typescript", "next.js"}
    modern_count = len(user_skills & modern_tech)
    if modern_count >= 3:
        score += 30
    elif modern_count >= 1:
        score += 18
    else:
        score += 5
        reasons.append("Consider highlighting modern technologies")

    explanation = "; ".join(reasons) if reasons else f"{skill_count} skills detected with good organization"
    return min(100.0, score), explanation


def _score_experience(
    resume_text: str,
    profile: dict,
) -> Tuple[float, str]:
    """Score experience section quality (0-100)."""
    score = 0.0
    reasons = []

    # Check for experience indicators
    prod_signals = count_production_signals(resume_text, profile)
    if prod_signals >= 5:
        score += 35
    elif prod_signals >= 3:
        score += 28
    elif prod_signals >= 1:
        score += 15
    else:
        score += 5
        reasons.append("No production experience indicators found")

    # Check for experience years
    exp = profile.get("experience_years") or profile.get("years_of_experience") or 0
    if isinstance(exp, (int, float)) and exp >= 2:
        score += 25
    elif isinstance(exp, (int, float)) and exp >= 1:
        score += 18
    else:
        score += 8
        reasons.append("Limited formal experience — projects are critical")

    # Check for action verbs
    resume_lower = resume_text.lower()
    verb_count = sum(1 for verb in ACTION_VERBS if verb in resume_lower)
    if verb_count >= 8:
        score += 25
    elif verb_count >= 4:
        score += 18
    elif verb_count >= 1:
        score += 10
    else:
        score += 3
        reasons.append("Use stronger action verbs (developed, built, deployed)")

    # Weak bullet detection
    weak_count = 0
    for line in resume_text.split("\n"):
        for pattern in WEAK_BULLET_PATTERNS:
            if pattern.search(line.strip()):
                weak_count += 1
                break
    if weak_count >= 3:
        score -= 10
        reasons.append(f"{weak_count} weak bullet points detected")
    elif weak_count >= 1:
        score -= 5
        reasons.append(f"{weak_count} bullet(s) could use stronger wording")

    explanation = "; ".join(reasons) if reasons else "Strong experience section with good action verbs"
    return max(0.0, min(100.0, score)), explanation


def _score_projects(
    resume_text: str,
    profile: dict,
) -> Tuple[float, str]:
    """Score projects section quality (0-100)."""
    score = 0.0
    reasons = []

    project_signals = count_project_signals(resume_text, profile)
    if project_signals >= 8:
        score += 50
    elif project_signals >= 5:
        score += 40
    elif project_signals >= 3:
        score += 28
    elif project_signals >= 1:
        score += 15
    else:
        score += 5
        reasons.append("Limited project indicators detected")

    # Check for project descriptions with tech keywords
    tech_in_projects = len(TECH_RE.findall(resume_text))
    if tech_in_projects >= 15:
        score += 30
    elif tech_in_projects >= 8:
        score += 22
    elif tech_in_projects >= 3:
        score += 12
    else:
        score += 5
        reasons.append("Projects lack sufficient technical detail")

    # Check for project count from parsed data
    parsed = profile.get("parsed_resume") or {}
    if isinstance(parsed, str):
        try:
            parsed = json.loads(parsed)
        except (json.JSONDecodeError, TypeError):
            parsed = {}
    projects = parsed.get("projects") or [] if isinstance(parsed, dict) else []
    if isinstance(projects, list) and len(projects) >= 3:
        score += 20
    elif isinstance(projects, list) and len(projects) >= 1:
        score += 12
    else:
        score += 3
        reasons.append("Add more portfolio projects")

    explanation = "; ".join(reasons) if reasons else f"Good project section with {project_signals} quality indicators"
    return min(100.0, score), explanation


def _score_education(resume_text: str) -> Tuple[float, str]:
    """Score education section (0-100)."""
    resume_lower = resume_text.lower()
    score = 0.0
    reasons = []

    edu_keywords = ["bachelor", "master", "degree", "b.tech", "b.sc", "m.tech",
                    "m.sc", "computer science", "engineering", "university",
                    "college", "diploma", "certification", "bootcamp"]
    edu_found = sum(1 for kw in edu_keywords if kw in resume_lower)

    if edu_found >= 3:
        score = 85.0
    elif edu_found >= 2:
        score = 70.0
    elif edu_found >= 1:
        score = 50.0
        reasons.append("Education section could be more detailed")
    else:
        score = 20.0
        reasons.append("No clear education section detected")

    # Check for relevant field
    relevant_fields = ["computer science", "software", "engineering", "information technology", "data science"]
    if any(f in resume_lower for f in relevant_fields):
        score = min(100.0, score + 15)
    else:
        reasons.append("Consider mentioning relevant coursework or field of study")

    explanation = "; ".join(reasons) if reasons else "Education section is well-structured"
    return min(100.0, score), explanation


def _score_technical_stack(user_skills: Set[str]) -> Tuple[float, str]:
    """Score technical stack breadth and modernity (0-100)."""
    score = 0.0
    reasons = []

    # Category coverage
    categories_covered = 0
    for cat_name, cat_skills in SKILL_CATEGORIES.items():
        if user_skills & set(cat_skills):
            categories_covered += 1

    if categories_covered >= 5:
        score += 50
    elif categories_covered >= 3:
        score += 35
    elif categories_covered >= 2:
        score += 22
    else:
        score += 10
        reasons.append("Narrow technical stack — expand to more areas")

    # Modernity
    modern = {"fastapi", "react", "docker", "kubernetes", "langchain", "llm",
              "typescript", "next.js", "generative ai", "ai agent"}
    modern_count = len(user_skills & modern)
    if modern_count >= 4:
        score += 50
    elif modern_count >= 2:
        score += 35
    elif modern_count >= 1:
        score += 20
    else:
        score += 8
        reasons.append("Consider learning modern technologies (Docker, TypeScript, etc.)")

    explanation = "; ".join(reasons) if reasons else f"Strong tech stack spanning {categories_covered} categories"
    return min(100.0, score), explanation


def _score_action_verbs(resume_text: str) -> Tuple[float, str]:
    """Score action verb usage in resume (0-100)."""
    resume_lower = resume_text.lower()
    found_verbs = [v for v in ACTION_VERBS if v in resume_lower]
    count = len(found_verbs)

    if count >= 10:
        return 95.0, f"Excellent action verb usage ({count} strong verbs)"
    elif count >= 7:
        return 80.0, f"Good action verb usage ({count} verbs)"
    elif count >= 4:
        return 60.0, f"{count} action verbs found; consider adding: developed, deployed, optimized"
    elif count >= 1:
        return 35.0, f"Only {count} action verb(s); bullets need stronger opening words"
    else:
        return 10.0, "No action verbs detected — rewrite bullets with verbs like: developed, built, deployed"


def _score_achievement_quantification(resume_text: str) -> Tuple[float, str]:
    """Score quantified achievements (0-100)."""
    # Look for numbers, percentages, metrics
    number_pattern = re.compile(r"\b\d+[%+]?\b")
    metric_keywords = ["reduced", "increased", "improved", "saved", "generated",
                       "grew", "scaled", "served", "processed", "handled"]

    numbers = number_pattern.findall(resume_text)
    resume_lower = resume_text.lower()
    metrics = sum(1 for kw in metric_keywords if kw in resume_lower)

    num_count = len(numbers)
    combined = num_count + metrics

    if combined >= 8:
        return 90.0, f"Strong quantification ({num_count} numbers, {metrics} metric verbs)"
    elif combined >= 5:
        return 70.0, f"Good quantification ({num_count} numbers); add more measurable outcomes"
    elif combined >= 2:
        return 45.0, f"Limited quantification; add specific numbers and impact metrics"
    else:
        return 15.0, "No quantified achievements; add numbers to show impact (e.g., 'Reduced load time by 40%')"


def _score_overall_structure(resume_text: str) -> Tuple[float, str]:
    """Score overall resume structure and readability (0-100)."""
    score = 0.0
    reasons = []

    lines = [l.strip() for l in resume_text.split("\n") if l.strip()]
    total_lines = len(lines)

    # Length balance
    if 20 <= total_lines <= 60:
        score += 35
    elif 10 <= total_lines < 20:
        score += 25
        reasons.append("Resume is short; consider adding more detail")
    elif total_lines > 60:
        score += 20
        reasons.append("Resume may be too long; consider condensing to 1-2 pages")
    else:
        score += 10
        reasons.append("Very short resume")

    # Paragraph vs bullet balance
    bullet_lines = sum(1 for l in lines if l.startswith(("-", "•", "*", "–")))
    bullet_ratio = bullet_lines / max(total_lines, 1)
    if 0.3 <= bullet_ratio <= 0.7:
        score += 35
    elif bullet_ratio > 0:
        score += 20
        reasons.append("Balance between bullets and paragraphs could be improved")
    else:
        score += 10
        reasons.append("Use bullet points for better ATS scanning")

    # Consistent formatting
    if total_lines >= 10:
        score += 30
    elif total_lines >= 5:
        score += 20
    else:
        score += 5

    explanation = "; ".join(reasons) if reasons else "Good overall structure and readability"
    return min(100.0, score), explanation


def calculate_ats_score(
    resume_text: str,
    user_skills: Set[str],
    target_keywords: Set[str],
    profile: dict,
) -> ATSScore:
    """
    Master ATS scoring function. Fully deterministic — no AI involved.
    Calculates scores across 10 categories and produces weighted overall.

    Args:
        resume_text: Raw resume text.
        user_skills: Extracted and expanded user skills.
        target_keywords: Keywords from target job/role.
        profile: User profile dict.

    Returns:
        ATSScore with overall, potential, and per-category breakdown.
    """
    logger.info("[OPTIMIZER] Calculating deterministic ATS score")

    categories: List[ATSScoreCategory] = []
    weighted_sum = 0.0

    # Scoring functions mapped to their weight keys
    scoring_pipeline = [
        ("Formatting & Structure", "formatting", lambda: _score_formatting(resume_text)),
        ("Keyword Coverage", "keyword_coverage", lambda: _score_keyword_coverage(resume_text, user_skills, target_keywords)),
        ("Skills Section", "skills_section", lambda: _score_skills_section(resume_text, user_skills)),
        ("Experience Quality", "experience", lambda: _score_experience(resume_text, profile)),
        ("Projects & Portfolio", "projects", lambda: _score_projects(resume_text, profile)),
        ("Education", "education", lambda: _score_education(resume_text)),
        ("Technical Stack", "technical_stack", lambda: _score_technical_stack(user_skills)),
        ("Action Verbs", "action_verbs", lambda: _score_action_verbs(resume_text)),
        ("Achievement Quantification", "achievement_quantification", lambda: _score_achievement_quantification(resume_text)),
        ("Overall Structure", "overall_structure", lambda: _score_overall_structure(resume_text)),
    ]

    for display_name, weight_key, scorer in scoring_pipeline:
        weight = ATS_WEIGHTS[weight_key]
        try:
            raw_score, explanation = scorer()
        except Exception as exc:
            logger.warning("[OPTIMIZER] Scoring failed for %s: %s", display_name, exc)
            raw_score, explanation = 50.0, "Unable to evaluate this category"

        cat = ATSScoreCategory(
            name=display_name,
            score=round(raw_score, 1),
            weight=weight,
            explanation=explanation,
        )
        categories.append(cat)
        weighted_sum += raw_score * (weight / 100.0)

    overall = calibrate_score(round(weighted_sum, 1))

    # Calculate potential score (assume all fixable issues are resolved)
    potential_weighted = 0.0
    for cat in categories:
        # Potential: each category can improve by up to 30 points
        potential = min(100.0, cat.score + 25.0)
        potential_weighted += potential * (cat.weight / 100.0)
    potential = calibrate_score(round(potential_weighted, 1))
    potential = max(potential, overall)  # Potential must be >= current

    score_label = "strong" if overall >= 75 else "moderate" if overall >= 55 else "needs improvement"
    summary = f"Your ATS score is {overall}/100 ({score_label}). With optimization, it could reach {potential}/100."

    logger.info("[OPTIMIZER] ATS Score: %.1f/100 (potential: %.1f/100)", overall, potential)

    return ATSScore(
        overall_score=overall,
        potential_score=potential,
        categories=categories,
        summary=summary,
    )


# ==============================================================================
# KEYWORD GAP ANALYSIS
# ==============================================================================

def analyze_keyword_gaps(
    resume_text: str,
    user_skills: Set[str],
    target_role: str,
    job_description: Optional[str] = None,
    profile: Optional[dict] = None,
) -> KeywordGapAnalysis:
    """
    Compare keywords from target job against resume, profile, and skills.
    Never recommends adding skills the user doesn't possess.
    Missing skills are flagged as "learn this", not "add this".

    Args:
        resume_text: Raw resume text.
        user_skills: Extracted user skills.
        target_role: Target role for keyword inference.
        job_description: Optional job description text.
        profile: Optional user profile dict.

    Returns:
        KeywordGapAnalysis with present, missing, and recommended keywords.
    """
    logger.info("[OPTIMIZER] Analyzing keyword gaps for: %s", target_role)

    # Extract target keywords from job description or infer from title
    target_keywords: Set[str] = set()
    if job_description:
        for m in TECH_RE.finditer(job_description):
            target_keywords.add(m.group(0).lower().strip())
    if not target_keywords:
        target_keywords = infer_skills_from_title(target_role)

    if not target_keywords:
        return KeywordGapAnalysis(
            target_role=target_role,
            keyword_match_percentage=0.0,
        )

    # Match user skills against target
    resume_lower = resume_text.lower()
    present: List[KeywordGap] = []
    missing: List[KeywordGap] = []
    recommended: List[KeywordGap] = []

    profile_skills = set()
    if profile:
        for item in profile.get("skills") or []:
            if isinstance(item, dict):
                name = item.get("name", "")
            elif isinstance(item, str):
                name = item
            else:
                continue
            if name:
                profile_skills.add(name.lower().strip())

    for kw in sorted(target_keywords):
        kw_lower = kw.lower()

        # Check presence in user skills or resume text
        in_skills = any(kw_lower in s or s in kw_lower for s in user_skills)
        in_resume = kw_lower in resume_lower
        in_profile = any(kw_lower in s or s in kw_lower for s in profile_skills)

        if in_skills or in_resume:
            source = "resume" if in_resume else "profile"
            present.append(KeywordGap(
                keyword=kw,
                status="present",
                source=source,
            ))
        elif in_profile:
            # User has the skill in profile but it's not visible in resume
            recommended.append(KeywordGap(
                keyword=kw,
                status="recommended",
                source="profile",
                recommendation=f"Add '{kw}' to your resume — it's in your profile but not visible to ATS",
            ))
        else:
            # SAFETY: User does NOT have this skill — recommend learning, not adding
            missing.append(KeywordGap(
                keyword=kw,
                status="missing",
                source="job_description",
                recommendation=f"Consider learning {kw} — do NOT add it until you have real experience",
            ))

    total = len(target_keywords)
    match_pct = (len(present) / total * 100) if total > 0 else 0.0

    logger.info(
        "[OPTIMIZER] Keyword analysis: %d present, %d missing, %d recommended (%.1f%% match)",
        len(present), len(missing), len(recommended), match_pct,
    )

    return KeywordGapAnalysis(
        target_role=target_role,
        present_keywords=present,
        missing_keywords=missing,
        recommended_keywords=recommended,
        keyword_match_percentage=round(match_pct, 1),
    )


# ==============================================================================
# SKILL OPTIMIZATION
# ==============================================================================

def optimize_skills(
    user_skills: Set[str],
    target_role: str,
) -> SkillOptimization:
    """
    Analyze current skill ordering and produce optimized groupings.
    Only reorganizes existing skills — never fabricates new ones.

    Args:
        user_skills: Current extracted user skills.
        target_role: Target role for relevance ordering.

    Returns:
        SkillOptimization with current skills and optimized groups.
    """
    logger.info("[OPTIMIZER] Optimizing skill organization for: %s", target_role)

    current = sorted(user_skills)
    groups: List[SkillGroup] = []
    categorized: Set[str] = set()
    visibility: List[str] = []
    notes: List[str] = []

    # Determine which skills are most relevant to target role
    target_skills = infer_skills_from_title(target_role)
    relevant_skills = user_skills & target_skills if target_skills else set()

    # Group skills by category
    for cat_name, cat_keywords in SKILL_CATEGORIES.items():
        cat_skills_lower = set(cat_keywords)
        matched_in_cat = [s for s in user_skills if s in cat_skills_lower]
        if matched_in_cat:
            # Sort by relevance to target role first
            matched_in_cat.sort(key=lambda s: (s not in relevant_skills, s))
            groups.append(SkillGroup(
                category=cat_name,
                skills=[s.title() for s in matched_in_cat],
            ))
            categorized.update(matched_in_cat)

    # Add uncategorized skills
    uncategorized = user_skills - categorized
    if uncategorized:
        groups.append(SkillGroup(
            category="Other",
            skills=[s.title() for s in sorted(uncategorized)],
        ))

    # Visibility suggestions for relevant skills
    if relevant_skills:
        top_relevant = sorted(relevant_skills)[:5]
        visibility = [
            f"Highlight '{s.title()}' — directly relevant to {target_role}"
            for s in top_relevant
            if s not in (user_skills - relevant_skills)  # Only if not already prominent
        ]

    # Relevance notes
    if target_skills:
        overlap = user_skills & target_skills
        if len(overlap) >= len(target_skills) * 0.7:
            notes.append(f"Strong skill alignment with {target_role} ({len(overlap)}/{len(target_skills)} core skills)")
        else:
            notes.append(f"Moderate skill alignment with {target_role} ({len(overlap)}/{len(target_skills)} core skills)")

    return SkillOptimization(
        current_skills=current,
        optimized_groups=groups,
        visibility_suggestions=visibility,
        relevance_notes=notes,
    )


# ==============================================================================
# PROJECT OPTIMIZATION
# ==============================================================================

def optimize_projects(
    resume_text: str,
    profile: dict,
    user_skills: Set[str],
    target_role: str,
) -> List[ProjectOptimization]:
    """
    Score each project for relevance to target role and recommend reordering.
    Never invents projects.

    Args:
        resume_text: Raw resume text.
        profile: User profile dict.
        user_skills: Extracted user skills.
        target_role: Target role for relevance scoring.

    Returns:
        List of ProjectOptimization with relevance scores and visibility recommendations.
    """
    logger.info("[OPTIMIZER] Optimizing project ordering for: %s", target_role)

    parsed = profile.get("parsed_resume") or {}
    if isinstance(parsed, str):
        try:
            parsed = json.loads(parsed)
        except (json.JSONDecodeError, TypeError):
            parsed = {}

    projects = []
    if isinstance(parsed, dict):
        projects = parsed.get("projects") or []
    if not isinstance(projects, list):
        projects = []

    if not projects:
        return []

    target_skills = infer_skills_from_title(target_role)
    optimizations: List[ProjectOptimization] = []

    for idx, proj in enumerate(projects):
        name = ""
        desc = ""
        if isinstance(proj, dict):
            name = proj.get("name", proj.get("title", f"Project {idx + 1}"))
            desc = proj.get("description", "")
        elif isinstance(proj, str):
            name = proj
        else:
            continue

        # Score relevance based on tech keyword overlap
        proj_text = f"{name} {desc}".lower()
        proj_techs = set(TECH_RE.findall(proj_text))
        overlap = proj_techs & target_skills if target_skills else set()
        quality_keywords = sum(1 for ind in PROJECT_QUALITY_INDICATORS if ind in proj_text)

        relevance = 0.0
        if target_skills:
            relevance = (len(overlap) / max(len(target_skills), 1)) * 70
        relevance += min(30.0, quality_keywords * 10)
        relevance = min(100.0, relevance)

        visibility = "highlight" if relevance >= 60 else "keep" if relevance >= 30 else "deprioritize"

        suggestions = []
        if overlap:
            suggestions.append(f"Emphasize: {', '.join(s.title() for s in sorted(overlap)[:3])}")
        if quality_keywords == 0:
            suggestions.append("Add more technical detail to the project description")
        if not desc:
            suggestions.append("Add a description showcasing technologies used and impact")

        optimizations.append(ProjectOptimization(
            project_name=name,
            relevance_score=round(relevance, 1),
            current_position=idx + 1,
            recommended_position=0,  # Will be set after sorting
            visibility=visibility,
            suggestions=suggestions,
        ))

    # Sort by relevance and assign recommended positions
    optimizations.sort(key=lambda p: p.relevance_score, reverse=True)
    for i, opt in enumerate(optimizations):
        opt.recommended_position = i + 1

    return optimizations


# ==============================================================================
# SECTION ANALYSIS
# ==============================================================================

def analyze_sections(
    resume_text: str,
    user_skills: Set[str],
    profile: dict,
    target_role: str,
) -> List[ResumeSectionFeedback]:
    """
    Evaluate each resume section and provide structured feedback.

    Returns:
        List of ResumeSectionFeedback for each detected section.
    """
    logger.info("[OPTIMIZER] Analyzing resume sections")

    sections: List[ResumeSectionFeedback] = []
    resume_lower = resume_text.lower()

    # Summary / Objective
    has_summary = any(kw in resume_lower for kw in ["summary", "objective", "about me", "profile"])
    sections.append(ResumeSectionFeedback(
        section_name="Summary / Objective",
        strengths=["Summary section present"] if has_summary else [],
        weaknesses=[] if has_summary else ["No summary/objective section detected"],
        suggestions=[
            "Add a 2-3 line professional summary tailored to " + target_role
        ] if not has_summary else [
            f"Ensure summary highlights your fit for {target_role}"
        ],
        priority="High" if not has_summary else "Medium",
        score=70.0 if has_summary else 20.0,
    ))

    # Skills
    skill_count = len(user_skills)
    skill_strengths = []
    skill_weaknesses = []
    if skill_count >= 10:
        skill_strengths.append(f"Strong skill set ({skill_count} skills detected)")
    if skill_count < 6:
        skill_weaknesses.append("Limited skills listed")

    sections.append(ResumeSectionFeedback(
        section_name="Skills",
        strengths=skill_strengths,
        weaknesses=skill_weaknesses,
        suggestions=["Organize skills into categories (Backend, Frontend, DevOps, etc.)"],
        priority="High",
        score=min(100, skill_count * 8),
    ))

    # Projects
    proj_signals = count_project_signals(resume_text, profile)
    sections.append(ResumeSectionFeedback(
        section_name="Projects",
        strengths=[f"{proj_signals} quality indicators found"] if proj_signals >= 3 else [],
        weaknesses=["Few project quality indicators"] if proj_signals < 3 else [],
        suggestions=[
            "Add technical details to project descriptions",
            f"Prioritize projects relevant to {target_role}",
        ],
        priority="High" if proj_signals < 3 else "Medium",
        score=min(100, proj_signals * 12),
    ))

    # Experience
    prod_signals = count_production_signals(resume_text, profile)
    exp_strengths = []
    exp_weaknesses = []
    if prod_signals >= 3:
        exp_strengths.append(f"{prod_signals} production experience indicators")
    else:
        exp_weaknesses.append("Limited production experience evidence")

    sections.append(ResumeSectionFeedback(
        section_name="Experience",
        strengths=exp_strengths,
        weaknesses=exp_weaknesses,
        suggestions=[
            "Use action verbs to start each bullet point",
            "Quantify impact where possible",
        ],
        priority="High" if prod_signals < 2 else "Medium",
        score=min(100, prod_signals * 15 + 20),
    ))

    # Education
    edu_score, edu_explanation = _score_education(resume_text)
    sections.append(ResumeSectionFeedback(
        section_name="Education",
        strengths=["Education section present"] if edu_score >= 50 else [],
        weaknesses=[edu_explanation] if edu_score < 50 else [],
        suggestions=["Add relevant coursework or certifications"] if edu_score < 70 else [],
        priority="Low",
        score=edu_score,
    ))

    # Certifications
    has_certs = any(kw in resume_lower for kw in ["certification", "certified", "certificate", "aws certified", "google certified"])
    sections.append(ResumeSectionFeedback(
        section_name="Certifications",
        strengths=["Certifications detected"] if has_certs else [],
        weaknesses=[] if has_certs else ["No certifications listed"],
        suggestions=[
            "Consider adding relevant certifications (AWS, Google Cloud, etc.)"
        ] if not has_certs else [],
        priority="Low",
        score=70.0 if has_certs else 15.0,
    ))

    return sections


# ==============================================================================
# BULLET POINT ANALYSIS (Deterministic Detection)
# ==============================================================================

def _detect_weak_bullets(resume_text: str) -> List[str]:
    """
    Detect weak bullet points in the resume using deterministic patterns.
    Returns a list of weak bullet text lines.
    """
    weak = []
    for line in resume_text.split("\n"):
        stripped = line.strip()
        if not stripped or len(stripped) < 10:
            continue
        # Strip common bullet markers before matching
        cleaned = re.sub(r"^[-•*–]\s*", "", stripped)
        if not cleaned or len(cleaned) < 8:
            continue
        for pattern in WEAK_BULLET_PATTERNS:
            if pattern.search(cleaned):
                weak.append(cleaned)
                break
    return weak[:10]  # Cap at 10 to avoid overwhelming output


# ==============================================================================
# AI ENHANCEMENT LAYER
# ==============================================================================

def _generate_ai_enhancements(
    resume_text: str,
    user_skills: Set[str],
    target_role: str,
    weak_bullets: List[str],
    profile: dict,
    job_description: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Single AI call for generating human-readable enhancements.
    AI is responsible ONLY for wording, not scoring.

    Returns dict with:
        - bullet_improvements: List of {original, improved, reasoning, category}
        - recruiter_feedback: Dict matching RecruiterFeedback fields
        - experience_suggestions: List of strings

    Raises Exception on AI failure (caller should handle fallback).
    """
    logger.info("[OPTIMIZER] Generating AI-powered enhancements")

    bullets_context = "\n".join(f"- {b}" for b in weak_bullets[:6]) if weak_bullets else "No weak bullets detected."

    truncated_resume = resume_text[:3000] if resume_text else ""
    truncated_jd = job_description[:1500] if job_description else "Not provided"

    system_prompt = (
        "You are an elite ATS Optimization Specialist and Senior Technical Recruiter at a top tech company.\n\n"
        "CRITICAL RULES:\n"
        "1. NEVER invent experience, skills, projects, metrics, or achievements.\n"
        "2. NEVER add skills the user does not possess.\n"
        "3. NEVER exaggerate or fabricate numbers.\n"
        "4. Only improve WORDING and PRESENTATION of existing content.\n"
        "5. If measurable impact is unknown, suggest the user quantify it themselves.\n"
        "6. Base recruiter feedback ONLY on evidence in the resume.\n"
        "7. All suggestions must be truthful and evidence-based.\n\n"
        "Respond with a JSON object matching this exact structure:\n"
        "{\n"
        '  "bullet_improvements": [\n'
        '    {"original": "...", "improved": "...", "reasoning": "...", "category": "action_verb|quantification|specificity|technical_detail"}\n'
        "  ],\n"
        '  "recruiter_feedback": {\n'
        '    "overall_impression": "...",\n'
        '    "biggest_strengths": ["..."],\n'
        '    "biggest_weaknesses": ["..."],\n'
        '    "shortlisting_probability": "High|Medium|Low",\n'
        '    "interview_readiness": "...",\n'
        '    "portfolio_quality": "...",\n'
        '    "ats_compatibility": "...",\n'
        '    "key_recommendations": ["..."]\n'
        "  },\n"
        '  "experience_suggestions": ["..."]\n'
        "}"
    )

    user_prompt = (
        f"Target Role: {target_role}\n"
        f"User Skills: {', '.join(sorted(user_skills)[:20])}\n\n"
        f"Resume (truncated):\n{truncated_resume}\n\n"
        f"Job Description:\n{truncated_jd}\n\n"
        f"Weak Bullets to Improve:\n{bullets_context}\n\n"
        "Generate improvements and recruiter feedback based ONLY on the evidence above."
    )

    response = generate_chat_completion(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.25,
        max_tokens=2000,
        response_format={"type": "json_object"},
    )

    raw = response.choices[0].message.content.strip()
    result = json.loads(raw)

    logger.info("[OPTIMIZER] AI enhancements generated successfully")
    return result


# ==============================================================================
# FALLBACK ENGINE (Deterministic-only optimization)
# ==============================================================================

def _generate_fallback_recruiter_feedback(
    user_skills: Set[str],
    resume_text: str,
    profile: dict,
    target_role: str,
    ats_score: float,
) -> RecruiterFeedback:
    """
    Generate deterministic recruiter feedback when AI is unavailable.
    All assessments are based on measurable evidence.
    """
    logger.info("[OPTIMIZER] Generating fallback recruiter feedback")

    prod_signals = count_production_signals(resume_text, profile)
    proj_signals = count_project_signals(resume_text, profile)
    skill_count = len(user_skills)

    # Determine strengths from evidence
    strengths = []
    if skill_count >= 12:
        strengths.append(f"Broad technical skill set ({skill_count} skills)")
    if prod_signals >= 3:
        strengths.append(f"Production experience indicators ({prod_signals} signals)")
    if proj_signals >= 5:
        strengths.append(f"Strong project portfolio ({proj_signals} quality signals)")
    target_skills = infer_skills_from_title(target_role)
    if target_skills:
        overlap = user_skills & target_skills
        if len(overlap) >= len(target_skills) * 0.6:
            strengths.append(f"Strong alignment with {target_role} requirements")

    if not strengths:
        strengths.append("Resume uploaded and structured")

    # Determine weaknesses
    weaknesses = []
    if skill_count < 6:
        weaknesses.append("Limited skills listed")
    if prod_signals < 2:
        weaknesses.append("Limited production experience evidence")
    if proj_signals < 3:
        weaknesses.append("Few project quality indicators")

    # Shortlisting probability
    if ats_score >= 75:
        probability = "High"
    elif ats_score >= 55:
        probability = "Medium"
    else:
        probability = "Low"

    # Interview readiness
    if ats_score >= 70 and prod_signals >= 2:
        readiness = "Ready for technical screening; prepare with targeted practice"
    elif ats_score >= 50:
        readiness = "Moderate readiness; address key gaps before applying"
    else:
        readiness = "Needs improvement; focus on building portfolio and skills first"

    # Portfolio quality
    if proj_signals >= 6:
        portfolio = "Strong portfolio with diverse, quality projects"
    elif proj_signals >= 3:
        portfolio = "Decent portfolio; add more technical depth to project descriptions"
    else:
        portfolio = "Portfolio needs more substantial, technical projects"

    # Recommendations
    recommendations = []
    if ats_score < 70:
        recommendations.append("Improve keyword coverage for target roles")
    if prod_signals < 3:
        recommendations.append("Highlight production experience and deployment details")
    recommendations.append(f"Tailor resume specifically for {target_role} positions")

    return RecruiterFeedback(
        overall_impression=f"Candidate with {skill_count} technical skills and {prod_signals} production indicators targeting {target_role}",
        biggest_strengths=strengths,
        biggest_weaknesses=weaknesses,
        shortlisting_probability=probability,
        interview_readiness=readiness,
        portfolio_quality=portfolio,
        ats_compatibility=f"ATS score: {ats_score}/100",
        key_recommendations=recommendations,
    )


def _generate_fallback_bullet_improvements(weak_bullets: List[str]) -> List[BulletPointImprovement]:
    """Generate deterministic bullet improvements when AI is unavailable."""
    improvements = []
    for bullet in weak_bullets[:5]:
        improved = bullet
        category = "action_verb"
        reasoning = ""

        # Replace weak openings with stronger ones
        for pattern in WEAK_BULLET_PATTERNS:
            match = pattern.search(bullet)
            if match:
                weak_phrase = match.group(0)
                if "worked on" in weak_phrase.lower():
                    improved = re.sub(pattern, "Developed", bullet, count=1)
                    reasoning = "Replace 'Worked on' with a specific action verb"
                elif "helped" in weak_phrase.lower() or "assisted" in weak_phrase.lower():
                    improved = re.sub(pattern, "Contributed to", bullet, count=1)
                    reasoning = "Replace vague 'helped/assisted' with a specific contribution"
                elif "used" in weak_phrase.lower() or "utilized" in weak_phrase.lower():
                    improved = re.sub(pattern, "Leveraged", bullet, count=1)
                    reasoning = "Lead with the impact, not the tool"
                    category = "specificity"
                elif "responsible for" in weak_phrase.lower():
                    improved = re.sub(pattern, "Managed", bullet, count=1)
                    reasoning = "Replace passive 'responsible for' with active verb"
                else:
                    improved = re.sub(pattern, "Implemented", bullet, count=1)
                    reasoning = "Use a strong action verb to start the bullet"
                break

        if improved != bullet:
            improvements.append(BulletPointImprovement(
                original=bullet,
                improved=improved,
                reasoning=reasoning,
                category=category,
            ))

    return improvements


# ==============================================================================
# OPTIMIZATION CHECKLIST GENERATOR
# ==============================================================================

def _generate_checklist(
    ats_score: ATSScore,
    keyword_analysis: KeywordGapAnalysis,
    skill_optimization: SkillOptimization,
    project_optimizations: List[ProjectOptimization],
    section_feedback: List[ResumeSectionFeedback],
) -> List[OptimizationChecklistItem]:
    """Generate a prioritized optimization checklist from all analyses."""
    items: List[OptimizationChecklistItem] = []

    # High priority items
    for kw in keyword_analysis.recommended_keywords[:3]:
        items.append(OptimizationChecklistItem(
            priority="High",
            action=kw.recommendation,
            category="keywords",
        ))

    for proj in project_optimizations:
        if proj.current_position != proj.recommended_position and proj.visibility == "highlight":
            items.append(OptimizationChecklistItem(
                priority="High",
                action=f"Move '{proj.project_name}' to position #{proj.recommended_position} (currently #{proj.current_position})",
                category="projects",
            ))

    for section in section_feedback:
        if section.priority == "High" and section.weaknesses:
            items.append(OptimizationChecklistItem(
                priority="High",
                action=section.suggestions[0] if section.suggestions else section.weaknesses[0],
                category="formatting",
            ))

    # Medium priority items
    for cat in ats_score.categories:
        if cat.score < 50:
            items.append(OptimizationChecklistItem(
                priority="Medium",
                action=f"Improve {cat.name}: {cat.explanation}",
                category="formatting",
            ))

    for note in skill_optimization.visibility_suggestions[:3]:
        items.append(OptimizationChecklistItem(
            priority="Medium",
            action=note,
            category="skills",
        ))

    # Low priority items
    for kw in keyword_analysis.missing_keywords[:3]:
        items.append(OptimizationChecklistItem(
            priority="Low",
            action=kw.recommendation,
            category="keywords",
        ))

    for section in section_feedback:
        if section.priority == "Low" and section.suggestions:
            items.append(OptimizationChecklistItem(
                priority="Low",
                action=section.suggestions[0],
                category="formatting",
            ))

    return items


# ==============================================================================
# MAIN ENTRY POINT
# ==============================================================================

def optimize_resume(
    resume_text: str = "",
    user_profile: Optional[dict] = None,
    target_role: Optional[str] = None,
    job_description: Optional[str] = None,
    resume_analysis: Optional[str] = None,
    skill_sync: Optional[dict] = None,
    job_match: Optional[dict] = None,
) -> ResumeOptimizationResponse:
    """
    Main orchestration function for resume optimization.
    Runs the complete optimization pipeline and returns structured results.

    All scoring is deterministic. AI enhances wording only.
    Falls back to deterministic-only results on AI failure.
    Never crashes.

    Args:
        resume_text: Raw resume text content.
        user_profile: User profile dict from Django.
        target_role: Target role for optimization (falls back to profile).
        job_description: Optional specific job description.
        resume_analysis: Optional pre-existing resume analysis.
        skill_sync: Optional skill sync data.
        job_match: Optional job match data.

    Returns:
        ResumeOptimizationResponse with complete optimization data.
    """
    logger.info("[OPTIMIZER] Starting resume optimization pipeline")

    # Input validation
    if not user_profile:
        user_profile = {}
    if not resume_text:
        resume_text = user_profile.get("resume_text", "")
    if not resume_text:
        logger.warning("[OPTIMIZER] No resume text available")
        return ResumeOptimizationResponse(
            target_role=target_role or "Not specified",
            summary=OptimizationSummary(
                current_ats_score=0.0,
                potential_ats_score=0.0,
                resume_strength="No resume available",
                top_improvements=["Upload your resume to get optimization recommendations"],
                recruiter_verdict="Cannot evaluate without a resume",
                overall_recommendation="Please upload your resume first to receive optimization recommendations.",
            ),
        )

    # Resolve target role
    resolved_role = (
        target_role
        or user_profile.get("target_role")
        or user_profile.get("preferred_role")
        or "Software Developer"
    )

    try:
        # 1. Extract skills (reuse shared utility)
        user_skills = extract_skills_from_profile(user_profile, resume_text)
        logger.info("[OPTIMIZER] Extracted %d skills", len(user_skills))

        # 2. Determine target keywords
        target_keywords: Set[str] = set()
        if job_description:
            for m in TECH_RE.finditer(job_description):
                target_keywords.add(m.group(0).lower().strip())
        if not target_keywords:
            target_keywords = infer_skills_from_title(resolved_role)

        # 3. Deterministic ATS Scoring
        ats = calculate_ats_score(resume_text, user_skills, target_keywords, user_profile)
        logger.info("[OPTIMIZER] ATS calculation complete: %.1f/100", ats.overall_score)

        # 4. Keyword Gap Analysis
        keywords = analyze_keyword_gaps(
            resume_text, user_skills, resolved_role, job_description, user_profile,
        )
        logger.info("[OPTIMIZER] Keyword analysis complete: %.1f%% match", keywords.keyword_match_percentage)

        # 5. Skill Optimization
        skills = optimize_skills(user_skills, resolved_role)

        # 6. Project Optimization
        projects = optimize_projects(resume_text, user_profile, user_skills, resolved_role)

        # 7. Section Analysis
        sections = analyze_sections(resume_text, user_skills, user_profile, resolved_role)

        # 8. Detect weak bullets for AI enhancement
        weak_bullets = _detect_weak_bullets(resume_text)

        # 9. AI Enhancement Layer (with fallback)
        recruiter = None
        bullet_improvements: List[BulletPointImprovement] = []
        experience_opts: List[ExperienceOptimization] = []

        try:
            logger.info("[OPTIMIZER] Attempting AI-powered enhancements")
            ai_result = _generate_ai_enhancements(
                resume_text, user_skills, resolved_role,
                weak_bullets, user_profile, job_description,
            )

            # Parse bullet improvements
            for bi in ai_result.get("bullet_improvements", []):
                if isinstance(bi, dict) and bi.get("original") and bi.get("improved"):
                    bullet_improvements.append(BulletPointImprovement(
                        original=bi["original"],
                        improved=bi["improved"],
                        reasoning=bi.get("reasoning", ""),
                        category=bi.get("category", ""),
                    ))

            # Parse recruiter feedback
            rf = ai_result.get("recruiter_feedback", {})
            if isinstance(rf, dict):
                recruiter = RecruiterFeedback(
                    overall_impression=rf.get("overall_impression", ""),
                    biggest_strengths=rf.get("biggest_strengths", []),
                    biggest_weaknesses=rf.get("biggest_weaknesses", []),
                    shortlisting_probability=rf.get("shortlisting_probability", ""),
                    interview_readiness=rf.get("interview_readiness", ""),
                    portfolio_quality=rf.get("portfolio_quality", ""),
                    ats_compatibility=rf.get("ats_compatibility", ""),
                    key_recommendations=rf.get("key_recommendations", []),
                )

            # Parse experience suggestions
            exp_suggestions = ai_result.get("experience_suggestions", [])
            if exp_suggestions and isinstance(exp_suggestions, list):
                experience_opts.append(ExperienceOptimization(
                    role="General",
                    overall_suggestions=exp_suggestions,
                    bullet_improvements=bullet_improvements,
                ))

            logger.info("[OPTIMIZER] AI enhancements applied successfully")

        except Exception as ai_error:
            logger.warning(
                "[OPTIMIZER] AI enhancement failed, using fallback: %s", str(ai_error)
            )
            # Fallback: deterministic bullet improvements
            bullet_improvements = _generate_fallback_bullet_improvements(weak_bullets)
            if bullet_improvements:
                experience_opts.append(ExperienceOptimization(
                    role="General",
                    overall_suggestions=[
                        "Use action verbs (developed, built, deployed) to start bullets",
                        "Quantify impact where possible (reduced by X%, handled Y requests)",
                        f"Highlight technologies relevant to {resolved_role}",
                    ],
                    bullet_improvements=bullet_improvements,
                ))

        # Fallback recruiter feedback if AI didn't produce it
        if not recruiter:
            recruiter = _generate_fallback_recruiter_feedback(
                user_skills, resume_text, user_profile, resolved_role, ats.overall_score,
            )

        # 10. Generate Optimization Checklist
        checklist = _generate_checklist(ats, keywords, skills, projects, sections)

        # 11. Build Summary
        strength = "Strong" if ats.overall_score >= 75 else "Moderate" if ats.overall_score >= 55 else "Needs Improvement"
        top_improvements = []
        for item in checklist:
            if item.priority == "High" and len(top_improvements) < 5:
                top_improvements.append(item.action)
        if not top_improvements:
            top_improvements.append("Your resume is well-optimized; consider minor refinements")

        summary = OptimizationSummary(
            current_ats_score=ats.overall_score,
            potential_ats_score=ats.potential_score,
            resume_strength=strength,
            top_improvements=top_improvements,
            recruiter_verdict=recruiter.overall_impression,
            overall_recommendation=(
                f"Your resume scores {ats.overall_score}/100 for ATS compatibility. "
                f"With the recommended optimizations, it could reach {ats.potential_score}/100. "
                f"{recruiter.shortlisting_probability} shortlisting probability for {resolved_role} roles."
            ),
        )

        logger.info("[OPTIMIZER] Optimization pipeline complete")

        return ResumeOptimizationResponse(
            target_role=resolved_role,
            ats_score=ats,
            keyword_analysis=keywords,
            skill_optimization=skills,
            project_optimizations=projects,
            experience_optimizations=experience_opts,
            section_feedback=sections,
            recruiter_feedback=recruiter,
            optimization_checklist=checklist,
            summary=summary,
        )

    except Exception as exc:
        logger.error("[OPTIMIZER] Critical error in optimization pipeline: %s", str(exc))
        # Ultimate fail-safe — never crash
        return ResumeOptimizationResponse(
            target_role=resolved_role,
            summary=OptimizationSummary(
                current_ats_score=0.0,
                potential_ats_score=0.0,
                resume_strength="Unable to evaluate",
                top_improvements=["An error occurred; please try again"],
                recruiter_verdict="Unable to evaluate at this time",
                overall_recommendation="We encountered an issue. Please try again later.",
            ),
        )


# ==============================================================================
# SIMPLE ENTRY POINT (matches resume_tool.run pattern)
# ==============================================================================

def run(
    message: str = None,
    auth_token: str = None,
    resume_text: str = "",
    user_profile: Optional[dict] = None,
    target_role: Optional[str] = None,
    job_description: Optional[str] = None,
) -> str:
    """
    Simple entry point for the Resume Optimizer tool.
    Orchestrates the full pipeline and returns formatted output.

    Args:
        message: User's message (used for context).
        auth_token: User's auth token (not used directly — data passed in).
        resume_text: Raw resume text.
        user_profile: User profile dict.
        target_role: Optional target role.
        job_description: Optional job description.

    Returns:
        Formatted markdown string ready for chat display.
    """
    result = optimize_resume(
        resume_text=resume_text,
        user_profile=user_profile,
        target_role=target_role,
        job_description=job_description,
    )
    return format_resume_optimization(result)


# ==============================================================================
# PREMIUM FORMATTER
# ==============================================================================

def format_resume_optimization(response: ResumeOptimizationResponse) -> str:
    """
    Format the ResumeOptimizationResponse into a concise executive dashboard.
    Designed for rapid readability and an actionable, premium SaaS feel.
    Detailed data is hidden but accessible via specific follow-up queries.
    """
    out: List[str] = []
    role_label = f" for {response.target_role}" if response.target_role else ""
    s = response.summary
    rf = response.recruiter_feedback

    # ── 1. Executive Summary & Header ─────────────────────────────────────────
    out.append(f"## Resume Optimization{role_label}\n")
    if rf and rf.overall_impression:
        out.append(f"> _{rf.overall_impression}_\n")

    # ── 2. ATS Score (Concise) ────────────────────────────────────────────────
    ats = response.ats_score
    if ats.overall_score > 0:
        out.append(f"### 📊 ATS Score: `{ats.overall_score}/100` (Potential: `{ats.potential_score}/100`)")
        out.append(f"_{ats.summary}_\n")

    # ── 3. Top 3 Strengths ────────────────────────────────────────────────────
    if rf and rf.biggest_strengths:
        out.append("### 🌟 Top Strengths")
        for strength in rf.biggest_strengths[:3]:
            out.append(f"- ✓ {strength}")
        out.append("")

    # ── 4. Top 3 High-Impact Improvements ─────────────────────────────────────
    if response.optimization_checklist:
        # Filter high/medium priority
        improvements = [i.action for i in response.optimization_checklist if i.priority in ("High", "Medium")]
        if not improvements:
            improvements = s.top_improvements
        
        if improvements:
            out.append("### ⚡ High-Impact Improvements")
            for imp in improvements[:3]:
                out.append(f"- [ ] {imp}")
            out.append("")

    # ── 5. Example Bullet Rewrite ─────────────────────────────────────────────
    all_bullet_improvements = []
    for exp_opt in response.experience_optimizations:
        all_bullet_improvements.extend(exp_opt.bullet_improvements)

    if all_bullet_improvements:
        out.append("### ✍️ Example Bullet Rewrite")
        bi = all_bullet_improvements[0]
        out.append(f"**Before:** _{bi.original}_")
        out.append(f"**After:** _{bi.improved}_")
        if bi.reasoning:
            out.append(f"> {bi.reasoning}")
        out.append("")

    # ── 6. Recruiter Verdict ──────────────────────────────────────────────────
    if rf and rf.shortlisting_probability:
        out.append("### 🎯 Recruiter Verdict")
        out.append(f"- **Shortlisting Probability:** `{rf.shortlisting_probability}`")
        out.append(f"- **Interview Readiness:** {rf.interview_readiness}")
        out.append("")

    # ── 7. Today's Priority ───────────────────────────────────────────────────
    if response.optimization_checklist:
        top_priority = next((i.action for i in response.optimization_checklist if i.priority == "High"), None)
        if not top_priority and s.top_improvements:
            top_priority = s.top_improvements[0]
            
        if top_priority:
            out.append("### 🚀 Today's Priority")
            out.append(f"**{top_priority}**\n")

    # Add hint for details
    out.append("---\n_💡 Want a deep dive? Try asking: \"Show ATS breakdown\", \"Show keyword analysis\", or \"Show detailed optimization report\"._")

    return "\n".join(out)
