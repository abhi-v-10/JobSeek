import re

import requests
from app.core.config import DJANGO_API_BASE_URL, DJANGO_INTERNAL_TOKEN

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# "intern" / "internship" are intentionally excluded.
# The Job model has no internship type — job_type is only "corporate" or
# "domestic", and position titles won't contain "intern" in a typical DB.
# Sending role=intern would filter position__icontains("intern") and zero
# out every result.  Those keywords still trigger the job_search intent;
# they just don't become a destructive API filter.
_ROLE_KEYWORDS: dict[str, str] = {
    "developer": "developer",
    "dev": "developer",
    "engineer": "engineer",
    "designer": "designer",
    "analyst": "analyst",
    "manager": "manager",
    "devops": "devops",
    "data scientist": "data scientist",
    "full stack": "full stack",
    "fullstack": "full stack",
    "backend": "backend",
    "frontend": "frontend",
    "front-end": "frontend",
    "back-end": "backend",
}

_SKILL_KEYWORDS: list[str] = [
    "react",
    "python",
    "django",
    "node",
    "javascript",
    "typescript",
    "flutter",
    "java",
    "golang",
    "go",
    "rust",
    "vue",
    "angular",
    "nextjs",
    "next.js",
    "sql",
    "mongodb",
    "postgres",
    "postgresql",
    "aws",
    "docker",
    "kubernetes",
    "express",
    "fastapi",
    "spring",
    "kotlin",
    "swift",
    "php",
    "laravel",
    "rails",
    "ruby",
]

_LOCATION_KEYWORDS: list[str] = [
    "hyderabad",
    "bangalore",
    "bengaluru",
    "delhi",
    "mumbai",
    "chennai",
    "pune",
    "kolkata",
    "noida",
    "gurgaon",
    "gurugram",
    "remote",
]


# ---------------------------------------------------------------------------
# Step 1 — Filter extraction (rule-based)
# ---------------------------------------------------------------------------


def extract_filters(query: str) -> dict:
    """
    Extract structured job search filters from a plain-text user query.
    Returns a dict suitable for use as query params against the Django API.
    """
    text = query.lower().strip()
    filters: dict = {}

    # Role — longest match first to avoid "dev" shadowing "developer"
    for keyword in sorted(_ROLE_KEYWORDS, key=len, reverse=True):
        if keyword in text:
            filters["role"] = _ROLE_KEYWORDS[keyword]
            break

    # Skills — collect the first match found
    for skill in _SKILL_KEYWORDS:
        if skill in text:
            filters["skills"] = skill
            break

    # Location — collect the first city found (remote handled separately)
    for loc in _LOCATION_KEYWORDS:
        if loc in text and loc != "remote":
            filters["location"] = loc
            break

    # Remote flag
    if "remote" in text:
        filters["remote"] = "true"

    # Salary cap — "under 50000", "below 80k", "under 1 lakh", etc.
    salary_match = re.search(r"\b(?:under|below)\s+(\d[\d,]*)\s*(?:k|lakh|l)?\b", text)
    if salary_match:
        raw = salary_match.group(1).replace(",", "")
        multiplier_text = salary_match.group(0).lower()
        value = int(raw)
        if "lakh" in multiplier_text or multiplier_text.endswith("l"):
            value *= 100_000
        elif "k" in multiplier_text:
            value *= 1_000
        filters["salary_max"] = str(value)

    return filters


# ---------------------------------------------------------------------------
# Step 2 — Fetch jobs from Django
# ---------------------------------------------------------------------------


# Sent on every internal SeekBot → Django request so Django can
# identify (and optionally gate) calls coming from this service.
# Value is read from .env — never hardcoded here.
_INTERNAL_HEADERS: dict[str, str] = (
    {"X-Internal-Token": DJANGO_INTERNAL_TOKEN} if DJANGO_INTERNAL_TOKEN else {}
)


def fetch_jobs(filters: dict) -> list:
    """
    Call the Django job search API with the given filters and return
    the list of job objects from the response.
    """
    url = f"{DJANGO_API_BASE_URL}/jobs/search/"

    # SeekBot is a tech job platform — always restrict to corporate jobs.
    # Domestic jobs (cooking, cleaning, etc.) are never relevant here.
    params = {"job_type": "corporate", **filters}

    try:
        response = requests.get(
            url, params=params, headers=_INTERNAL_HEADERS, timeout=10
        )
        response.raise_for_status()
        data = response.json()
        return data.get("results", [])
    except requests.exceptions.Timeout:
        raise RuntimeError("Request to Django API timed out.")
    except requests.exceptions.RequestException as exc:
        raise RuntimeError(f"Django API request failed: {exc}") from exc


# ---------------------------------------------------------------------------
# Step 3 — Format response for chat UI
# ---------------------------------------------------------------------------


def format_jobs(jobs: list) -> str:
    """
    Format a list of job dicts into a clean, readable chat response.
    Returns the top 5 results only.
    """
    if not jobs:
        return "No matching jobs found."

    top_jobs = jobs[:5]
    lines: list[str] = ["Here are some matching jobs:\n"]

    for idx, job in enumerate(top_jobs, start=1):
        title = job.get("title") or "Untitled Role"
        company = job.get("company_name") or "Unknown Company"
        location = job.get("location") or "Not specified"
        job_type = job.get("job_type") or "Not specified"
        is_remote = job.get("is_remote", False)

        location_label = f"{location} (Remote)" if is_remote else location

        lines.append(f"{idx}. {title} - {company}")
        lines.append(f"   \U0001f4cd {location_label}")
        lines.append(f"   \U0001f4bc {job_type.capitalize()}")
        lines.append("")

    return "\n".join(lines).rstrip()


# ---------------------------------------------------------------------------
# Step 4 — Main entry point
# ---------------------------------------------------------------------------


def run(query: str) -> str:
    """
    Main entry point for the job search tool.

    Extracts filters from the user query, calls the Django job search API,
    and returns a formatted string ready for display in the chat UI.
    """
    try:
        filters = extract_filters(query)
        jobs = fetch_jobs(filters)
        return format_jobs(jobs)
    except RuntimeError:
        return "Something went wrong while fetching jobs. Please try again."
    except Exception:
        return "Something went wrong while fetching jobs. Please try again."


def run_with_data(query: str) -> tuple[str, list]:
    """
    Like run(), but also returns the raw job list so callers can include
    structured data in the API response alongside the formatted text.

    Returns:
        (formatted_text: str, jobs: list)  — jobs is [] on error or no results.
    """
    try:
        filters = extract_filters(query)
        jobs = fetch_jobs(filters)
        text = format_jobs(jobs)
        return text, jobs[:5]
    except RuntimeError:
        return "Something went wrong while fetching jobs. Please try again.", []
    except Exception:
        return "Something went wrong while fetching jobs. Please try again.", []
