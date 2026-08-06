"""
Lightweight objective planner.

Principle 2: plan only as much as necessary. This planner has three tiers,
ordered by cost, and stops at the first one that produces a usable plan:

    Tier 0  confirmation   — user is answering a pending write action.  0 LLM calls
    Tier 1  fast path      — deterministic objective segmentation + rules. 0 LLM calls
    Tier 2  LLM planner    — one structured JSON call, only when Tier 1 is
                             ambiguous or the message is genuinely complex.

Tier 1 handles multi-objective messages too: the message is split on
objective boundaries and each segment resolved independently, so
"analyse my resume and recommend jobs" produces a two-objective plan without
ever calling the model.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Optional

from app.agent.capabilities import capability_names, get_capability, planner_catalogue
from app.agent.schemas import ExecutionPlan, Objective
from app.core.config import settings
from app.core.openai_client import generate_chat_completion
from app.services.intent_service import detect_intent_rule

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Intent → capability mapping
# ---------------------------------------------------------------------------
#
# Every intent the legacy rule layer can emit now maps to a capability.
# Previously career_roadmap / market_insights / skill_guidance /
# project_suggestions were classified but had no handler and fell silently
# into general chat — they are explicit here.

_INTENT_CAPABILITY: dict[str, str] = {
    "job_search": "job_search",
    "job_recommendation": "job_recommendation",
    "resume_review": "resume_analysis",
    "resume_analysis": "resume_analysis",
    "skill_analysis": "resume_analysis",
    "resume_optimization": "resume_optimization",
    "interview_prep": "interview_prep",
    "application_strategy": "application_strategy",
    "readiness_check": "readiness_check",
    "career_progress": "career_progress",
    "profile_update": "skill_profile_sync",
    "career_roadmap": "general_answer",
    "market_insights": "general_answer",
    "skill_guidance": "general_answer",
    "project_suggestions": "general_answer",
    "general_chat": "general_answer",
}


# ---------------------------------------------------------------------------
# Tier 0 — confirmation of a pending write
# ---------------------------------------------------------------------------

_AFFIRMATIVE = {
    "yes", "y", "yeah", "yep", "yup", "sure", "ok", "okay", "confirm",
    "confirmed", "do it", "go ahead", "please do", "add them", "add it",
    "sounds good", "proceed", "yes please", "add", "update it",
}

_NEGATIVE = {
    "no", "n", "nope", "nah", "don't", "dont", "cancel", "stop",
    "not now", "later", "skip", "no thanks", "leave it",
}


def _normalise(message: str) -> str:
    return re.sub(r"[^a-z0-9' ]+", "", (message or "").lower()).strip()


def classify_confirmation(message: str) -> Optional[bool]:
    """
    Decide whether a short message confirms or rejects a pending action.

    Returns True (confirm), False (reject), or None (not a confirmation —
    the user changed the subject, so the pending action is simply dropped).
    """
    text = _normalise(message)
    if not text or len(text.split()) > 5:
        return None
    if text in _AFFIRMATIVE or any(text.startswith(p) for p in ("yes", "yeah", "yep", "sure", "ok", "go ahead", "do it")):
        return True
    if text in _NEGATIVE or any(text.startswith(p) for p in ("no", "nope", "nah", "cancel", "don't", "dont")):
        return False
    return None


def build_confirmation_plan(pending_action: dict[str, Any]) -> ExecutionPlan:
    """Turn a confirmed pending action into a one-objective execution plan."""
    capability = pending_action.get("type", "skill_profile_sync")
    params = {k: v for k, v in pending_action.items() if k != "type"}
    params["confirmed"] = True

    objective = Objective(
        id="o1",
        goal="Carry out the action the user just confirmed",
        capability=capability,
        params=params,
    )
    cap = get_capability(capability)
    return ExecutionPlan(
        objectives=[objective],
        required_context=list(cap.requires) if cap else [],
        source="confirmation",
    )


# ---------------------------------------------------------------------------
# Tier 1 — objective segmentation
# ---------------------------------------------------------------------------

# Boundaries that reliably separate two distinct requests. Note the trailing
# context requirement: a bare " and " is only a boundary when what follows
# starts like a new instruction, so "react and python jobs" stays one objective.
_SEGMENT_SPLIT = re.compile(
    r"""
    \s*(?:
        [;]                                   # explicit separator
      | ,?\s*(?:and\s+)?then\s+               # "then", "and then"
      | ,?\s*(?:and|also|plus)\s+(?=          # "and"/"also"/"plus" followed by...
            (?:please\s+)?
            (?:can\s+you\s+|could\s+you\s+|i\s+want\s+you\s+to\s+)?
            (?:analyse|analyze|review|check|update|add|sync|show|find|
               recommend|suggest|prepare|optimi[sz]e|improve|tailor|
               give|tell|create|build|make|list|search|help)\b
        )
      | ,\s*(?=(?:analyse|analyze|review|check|update|add|sync|show|find|
                 recommend|suggest|prepare|optimi[sz]e|improve|tailor)\b)
    )\s*
    """,
    re.IGNORECASE | re.VERBOSE,
)

# Phrases that mean "write my extracted skills to my profile".
_PROFILE_UPDATE_TRIGGERS = (
    "update my profile",
    "update profile",
    "add them to my profile",
    "add to my profile",
    "add the missing skills",
    "add missing skills",
    "update my skills",
    "sync my skills",
    "sync my profile",
    "save them to my profile",
    "add these skills",
    "put them on my profile",
)


def segment_objectives(message: str) -> list[str]:
    """
    Split a message into candidate objective segments.

    Conservative by design: over-splitting sends two tool calls where one was
    wanted, which is worse than under-splitting (Tier 2 catches the rest).
    """
    if not message or not message.strip():
        return []

    parts = [p.strip(" .,") for p in _SEGMENT_SPLIT.split(message.strip())]
    segments = [p for p in parts if p and len(p) > 2]
    return segments or [message.strip()]


# ---------------------------------------------------------------------------
# Readiness-doubt detection
# ---------------------------------------------------------------------------
#
# A single sentence like "I'm interested in python jobs but I'm not sure if
# my resume is good enough" never crosses a segment boundary (no "and" /
# "then"), so it stays one segment — and the rule layer's job_keywords check
# hits on the bare word "jobs" and returns job_search before the doubt half
# of the sentence gets any say. That is the exact keyword-over-objective
# failure this architecture exists to avoid, so it gets a dedicated check
# rather than being left to a substring match on "jobs".
#
# Explicit phrasing is caught directly; the hedge+doubt combo generalises to
# phrasings not on the list, but is gated on a resume/profile/readiness word
# being present so it doesn't fire on unrelated hedged sentences ("I like
# Python but I don't know Java").

_READINESS_PHRASES: tuple[str, ...] = (
    "not sure if my resume",
    "not sure if my profile",
    "not sure if i'm ready",
    "not sure if im ready",
    "is my resume good enough",
    "is my resume ready",
    "is my profile ready",
    "resume good enough",
    "am i qualified",
    "am i good enough",
    "not confident about my resume",
    "not confident in my resume",
)

_HEDGE_RE = re.compile(r"\b(but|however|although|though|even though)\b", re.IGNORECASE)
_DOUBT_RE = re.compile(
    r"\b(not sure|unsure|don'?t know|no idea|wondering|worried|good enough|ready enough|qualified)\b",
    re.IGNORECASE,
)
_READINESS_CONTEXT_RE = re.compile(r"\b(resume|cv|profile|qualified|ready)\b", re.IGNORECASE)

_ROLE_HINT_RE = re.compile(r"\b([A-Za-z][\w+.#-]*)\s+jobs?\b", re.IGNORECASE)
_ROLE_HINT_STOPWORDS = {
    "the", "some", "any", "more", "new", "these", "those", "good", "great",
    "enough", "for", "in", "my", "your", "our", "a", "an", "find", "show", "get", "no",
}


def _is_readiness_doubt(text: str) -> bool:
    if any(phrase in text for phrase in _READINESS_PHRASES):
        return True
    # General fallback: a contrastive connector plus a doubt marker, but only
    # when the sentence is actually about resume/profile/readiness — keeps
    # this from firing on hedge sentences unrelated to job-readiness.
    return bool(_HEDGE_RE.search(text) and _DOUBT_RE.search(text) and _READINESS_CONTEXT_RE.search(text))


def _extract_role_hint(text: str) -> Optional[str]:
    """Pull a role/skill hint out of "<hint> job(s)" phrasing, e.g. 'python jobs' -> 'Python'."""
    match = _ROLE_HINT_RE.search(text)
    if not match:
        return None
    hint = match.group(1).strip()
    if not hint or hint.lower() in _ROLE_HINT_STOPWORDS:
        return None
    return hint.upper() if len(hint) <= 3 else hint[0].upper() + hint[1:]


def _rule_intent(segment: str) -> Optional[str]:
    """Rule-based intent for one segment, including the write and readiness-doubt intents."""
    text = segment.lower()

    if any(trigger in text for trigger in _PROFILE_UPDATE_TRIGGERS):
        return "profile_update"

    intent = detect_intent_rule(segment)

    # Explicit "build me a strategy / am I ready to apply" phrasing keeps its
    # existing behaviour — the full application_strategy report is what was
    # actually asked for.
    if intent == "application_strategy":
        return intent

    if _is_readiness_doubt(text):
        return "readiness_check"

    return intent


def _objective_from_intent(index: int, intent: str, segment: str, full_message: str) -> Objective:
    capability = _INTENT_CAPABILITY.get(intent, "general_answer")
    params: dict[str, Any] = {}

    # Give search-style capabilities the segment, not the whole message, so a
    # compound request doesn't pollute the query with the other objective.
    if capability in {"job_search", "job_recommendation", "application_strategy", "readiness_check"}:
        params["query"] = segment
    if capability == "readiness_check":
        role_hint = _extract_role_hint(segment) or _extract_role_hint(full_message)
        if role_hint:
            params["target_role"] = role_hint
    elif capability in {"resume_analysis", "general_answer"}:
        params["question"] = segment
    elif capability == "interview_prep":
        params["target_role"] = segment

    return Objective(
        id=f"o{index}",
        goal=segment[:160],
        capability=capability,
        params=params,
    )


def fast_path_plan(message: str) -> Optional[ExecutionPlan]:
    """
    Try to build a plan with zero LLM calls.

    Returns None when the message is ambiguous enough to deserve the planner.
    """
    segments = segment_objectives(message)
    if not segments:
        return None

    resolved: list[tuple[str, str]] = []  # (intent, segment)
    for segment in segments:
        intent = _rule_intent(segment)
        if intent:
            resolved.append((intent, segment))

    # Single segment, confident rule hit → the common case, done.
    if len(segments) == 1:
        if not resolved:
            return None
        intent, segment = resolved[0]
        return _plan_from_pairs([(intent, segment)], message, source="fast_path")

    # Multi-segment: every segment must resolve, otherwise the model decides.
    if len(resolved) != len(segments):
        return None

    # Collapse identical consecutive intents ("show jobs and show more jobs").
    deduped: list[tuple[str, str]] = []
    for intent, segment in resolved:
        if deduped and deduped[-1][0] == intent:
            continue
        deduped.append((intent, segment))

    if len(deduped) < 2:
        return _plan_from_pairs(deduped, message, source="fast_path")

    return _plan_from_pairs(deduped, message, source="fast_path")


def _plan_from_pairs(pairs: list[tuple[str, str]], message: str, source: str) -> ExecutionPlan:
    objectives = [
        _objective_from_intent(i, intent, segment, message)
        for i, (intent, segment) in enumerate(pairs, start=1)
    ]
    return _finalise_plan(objectives, source)


# ---------------------------------------------------------------------------
# Tier 2 — single structured LLM planning call
# ---------------------------------------------------------------------------

_PLANNER_SYSTEM = """You are the planning component of SeekBot, a career agent.

