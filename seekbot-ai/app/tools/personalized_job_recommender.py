"""
Personalized Job Recommender for SeekBot AI.

Finds and ranks matching jobs for a user based on their profile,
resume, skills, projects, and career goals. All match scoring is
deterministic and transparent.  OpenAI is invoked exactly once (batch)
to generate human-readable explanations, guidance, and next steps.

Architecture:
    FastAPI tool → Django /jobs/search/ API (job listings)
                 → OpenAI gpt-4o-mini     (explanations, batch)

Scoring breakdown (deterministic, 0-100):
    Required skill overlap  60 pts  — fraction of required skills user has
    Preferred skill overlap 15 pts  — tech keywords found in description
    Experience alignment    15 pts  — required_experience_years vs user's
    Work-mode alignment      5 pts  — remote/onsite preference match
    Target-role alignment    5 pts  — job title contains target keywords

Priority labels:
    Apply Now           85+
    Strong Fit          70 – 84
    Stretch Opportunity 50 – 69
    (below 50 excluded)

Public API:
    recommend_jobs_for_user(...)  →  PersonalizedJobRecommendationsResponse
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Optional

import requests
from app.core.config import DJANGO_API_BASE_URL, DJANGO_INTERNAL_TOKEN
from app.core.openai_client import generate_chat_completion
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Module-level singletons
# ---------------------------------------------------------------------------

# Sent on every internal SeekBot → Django request so Django can identify
# (and optionally rate-limit) calls from this service.
_INTERNAL_HEADERS: dict[str, str] = (
    {"X-Internal-Token": DJANGO_INTERNAL_TOKEN} if DJANGO_INTERNAL_TOKEN else {}
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Only corporate jobs are relevant on an AI tech-career platform.
_JOB_TYPE_FILTER: str = "corporate"

# Deterministic scoring weights — must sum to 100.
_WEIGHT_REQUIRED_SKILLS: int = 60
_WEIGHT_PREFERRED_SKILLS: int = 15
_WEIGHT_EXPERIENCE: int = 15
_WEIGHT_WORK_MODE: int = 5
_WEIGHT_ROLE_ALIGNMENT: int = 5

# Priority thresholds.
_THRESHOLD_APPLY_NOW: float = 85.0
_THRESHOLD_STRONG_FIT: float = 70.0
_THRESHOLD_STRETCH: float = 50.0

# Maximum jobs fetched before client-side scoring.
_MAX_FETCH: int = 100

# OpenAI settings (consistent with the rest of the project).
_AI_MODEL: str = "Qwen/Qwen3-14B"
_AI_TEMPERATURE: float = 0.3
_AI_MAX_TOKENS_INSIGHTS: int = 3000
_AI_MAX_TOKENS_SUMMARY: int = 600

# Regex that recognises common tech keywords in raw text (resume / description).
_TECH_RE: re.Pattern[str] = re.compile(
    r"\b("
    # Languages
    r"python|javascript|typescript|java|kotlin|swift|golang|go|rust|"
    r"c\+\+|c#|php|ruby|scala|dart|r\b|"
    # Frontend frameworks / libs
    r"react|vue|angular|next\.?js|nuxt|svelte|remix|"
    # Backend frameworks
    r"django|fastapi|flask|express|nest\.?js|spring|laravel|rails|gin|fiber|"
    # Runtimes
    r"node\.?js|deno|bun|"
    # Databases
    r"postgresql|postgres|mysql|mongodb|redis|sqlite|cassandra|dynamodb|"
    r"elasticsearch|supabase|firebase|"
    # Cloud / DevOps / Infra
    r"aws|azure|gcp|docker|kubernetes|k8s|terraform|ansible|linux|nginx|"
    # Data / ML
    r"machine learning|deep learning|tensorflow|pytorch|scikit-learn|"
    r"pandas|numpy|spark|hadoop|kafka|airflow|"
    # Web / API
    r"html|css|sass|tailwind|bootstrap|graphql|rest|grpc|websocket|"
    # Version control / tools
    r"git|github|gitlab|jira|"
    # Generic
    r"sql|nosql|api|orm|microservices|ci/cd"
    r")\b",
    re.IGNORECASE,
)

# Stop-words removed before keyword pre-filtering.
_FILTER_STOP_WORDS: frozenset[str] = frozenset(
    {
        "job",
        "jobs",
        "role",
        "roles",
        "me",
        "my",
        "i",
        "a",
        "an",
        "the",
        "for",
        "with",
        "in",
        "at",
        "want",
        "looking",
        "show",
        "best",
        "find",
        "recommend",
        "suggest",
        "what",
        "which",
        "are",
        "should",
        "apply",
        "right",
        "now",
        "current",
        "available",
        "good",
        "fit",
        "match",
        "please",
        "can",
        "you",
        "give",
        "get",
        "tell",
    }
)


# ---------------------------------------------------------------------------
# Pydantic models (public)
# ---------------------------------------------------------------------------


class SkillGap(BaseModel):
    """A single skill the user is missing for a given job."""

    skill: str = Field(..., description="Name of the missing skill.")
    importance: str = Field(
        ...,
        description="How critical this skill is to the role: High, Medium, or Low.",
    )
    recommendation: str = Field(
        ...,
        description="Actionable guidance on how to acquire this skill.",
    )


class RecommendedJob(BaseModel):
    """One fully-scored and AI-enriched job recommendation."""

    job_id: int = Field(..., description="Django primary key of the job.")
    title: str = Field(..., description="Job title / position.")
    company: str = Field(..., description="Hiring company name.")
    location: str = Field(..., description="Job location.")
    employment_type: Optional[str] = Field(
        default=None, description="full_time or part_time (when available)."
    )
    match_score: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Deterministic fit score 0–100.",
    )
    recommendation_reason: str = Field(
        ...,
        description="AI-generated explanation of why this role matches the user.",
    )
    matching_skills: list[str] = Field(
        default_factory=list,
        description="Required skills the user already possesses.",
    )
    missing_skills: list[str] = Field(
        default_factory=list,
        description="Required skills the user currently lacks.",
    )
    skill_gaps: list[SkillGap] = Field(
        default_factory=list,
        description="Detailed gap analysis with prioritised learning guidance.",
    )
    priority: str = Field(
        ...,
        description=(
            "Apply Now (85+) | Strong Fit (70–84) | Stretch Opportunity (50–69)."
        ),
    )
    next_steps: list[str] = Field(
        default_factory=list,
        description="Concrete immediate actions the user should take.",
    )
    is_remote: bool = Field(
        default=False,
        description="Whether the job is remote (for frontend badge display).",
    )
    created_at: str = Field(
        default="",
        description="ISO date string of when the job was posted.",
    )


class PersonalizedJobRecommendationsResponse(BaseModel):
    """Full recommendation payload returned by recommend_jobs_for_user."""

    target_role: Optional[str] = Field(
        default=None,
        description="The role or job type the user is targeting.",
    )
    summary: str = Field(
        ...,
        description="Human-friendly overview of the recommendation results.",
    )
    total_jobs_evaluated: int = Field(
        ...,
        description="Number of active jobs considered during scoring.",
    )
    total_recommendations: int = Field(
        ...,
        description="Number of jobs that passed the minimum score threshold.",
    )
    recommended_jobs: list[RecommendedJob] = Field(
        default_factory=list,
        description="Ranked list of recommendations (highest match first).",
    )
    strategic_advice: list[str] = Field(
        default_factory=list,
        description="High-level career strategy tips tailored to this user.",
    )


# ---------------------------------------------------------------------------
# Internal scored-job container (not exported)
# ---------------------------------------------------------------------------


class _ScoredJob(BaseModel):
    """Intermediate representation used between scoring and AI enrichment."""

    raw: dict[str, Any]
    match_score: float
    matching_skills: list[str]
    missing_skills: list[str]
    priority: str


# ---------------------------------------------------------------------------
# Helper: skill extraction
# ---------------------------------------------------------------------------


def _extract_user_skills(
    user_profile: dict[str, Any],
    resume_text: Optional[str],
) -> set[str]:
    """
    Build a normalised lowercase set of all skills known about the user.

    Sources (highest to lowest reliability):
      1. profile.skills list  — skills the user explicitly added
      2. profile.parsed_resume JSON — fields extracted by the resume parser
      3. resume_text argument — caller-supplied raw resume text
      4. profile.resume_text — resume text stored on the Django profile

    Args:
        user_profile: Profile dict from the Django API.
        resume_text:  Optional raw plaintext resume supplied by the caller.

    Returns:
        Set of lowercase, stripped skill strings.
    """
    skills: set[str] = set()

    # ── 1. Explicit profile skills ────────────────────────────────────────────
    for item in user_profile.get("skills") or []:
        if isinstance(item, dict):
            name = item.get("name", "")
        elif isinstance(item, str):
            name = item
        else:
            continue
        if name and isinstance(name, str):
            skills.add(name.lower().strip())

    # ── 2. parsed_resume JSON ─────────────────────────────────────────────────
    parsed: Any = user_profile.get("parsed_resume") or {}
    if isinstance(parsed, str):
        try:
            parsed = json.loads(parsed)
        except (json.JSONDecodeError, TypeError):
            parsed = {}

    if isinstance(parsed, dict):
        for key in (
            "skills",
            "technologies",
            "tech_stack",
            "frameworks",
            "languages",
            "tools",
        ):
            val = parsed.get(key)
            if isinstance(val, list):
                for s in val:
                    if isinstance(s, str) and s.strip():
                        skills.add(s.lower().strip())
            elif isinstance(val, str) and val.strip():
                for part in val.split(","):
                    part = part.strip()
                    if part:
                        skills.add(part.lower())

    # ── 3. Caller-supplied resume text ───────────────────────────────────────
    for text_source in (resume_text, user_profile.get("resume_text")):
        if text_source and isinstance(text_source, str):
            for m in _TECH_RE.finditer(text_source):
                skills.add(m.group(0).lower().strip())
            break  # Use only the first non-empty source to avoid duplication

    skills.discard("")
    return skills


# ---------------------------------------------------------------------------
# Helper: fetch jobs from Django
# ---------------------------------------------------------------------------


def _fetch_active_jobs(
    extra_filters: Optional[dict[str, str]] = None,
) -> list[dict[str, Any]]:
    """
    Retrieve active corporate jobs from the Django /jobs/search/ endpoint.

    The endpoint returns `JobSearchSerializer` data:
        id, title, company_name, location, is_remote,
        job_type, skills (= required_experience_fields), created_at

    Uses the internal service token so no user auth is required.
    Returns an empty list on any network or parsing error.

    Args:
        extra_filters: Additional query params forwarded to the Django API.

    Returns:
        List of raw job dicts.
    """
    url = f"{DJANGO_API_BASE_URL}/jobs/search/"
    params: dict[str, str] = {"job_type": _JOB_TYPE_FILTER}
    if extra_filters:
        params.update(extra_filters)

    try:
        response = requests.get(
            url,
            params=params,
            headers=_INTERNAL_HEADERS,
            timeout=15,
        )
        response.raise_for_status()
        data = response.json()
        jobs: list[dict[str, Any]] = data.get("results", [])
        logger.info("Fetched %d corporate jobs from Django (/jobs/search/)", len(jobs))
        return jobs[:_MAX_FETCH]
    except requests.exceptions.Timeout:
        logger.error("Timeout fetching jobs from Django")
        return []
    except requests.exceptions.RequestException as exc:
        logger.error("Django job fetch failed: %s", exc)
        return []
    except (ValueError, KeyError, AttributeError) as exc:
        logger.error("Unexpected job response format from Django: %s", exc)
        return []


# ---------------------------------------------------------------------------
# Helper: keyword pre-filter
# ---------------------------------------------------------------------------


def _pre_filter_jobs(
    jobs: list[dict[str, Any]],
    target_role: Optional[str],
    user_query: Optional[str],
) -> list[dict[str, Any]]:
    """
    Quickly narrow the job list using keyword matching before heavier scoring.

    This is a heuristic shortlist step — it never permanently disqualifies
    jobs.  If filtering removes everything, the full list is returned so the
    scoring step can still find matches.

    Args:
        jobs:        All fetched jobs.
        target_role: Role the user is targeting (e.g., "backend developer").
        user_query:  Free-text chat query.

    Returns:
        Filtered (or original) list of jobs.
    """
    if not target_role and not user_query:
        return jobs

    combined = " ".join(filter(None, [target_role, user_query])).lower()
    tokens = set(re.findall(r"\b\w+\b", combined)) - _FILTER_STOP_WORDS

    if not tokens:
        return jobs

    filtered: list[dict[str, Any]] = []
    for job in jobs:
        searchable = " ".join(
            str(job.get(k) or "").lower()
            for k in ("title", "company_name", "location", "skills")
        )
        if any(tok in searchable for tok in tokens):
            filtered.append(job)

    # Guard: never return an empty list due to overly-specific tokens.
    return filtered if filtered else jobs


# ---------------------------------------------------------------------------
# Helper: extract job required skills
# ---------------------------------------------------------------------------


def _extract_job_skills(job: dict[str, Any]) -> list[str]:
    """
    Parse the comma-separated skills / required_experience_fields field from
    a job dict into a cleaned lowercase list.

    Args:
        job: Raw job dict (JobSearchSerializer or JobSerializer payload).

    Returns:
        Lowercase list of trimmed skill tokens.  Empty list if none.
    """
    raw = job.get("skills") or job.get("required_experience_fields") or ""
    if not isinstance(raw, str) or not raw.strip():
        return []
    return [s.strip().lower() for s in raw.split(",") if s.strip()]


# ---------------------------------------------------------------------------
# Helper: infer user experience years
# ---------------------------------------------------------------------------


def _infer_user_experience_years(user_profile: dict[str, Any]) -> Optional[int]:
    """
    Attempt to determine the user's total years of professional experience.

    Checks direct profile fields first, then parsed_resume JSON sub-fields.

    Args:
        user_profile: Profile dict from the Django API.

    Returns:
        Integer years, or None if the information is not available.
    """
    for key in ("experience_years", "years_of_experience", "total_experience"):
        val = user_profile.get(key)
        if val is not None:
            try:
                return int(float(str(val)))
            except (TypeError, ValueError):
                pass

    parsed: Any = user_profile.get("parsed_resume") or {}
    if isinstance(parsed, str):
        try:
            parsed = json.loads(parsed)
        except (json.JSONDecodeError, TypeError):
            parsed = {}

    if isinstance(parsed, dict):
        for key in (
            "experience_years",
            "total_experience",
            "years_of_experience",
            "work_experience_years",
        ):
            val = parsed.get(key)
            if val is not None:
                try:
                    return int(float(str(val)))
                except (TypeError, ValueError):
                    pass

    return None


# ---------------------------------------------------------------------------
# Helper: infer user work-mode preference
# ---------------------------------------------------------------------------


def _infer_user_work_mode_preference(user_profile: dict[str, Any]) -> Optional[str]:
    """
    Try to determine whether the user prefers remote, onsite, or hybrid work.

    Args:
        user_profile: Profile dict.

    Returns:
        One of "remote", "onsite", "hybrid", or None if unknown.
    """
    _valid = {"remote", "onsite", "hybrid"}

    for key in ("preferred_work_mode", "work_mode_preference", "work_mode"):
        val = user_profile.get(key)
        if isinstance(val, str) and val.strip().lower() in _valid:
            return val.strip().lower()

    parsed: Any = user_profile.get("parsed_resume") or {}
    if isinstance(parsed, str):
        try:
            parsed = json.loads(parsed)
        except (json.JSONDecodeError, TypeError):
            parsed = {}
    if isinstance(parsed, dict):
        for key in ("preferred_work_mode", "work_preference"):
            val = parsed.get(key)
            if isinstance(val, str) and val.strip().lower() in _valid:
                return val.strip().lower()

    return None


# ---------------------------------------------------------------------------
# Helper: deterministic match scoring
# ---------------------------------------------------------------------------


def _calculate_match_score(
    user_skills: set[str],
    job: dict[str, Any],
    target_role: Optional[str],
    user_profile: dict[str, Any],
) -> tuple[float, list[str], list[str]]:
    """
    Compute a transparent, reproducible 0–100 match score for a user-job pair.

    Scoring breakdown
    -----------------
    Required skill overlap   60 pts
        Fraction of the job's required skills the user already has.
        Partial credit (30 pts) when the job lists no required skills.

    Preferred skill overlap  15 pts
        Tech keywords extracted from the job description that the user has.
        Half credit when no description is available.

    Experience alignment     15 pts
        Sliding scale based on how many years short the user is.
        Full credit when no requirement is stated.

    Work-mode alignment       5 pts
        Full credit on exact match or hybrid job; partial otherwise.
        Half credit when preference is unknown.

    Target-role alignment     5 pts
        Full credit when any target-role token appears in the job title.

    Args:
        user_skills:  Normalised set of the user's skills (lowercase).
        job:          Raw job dict from Django (JobSearchSerializer fields).
        target_role:  Optional role the user is targeting.
        user_profile: Full profile dict (for experience / preference inference).

    Returns:
        (match_score, matching_skills, missing_skills)
        match_score is clamped to [0.0, 100.0].
    """
    score: float = 0.0

    # ── Required skills (60 pts) ─────────────────────────────────────────────
    required_skills = _extract_job_skills(job)
    matching_skills: list[str] = []
    missing_skills: list[str] = []

    if required_skills:
        for skill in required_skills:
            # Fuzzy substring check: handles "react" ↔ "reactjs", etc.
            matched = any(skill in us or us in skill for us in user_skills)
            (matching_skills if matched else missing_skills).append(skill)
        score += (len(matching_skills) / len(required_skills)) * _WEIGHT_REQUIRED_SKILLS
    else:
        # No requirements listed — neutral (half credit)
        score += _WEIGHT_REQUIRED_SKILLS * 0.5

    # ── Preferred skill overlap from description (15 pts) ─────────────────────
    # Note: /jobs/search/ returns 'skills' but not 'description'.
    # We still attempt to parse any description field if present.
    description = str(job.get("description") or "").lower()
    if description:
        desc_tech = {m.group(0).lower() for m in _TECH_RE.finditer(description)}
        extra_tech = desc_tech - {s.lower() for s in required_skills}
        if extra_tech:
            extra_hit = sum(
                1 for s in extra_tech if any(s in us or us in s for us in user_skills)
            )
            score += (extra_hit / len(extra_tech)) * _WEIGHT_PREFERRED_SKILLS
        else:
            score += _WEIGHT_PREFERRED_SKILLS * 0.5
    else:
        score += _WEIGHT_PREFERRED_SKILLS * 0.5

    # ── Experience alignment (15 pts) ─────────────────────────────────────────
    required_exp: Optional[int] = job.get("required_experience_years")
    user_exp: Optional[int] = _infer_user_experience_years(user_profile)

    if required_exp is None:
        score += _WEIGHT_EXPERIENCE  # no requirement → full credit
    elif user_exp is None:
        score += _WEIGHT_EXPERIENCE * 0.5  # unknown → neutral
    elif user_exp >= required_exp:
        score += _WEIGHT_EXPERIENCE  # meets or exceeds
    elif user_exp >= required_exp - 1:
        score += _WEIGHT_EXPERIENCE * 0.80  # 1 year short
    elif user_exp >= max(required_exp - 2, 0):
        score += _WEIGHT_EXPERIENCE * 0.50  # 2 years short
    else:
        score += _WEIGHT_EXPERIENCE * 0.20  # significantly under

    # ── Work-mode alignment (5 pts) ──────────────────────────────────────────
    # /jobs/search/ returns is_remote (bool) instead of work_mode string.
    is_remote_flag: Optional[bool] = job.get("is_remote")
    job_work_mode: str = (
        job.get("work_mode") or ("remote" if is_remote_flag else "onsite")
    ).lower()

    user_pref = _infer_user_work_mode_preference(user_profile)
    if user_pref:
        if user_pref == job_work_mode or job_work_mode == "hybrid":
            score += _WEIGHT_WORK_MODE
        else:
            score += _WEIGHT_WORK_MODE * 0.3
    else:
        score += _WEIGHT_WORK_MODE * 0.5  # unknown pref → neutral

    # ── Target-role alignment (5 pts) ────────────────────────────────────────
    if target_role:
        job_title = str(job.get("title") or "").lower()
        role_tokens = (
            set(re.findall(r"\b\w+\b", target_role.lower())) - _FILTER_STOP_WORDS
        )
        if role_tokens and any(tok in job_title for tok in role_tokens):
            score += _WEIGHT_ROLE_ALIGNMENT

    return round(max(0.0, min(100.0, score)), 2), matching_skills, missing_skills


# ---------------------------------------------------------------------------
# Helper: priority label
# ---------------------------------------------------------------------------


def _determine_priority(score: float) -> str:
    """
    Map a numeric score to a human-readable priority label.

    Args:
        score: Match score in [50.0, 100.0].

    Returns:
        "Apply Now" | "Strong Fit" | "Stretch Opportunity"
    """
    if score >= _THRESHOLD_APPLY_NOW:
        return "Apply Now"
    if score >= _THRESHOLD_STRONG_FIT:
        return "Strong Fit"
    return "Stretch Opportunity"


# ---------------------------------------------------------------------------
# Helper: AI-generated batch insights
# ---------------------------------------------------------------------------


def _generate_ai_insights(
    scored_jobs: list[_ScoredJob],
    user_profile: dict[str, Any],
    user_skills: set[str],
    target_role: Optional[str],
    resume_text: Optional[str],
    user_query: Optional[str],
) -> dict[int, dict[str, Any]]:
    """
    Call OpenAI once with a batched payload to produce human-readable
    recommendation reasons, skill-gap guidance, and next steps for every
    scored job.

    The model acts as a senior recruiter + technical career coach.
    Temperature is kept low (0.3) for consistent, professional output.

    Returns:
        Mapping of job-list index (0-based) → insight dict containing:
            recommendation_reason  (str)
            skill_gaps             (list[dict])
            next_steps             (list[str])

        Returns an empty dict on any OpenAI error; callers fall back to
        _generate_fallback_insights in that case.

    Args:
        scored_jobs:  Top-ranked jobs that passed the score threshold.
        user_profile: Full user profile dict.
        user_skills:  Normalised user skill set.
        target_role:  User's target role (if any).
        resume_text:  Raw resume text (if any).
        user_query:   Original chat query.
    """
    if not scored_jobs:
        return {}

    user_name = (
        user_profile.get("full_name") or user_profile.get("username") or "the candidate"
    )
    skill_list = ", ".join(sorted(user_skills)) if user_skills else "not specified"
    exp_years = _infer_user_experience_years(user_profile)
    exp_str = f"{exp_years} year(s)" if exp_years is not None else "not specified"

    # Compact job summaries sent to OpenAI (avoid sending full description text)
    jobs_payload = [
        {
            "index": i,
            "title": sj.raw.get("title") or sj.raw.get("position") or "Untitled",
            "company": sj.raw.get("company_name") or sj.raw.get("company") or "Unknown",
            "match_score": sj.match_score,
            "matching_skills": sj.matching_skills,
            "missing_skills": sj.missing_skills[:8],  # Cap to control prompt size
            "required_experience_years": sj.raw.get("required_experience_years"),
            "work_mode": sj.raw.get("work_mode")
            or ("remote" if sj.raw.get("is_remote") else "onsite"),
            "location": sj.raw.get("location") or "",
        }
        for i, sj in enumerate(scored_jobs)
    ]

    system_prompt = (
        "You are a senior technical recruiter, career coach, and resume strategist "
        "on an AI-powered career platform called JobSeek.\n\n"
        "Your task: generate honest, practical, and encouraging job recommendation "
        "insights for a candidate.\n\n"
        "Rules:\n"
        "- Be specific to the candidate's actual skills and the job requirements.\n"
        "- recommendation_reason: 2–3 concise sentences. Reference real skills/role.\n"
        "- skill_gaps: only truly missing skills. Importance = High if the skill is "
        "  central to the role, Medium if beneficial, Low if optional.\n"
        "- next_steps: 2–4 immediate, concrete, actionable steps.\n"
        "- Language: direct second-person ('you', 'your').\n"
        "- Output: valid JSON object only — no markdown, no commentary."
    )

    user_content = (
        f"Candidate name: {user_name}\n"
        f"Candidate skills: {skill_list}\n"
        f"Candidate experience: {exp_str}\n"
        f"Target role: {target_role or 'not specified'}\n"
        f"User's question: {user_query or 'not specified'}\n\n"
        "Analyse the following jobs and return a JSON object with this exact structure:\n"
        "{\n"
        '  "recommendations": [\n'
        "    {\n"
        '      "index": <int>,\n'
        '      "recommendation_reason": "<2-3 sentence personalised reason>",\n'
        '      "skill_gaps": [\n'
        "        {\n"
        '          "skill": "<skill name>",\n'
        '          "importance": "High" | "Medium" | "Low",\n'
        '          "recommendation": "<one actionable sentence>"\n'
        "        }\n"
        "      ],\n"
        '      "next_steps": ["<step>", "<step>"]\n'
        "    }\n"
        "  ]\n"
        "}\n\n"
        f"Jobs to analyse:\n{json.dumps(jobs_payload, indent=2)}"
    )

    try:
        response = _openai_client.chat.completions.create(
            model=_AI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            temperature=_AI_TEMPERATURE,
            max_tokens=_AI_MAX_TOKENS_INSIGHTS,
            response_format={"type": "json_object"},
        )
        raw_content = response.choices[0].message.content.strip()
        parsed: Any = json.loads(raw_content)

        # Unwrap: expect {"recommendations": [...]}
        if isinstance(parsed, dict):
            items = parsed.get("recommendations")
            if not isinstance(items, list):
                # Fallback: look for any list value in the dict
                items = next((v for v in parsed.values() if isinstance(v, list)), [])
        elif isinstance(parsed, list):
            items = parsed
        else:
            logger.warning("AI insights returned unexpected type: %s", type(parsed))
            return {}

        result: dict[int, dict[str, Any]] = {}
        for item in items:
            if not isinstance(item, dict):
                continue
            idx = item.get("index")
            if idx is not None:
                result[int(idx)] = item

        logger.info("AI insights generated for %d jobs", len(result))
        return result

    except json.JSONDecodeError as exc:
        logger.error("AI insights JSON parse error: %s", exc)
        return {}
    except Exception as exc:
        logger.error("OpenAI batch insights call failed: %s", exc)
        return {}


# ---------------------------------------------------------------------------
# Helper: rule-based fallback insights
# ---------------------------------------------------------------------------


def _generate_fallback_insights(
    scored_job: _ScoredJob,
    user_skills: set[str],
    target_role: Optional[str],
) -> dict[str, Any]:
    """
    Produce deterministic recommendation text when OpenAI is unavailable.

    Used as a transparent, always-reliable fallback so the tool never
    returns empty guidance.

    Args:
        scored_job:  The scored job that needs insights.
        user_skills: Normalised user skill set.
        target_role: User's target role.

    Returns:
        Dict with keys: recommendation_reason, skill_gaps, next_steps.
    """
    raw = scored_job.raw
    title = raw.get("title") or raw.get("position") or "this role"
    company = raw.get("company_name") or raw.get("company") or "this company"
    score = scored_job.match_score

    # Recommendation reason — differentiated by priority band
    if score >= _THRESHOLD_APPLY_NOW:
        reason = (
            f"Your skills are an excellent match for {title} at {company}. "
            f"You already have {len(scored_job.matching_skills)} of the key required "
            "skills, making this a top-priority application — submit today."
        )
    elif score >= _THRESHOLD_STRONG_FIT:
        top_matches = ", ".join(scored_job.matching_skills[:3])
        reason = (
            f"You are a strong candidate for {title} at {company}. "
            f"Your proficiency in {top_matches or 'the core technologies'} covers the "
            "primary requirements, and a small amount of upskilling would make you "
            "fully qualified."
        )
    else:
        role_hint = f" toward a {target_role} career" if target_role else ""
        reason = (
            f"This {title} role at {company} is a stretch opportunity aligned with "
            f"your growth direction{role_hint}. Addressing the skill gaps in parallel "
            "with applying proactively is a sound career-building strategy."
        )

    # Skill gaps — first five missing skills, descending importance
    skill_gaps: list[dict[str, str]] = [
        {
            "skill": skill,
            "importance": "High" if i < 2 else ("Medium" if i < 4 else "Low"),
            "recommendation": (
                f"Build {skill} skills through the official documentation and a "
                "small hands-on project. Add the project to your GitHub portfolio."
            ),
        }
        for i, skill in enumerate(scored_job.missing_skills[:5])
    ]

    # Next steps — concrete and actionable
    next_steps: list[str] = []
    if scored_job.missing_skills:
        next_steps.append(
            f"Start learning {scored_job.missing_skills[0]} — "
            "it is the highest-priority gap for this role."
        )
    if scored_job.matching_skills:
        skills_str = ", ".join(scored_job.matching_skills[:3])
        next_steps.append(
            f"Update your resume to prominently feature your {skills_str} experience."
        )
    next_steps.append(
        f"Submit your application to {company} promptly "
        "to stay ahead of the applicant pool."
    )
    if len(scored_job.missing_skills) > 2:
        next_steps.append(
            "Build one small project that combines the missing skills "
            "to strengthen your portfolio before applying."
        )

    return {
        "recommendation_reason": reason,
        "skill_gaps": skill_gaps,
        "next_steps": next_steps,
    }


# ---------------------------------------------------------------------------
# Helper: overall summary
# ---------------------------------------------------------------------------


def _build_summary(
    total_evaluated: int,
    scored_jobs: list[_ScoredJob],
    target_role: Optional[str],
    user_skills: set[str],
) -> str:
    """
    Compose a concise, human-friendly summary of the recommendation results.

    Args:
        total_evaluated: Jobs that were considered by the scorer.
        scored_jobs:     Jobs that passed the 50-point threshold (sorted).
        target_role:     User's target role (if any).
        user_skills:     User's skill set.

    Returns:
        Short paragraph suitable for the SeekBot chat UI.
    """
    n = len(scored_jobs)

    if n == 0:
        base = (
            f"I evaluated {total_evaluated} active corporate job listing(s) but "
            "couldn't find any roles with a match score above 50%. "
        )
        if not user_skills:
            base += (
                "Your profile doesn't appear to have any skills listed yet. "
                "Adding your technical skills, uploading a resume, or specifying "
                "a target role will significantly improve future recommendations."
            )
        else:
            hint = f" for {target_role} roles" if target_role else ""
            base += (
                f"Try broadening your search{hint} or upskilling in the technologies "
                "most common in your target field."
            )
        return base

    apply_now = sum(1 for sj in scored_jobs if sj.priority == "Apply Now")
    strong_fit = sum(1 for sj in scored_jobs if sj.priority == "Strong Fit")
    stretch = sum(1 for sj in scored_jobs if sj.priority == "Stretch Opportunity")
    top_score = scored_jobs[0].match_score

    role_hint = f" for {target_role} roles" if target_role else ""
    parts: list[str] = []
    if apply_now:
        parts.append(f"{apply_now} Apply Now (85%+ match)")
    if strong_fit:
        parts.append(f"{strong_fit} Strong Fit (70–84%)")
    if stretch:
        parts.append(
            f"{stretch} Stretch Opportunit{'y' if stretch == 1 else 'ies'} (50–69%)"
        )

    distribution = " — " + ", ".join(parts) + "." if parts else "."

    return (
        f"Out of {total_evaluated} active listing(s), I found "
        f"{n} strong recommendation(s){role_hint}{distribution} "
        f"Your highest match score is {top_score:.0f}%."
    )


# ---------------------------------------------------------------------------
# Helper: strategic advice
# ---------------------------------------------------------------------------


def _build_strategic_advice(
    scored_jobs: list[_ScoredJob],
    user_skills: set[str],
    target_role: Optional[str],
    user_profile: dict[str, Any],
) -> list[str]:
    """
    Generate 3–5 high-level, rule-based career strategy tips tailored to
    this specific user's situation.

    Covers: profile completeness, top missing skills across all recommended
    jobs, experience level, and role-specificity.

    Args:
        scored_jobs:  Jobs that passed the score threshold.
        user_skills:  User's skill set.
        target_role:  Desired role.
        user_profile: Full profile dict.

    Returns:
        List of up to 5 strategic advice strings.
    """
    advice: list[str] = []

    # ── Profile completeness ──────────────────────────────────────────────────
    missing_items: list[str] = []
    if not (user_profile.get("resume") or user_profile.get("resume_text")):
        missing_items.append("resume")
    if not user_profile.get("linkedin_url"):
        missing_items.append("LinkedIn URL")
    if not user_profile.get("github_url"):
        missing_items.append("GitHub URL")
    if missing_items:
        advice.append(
            f"Complete your profile by adding: {', '.join(missing_items)}. "
            "Most corporate job applications on JobSeek require these before you can apply."
        )

    # ── Empty skill profile ───────────────────────────────────────────────────
    if not user_skills:
        advice.append(
            "Add your technical skills to your profile and upload a resume to unlock "
            "accurate match scores and personalised recommendations."
        )

    # ── Most-needed skills across all recommended jobs ────────────────────────
    if scored_jobs:
        skill_freq: dict[str, int] = {}
        for sj in scored_jobs:
            for ms in sj.missing_skills:
                skill_freq[ms] = skill_freq.get(ms, 0) + 1
        top_missing = sorted(skill_freq.items(), key=lambda x: x[1], reverse=True)[:3]
        if top_missing:
            names = [m[0] for m in top_missing]
            advice.append(
                f"The skills most frequently required across your recommended jobs are "
                f"{', '.join(names)}. Learning these will unlock the most new opportunities."
            )

    # ── Experience-level specific advice ─────────────────────────────────────
    exp = _infer_user_experience_years(user_profile)
    if exp is not None and exp == 0:
        advice.append(
            "As a fresher, build 2–3 real-world projects and push them to GitHub. "
            "Demonstrable work consistently matters more than years of experience "
            "at the entry level."
        )
    elif exp is not None and 1 <= exp <= 2:
        advice.append(
            "With 1–2 years of experience, deep-specialising in one tech stack will "
            "set you apart from other early-career candidates with similar backgrounds."
        )

    # ── Target-role guidance ──────────────────────────────────────────────────
    if target_role:
        advice.append(
            f"For {target_role} roles, focus on your Apply Now matches first — "
            "they represent the closest alignment to your current profile and are "
            "your highest-probability applications."
        )
    else:
        advice.append(
            "Setting a specific target role improves recommendation precision "
            "and gives you a clear north star for your upskilling plan."
        )

    return advice[:5]


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def recommend_jobs_for_user(
    user_profile: dict[str, Any],
    resume_text: Optional[str] = None,
    target_role: Optional[str] = None,
    user_query: Optional[str] = None,
    limit: int = 10,
) -> PersonalizedJobRecommendationsResponse:
    """
    Generate personalised, ranked job recommendations for a user.

    Full workflow
    -------------
    1.  Validate and sanitise all inputs.
    2.  Extract the user's skills from profile, parsed_resume, and resume text.
    3.  Fetch active corporate jobs from the Django backend.
    4.  Optionally pre-filter by target role / user-query keywords.
    5.  Score every job deterministically (0–100, multi-factor).
    6.  Exclude jobs below the 50-point minimum threshold.
    7.  Rank by score descending; keep the top `limit` results.
    8.  Call OpenAI once (batched) for recommendation reasons, skill-gap
        guidance, and next steps.
    9.  Fall back to rule-based insights if OpenAI is unavailable.
    10. Assemble and return a fully-populated Pydantic response.

    Args:
        user_profile:
            Dict containing any combination of: skills, parsed_resume,
            resume_text, full_name, experience_years, preferred_work_mode,
            linkedin_url, github_url.  Missing keys are handled gracefully.
        resume_text:
            Raw resume plaintext.  Supplements profile.resume_text if both
            are present; the caller-supplied value takes precedence.
        target_role:
            Free-text role the user is aiming for (e.g., "backend developer",
            "React frontend engineer").  Improves filtering and scoring.
        user_query:
            Original chat message (e.g., "What jobs should I apply for now?").
            Used for keyword-level pre-filtering only.
        limit:
            Maximum recommendations to return.  Clamped to [1, 50].

    Returns:
        PersonalizedJobRecommendationsResponse — always populated, never
        raises; errors surface through the response's summary field.
    """

    # ── 1. Validate inputs ────────────────────────────────────────────────────
    if not isinstance(user_profile, dict):
        logger.warning(
            "recommend_jobs_for_user received non-dict user_profile (%s); using {}",
            type(user_profile),
        )
        user_profile = {}

    limit = max(1, min(int(limit), 50))

    # Sanitise free-text strings: strip whitespace and apply safety length caps.
    if target_role and isinstance(target_role, str):
        target_role = target_role.strip()[:200] or None
    if user_query and isinstance(user_query, str):
        user_query = user_query.strip()[:500] or None
    if resume_text and isinstance(resume_text, str):
        resume_text = resume_text.strip()[:50_000] or None

    logger.info(
        "Job recommendations requested | target_role=%r | limit=%d | query=%r",
        target_role,
        limit,
        (user_query or "")[:80],
    )

    # ── 2. Extract user skills ────────────────────────────────────────────────
    user_skills = _extract_user_skills(user_profile, resume_text)
    logger.info("User skill set: %d skill(s) identified", len(user_skills))

    # ── 3. Fetch jobs ─────────────────────────────────────────────────────────
    all_jobs = _fetch_active_jobs()

    if not all_jobs:
        logger.warning("No jobs retrieved from Django — returning empty response")
        return PersonalizedJobRecommendationsResponse(
            target_role=target_role,
            summary=(
                "I wasn't able to retrieve job listings at this moment. "
                "The jobs service may be temporarily unavailable — please try again shortly."
            ),
            total_jobs_evaluated=0,
            total_recommendations=0,
            recommended_jobs=[],
            strategic_advice=_build_strategic_advice(
                [], user_skills, target_role, user_profile
            ),
        )

    # ── 4. Pre-filter by role / query ─────────────────────────────────────────
    candidate_jobs = _pre_filter_jobs(all_jobs, target_role, user_query)
    logger.info(
        "Pre-filter result: %d → %d candidate job(s)",
        len(all_jobs),
        len(candidate_jobs),
    )

    # ── 5 & 6. Score and threshold-filter ────────────────────────────────────
    scored: list[_ScoredJob] = []
    for raw_job in candidate_jobs:
        try:
            score, matching, missing = _calculate_match_score(
                user_skills, raw_job, target_role, user_profile
            )
        except Exception as exc:
            logger.warning(
                "Scoring failed for job id=%s: %s — skipping",
                raw_job.get("id"),
                exc,
            )
            continue

        if score < _THRESHOLD_STRETCH:
            continue  # Below minimum quality threshold — discard

        scored.append(
            _ScoredJob(
                raw=raw_job,
                match_score=score,
                matching_skills=matching,
                missing_skills=missing,
                priority=_determine_priority(score),
            )
        )

    logger.info(
        "%d job(s) passed the %.0f-point threshold out of %d candidate(s)",
        len(scored),
        _THRESHOLD_STRETCH,
        len(candidate_jobs),
    )

    # ── 7. Rank and cap ───────────────────────────────────────────────────────
    scored.sort(key=lambda sj: sj.match_score, reverse=True)
    top_scored = scored[:limit]

    # ── 8. AI explanations — single batched call ──────────────────────────────
    ai_insights = _generate_ai_insights(
        top_scored, user_profile, user_skills, target_role, resume_text, user_query
    )

    # ── 9. Assemble RecommendedJob objects ────────────────────────────────────
    recommended: list[RecommendedJob] = []
    for i, sj in enumerate(top_scored):
        raw = sj.raw
        insight = ai_insights.get(i) or {}

        if insight:
            recommendation_reason = str(
                insight.get("recommendation_reason") or ""
            ).strip()
            raw_gaps = insight.get("skill_gaps") or []
            raw_steps = insight.get("next_steps") or []
        else:
            # AI unavailable or index not returned — use rule-based fallback
            fallback = _generate_fallback_insights(sj, user_skills, target_role)
            recommendation_reason = fallback["recommendation_reason"]
            raw_gaps = fallback["skill_gaps"]
            raw_steps = fallback["next_steps"]

        # Validate and normalise SkillGap objects
        skill_gaps: list[SkillGap] = []
        for gap in raw_gaps if isinstance(raw_gaps, list) else []:
            if not isinstance(gap, dict):
                continue
            skill_name = str(gap.get("skill") or "").strip()
            importance = str(gap.get("importance") or "Medium").strip().capitalize()
            reco = str(gap.get("recommendation") or "").strip()
            if not skill_name:
                continue
            if importance not in ("High", "Medium", "Low"):
                importance = "Medium"
            skill_gaps.append(
                SkillGap(
                    skill=skill_name,
                    importance=importance,
                    recommendation=reco
                    or (
                        f"Study {skill_name} through its official documentation "
                        "and build a small demo project to show proficiency."
                    ),
                )
            )

        # Normalise next_steps
        next_steps: list[str] = [
            str(s).strip()
            for s in (raw_steps if isinstance(raw_steps, list) else [])
            if str(s).strip()
        ]

        # Resolve title: JobSearchSerializer stores it as 'title'; full JobSerializer
        # stores position/work.  Support both gracefully.
        title = str(
            raw.get("title")
            or raw.get("position")
            or raw.get("work")
            or "Untitled Role"
        )
        company = str(
            raw.get("company_name") or raw.get("company") or "Unknown Company"
        )

        recommended.append(
            RecommendedJob(
                job_id=int(raw.get("id") or 0),
                title=title,
                company=company,
                location=str(raw.get("location") or "Not specified"),
                employment_type=raw.get("type") or raw.get("employment_type") or None,
                match_score=sj.match_score,
                recommendation_reason=recommendation_reason,
                matching_skills=sj.matching_skills,
                missing_skills=sj.missing_skills,
                skill_gaps=skill_gaps,
                priority=sj.priority,
                next_steps=next_steps,
                is_remote=bool(raw.get("is_remote", False)),
                created_at=str(raw.get("created_at") or ""),
            )
        )

    # ── 10. Build and return final response ───────────────────────────────────
    summary = _build_summary(
        total_evaluated=len(candidate_jobs),
        scored_jobs=top_scored,
        target_role=target_role,
        user_skills=user_skills,
    )

    strategic_advice = _build_strategic_advice(
        scored_jobs=top_scored,
        user_skills=user_skills,
        target_role=target_role,
        user_profile=user_profile,
    )

    logger.info(
        "Recommendations complete | %d result(s) | top_score=%.1f%%",
        len(recommended),
        top_scored[0].match_score if top_scored else 0.0,
    )

    return PersonalizedJobRecommendationsResponse(
        target_role=target_role,
        summary=summary,
        total_jobs_evaluated=len(candidate_jobs),
        total_recommendations=len(recommended),
        recommended_jobs=recommended,
        strategic_advice=strategic_advice,
    )


# ---------------------------------------------------------------------------
# Public exports
# ---------------------------------------------------------------------------

__all__ = [
    "recommend_jobs_for_user",
    "PersonalizedJobRecommendationsResponse",
    "RecommendedJob",
    "SkillGap",
]
