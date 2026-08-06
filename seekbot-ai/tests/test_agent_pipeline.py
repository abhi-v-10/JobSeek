"""
Executor / completion / composer tests.

Plain script, matching this repo's test convention:
    python tests/test_agent_pipeline.py

Capabilities are stubbed with instrumented fakes, so nothing here touches
Django, the model endpoint, or the network. What is verified is the pipeline
itself: parallelism, dependency ordering, failure isolation, the completion
check, and response merging.
"""

import logging
import os
import sys
import threading
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

os.environ["SEEKBOT_AGENT_PLANNER"] = "0"

# Several tests deliberately trigger capability failures to prove they are
# isolated. Their stack traces are expected — keep them out of the output.
logging.disable(logging.CRITICAL)

from app.agent import capabilities as caps  # noqa: E402
from app.agent.completion import verify  # noqa: E402
from app.agent.composer import compose, extract_pending_action  # noqa: E402
from app.agent.context import AgentContext  # noqa: E402
from app.agent.executor import build_waves, execute_plan  # noqa: E402
from app.agent.schemas import AgentState, CapabilityResult, ExecutionPlan, Objective  # noqa: E402


# ---------------------------------------------------------------------------
# Stub helpers
# ---------------------------------------------------------------------------


class _Tracker:
    """Records concurrency and ordering across stubbed capabilities."""

    def __init__(self):
        self.lock = threading.Lock()
        self.active = 0
        self.peak = 0
        self.order = []


def _stub(name, tracker, *, delay=0.05, fail=False, message_type="text", data=None, parallel_safe=True):
    """Register a fake capability that records when it ran."""

    def handler(objective, ctx, state):
        with tracker.lock:
            tracker.active += 1
            tracker.peak = max(tracker.peak, tracker.active)
            tracker.order.append(name)
        time.sleep(delay)
        with tracker.lock:
            tracker.active -= 1

        if fail:
            raise RuntimeError(f"{name} exploded")

        return CapabilityResult(
            objective_id=objective.id,
            capability=name,
            success=True,
            text=f"{name} output",
            message_type=message_type,
            data=data,
        )

    caps.register(
        caps.Capability(
            name=name,
            purpose=f"stub {name}",
            handler=handler,
            parallel_safe=parallel_safe,
        )
    )


def _plan(*objectives):
    return ExecutionPlan(objectives=list(objectives), source="fast_path")


def _ctx():
    return AgentContext(session_id="test-session", message="test message")


def _obj(oid, capability, depends_on=None):
    return Objective(id=oid, goal=f"goal {oid}", capability=capability, depends_on=depends_on or [])


# ---------------------------------------------------------------------------
# Executor
# ---------------------------------------------------------------------------


def test_independent_objectives_run_in_parallel():
    tracker = _Tracker()
    _stub("t_par_a", tracker)
    _stub("t_par_b", tracker)
    _stub("t_par_c", tracker)

    plan = _plan(_obj("o1", "t_par_a"), _obj("o2", "t_par_b"), _obj("o3", "t_par_c"))

    started = time.perf_counter()
    state = execute_plan(plan, _ctx())
    elapsed = time.perf_counter() - started

    assert tracker.peak >= 2, f"expected concurrency, peak was {tracker.peak}"
    assert elapsed < 0.14, f"serial execution suspected ({elapsed:.3f}s for 3x50ms)"
    assert len(state.completed) == 3, state.completed


def test_dependencies_are_serialised():
    tracker = _Tracker()
    _stub("t_dep_first", tracker, delay=0.02)
    _stub("t_dep_second", tracker, delay=0.02)

    plan = _plan(_obj("o1", "t_dep_first"), _obj("o2", "t_dep_second", depends_on=["o1"]))
    execute_plan(plan, _ctx())

    assert tracker.order == ["t_dep_first", "t_dep_second"], tracker.order


def test_write_capabilities_get_their_own_wave():
    tracker = _Tracker()
    _stub("t_read_x", tracker, delay=0.02)
    _stub("t_write_y", tracker, delay=0.02, parallel_safe=False)

    plan = _plan(_obj("o1", "t_read_x"), _obj("o2", "t_write_y"))
    waves = build_waves(plan)

    assert len(waves) == 2, [[o.capability for o in w] for w in waves]
    execute_plan(plan, _ctx())
    assert tracker.peak == 1, tracker.peak


def test_dependency_cycle_does_not_hang():
    tracker = _Tracker()
    _stub("t_cyc_a", tracker, delay=0.01)
    _stub("t_cyc_b", tracker, delay=0.01)

    plan = _plan(
        _obj("o1", "t_cyc_a", depends_on=["o2"]),
        _obj("o2", "t_cyc_b", depends_on=["o1"]),
    )
    state = execute_plan(plan, _ctx())
    assert len(state.results) == 2, state.results


