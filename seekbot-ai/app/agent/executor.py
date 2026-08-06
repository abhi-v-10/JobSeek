"""
Dependency-aware parallel executor.

Principle 4: run independent work concurrently, serialise only true
dependencies. The plan's `depends_on` edges are resolved into execution
waves — every objective in a wave is independent of the others, so the whole
wave runs on a thread pool. Most turns are a single wave.

Capabilities marked `parallel_safe=False` (writes, and heavy internal
orchestrators) are always given a wave to themselves.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from app.agent.capabilities import get_capability, run_capability
from app.agent.context import AgentContext
from app.agent.schemas import AgentState, CapabilityResult, ExecutionPlan, Objective
from app.core.config import settings

logger = logging.getLogger(__name__)


def build_waves(plan: ExecutionPlan) -> list[list[Objective]]:
    """
    Group objectives into execution waves by dependency depth.

    Objectives with unsatisfiable dependencies (cycles, or edges to pruned
    objectives) are appended to a final wave rather than dropped — the user
    asked for them, so they run.
    """
    remaining = list(plan.objectives)
    satisfied: set[str] = set()
    waves: list[list[Objective]] = []

    while remaining:
        ready = [obj for obj in remaining if all(dep in satisfied for dep in obj.depends_on)]

        if not ready:
            # Cycle or dangling edge — run what's left, in order, rather than
            # silently ignoring objectives.
            logger.warning("Unresolvable dependencies; flushing %d objective(s)", len(remaining))
            waves.append(remaining)
            break

        # Non-parallel-safe capabilities get their own wave.
        exclusive = [o for o in ready if not _is_parallel_safe(o)]
        shared = [o for o in ready if _is_parallel_safe(o)]

        if shared:
            waves.append(shared)
        for obj in exclusive:
            waves.append([obj])

        for obj in ready:
            satisfied.add(obj.id)
            remaining.remove(obj)

    return waves


def _is_parallel_safe(objective: Objective) -> bool:
    cap = get_capability(objective.capability)
    return cap.parallel_safe if cap else True


def execute_plan(plan: ExecutionPlan, ctx: AgentContext) -> AgentState:
    """
    Run every objective in the plan and return the resulting state.

    Never raises — individual capability failures are captured as failed
    results so the composer can still answer the remaining objectives.
    """
    state = AgentState(
        objectives=[obj.id for obj in plan.objectives],
        pending=[obj.id for obj in plan.objectives],
        retrieved=list(ctx.loaded),
        missing=list(ctx.missing),
    )

    waves = build_waves(plan)
    logger.info(
        "Executing %d objective(s) in %d wave(s)",
        len(plan.objectives),
        len(waves),
    )

    for index, wave in enumerate(waves, start=1):
        if len(wave) == 1:
            result = run_capability(wave[0], ctx, state)
            state.record(result)
            continue

        workers = max(1, min(len(wave), settings.agent_max_workers))
        logger.info("Wave %d — running %d capabilities in parallel", index, len(wave))

        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(run_capability, obj, ctx, state): obj for obj in wave}
            for future in as_completed(futures):
                objective = futures[future]
                try:
                    result = future.result()
                except Exception as exc:  # noqa: BLE001 — defensive; run_capability already catches
                    logger.exception("Wave execution error for %s", objective.capability)
                    result = CapabilityResult(
                        objective_id=objective.id,
                        capability=objective.capability,
                        success=False,
                        error=str(exc)[:300],
                    )
                state.record(result)

    return state
