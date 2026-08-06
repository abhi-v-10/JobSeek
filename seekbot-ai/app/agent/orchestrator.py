"""
Agent orchestrator — the one entry point for a chat turn.

    User Request
        ↓  extract pending action (previous turn's proposal)
        ↓  build_plan()        objectives, not keywords
        ↓  load_context()      required information, in parallel
        ↓  execute_plan()      capabilities, in parallel where independent
        ↓  verify()            one lightweight completion check
        ↓  compose()           single concise response
    Final Response

LLM budget per turn:
    0 calls  — fast-path plan + deterministic capabilities
    1 call   — planner fallback, or a capability that needs generation
    2 calls  — planner fallback plus one generative capability

The orchestrator itself never calls the model.
"""

from __future__ import annotations

import logging
import time
from typing import Optional

from app.agent.completion import verify
from app.agent.composer import compose, extract_pending_action
from app.agent.context import load_context
from app.agent.executor import execute_plan
from app.agent.planner import build_plan
from app.agent.schemas import AgentTurn
from app.core.config import settings

logger = logging.getLogger(__name__)


def run_agent(
    session_id: str,
    message: str,
    authorization: Optional[str] = None,
    history: Optional[list] = None,
    file_context: Optional[str] = None,
    image_base64: Optional[str] = None,
) -> AgentTurn:
    """
    Handle one chat turn end to end.

    Args:
        session_id: Chat session id (logging and tool context only).
        message: The user's raw message.
        authorization: Bearer token forwarded to Django on the user's behalf.
        history: Prior messages, used for conversational context and to
            recover a pending write action proposed last turn.
        file_context: Extracted text from an attached document, if any.
        image_base64: Encoded image from an attached image, if any.

    Returns:
        AgentTurn — always populated. Never raises; any unexpected failure
        degrades to a plain apology so the caller can still persist a reply.
    """
    started = time.perf_counter()

    try:
        # ── Recover a pending write proposed on the previous turn ────────
        pending_action = extract_pending_action(history or [])

        # ── Plan ─────────────────────────────────────────────────────────
        plan = build_plan(message, pending_action=pending_action)

        # ── Gather only the information the plan actually needs ──────────
        ctx = load_context(
            required=plan.required_context,
            authorization=authorization,
            session_id=session_id,
            message=message,
            history=history,
            file_context=file_context,
            image_base64=image_base64,
        )

        # ── Execute ──────────────────────────────────────────────────────
        state = execute_plan(plan, ctx)

        # ── One completion check, then respond ───────────────────────────
        report = verify(plan, state)
        turn = compose(plan, state, report)

        if settings.agent_debug_plan:
            turn.metadata["_plan"] = plan.model_dump()
            turn.metadata["_state"] = {
                "completed": state.completed,
                "failed": state.failed,
                "retrieved": state.retrieved,
                "missing": state.missing,
            }

        elapsed = int((time.perf_counter() - started) * 1000)
        logger.info(
            "Agent turn complete | source=%s | objectives=%s | %dms",
            plan.source,
            ",".join(turn.objectives_run) or "-",
            elapsed,
        )
        return turn

    except Exception as exc:  # noqa: BLE001 — a turn must always produce a reply
        logger.exception("Agent pipeline failed: %s", exc)
        return AgentTurn(
            text="I hit a problem processing that. Could you try again?",
            message_type="text",
            plan_source="fallback",
        )
