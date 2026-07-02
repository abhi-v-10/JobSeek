"""
Shared scoring utilities for SeekBot AI tools.

Contains reusable scoring functions shared across multiple tools
(application_strategy_tool, resume_optimizer_tool, etc.).

All scoring is deterministic — no AI involvement.
"""

from __future__ import annotations

import json
import logging
from typing import Dict, List, Optional, Set

logger = logging.getLogger(__name__)


# ==============================================================================
# PRODUCTION EXPERIENCE INDICATORS
# ==============================================================================

PRODUCTION_INDICATORS: List[str] = [
    "production", "deployed", "live system", "monorepo", "CI/CD",
    "debugging", "monitoring", "scaling", "migration", "release",
    "staging", "load balancing", "incident", "SLA", "uptime",
]


# ==============================================================================
# PROJECT QUALITY INDICATORS
# ==============================================================================

PROJECT_QUALITY_INDICATORS: List[str] = [
    "stripe", "payment", "authentication", "oauth", "jwt",
    "real-time", "websocket", "api integration", "ai-powered",
    "chrome extension", "mobile app", "full-stack", "ocr",
    "database", "crud", "deployment",
]


# ==============================================================================
# SCORE CALIBRATION
# ==============================================================================

def calibrate_score(raw_score: float) -> float:
    """
    Apply diminishing returns to raw scores.
    Prevents unrealistic 100% scores while preserving relative ordering.

    Mapping (approximate):
        raw 100 -> 93       raw 60 -> 60
        raw  90 -> 86       raw 50 -> 50
        raw  80 -> 78       raw 40 -> 40
        raw  70 -> 70       raw  0 ->  0
    """
    if raw_score <= 70:
        return round(raw_score, 1)
    # Above 70: compress with diminishing returns — never exceed 95
    excess = raw_score - 70
    calibrated = 70 + excess * (1 - excess / 120)
    return round(min(95.0, max(0.0, calibrated)), 1)


# ==============================================================================
# PRODUCTION EXPERIENCE SIGNALS
# ==============================================================================

def count_production_signals(
    resume_text: Optional[str],
    profile: dict,
) -> int:
    """
    Count how many production-experience indicators appear in the resume.
    Used as a quality multiplier for experience scoring.
    """
    text = (resume_text or profile.get("resume_text") or "").lower()
    if not text:
        return 0
    return sum(1 for indicator in PRODUCTION_INDICATORS if indicator.lower() in text)


# ==============================================================================
# PROJECT QUALITY SIGNALS
# ==============================================================================

def count_project_signals(
    resume_text: Optional[str],
    profile: dict,
) -> int:
    """
    Count project quality signals from resume text and parsed resume projects.
    """
    count = 0
    text = (resume_text or profile.get("resume_text") or "").lower()
    if text:
        count += sum(1 for ind in PROJECT_QUALITY_INDICATORS if ind.lower() in text)

    # Also check parsed_resume for project entries
    parsed = profile.get("parsed_resume") or {}
    if isinstance(parsed, str):
        try:
            parsed = json.loads(parsed)
        except (json.JSONDecodeError, TypeError):
            parsed = {}
    if isinstance(parsed, dict):
        projects = parsed.get("projects") or []
        if isinstance(projects, list):
            count += min(len(projects), 5)  # Cap contribution at 5 projects

    return count
