"""
Parallel, lazy context loading.

Principle 4 (execute efficiently) applies first and foremost to information
gathering: profile, resume, dashboard, analytics and interviews are five
independent HTTP round-trips to Django. Serially that is ~5x latency for no
reason. This module fetches exactly the keys the plan declared, in parallel,
and never raises — a failed fetch degrades to an empty value and is recorded
in `missing` so the completion check can see it.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Optional

from app.core.config import settings
from app.services.django_service import (
    fetch_application_analytics,
    fetch_application_dashboard,
    fetch_upcoming_interviews,
    fetch_user_profile,
)

logger = logging.getLogger(__name__)


# Context keys a plan may request. Kept small on purpose — every extra key is
# an extra network call.
CONTEXT_KEYS: set[str] = {
    "profile",       # /users/profile/  (includes skills + resume_text)
    "dashboard",     # /applications/dashboard/
    "analytics",     # /applications/analytics/
    "interviews",    # /applications/upcoming-interviews/
}


class AgentContext:
    """
    Per-turn snapshot of the user's data.

    Read-only from the capabilities' point of view. `resume_text` is derived
    from the profile rather than fetched separately, because the profile
    endpoint already returns it — one call instead of two.
    """

    def __init__(
        self,
        authorization: Optional[str] = None,
        session_id: str = "",
        message: str = "",
        history: Optional[list] = None,
        file_context: Optional[str] = None,
        image_base64: Optional[str] = None,
    ) -> None:
        self.authorization = authorization
        self.session_id = session_id
        self.message = message
        self.history = history or []
        self.file_context = file_context
        self.image_base64 = image_base64

        self.profile: dict[str, Any] = {}
        self.dashboard: dict[str, Any] = {}
        self.analytics: dict[str, Any] = {}
        self.interviews: list[Any] = []

        self.loaded: list[str] = []
        self.missing: list[str] = []

    # ── Derived accessors ────────────────────────────────────────────────

    @property
    def resume_text(self) -> str:
        """Resume plaintext from the profile payload; empty string if absent."""
        value = self.profile.get("resume_text") if isinstance(self.profile, dict) else None
        return value if isinstance(value, str) else ""

    @property
    def has_resume(self) -> bool:
        return bool(self.resume_text.strip())

    @property
    def target_role(self) -> Optional[str]:
        if not isinstance(self.profile, dict):
            return None
        return self.profile.get("target_role") or self.profile.get("role") or None

    @property
    def experience_level(self) -> Optional[str]:
        if not isinstance(self.profile, dict):
            return None
        return self.profile.get("experience_level")

    @property
    def profile_skills(self) -> list[str]:
        """Flat list of skill names already on the profile."""
        if not isinstance(self.profile, dict):
            return []
        raw = self.profile.get("skills") or []
        names: list[str] = []
        for item in raw:
            if isinstance(item, dict):
                name = item.get("name")
            else:
                name = item
            if isinstance(name, str) and name.strip():
                names.append(name.strip())
        return names


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------


def _loader_map(auth: Optional[str]) -> dict[str, Callable[[], Any]]:
    """Map each context key to a zero-arg callable that fetches it."""
    return {
        "profile": lambda: fetch_user_profile(auth_token=auth) or {},
        "dashboard": lambda: fetch_application_dashboard(auth_token=auth) or {},
        "analytics": lambda: fetch_application_analytics(auth_token=auth) or {},
        "interviews": lambda: fetch_upcoming_interviews(auth_token=auth) or {},
    }


def _normalise_interviews(payload: Any) -> list:
    """Django may return a list or a paginated dict — accept both."""
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("results", "data", "upcoming_interviews"):
            value = payload.get(key)
            if isinstance(value, list):
                return value
    return []


def load_context(
    required: list[str],
    authorization: Optional[str],
    session_id: str = "",
    message: str = "",
    history: Optional[list] = None,
    file_context: Optional[str] = None,
    image_base64: Optional[str] = None,
) -> AgentContext:
    """
    Fetch the requested context keys in parallel, best-effort.

    Args:
        required: Context keys the plan needs. Unknown keys are ignored.
        authorization: Bearer token forwarded from the caller.

    Returns:
        AgentContext — always usable. Failed fetches leave empty values and
        are listed in `context.missing`.
    """
    ctx = AgentContext(
        authorization=authorization,
        session_id=session_id,
        message=message,
        history=history,
        file_context=file_context,
        image_base64=image_base64,
    )

    wanted = [key for key in dict.fromkeys(required) if key in CONTEXT_KEYS]

    if not wanted:
        return ctx

    if not authorization:
        # Anonymous turn — nothing user-scoped can be fetched. Not an error.
        ctx.missing.extend(wanted)
        logger.info("Context skipped (no auth token): %s", ", ".join(wanted))
        return ctx

    loaders = _loader_map(authorization)
    workers = max(1, min(len(wanted), settings.agent_max_workers))

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(loaders[key]): key for key in wanted}

        for future in as_completed(futures):
            key = futures[future]
            try:
                value = future.result()
            except Exception as exc:  # noqa: BLE001 — degrade, never fail the turn
                logger.warning("Context fetch failed for '%s': %s", key, exc)
                ctx.missing.append(key)
                continue

            if key == "profile":
                ctx.profile = value if isinstance(value, dict) else {}
            elif key == "dashboard":
                ctx.dashboard = value if isinstance(value, dict) else {}
            elif key == "analytics":
                ctx.analytics = value if isinstance(value, dict) else {}
            elif key == "interviews":
                ctx.interviews = _normalise_interviews(value)

            ctx.loaded.append(key)

    logger.info(
        "Context loaded in parallel | ok=%s | missing=%s",
        ",".join(ctx.loaded) or "-",
        ",".join(ctx.missing) or "-",
    )
    return ctx