def test_one_failure_does_not_kill_the_turn():
    tracker = _Tracker()
    _stub("t_fail_bad", tracker, delay=0.01, fail=True)
    _stub("t_fail_good", tracker, delay=0.01)

    plan = _plan(_obj("o1", "t_fail_bad"), _obj("o2", "t_fail_good"))
    state = execute_plan(plan, _ctx())

    assert state.failed == ["o1"], state.failed
    assert state.completed == ["o2"], state.completed


def test_unknown_capability_degrades_to_general_answer():
    objective = _obj("o1", "does_not_exist")
    result = caps.run_capability(objective, _ctx(), AgentState())
    # Coerced to general_answer, which will fail offline — the point is that
    # it produced a result instead of raising.
    assert isinstance(result, CapabilityResult)
    assert result.capability == "general_answer", result.capability


# ---------------------------------------------------------------------------
# Completion check
# ---------------------------------------------------------------------------


def test_completion_passes_when_all_objectives_succeed():
    tracker = _Tracker()
    _stub("t_done_a", tracker, delay=0.01)
    plan = _plan(_obj("o1", "t_done_a"))
    state = execute_plan(plan, _ctx())

    report = verify(plan, state)
    assert report.complete is True
    assert report.unmet == []


def test_completion_flags_a_silently_skipped_objective():
    plan = _plan(_obj("o1", "t_done_a"), _obj("o2", "t_missing"))
    state = AgentState(objectives=["o1", "o2"])
    state.record(CapabilityResult(objective_id="o1", capability="t_done_a", text="done"))

    report = verify(plan, state)
    assert report.complete is False
    assert len(report.unmet) == 1, report.unmet


def test_completion_detects_a_blocking_condition():
    plan = _plan(_obj("o1", "skill_profile_sync"))
    state = AgentState(objectives=["o1"])
    state.record(
        CapabilityResult(
            objective_id="o1",
            capability="skill_profile_sync",
            success=False,
            text="",
            error="no_resume",
        )
    )

    report = verify(plan, state)
    assert report.is_blocked is True
    assert "resume" in report.blocking_message.lower()


# ---------------------------------------------------------------------------
# Composer
# ---------------------------------------------------------------------------


def test_multiple_payloads_merge_into_metadata():
    tracker = _Tracker()
    _stub("t_comp_jobs", tracker, delay=0.01, message_type="jobs", data=[{"id": 1, "title": "Dev"}])
    _stub("t_comp_interview", tracker, delay=0.01, message_type="interview", data={"questions": []})

    plan = _plan(_obj("o1", "t_comp_jobs"), _obj("o2", "t_comp_interview"))
    state = execute_plan(plan, _ctx())
    turn = compose(plan, state, verify(plan, state))

    assert turn.message_type == "jobs", turn.message_type          # richest type leads
    assert "jobs" in turn.metadata and "interview" in turn.metadata, turn.metadata
    assert "t_comp_jobs output" in turn.text
    assert "t_comp_interview output" in turn.text


def test_message_type_is_always_django_safe():
    tracker = _Tracker()
    _stub("t_comp_bogus", tracker, delay=0.01, message_type="not_a_real_type", data={"x": 1})

    plan = _plan(_obj("o1", "t_comp_bogus"))
    state = execute_plan(plan, _ctx())
    turn = compose(plan, state, verify(plan, state))

    assert turn.message_type == "text", turn.message_type


def test_partial_failure_still_answers_the_successful_objective():
    tracker = _Tracker()
    _stub("t_mix_ok", tracker, delay=0.01, message_type="jobs", data=[{"id": 2}])
    _stub("t_mix_bad", tracker, delay=0.01, fail=True)

    plan = _plan(_obj("o1", "t_mix_ok"), _obj("o2", "t_mix_bad"))
    state = execute_plan(plan, _ctx())
    turn = compose(plan, state, verify(plan, state))

    assert "t_mix_ok output" in turn.text
    assert turn.message_type == "jobs"


def test_pending_action_round_trips_through_metadata():
    plan = _plan(_obj("o1", "skill_profile_sync"))
    state = AgentState(objectives=["o1"])
    state.record(
        CapabilityResult(
            objective_id="o1",
            capability="skill_profile_sync",
            text="I found 3 skills. Reply 'yes' and I'll add them.",
            pending_action={"type": "skill_profile_sync", "skills": ["Docker", "Redis", "AWS"]},
        )
    )

    turn = compose(plan, state, verify(plan, state))
    assert turn.metadata["pending_action"]["skills"] == ["Docker", "Redis", "AWS"]

    # ...and is recoverable from Django-shaped history on the next turn.
    history = [
        {"role": "user", "content": "analyze my resume and update my profile"},
        {"role": "assistant", "content": turn.text, "metadata": turn.metadata},
        {"role": "user", "content": "yes"},
    ]
    recovered = extract_pending_action(history)
    assert recovered is not None and recovered["skills"] == ["Docker", "Redis", "AWS"], recovered


