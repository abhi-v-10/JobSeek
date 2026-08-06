"""
One lightweight completion check.

Principle 6: no expensive self-reflection after every step — a single
deterministic validation before responding. This module makes zero LLM calls;
it inspects the state that execution already produced.

Checks:
    1. Did every objective produce a result?
    2. Did any objective fail in a way the user must be told about?
    3. Is the agent genuinely blocked and required to ask?
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from app.agent.schemas import AgentState, ExecutionPlan

logger = logging.getLogger(__name__)


# Errors that mean "the user must supply something" — the only situation in
# which the agent is allowed to interrupt the workflow (principle 8).
_BLOCKING_ERRORS: dict[str, str] = {
    "no_resume": "I don't have a resume on file for you yet — upload one and I can work from it.",
    "no_auth": "You'll need to be signed in for me to read or update your profile.",
}


@dataclass
class CompletionReport:
    """Outcome of the pre-response validation."""

    complete: bool = True
    unmet: list[str] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)
    blocking_message: str | None = None
    notes: list[str] = field(default_factory=list)

    @property
    def is_blocked(self) -> bool:
        return self.blocking_message is not None


def verify(plan: ExecutionPlan, state: AgentState) -> CompletionReport:
    """
    Confirm every objective was addressed before the response goes out.

    Returns:
        CompletionReport — `complete` is False only when an objective was
        silently skipped, which the composer surfaces honestly instead of
        pretending the work was done.
    """
    report = CompletionReport()

    for objective in plan.objectives:
        result = state.result_for(objective.id)

        # 1. Silently skipped — should not happen, but never hide it.
        if result is None:
            report.complete = False
            report.unmet.append(objective.goal)
            logger.warning("Objective '%s' (%s) produced no result", objective.goal, objective.capability)
            continue

        # 2. Failed with an actionable reason.
        if not result.success:
            report.failures.append(objective.capability)
            if result.error in _BLOCKING_ERRORS and not result.text:
                report.blocking_message = _BLOCKING_ERRORS[result.error]
            continue

        # 3. Succeeded but produced nothing usable.
        if not (result.text or result.data):
            report.notes.append(objective.capability)

    if report.unmet or report.failures:
        report.complete = False

    logger.info(
        "Completion check | complete=%s | unmet=%d | failed=%d",
        report.complete,
        len(report.unmet),
        len(report.failures),
    )
    return report