Your only job is to translate the user's message into the objectives they want accomplished, then pick the capability that satisfies each objective.

Rules:
- Identify what the user wants to ACCOMPLISH, not which words they used.
- One message may contain several objectives. Emit one entry per objective.
- Emit as few objectives as possible — never more than {max_objectives}.
- If an objective needs the output of an earlier one, list that objective's id in depends_on. Otherwise leave depends_on empty so they run in parallel.
- If the user asked for an action, plan the action. Do not replace it with advice.
- Use general_answer for anything conversational or advisory that no other capability covers.

Available capabilities:
{catalogue}

Return ONLY this JSON, nothing else:
{{"objectives":[{{"id":"o1","goal":"<what the user wants>","capability":"<capability name>","params":{{}},"depends_on":[]}}]}}"""


def _extract_json(text: str) -> Optional[dict]:
    """
    Pull a JSON object out of a model response.

    Handles reasoning-model output (<think> blocks), fenced code, and
    surrounding prose.
    """
    if not text:
        return None

    cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(r"^```(?:json)?|```$", "", cleaned.strip(), flags=re.MULTILINE).strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Fall back to the outermost balanced-looking object.
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None


def llm_plan(message: str) -> Optional[ExecutionPlan]:
    """
    Ask the model for a structured plan. Exactly one LLM call, temperature 0.

    Returns None on any failure — the caller degrades to a general answer
    rather than surfacing an error.
    """
    if not settings.agent_planner_enabled:
        return None

    system = _PLANNER_SYSTEM.format(
        catalogue=planner_catalogue(),
        max_objectives=settings.agent_max_objectives,
    )

    try:
        response = generate_chat_completion(
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": message[:1500]},
            ],
            temperature=0.0,
            max_tokens=settings.agent_planner_max_tokens,
        )
        raw = response.choices[0].message.content
    except Exception as exc:  # noqa: BLE001
        logger.warning("Planner LLM call failed: %s", exc)
        return None

    payload = _extract_json(raw)
    if not isinstance(payload, dict):
        logger.warning("Planner returned unparseable output: %s", (raw or "")[:200])
        return None

    raw_objectives = payload.get("objectives")
    if not isinstance(raw_objectives, list) or not raw_objectives:
        return None

    valid_names = set(capability_names())
    objectives: list[Objective] = []

    for index, entry in enumerate(raw_objectives, start=1):
        if not isinstance(entry, dict):
            continue

        capability = str(entry.get("capability") or "").strip()
        if capability not in valid_names:
            logger.info("Planner proposed unknown capability '%s' — coercing to general_answer", capability)
            capability = "general_answer"

        params = entry.get("params")
        depends_on = entry.get("depends_on")

        objectives.append(
            Objective(
                id=str(entry.get("id") or f"o{index}"),
                goal=str(entry.get("goal") or message)[:160],
                capability=capability,
                params=params if isinstance(params, dict) else {},
                depends_on=[str(d) for d in depends_on] if isinstance(depends_on, list) else [],
            )
        )

    if not objectives:
        return None

    return _finalise_plan(objectives, source="planner")


# ---------------------------------------------------------------------------
# Shared finalisation
# ---------------------------------------------------------------------------


# Capability pairs where the second is subsumed by the first.
#
# skill_profile_sync already reads and parses the resume itself (it extracts
# missing skills straight from ctx.resume_text) — running resume_analysis
# alongside it produces a full generic career-review essay that answers a
# question the user didn't ask ("analyse my resume and update my profile
# with the missing skills" is one action, not two). Keeping both violates
# principle 9 (concise responses, expose only results) for zero added value:
# the write capability's own reply already says what it found.
_SUBSUMES: dict[str, set[str]] = {
    "skill_profile_sync": {"resume_analysis"},
}


def _drop_subsumed_objectives(objectives: list[Objective]) -> list[Objective]:
    """Remove objectives whose capability is made redundant by another in the same plan."""
    present = {obj.capability for obj in objectives}
    redundant: set[str] = set()
    for primary, subsumed in _SUBSUMES.items():
        if primary in present:
            redundant |= (subsumed & present)

    if not redundant:
        return objectives

    kept = [obj for obj in objectives if obj.capability not in redundant]
    logger.info("Dropped subsumed objective(s): %s", ", ".join(sorted(redundant)))
    return kept or objectives  # never drop down to nothing


def _finalise_plan(objectives: list[Objective], source: str) -> ExecutionPlan:
    """
    Normalise a raw objective list into a safe, executable plan.

    - caps objective count
    - drops duplicate capabilities (same tool twice is always waste)
    - drops objectives subsumed by another capability in the same plan
    - rewrites ids to be contiguous and prunes dangling dependencies
    - collects the union of required context keys
    """
    capped = objectives[: settings.agent_max_objectives]

    seen: set[str] = set()
    unique: list[Objective] = []
    for obj in capped:
        if obj.capability in seen:
            continue
        seen.add(obj.capability)
        unique.append(obj)

    unique = _drop_subsumed_objectives(unique)

    # Reassign ids so dependency resolution is always well-defined.
    id_remap = {obj.id: f"o{i}" for i, obj in enumerate(unique, start=1)}
    valid_ids = set(id_remap.values())

    normalised: list[Objective] = []
    for obj in unique:
        new_id = id_remap[obj.id]
        deps = [id_remap[d] for d in obj.depends_on if d in id_remap]
        # A dependency on itself or on a pruned objective is meaningless.
        deps = [d for d in deps if d != new_id and d in valid_ids]
        normalised.append(obj.model_copy(update={"id": new_id, "depends_on": deps}))

    context_keys: list[str] = []
    for obj in normalised:
        cap = get_capability(obj.capability)
        if not cap:
            continue
        for key in cap.requires:
            if key not in context_keys:
                context_keys.append(key)

    return ExecutionPlan(objectives=normalised, required_context=context_keys, source=source)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def build_plan(message: str, pending_action: Optional[dict[str, Any]] = None) -> ExecutionPlan:
    """
    Produce the execution plan for one user turn.

    Args:
        message: The user's raw message.
        pending_action: A write action proposed on the previous turn, if any.

    Returns:
        ExecutionPlan — always non-empty; degrades to a single general_answer
        objective if every tier fails.
    """
    # ── Tier 0: confirmation of a pending write ──────────────────────────
    if pending_action:
        decision = classify_confirmation(message)
        if decision is True:
            logger.info("Plan source=confirmation | action=%s", pending_action.get("type"))
            return build_confirmation_plan(pending_action)
        if decision is False:
            return ExecutionPlan(
                objectives=[
                    Objective(
                        id="o1",
                        goal="Acknowledge the cancelled action",
                        capability="general_answer",
                        params={"question": "The user declined the profile update. Acknowledge briefly and offer to help with something else."},
                    )
                ],
                required_context=[],
                source="confirmation",
            )
        # Neither — user moved on. Fall through and plan normally.

    # ── Tier 1: deterministic fast path ──────────────────────────────────
    plan = fast_path_plan(message)
    if plan and plan.objectives:
        logger.info(
            "Plan source=fast_path | objectives=%s",
            ", ".join(o.capability for o in plan.objectives),
        )
        return plan

    # ── Tier 2: one structured LLM planning call ─────────────────────────
    plan = llm_plan(message)
    if plan and plan.objectives:
        logger.info(
            "Plan source=planner | objectives=%s",
            ", ".join(o.capability for o in plan.objectives),
        )
        return plan

    # ── Tier 3: never fail — answer conversationally ─────────────────────
    logger.info("Plan source=fallback | general_answer")
    return ExecutionPlan(
        objectives=[
            Objective(id="o1", goal=message[:160], capability="general_answer", params={"question": message})
        ],
        required_context=[],
        source="fallback",
    )
