"""
Response composition.

Principle 9: expose results, not reasoning. The composer merges the outputs
of every objective into one concise reply — with no LLM call, because
stitching text the tools already produced does not need a model.

Multi-objective turns keep the frontend contract intact: the response carries
the dominant capability's `message_type`, and every structured payload is
merged into `metadata` (jobs, interview, ...). Existing renderers keep
working; extra payloads are simply available to them.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from app.agent.completion import CompletionReport
from app.agent.schemas import ALLOWED_MESSAGE_TYPES, AgentState, AgentTurn, ExecutionPlan

logger = logging.getLogger(__name__)


# When several objectives return payloads, this decides which message_type
# leads. Richer, more visual types win — a jobs carousel is more useful as the
# primary render than a block of text.
_TYPE_PRIORITY: dict[str, int] = {
    "jobs": 40,
    "interview": 35,
    "resume_feedback": 30,
    "roadmap": 20,
    "text": 10,
    "error": 0,
}

_METADATA_KEY: dict[str, str] = {
    "jobs": "jobs",
    "interview": "interview",
    "resume_feedback": "resume_feedback",
    "roadmap": "roadmap",
}


def _clamp_type(message_type: str) -> str:
    """Django's ChatMessage rejects unknown types — never emit one."""
    return message_type if message_type in ALLOWED_MESSAGE_TYPES else "text"


def compose(plan: ExecutionPlan, state: AgentState, report: CompletionReport) -> AgentTurn:
    """
    Merge all capability results into the single turn returned to the user.

    Args:
        plan: The executed plan (provides objective ordering).
        state: Execution results.
        report: Output of the completion check.

    Returns:
        AgentTurn ready to persist and return.
    """
    results = state.ordered_results()
    successful = [r for r in results if r.success and (r.text or r.data)]

    # ── Genuinely blocked — ask, and only then ───────────────────────────
    if report.is_blocked and not successful:
        return AgentTurn(
            text=report.blocking_message or "I need a bit more information to help with that.",
            message_type="text",
            plan_source=plan.source,
            objectives_run=[o.capability for o in plan.objectives],
        )

    # ── Nothing usable at all ────────────────────────────────────────────
    if not successful:
        failed_text = next((r.text for r in results if r.text), "")
        return AgentTurn(
            text=failed_text or "I ran into a problem handling that. Could you try rephrasing it?",
            message_type="text",
            plan_source=plan.source,
            objectives_run=[o.capability for o in plan.objectives],
        )

    # ── Merge text ───────────────────────────────────────────────────────
    fragments: list[str] = []
    for result in successful:
        text = (result.text or "").strip()
        if text and text not in fragments:
            fragments.append(text)

    # Failed objectives get one honest line rather than being hidden.
    for result in results:
        if not result.success and result.text:
            line = result.text.strip()
            if line and line not in fragments:
                fragments.append(line)

    body = "\n\n".join(fragments)

    # ── Pick the primary message_type and payload ────────────────────────
    primary = max(
        successful,
        key=lambda r: (_TYPE_PRIORITY.get(r.message_type, 5), 1 if r.data else 0),
    )
    message_type = _clamp_type(primary.message_type)
    primary_data = primary.data

    # ── Merge every structured payload into metadata ─────────────────────
    metadata: dict[str, Any] = {}
    for result in successful:
        if result.data is None:
            continue
        key = _METADATA_KEY.get(result.message_type)
        if not key:
            continue
        if key in metadata:
            # Two objectives produced the same payload kind — keep the first,
            # which is the higher-priority one in plan order.
            continue
        metadata[key] = result.data

    # ── Pending write action rides in metadata for the next turn ─────────
    pending = next((r.pending_action for r in results if r.pending_action), None)
    if pending:
        metadata["pending_action"] = pending

    turn = AgentTurn(
        text=body,
        message_type=message_type,
        data=primary_data,
        metadata=metadata,
        plan_source=plan.source,
        objectives_run=[o.capability for o in plan.objectives],
    )

    logger.info(
        "Composed turn | type=%s | fragments=%d | metadata=%s",
        turn.message_type,
        len(fragments),
        ",".join(metadata.keys()) or "-",
    )
    return turn


def extract_pending_action(history: list) -> Optional[dict]:
    """
    Find a write action proposed on the previous assistant turn.

    Reads the last assistant message's metadata, which Django round-trips
    for us — no extra storage or state server needed.
    """
    if not history:
        return None

    for message in reversed(history):
        if not isinstance(message, dict):
            continue
        if message.get("role") != "assistant":
            continue

        metadata = message.get("metadata")
        if isinstance(metadata, dict):
            pending = metadata.get("pending_action")
            if isinstance(pending, dict) and pending.get("type"):
                return pending
        # Only the most recent assistant message can hold a live pending action.
        return None

    return None
