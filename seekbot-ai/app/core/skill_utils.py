"""
Shared skill utilities for SeekBot AI tools.

Contains reusable functions and constants for skill extraction, matching,
and analysis that are shared across multiple tools (application_strategy_tool,
resume_optimizer_tool, personalized_job_recommender, etc.).

Extracted to avoid tight coupling between tools and prevent circular imports.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Dict, Optional, Set

logger = logging.getLogger(__name__)


# ==============================================================================
# TECHNOLOGY KEYWORD REGEX
# ==============================================================================

TECH_RE: re.Pattern[str] = re.compile(
    r"\b("
    # Languages
    r"python|javascript|typescript|java|kotlin|swift|golang|go|rust|"
    r"c\+\+|c#|php|ruby|scala|dart|"
    # Frontend frameworks / libs
    r"react|vue|angular|next\.?js|nuxt|svelte|remix|"
    # Backend frameworks
    r"django|fastapi|flask|express|nest\.?js|spring|laravel|rails|gin|fiber|"
    # Runtimes
    r"node\.?js|deno|bun|"
    # Databases
    r"postgresql|postgres|mysql|mongodb|redis|sqlite|cassandra|dynamodb|"
    r"elasticsearch|supabase|firebase|pinecone|weaviate|chromadb|"
    # Cloud / DevOps / Infra
    r"aws|azure|gcp|docker|kubernetes|k8s|terraform|ansible|linux|nginx|"
    r"vercel|netlify|heroku|"
    # Data / ML / AI
    r"machine learning|deep learning|tensorflow|pytorch|scikit-learn|"
    r"pandas|numpy|spark|hadoop|kafka|airflow|"
    r"langchain|langgraph|llm|rag|vector database|huggingface|transformers|"
    r"prompt engineering|ai agent|generative ai|gemini|elevenlabs|"
    r"openai|bedrock|"
    # Web / API
    r"html|css|sass|tailwind|bootstrap|graphql|rest|grpc|websocket|"
    r"stripe|oauth|jwt|authentication|"
    # Version control / tools
    r"git|github|gitlab|jira|github actions|ci/cd|"
    # Generic
    r"sql|nosql|api|orm|microservices|ocr"
    r")\b",
    re.IGNORECASE,
)


# ==============================================================================
# SEMANTIC SKILL ALIASES
# ==============================================================================

SKILL_ALIASES: Dict[str, Set[str]] = {
    "ai agent": {"langchain", "llm", "generative ai"},
    "prompt engineering": {"llm", "generative ai"},
    "generative ai": {"llm"},
    "fastapi": {"rest", "api", "python"},
    "django": {"python", "sql", "orm"},
    "express": {"javascript", "node.js", "api"},
    "react": {"javascript", "html", "css"},
    "flask": {"python", "api"},
    "postgresql": {"sql"},
    "mongodb": {"nosql"},
    "github actions": {"ci/cd", "git"},
    "docker": {"linux"},
    "kubernetes": {"docker"},
    "elevenlabs": {"ai agent", "api"},
    "gemini": {"llm", "generative ai"},
    "openai": {"llm", "generative ai", "api"},
    "langchain": {"llm", "rag", "generative ai"},
    "redis": {"nosql"},
}


# ==============================================================================
# TITLE-BASED SKILL INFERENCE
# ==============================================================================

TITLE_SKILL_MAP: Dict[str, Set[str]] = {
    "software developer": {
        "python", "javascript", "sql", "git", "api", "html", "css",
        "docker", "rest", "ci/cd",
    },
    "software engineer": {
        "python", "javascript", "sql", "git", "api", "docker",
        "rest", "ci/cd", "linux",
    },
    "backend developer": {
        "python", "django", "fastapi", "sql", "api", "docker",
        "git", "rest", "postgresql", "redis", "linux", "ci/cd",
    },
    "backend engineer": {
        "python", "django", "fastapi", "sql", "api", "docker",
        "git", "rest", "postgresql", "redis", "linux", "ci/cd",
    },
    "frontend developer": {
        "javascript", "react", "html", "css", "typescript", "git",
        "rest", "api", "node.js",
    },
    "frontend engineer": {
        "javascript", "react", "html", "css", "typescript", "git",
        "rest", "api", "node.js",
    },
    "full stack developer": {
        "python", "javascript", "react", "sql", "api", "html", "css",
        "git", "node.js", "docker", "rest", "postgresql",
    },
    "full stack engineer": {
        "python", "javascript", "react", "sql", "api", "html", "css",
        "git", "node.js", "docker", "rest", "postgresql",
    },
    "ai engineer": {
        "python", "machine learning", "deep learning", "llm",
        "langchain", "rag", "vector database", "docker", "api",
        "tensorflow", "pytorch", "git",
    },
    "ml engineer": {
        "python", "machine learning", "deep learning", "tensorflow",
        "pytorch", "pandas", "numpy", "docker", "sql", "git",
    },
    "data scientist": {
        "python", "machine learning", "sql", "pandas", "numpy",
        "tensorflow", "git",
    },
    "devops engineer": {
        "docker", "kubernetes", "aws", "linux", "terraform",
        "ci/cd", "git", "python", "nginx",
    },
    "data engineer": {
        "python", "sql", "spark", "kafka", "airflow", "aws",
        "docker", "postgresql", "git",
    },
    "web developer": {
        "javascript", "html", "css", "react", "node.js", "api",
        "git", "sql", "rest",
    },
    "cloud engineer": {
        "aws", "azure", "gcp", "docker", "kubernetes", "terraform",
        "linux", "python", "ci/cd", "git",
    },
    "site reliability engineer": {
        "linux", "docker", "kubernetes", "python", "aws",
        "terraform", "ci/cd", "git", "nginx",
    },
}


# ==============================================================================
# SKILL EXPANSION
# ==============================================================================

def expand_skills_with_aliases(skills: Set[str]) -> Set[str]:
    """
    Expand a skill set by adding implied skills from the alias map.
    e.g., having 'django' implies 'python', 'sql', 'orm'.
    """
    expanded = set(skills)
    for skill in skills:
        aliases = SKILL_ALIASES.get(skill)
        if aliases:
            expanded.update(aliases)
    return expanded


# ==============================================================================
# SKILL EXTRACTION
# ==============================================================================

def extract_skills_from_profile(
    profile: dict,
    resume_text: Optional[str] = None,
) -> Set[str]:
    """
    Safely extract skills from all available sources in the user profile.

    Sources (highest to lowest reliability):
      1. profile.skills list -- skills the user explicitly added (handles both str and dict)
      2. profile.parsed_resume JSON -- fields extracted by the resume parser
      3. resume_text argument -- caller-supplied raw resume text
      4. profile.resume_text -- resume text stored on the Django profile

    Returns:
        A normalized, alias-expanded set of lowercase skill strings.
    """
    skills: Set[str] = set()

    # -- 1. Explicit profile skills ----
    for item in profile.get("skills") or []:
        if isinstance(item, dict):
            name = item.get("name", "")
        elif isinstance(item, str):
            name = item
        else:
            continue
        if name and isinstance(name, str):
            skills.add(name.lower().strip())

    # -- 2. parsed_resume JSON ----
    parsed = profile.get("parsed_resume") or {}
    if isinstance(parsed, str):
        try:
            parsed = json.loads(parsed)
        except (json.JSONDecodeError, TypeError):
            parsed = {}

    if isinstance(parsed, dict):
        for key in ("skills", "technologies", "tech_stack", "frameworks", "languages", "tools"):
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

    # -- 3. Regex extraction from resume text ----
    for text_source in (resume_text, profile.get("resume_text")):
        if text_source and isinstance(text_source, str):
            for m in TECH_RE.finditer(text_source):
                skills.add(m.group(0).lower().strip())
            break  # Use only the first non-empty source to avoid duplication

    skills.discard("")

    # -- 4. Expand with semantic aliases ----
    expanded = expand_skills_with_aliases(skills)

    logger.info(
        "[SKILL_UTILS] Extracted %d base skills (+%d via aliases = %d total): %s",
        len(skills), len(expanded) - len(skills), len(expanded), sorted(expanded),
    )
    return expanded


# ==============================================================================
# SKILL MATCHING
# ==============================================================================

def fuzzy_skill_match(user_skills: Set[str], job_reqs: Set[str]) -> tuple:
    """
    Compare user skills against job requirements using fuzzy substring matching
    plus semantic alias expansion.
    Handles variations like 'react' <-> 'reactjs', 'node.js' <-> 'nodejs', etc.

    Returns:
        (matched_skills: list, missing_skills: list)
    """
    user_lower = {s.lower() for s in user_skills}
    matched = []
    missing = []
    for req in job_reqs:
        req_lower = req.lower()
        # Direct or substring match
        found = any(req_lower in us or us in req_lower for us in user_lower)
        if found:
            matched.append(req)
        else:
            missing.append(req)
    return matched, missing


# ==============================================================================
# TITLE-BASED INFERENCE
# ==============================================================================

def infer_skills_from_title(job_title: str) -> Set[str]:
    """
    Infer expected skills from a job title when no explicit requirements are listed.
    Uses fuzzy matching against known role patterns.
    Prefers the most specific (longest) match to avoid generic fallback.
    """
    if not job_title:
        return set()
    title_lower = job_title.lower().strip()

    # Sort patterns by length descending so more specific patterns match first
    sorted_patterns = sorted(TITLE_SKILL_MAP.keys(), key=len, reverse=True)

    # First pass: prefer full pattern match
    for pattern in sorted_patterns:
        if pattern in title_lower:
            logger.info(
                "[SKILL_UTILS] Title '%s' matched pattern '%s' -> inferred %d skills",
                job_title, pattern, len(TITLE_SKILL_MAP[pattern]),
            )
            return TITLE_SKILL_MAP[pattern]

    # Second pass: match any significant word (len > 3)
    for pattern in sorted_patterns:
        if any(word in title_lower for word in pattern.split() if len(word) > 3):
            logger.info(
                "[SKILL_UTILS] Title '%s' word-matched pattern '%s' -> inferred %d skills",
                job_title, pattern, len(TITLE_SKILL_MAP[pattern]),
            )
            return TITLE_SKILL_MAP[pattern]

    return set()
