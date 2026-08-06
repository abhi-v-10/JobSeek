"""
Structured data exchanged between agent components.

Every component boundary uses these models — the planner emits an
ExecutionPlan, the executor emits CapabilityResults, and the orchestrator
returns an AgentTurn. Nothing passes free-form dicts between stages, which
keeps the pipeline debuggable and cheap to validate.
"""

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

# Message types the Django ChatMessage model accepts. Anything outside this
# set would be rejected on persist, so the composer clamps to it.
ALLOWED_MESSAGE_TYPES: set[str] = {
    "text",
    "jobs",
    "resume_feedback",
    "roadmap",
    "interview",
    "error",
}

PlanSource = Literal["fast_path", "planner", "confirmation", "fallback"]


# ---------------------------------------------------------------------------
# Planning
# ---------------------------------------------------------------------------


class Objective(BaseModel):
    """
    One thing the user wants accomplished in this turn.

    An objective is *what the user wants*, deliberately kept separate from
    the capability chosen to satisfy it — the same objective may be served
    by different capabilities as the toolset evolves.
    """

    id: str = Field(..., description="Stable id within this plan, e.g. 'o1'.")
    goal: str = Field(..., description="The user's objective in plain language.")
    capability: str = Field(..., description="Registry key of the capability that satisfies it.")
    params: dict[str, Any] = Field(
        default_factory=dict,
        description="Capability-specific arguments extracted from the message.",
    )
    depends_on: list[str] = Field(
        default_factory=list,
        description="Objective ids whose output this objective needs. Empty = runs in parallel.",
    )


class ExecutionPlan(BaseModel):
    """A minimal plan: objectives, the context they need, and their order."""

    objectives: list[Objective] = Field(default_factory=list)
    required_context: list[str] = Field(
        default_factory=list,
        description="Context keys to fetch before execution (profile, resume, ...).",
    )
    source: PlanSource = Field(
        default="fast_path",
        description="How the plan was produced — used for logging and cost tracking.",
    )
    clarification: Optional[str] = Field(
        default=None,
        description="Set only when the agent is genuinely blocked and must ask.",
    )

    @property
    def is_multi_objective(self) -> bool:
        return len(self.objectives) > 1

    def objective_by_id(self, objective_id: str) -> Optional[Objective]:
        for obj in self.objectives:
            if obj.id == objective_id:
                return obj
        return None


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------


class CapabilityResult(BaseModel):
    """Outcome of running one capability for one objective."""

    objective_id: str
    capability: str
    success: bool = True
    text: str = Field(default="", description="Human-readable output fragment.")
    message_type: str = Field(default="text")
    data: Optional[Any] = Field(default=None, description="Structured payload for the frontend.")
    error: Optional[str] = Field(default=None)
    pending_action: Optional[dict[str, Any]] = Field(
        default=None,
        description="A write action awaiting user confirmation on the next turn.",
    )
    duration_ms: int = Field(default=0)

    model_config = {"arbitrary_types_allowed": True}


class AgentState(BaseModel):
    """
    Lightweight execution state — only what later steps actually need.

    Deliberately does NOT accumulate full conversation history or raw tool
    payloads; the orchestrator discards it at the end of every turn.
    """

    objectives: list[str] = Field(default_factory=list)
    completed: list[str] = Field(default_factory=list)
    pending: list[str] = Field(default_factory=list)
    failed: list[str] = Field(default_factory=list)
    retrieved: list[str] = Field(default_factory=list, description="Context keys successfully loaded.")
    missing: list[str] = Field(default_factory=list, description="Context keys that could not be loaded.")
    results: dict[str, CapabilityResult] = Field(default_factory=dict)

    def record(self, result: CapabilityResult) -> None:
        """Move an objective from pending to completed/failed and store its result."""
        self.results[result.objective_id] = result
        if result.objective_id in self.pending:
            self.pending.remove(result.objective_id)
        target = self.completed if result.success else self.failed
        if result.objective_id not in target:
            target.append(result.objective_id)

    def result_for(self, objective_id: str) -> Optional[CapabilityResult]:
        return self.results.get(objective_id)

    def ordered_results(self) -> list[CapabilityResult]:
        """Results in the plan's original objective order."""
        return [self.results[oid] for oid in self.objectives if oid in self.results]


# ---------------------------------------------------------------------------
# Turn output
# ---------------------------------------------------------------------------


class AgentTurn(BaseModel):
    """Everything the chat endpoint needs to answer and persist a turn."""

    text: str = ""
    message_type: str = "text"
    data: Optional[Any] = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    plan_source: PlanSource = "fast_path"
    objectives_run: list[str] = Field(default_factory=list)
    llm_calls: int = 0

    model_config = {"arbitrary_types_allowed": True}
