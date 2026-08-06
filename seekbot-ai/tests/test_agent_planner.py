"""
Planner tests — objective segmentation, capability selection, confirmation.

Plain script, matching this repo's test convention:
    python tests/test_agent_planner.py

Every assertion here runs with the LLM planner DISABLED, so the suite is
deterministic, offline, and fast. Tier 2 is exercised only for its JSON
parsing, which is pure.
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Force the deterministic tier so tests never hit the network.
os.environ["SEEKBOT_AGENT_PLANNER"] = "0"

from app.agent import planner  # noqa: E402
from app.agent.capabilities import capability_names, get_capability  # noqa: E402
from app.core.config import settings  # noqa: E402

settings.agent_planner_enabled = False


def _capabilities(message):
    """Convenience: the ordered capability list a message plans to."""
    plan = planner.build_plan(message)
    return [obj.capability for obj in plan.objectives]


# ---------------------------------------------------------------------------
# Tier 1 — single objective
# ---------------------------------------------------------------------------


def test_single_objective_routing():
    # Note: "show ... jobs" resolves to job_recommendation, not job_search.
    # That is deliberate, pre-existing behaviour from the rule layer (see
    # tests/test_routing.py) and is preserved unchanged by the agent pipeline.
    cases = {
        "Find react developer jobs in Bangalore": "job_search",
        "python jobs in hyderabad": "job_search",
        "Show me react developer jobs in Bangalore": "job_recommendation",
        "Recommend jobs for me": "job_recommendation",
        "Review my resume": "resume_analysis",
        "Optimize my resume for ATS": "resume_optimization",
        "Prepare me for a backend interview": "interview_prep",
        "What jobs should I apply for first?": "application_strategy",
        "How is my placement preparation going?": "career_progress",
    }
    for message, expected in cases.items():
        caps = _capabilities(message)
        assert caps == [expected], f"{message!r} -> {caps}, expected [{expected!r}]"


def test_single_objective_costs_no_llm_call():
    """Fast path must resolve without the planner."""
    plan = planner.build_plan("Show me python jobs in Hyderabad")
    assert plan.source == "fast_path", plan.source


# ---------------------------------------------------------------------------
# Tier 1 — multi-objective
# ---------------------------------------------------------------------------


def test_multi_objective_resume_then_profile_update():
    """
    "Analyse my resume and update my profile with the missing skills" is one
    action, not two: skill_profile_sync already reads the resume itself to
    find what's missing, so a separate full resume_analysis objective would
    just produce a redundant career-review essay alongside it.
    """
    caps = _capabilities("Analyze my resume and update my profile with the missing skills")
    assert caps == ["skill_profile_sync"], caps


def test_resume_analysis_survives_when_not_paired_with_a_write():
    """The subsumption rule must not blanket-suppress resume_analysis."""
    caps = _capabilities("Review my resume and recommend jobs for me")
    assert caps == ["resume_analysis", "job_recommendation"], caps


def test_multi_objective_variants():
    cases = {
        "Review my resume and recommend jobs for me": ["resume_analysis", "job_recommendation"],
        "Optimize my resume, then prepare me for an interview": ["resume_optimization", "interview_prep"],
        "Find react jobs in Pune and prepare me for the interview": ["job_search", "interview_prep"],
    }
    for message, expected in cases.items():
        caps = _capabilities(message)
        assert caps == expected, f"{message!r} -> {caps}, expected {expected}"


def test_conjunction_inside_one_objective_is_not_split():
    """'react and python jobs' is ONE objective, not two."""
    for message in (
        "Find me react and python developer jobs",
        "Show jobs in Hyderabad and Bangalore",
    ):
        caps = _capabilities(message)
        assert len(caps) == 1, f"{message!r} over-split into {caps}"


def test_duplicate_capabilities_are_collapsed():
    plan = planner.build_plan("Show me backend jobs and show me frontend jobs")
    assert len(plan.objectives) == 1, [o.capability for o in plan.objectives]


def test_objective_count_is_capped():
    message = (
        "Review my resume, optimize my resume, recommend jobs for me, "
        "prepare me for an interview, and show my career progress"
    )
    plan = planner.build_plan(message)
    assert len(plan.objectives) <= settings.agent_max_objectives, len(plan.objectives)


# ---------------------------------------------------------------------------
# Plan integrity
# ---------------------------------------------------------------------------


def test_every_capability_in_a_plan_exists():
    messages = [
        "Show me jobs",
        "Review my resume and recommend jobs",
        "What's the market like for AI engineers?",
        "How do I become a data scientist?",
        "Suggest some portfolio projects",
    ]
    for message in messages:
        for obj in planner.build_plan(message).objectives:
            assert get_capability(obj.capability) is not None, f"{message!r} -> unknown {obj.capability}"


def test_previously_unhandled_intents_now_route_explicitly():
    """
    career_roadmap / market_insights / skill_guidance / project_suggestions
    used to be classified then silently dropped into general chat.
    """
    for message in (
        "How do I become a backend developer?",
        "What's the salary trend for React developers?",
        "What should I learn next?",
        "Suggest projects for my portfolio",
    ):
        caps = _capabilities(message)
        assert caps, f"{message!r} produced no objectives"
        assert all(get_capability(c) for c in caps), caps


def test_required_context_is_derived_from_capabilities():
    plan = planner.build_plan("Recommend jobs for me")
    assert "profile" in plan.required_context, plan.required_context

    # Plain keyword search needs no user data, so no Django calls are made.
    plan = planner.build_plan("Find react jobs in Pune")
    assert plan.required_context == [], plan.required_context


def test_plan_is_never_empty():
    for message in ("", "   ", "asdkjhaskjdh", "hi"):
        plan = planner.build_plan(message)
        assert plan.objectives, f"{message!r} produced an empty plan"


def test_ids_are_contiguous_and_dependencies_are_valid():
    plan = planner.build_plan("Analyze my resume and update my profile with the missing skills")
    ids = [o.id for o in plan.objectives]
    assert ids == [f"o{i}" for i in range(1, len(ids) + 1)], ids
    for obj in plan.objectives:
        for dep in obj.depends_on:
            assert dep in ids and dep != obj.id, f"{obj.id} has bad dependency {dep}"


# ---------------------------------------------------------------------------
# Tier 0 — confirmation of pending writes
# ---------------------------------------------------------------------------


def test_confirmation_classification():
    for message in ("yes", "Yes please", "go ahead", "sure", "ok", "do it"):
        assert planner.classify_confirmation(message) is True, message
    for message in ("no", "nope", "cancel", "not now"):
        assert planner.classify_confirmation(message) is False, message
    for message in ("show me react jobs in pune instead", "what about interview prep for backend roles"):
        assert planner.classify_confirmation(message) is None, message


def test_confirmed_pending_action_executes_the_write():
    pending = {"type": "skill_profile_sync", "skills": ["FastAPI", "Docker"], "category": "technical"}
    plan = planner.build_plan("yes", pending_action=pending)

    assert plan.source == "confirmation", plan.source
    assert len(plan.objectives) == 1
    objective = plan.objectives[0]
    assert objective.capability == "skill_profile_sync"
    assert objective.params["confirmed"] is True
    assert objective.params["skills"] == ["FastAPI", "Docker"]


def test_declined_pending_action_does_not_write():
    pending = {"type": "skill_profile_sync", "skills": ["FastAPI"]}
    plan = planner.build_plan("no", pending_action=pending)
    assert [o.capability for o in plan.objectives] == ["general_answer"], plan.objectives


def test_changing_the_subject_drops_the_pending_action():
    pending = {"type": "skill_profile_sync", "skills": ["FastAPI"]}
    plan = planner.build_plan("actually show me react jobs in Pune", pending_action=pending)
    assert plan.source != "confirmation", plan.source
    assert "skill_profile_sync" not in [o.capability for o in plan.objectives]


# ---------------------------------------------------------------------------
# Readiness-doubt detection
# ---------------------------------------------------------------------------
#
# Regression coverage for: "I'm interested in python jobs but I'm not sure if
# my resume is good enough" used to resolve to plain job_search — the bare
# word "jobs" won a substring match before the doubt half of the sentence
# ever got a say, because the message never crosses a segmentation boundary
# (no "and"/"then") and Tier 1 trusted its first rule hit unconditionally.


def test_reported_case_routes_to_readiness_check_not_job_search():
    caps = _capabilities("I'm interested in python jobs but I'm not sure if my resume is good enough.")
    assert caps == ["readiness_check"], caps


def test_readiness_doubt_variants():
    for message in (
        "Is my resume good enough for AI jobs?",
        "not sure if my resume is good enough",
        "Am I qualified for backend roles?",
        "I want frontend jobs but I'm not sure if my profile is ready",
    ):
        caps = _capabilities(message)
        assert caps == ["readiness_check"], f"{message!r} -> {caps}"


def test_role_hint_is_extracted_from_the_jobs_phrase():
    plan = planner.build_plan("I'm interested in python jobs but I'm not sure if my resume is good enough.")
    assert plan.objectives[0].params.get("target_role") == "Python", plan.objectives[0].params

    plan = planner.build_plan("Is my resume good enough for AI jobs?")
    assert plan.objectives[0].params.get("target_role") == "AI", plan.objectives[0].params


def test_explicit_strategy_request_is_not_downgraded_to_readiness_check():
    """
    "Am I ready to apply?" already has dedicated, richer handling
    (application_strategy) — the new doubt detector must not steal it.
    """
    for message in (
        "Am I ready to apply?",
        "What jobs should I apply for first?",
        "Create an application strategy for me.",
    ):
        caps = _capabilities(message)
        assert caps == ["application_strategy"], f"{message!r} -> {caps}"


def test_unrelated_hedge_sentences_do_not_trigger_readiness_check():
    """The hedge+doubt fallback is gated on resume/profile/readiness context."""
    for message in (
        "I like React but I don't know GraphQL well",
        "I want to learn Go but I'm not sure where to start",
    ):
        caps = _capabilities(message)
        assert caps != ["readiness_check"], f"{message!r} incorrectly routed to readiness_check"


# ---------------------------------------------------------------------------
# Tier 2 — JSON extraction (pure, no network)
# ---------------------------------------------------------------------------


def test_json_extraction_handles_model_noise():
    payload = '{"objectives":[{"id":"o1","goal":"g","capability":"job_search","params":{},"depends_on":[]}]}'

    variants = [
        payload,
        f"```json\n{payload}\n```",
        f"<think>The user wants jobs. I should use job_search.</think>\n{payload}",
        f"Here is the plan:\n{payload}\nHope that helps.",
    ]
    for variant in variants:
        parsed = planner._extract_json(variant)
        assert isinstance(parsed, dict), variant[:60]
        assert parsed["objectives"][0]["capability"] == "job_search"

    assert planner._extract_json("no json at all") is None
    assert planner._extract_json("") is None


def test_planner_prompt_lists_every_capability():
    from app.agent.capabilities import planner_catalogue

    catalogue = planner_catalogue()
    for name in capability_names():
        assert name in catalogue, f"{name} missing from planner catalogue"


def run_tests():
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    for test in tests:
        test()
        print(f"  ok  {test.__name__}")
    print(f"\nAll {len(tests)} planner tests passed.")


if __name__ == "__main__":
    run_tests()