def test_stale_pending_action_is_not_reused():
    """Only the most recent assistant message can hold a live pending action."""
    history = [
        {"role": "assistant", "content": "old", "metadata": {"pending_action": {"type": "skill_profile_sync"}}},
        {"role": "user", "content": "no thanks"},
        {"role": "assistant", "content": "ok", "metadata": {}},
        {"role": "user", "content": "yes"},
    ]
    assert extract_pending_action(history) is None
    assert extract_pending_action([]) is None


# ---------------------------------------------------------------------------
# Skill diffing (write capability, pure logic)
# ---------------------------------------------------------------------------


def test_missing_skills_diff_ignores_what_the_profile_already_has():
    ctx = AgentContext()
    ctx.profile = {
        "skills": [{"name": "Python"}, {"name": "React"}],
        "resume_text": "Built services with Python, React, FastAPI, Docker and PostgreSQL.",
    }

    missing = {s.lower() for s in caps._missing_skills(ctx)}
    assert "fastapi" in missing and "docker" in missing and "postgresql" in missing, missing
    assert "python" not in missing and "react" not in missing, missing


def test_missing_skills_is_empty_without_a_resume():
    ctx = AgentContext()
    ctx.profile = {"skills": [{"name": "Python"}], "resume_text": ""}
    assert caps._missing_skills(ctx) == []


# ---------------------------------------------------------------------------
# readiness_check gap aggregation (pure logic)
# ---------------------------------------------------------------------------


def _strategy_with_gaps(strongest_gaps, stretch_gaps):
    """Minimal ApplicationStrategyResponse-shaped stand-in for aggregation tests."""
    from app.tools.application_strategy_tool import ApplicationOpportunity, ApplicationStrategyResponse, SkillGap

    def _opportunity(gaps):
        return ApplicationOpportunity(
            job_id=1, title="Role", company="Co", match_score=70, readiness_score=70,
            application_priority="Strong Fit", confidence_level="Medium", why_recommended="fit",
            strengths_for_role=[], skill_gaps=[SkillGap(**g) for g in gaps], required_next_steps=[],
        )

    return ApplicationStrategyResponse(
        target_role="Role",
        career_summary="",
        overall_readiness_score=70.0,
        strongest_opportunities=[_opportunity(strongest_gaps)] if strongest_gaps else [],
        stretch_opportunities=[_opportunity(stretch_gaps)] if stretch_gaps else [],
        jobs_to_delay=[],
        application_strategy=[],
        strategic_advice=[],
        final_recommendation="",
    )


def test_top_skill_gaps_ranks_by_severity_then_frequency():
    strategy = _strategy_with_gaps(
        strongest_gaps=[
            {"skill": "Docker", "severity": "High", "recommendation": "x"},
            {"skill": "Testing", "severity": "Low", "recommendation": "x"},
        ],
        stretch_gaps=[
            {"skill": "Docker", "severity": "Medium", "recommendation": "x"},
            {"skill": "Kubernetes", "severity": "Medium", "recommendation": "x"},
        ],
    )
    top = caps._top_skill_gaps(strategy, limit=5)
    # Docker: High severity (worst seen) + appears twice -> ranks first.
    assert top[0] == "Docker", top
    assert "Testing" in top and "Kubernetes" in top


def test_top_skill_gaps_respects_limit_and_dedupes():
    strategy = _strategy_with_gaps(
        strongest_gaps=[{"skill": f"Skill{i}", "severity": "Medium", "recommendation": "x"} for i in range(8)],
        stretch_gaps=[{"skill": "Skill0", "severity": "High", "recommendation": "x"}],  # duplicate of Skill0
    )
    top = caps._top_skill_gaps(strategy, limit=5)
    assert len(top) == 5, top
    assert len(set(top)) == len(top), "duplicates were not collapsed"
    assert top[0] == "Skill0", "Skill0 has the worst severity (High) and highest frequency"


def test_top_skill_gaps_empty_when_no_gaps():
    strategy = _strategy_with_gaps(strongest_gaps=[], stretch_gaps=[])
    assert caps._top_skill_gaps(strategy) == []


def run_tests():
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    for test in tests:
        test()
        print(f"  ok  {test.__name__}")
    print(f"\nAll {len(tests)} pipeline tests passed.")


if __name__ == "__main__":
    run_tests()
