"""
Capability registry.

Principle 3: tools are capabilities, never routing destinations. The planner
selects a capability to satisfy an *objective*; it never sees tool modules,
function signatures, or Django endpoints. Everything below is a thin,
uniform adapter over the existing tools in app/tools/ — no scoring, parsing,
or matching logic is duplicated here.

Adding a capability = one Capability entry. The planner prompt is generated
from this registry, so new capabilities become plannable automatically.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Callable, Optional

from app.agent.context import AgentContext
from app.agent.schemas import AgentState, CapabilityResult, Objective
from app.core.ai_logger import log_tool_call
from app.core.skill_utils import (
    TECH_RE,
    canonical_skill_name,
    expand_skills_with_aliases,
    extract_skills_from_profile,
    filter_demonstrated_skills,
    fuzzy_skill_match,
    infer_skills_from_title,
)
from app.core.voice import enforce_second_person
from app.services.django_service import add_user_skills
from app.services.openai_service import ask_ai
from app.tools import (
    application_strategy_tool,
    career_progress_tool,
    interview_tool,
    resume_optimizer_tool,
    resume_tool,
    job_tool,
)
from app.tools.personalized_job_recommender import recommend_jobs_for_user

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Registry model
# ---------------------------------------------------------------------------


Handler = Callable[[Objective, AgentContext, AgentState], CapabilityResult]


@dataclass(frozen=True)
class Capability:
    """
    One thing the agent can do.

    Attributes:
        name: Registry key the planner emits.
        purpose: One-line description shown to the planner. Written from the
            user's point of view, since the planner matches objectives.
        requires: Context keys that must be loaded before this can run.
        produces: Default message_type of the output.
        parallel_safe: False for capabilities that write data or are already
            heavy orchestrators — those run alone.
        writes: True if the capability mutates user data (triggers confirmation).
        handler: The adapter function.
    """

    name: str
    purpose: str
    handler: Handler
    requires: tuple[str, ...] = ()
    produces: str = "text"
    parallel_safe: bool = True
    writes: bool = False
    params_hint: str = ""


_REGISTRY: dict[str, Capability] = {}


def register(capability: Capability) -> Capability:
    _REGISTRY[capability.name] = capability
    return capability


def get_capability(name: str) -> Optional[Capability]:
    return _REGISTRY.get(name)


def all_capabilities() -> dict[str, Capability]:
    return dict(_REGISTRY)


def capability_names() -> list[str]:
    return list(_REGISTRY.keys())


def required_context_for(names: list[str]) -> list[str]:
    """Union of context keys needed by the given capabilities."""
    keys: list[str] = []
    for name in names:
        cap = _REGISTRY.get(name)
        if not cap:
            continue
        for key in cap.requires:
            if key not in keys:
                keys.append(key)
    return keys


def planner_catalogue() -> str:
    """Render the registry as a compact catalogue for the planner prompt."""
    lines: list[str] = []
    for cap in _REGISTRY.values():
        hint = f" | params: {cap.params_hint}" if cap.params_hint else ""
        lines.append(f"- {cap.name}: {cap.purpose}{hint}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _jobs_payload(recommended_jobs: list) -> list[dict]:
    """Map RecommendedJob models into the frontend's job-card shape."""
    return [
        {
            "id": job.job_id,
            "title": job.title,
            "company_name": job.company,
            "location": job.location,
            "is_remote": job.is_remote,
            "job_type": "corporate",
            "skills": (", ".join(job.matching_skills + job.missing_skills) or None),
            "created_at": job.created_at,
        }
        for job in recommended_jobs
    ]


def _param_str(objective: Objective, key: str, fallback: str = "") -> str:
    value = objective.params.get(key)
    return value.strip() if isinstance(value, str) and value.strip() else fallback


def _param_int(objective: Objective, key: str, fallback: int) -> int:
    value = objective.params.get(key)
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _ok(objective: Objective, text: str, message_type: str = "text", data=None, **extra) -> CapabilityResult:
    return CapabilityResult(
        objective_id=objective.id,
        capability=objective.capability,
        success=True,
        text=text,
        message_type=message_type,
        data=data,
        **extra,
    )


# ---------------------------------------------------------------------------
# Capability: job_search
# ---------------------------------------------------------------------------


def _run_job_search(obj: Objective, ctx: AgentContext, state: AgentState) -> CapabilityResult:
    """Keyword job lookup — used when the user names concrete criteria."""
    query = _param_str(obj, "query", ctx.message)
    log_tool_call(ctx.session_id, "job_search", f'query="{query[:60]}"')

    text, raw_jobs = job_tool.run_with_data(query)
    return _ok(obj, text, "jobs", raw_jobs or None)


register(
    Capability(
        name="job_search",
        purpose="Find job listings matching explicit criteria the user stated (role, skill, location).",
        handler=_run_job_search,
        requires=(),
        produces="jobs",
        params_hint="query",
    )
)


# ---------------------------------------------------------------------------
# Capability: job_recommendation
# ---------------------------------------------------------------------------


def _run_job_recommendation(obj: Objective, ctx: AgentContext, state: AgentState) -> CapabilityResult:
    """Personalised, scored job matches based on the user's own profile."""
    log_tool_call(
        ctx.session_id,
        "job_recommender",
        f"skills={len(ctx.profile_skills)} has_resume={'yes' if ctx.has_resume else 'no'}",
    )

    recommendations = recommend_jobs_for_user(
        user_profile=ctx.profile,
        resume_text=ctx.resume_text or None,
        target_role=_param_str(obj, "target_role") or None,
        user_query=_param_str(obj, "query", ctx.message),
        limit=_param_int(obj, "limit", 10),
    )

    # No personalised matches — fall back to a plain search rather than
    # returning nothing (principle 7: prefer action).
    if not recommendations.recommended_jobs:
        log_tool_call(ctx.session_id, "job_search", "fallback — no recommendations found")
        fallback_text, fallback_jobs = job_tool.run_with_data(ctx.message)
        text = (
            f"{recommendations.summary}\n\n{fallback_text}"
            if fallback_text
            else recommendations.summary
        )
        return _ok(obj, text, "jobs", fallback_jobs or None)

    lines = [recommendations.summary]
    if recommendations.strategic_advice:
        lines.append("")
        lines.extend(f"• {tip}" for tip in recommendations.strategic_advice[:3])

    return _ok(obj, "\n".join(lines), "jobs", _jobs_payload(recommendations.recommended_jobs))


register(
    Capability(
        name="job_recommendation",
        purpose="Recommend jobs personalised to the user's own profile, skills and resume, with match scores.",
        handler=_run_job_recommendation,
        requires=("profile",),
        produces="jobs",
        params_hint="query, target_role, limit",
    )
)


# ---------------------------------------------------------------------------
# Capability: resume_analysis
# ---------------------------------------------------------------------------


def _run_resume_analysis(obj: Objective, ctx: AgentContext, state: AgentState) -> CapabilityResult:
    """Read the user's resume and answer about it, or give a structured review."""
    log_tool_call(ctx.session_id, "resume_review")
    question = _param_str(obj, "question", ctx.message)
    text = resume_tool.run(message=question, auth_token=ctx.authorization)
    return _ok(obj, text, "resume_feedback")


register(
    Capability(
        name="resume_analysis",
        purpose="Read and analyse the user's resume — review it, or answer a specific question about its contents.",
        handler=_run_resume_analysis,
        requires=(),
        produces="resume_feedback",
        params_hint="question",
    )
)


# ---------------------------------------------------------------------------
# Capability: resume_optimization
# ---------------------------------------------------------------------------


def _run_resume_optimization(obj: Objective, ctx: AgentContext, state: AgentState) -> CapabilityResult:
    """ATS scoring, keyword gaps and truthful rewrite suggestions."""
    log_tool_call(ctx.session_id, "resume_optimizer_tool")

    target_role = _param_str(obj, "target_role") or ctx.target_role
    job_description = ctx.file_context

    result = resume_optimizer_tool.optimize_resume(
        resume_text=ctx.resume_text,
        user_profile=ctx.profile,
        target_role=target_role,
        job_description=job_description,
    )
    return _ok(obj, resume_optimizer_tool.format_resume_optimization(result), "resume_feedback")


register(
    Capability(
        name="resume_optimization",
        purpose="Improve the resume for ATS and recruiters — scoring, keyword gaps, rewritten bullets.",
        handler=_run_resume_optimization,
        requires=("profile",),
        produces="resume_feedback",
        params_hint="target_role",
    )
)


# ---------------------------------------------------------------------------
# Capability: interview_prep
# ---------------------------------------------------------------------------


def _run_interview_prep(obj: Objective, ctx: AgentContext, state: AgentState) -> CapabilityResult:
    """Role-specific questions, study plan and mock rounds."""
    log_tool_call(ctx.session_id, "interview_prep")

    payload = interview_tool.prepare_interview(
        target_role=_param_str(obj, "target_role", ctx.message),
        user_profile=ctx.profile,
        resume_text=ctx.resume_text or None,
        job_description=ctx.file_context,
        experience_level=ctx.experience_level,
        focus_area=_param_str(obj, "focus_area") or None,
        question_count=_param_int(obj, "question_count", 10),
    )

    lines = [payload.preparation_summary]
    if payload.recommended_topics_to_study:
        lines.append(f"Focus topics: {', '.join(payload.recommended_topics_to_study[:5])}.")
    if payload.final_tips:
        lines.append(f"Tip: {payload.final_tips[0]}")

    return _ok(obj, "\n".join(lines), "interview", payload.model_dump())


register(
    Capability(
        name="interview_prep",
        purpose="Prepare the user for an interview — questions, mock rounds, study plan for a target role.",
        handler=_run_interview_prep,
        requires=("profile",),
        produces="interview",
        params_hint="target_role, focus_area, question_count",
    )
)


# ---------------------------------------------------------------------------
# Capability: application_strategy
# ---------------------------------------------------------------------------


def _run_application_strategy(obj: Objective, ctx: AgentContext, state: AgentState) -> CapabilityResult:
    """Which roles to apply to, in what order, and what to fix first."""
    log_tool_call(ctx.session_id, "application_strategy_tool")

    recommendations = recommend_jobs_for_user(
        user_profile=ctx.profile,
        resume_text=ctx.resume_text or None,
        user_query=_param_str(obj, "query", ctx.message),
        limit=_param_int(obj, "limit", 10),
    )

    jobs_dicts = []
    for job in recommendations.recommended_jobs:
        job_dict = job.model_dump()
        job_dict["id"] = job.job_id
        job_dict["required_skills"] = job.matching_skills + job.missing_skills
        jobs_dicts.append(job_dict)

    strategy = application_strategy_tool.generate_application_strategy(
        user_profile=ctx.profile,
        resume_text=ctx.resume_text or None,
        recommended_jobs=jobs_dicts,
        target_role=_param_str(obj, "target_role") or ctx.target_role or "Your Next Role",
    )

    return _ok(
        obj,
        application_strategy_tool.format_application_strategy(strategy),
        "text",
        _jobs_payload(recommendations.recommended_jobs),
    )


register(
    Capability(
        name="application_strategy",
        purpose="Decide which jobs to apply to first, whether the user is ready, and what to fix before applying.",
        handler=_run_application_strategy,
        requires=("profile",),
        produces="text",
        params_hint="query, target_role",
    )
)


# ---------------------------------------------------------------------------
# Capability: readiness_check
# ---------------------------------------------------------------------------

_SEVERITY_RANK: dict[str, int] = {"High": 3, "Medium": 2, "Low": 1}


def _top_skill_gaps(strategy, limit: int = 5) -> list[str]:
    """
    Aggregate skill gaps across opportunities into one ranked, de-duplicated
    list — a short "biggest gaps" line, not the tool's full per-job breakdown.
    """
    frequency: dict[str, int] = {}
    worst_severity: dict[str, str] = {}

    for opportunity in strategy.strongest_opportunities + strategy.stretch_opportunities:
        for gap in opportunity.skill_gaps:
            frequency[gap.skill] = frequency.get(gap.skill, 0) + 1
            if _SEVERITY_RANK.get(gap.severity, 0) > _SEVERITY_RANK.get(worst_severity.get(gap.skill, ""), 0):
                worst_severity[gap.skill] = gap.severity

    ranked = sorted(
        frequency,
        key=lambda skill: (-_SEVERITY_RANK.get(worst_severity.get(skill, ""), 0), -frequency[skill]),
    )
    return ranked[:limit]


# Verdict bands. The user asked a yes/no question ("is my resume good enough?"),
# so the reply opens with an actual answer — encouraging but honest, never
# "you're perfect" and never "you have no chance".
def _readiness_verdict(score: float, role_label: str) -> str:
    if score >= 75:
        return f"Yes — you're already competitive for most {role_label}."
    if score >= 60:
        return f"Mostly yes — you're competitive for a good number of {role_label}, with a couple of gaps worth closing."
    if score >= 45:
        return f"You're close. You've got the foundation for {role_label}, but a few gaps are holding you back right now."
    return (
        f"Honestly, not quite yet for most {role_label} — but you're closer than you might think, "
        "and the gaps are specific enough to fix."
    )


# Umbrella terms that are true of almost everyone — they pad the justification
# without telling the user anything they'd recognise as a strength.
_GENERIC_SKILLS = {"api", "rest", "git", "sql", "nosql", "orm", "linux", "html", "css"}


def _relevant_strengths(ctx: AgentContext, target_role: str, limit: int = 5) -> list[str]:
    """
    The user's skills that actually matter for the target role.

    Compared against what the role expects rather than a generic template, so
    the justification names evidence the user can recognise in their own resume.

    Two cases:
      - target is a role title ("backend developer") -> intersect with the
        skills that role expects.
      - target is a bare technology ("Python") -> lead with that technology and
        the skills that imply it, since that's what the user asked about.
    """
    user_skills = extract_skills_from_profile(ctx.profile, ctx.resume_text or None)
    expected = infer_skills_from_title(target_role) if target_role else set()

    if expected:
        relevant, _ = fuzzy_skill_match(user_skills, expected)
    else:
        relevant = sorted(user_skills)

    target_key = (target_role or "").strip().lower()

    def rank(skill: str) -> tuple[int, str]:
        key = skill.lower()
        # 0 = the thing they asked about, 1 = concrete tech, 2 = generic filler.
        if target_key and (key == target_key or target_key in expand_skills_with_aliases({key})):
            return (0, key)
        if key in _GENERIC_SKILLS:
            return (2, key)
        return (1, key)

    seen: set[str] = set()
    out: list[str] = []
    for skill in sorted(relevant, key=rank):
        key = skill.lower()
        if key in seen:
            continue
        seen.add(key)
        display = canonical_skill_name(skill)
        if display:
            out.append(display)
        if len(out) >= limit:
            break
    return out


def _humanise_list(items: list[str]) -> str:
    """['a','b','c'] -> 'a, b and c'."""
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    return f"{', '.join(items[:-1])} and {items[-1]}"


def _run_readiness_check(obj: Objective, ctx: AgentContext, state: AgentState) -> CapabilityResult:
    """
    A quick, honest readiness read: score, top skill gaps, matching job count.

    Same deterministic engine as application_strategy (readiness scoring,
    skill-gap analysis, job matching) — the difference is purely the output
    shape. This is for casual, doubt-laden questions ("not sure if my resume
    is good enough for X jobs") where the user never asked for a full
    application plan; application_strategy stays reserved for when they
    explicitly want one ("what should I apply to first", "build me a plan").
    """
    log_tool_call(ctx.session_id, "readiness_check")

    target_role = _param_str(obj, "target_role") or ctx.target_role or ""

    recommendations = recommend_jobs_for_user(
        user_profile=ctx.profile,
        resume_text=ctx.resume_text or None,
        target_role=target_role or None,
        user_query=_param_str(obj, "query", ctx.message),
        limit=_param_int(obj, "limit", 20),
    )

    jobs_dicts = []
    for job in recommendations.recommended_jobs:
        job_dict = job.model_dump()
        job_dict["id"] = job.job_id
        job_dict["required_skills"] = job.matching_skills + job.missing_skills
        jobs_dicts.append(job_dict)

    strategy = application_strategy_tool.generate_application_strategy(
        user_profile=ctx.profile,
        resume_text=ctx.resume_text or None,
        recommended_jobs=jobs_dicts,
        target_role=target_role or "your target roles",
    )

    job_count = len(recommendations.recommended_jobs)
    role_label = f"{target_role} roles" if target_role else "these roles"
    score = int(round(strategy.overall_readiness_score))

    # Gaps must be evidence-based. The scoring engine (and the model behind it)
    # can propose a gap the user demonstrably already has — recommending
    # "learn GenAI" to someone who shipped a Gemini integration destroys trust
    # in every other recommendation in the reply.
    user_skills = extract_skills_from_profile(ctx.profile, ctx.resume_text or None)
    top_gaps = [
        canonical_skill_name(gap)
        for gap in filter_demonstrated_skills(
            _top_skill_gaps(strategy, limit=8),
            user_skills,
            ctx.resume_text or None,
        )[:4]
    ]

    strengths = _relevant_strengths(ctx, target_role)

    # ── Answer the actual question first, then justify it ────────────────
    lines: list[str] = [_readiness_verdict(score, role_label)]

    if strengths:
        lines.append(
            f"\nI'd put you at roughly {score}% ready, mainly because you already have "
            f"{_humanise_list(strengths)} behind you."
        )
    else:
        lines.append(f"\nI'd put you at roughly {score}% ready for these roles right now.")

    if top_gaps:
        gap_intro = (
            "The main thing standing between you and a stronger match is"
            if len(top_gaps) == 1
            else "What would move the needle most:"
        )
        if len(top_gaps) == 1:
            lines.append(f"\n{gap_intro} {top_gaps[0]}.")
        else:
            lines.append(f"\n{gap_intro}")
            lines.extend(f"• {gap}" for gap in top_gaps)

        lines.append(
            f"\nThese come straight from what the {role_label} I'm seeing actually ask for — "
            f"I'd start with {top_gaps[0]}, since it shows up most often."
        )
    else:
        lines.append(
            "\nI'm not seeing a meaningful skill gap for these roles — at this point it's "
            "about how well your resume presents what you've already done."
        )

    if job_count:
        lines.append(
            f"\nI found {job_count} matching job{'s' if job_count != 1 else ''} for you today — "
            "worth a look while this is fresh."
        )

    return _ok(obj, "\n".join(lines), "jobs", _jobs_payload(recommendations.recommended_jobs))


register(
    Capability(
        name="readiness_check",
        purpose=(
            "Give a quick, honest readiness read for a type of role — score, top skill gaps, and how many "
            "matching jobs exist right now. Use for casual doubt about being good enough "
            "(\"not sure if my resume is good enough for X jobs\", \"am I qualified for Y\"), "
            "not an explicit request to build a full application strategy."
        ),
        handler=_run_readiness_check,
        requires=("profile",),
        produces="jobs",
        params_hint="target_role, query",
    )
)


# ---------------------------------------------------------------------------
# Capability: career_progress
# ---------------------------------------------------------------------------


def _run_career_progress(obj: Objective, ctx: AgentContext, state: AgentState) -> CapabilityResult:
    """Cross-cutting placement-readiness picture. Already orchestrates internally."""
    log_tool_call(ctx.session_id, "career_progress_tool")
    text = career_progress_tool.generate_career_progress(
        session_id=ctx.session_id,
        message=ctx.message,
        authorization=ctx.authorization,
    )
    return _ok(obj, text, "text")


register(
    Capability(
        name="career_progress",
        purpose="Report overall placement readiness and progress across applications, interviews and resume.",
        handler=_run_career_progress,
        requires=(),
        produces="text",
        # Heavy internal orchestrator (5 Django calls + 3 tools). Running it
        # alongside others would multiply load for little latency gain.
        parallel_safe=False,
    )
)


# ---------------------------------------------------------------------------
# Capability: skill_profile_sync  (WRITE)
# ---------------------------------------------------------------------------


_MIN_SKILL_LEN = 2


def _skills_from_resume(resume_text: str) -> list[str]:
    """Extract technology mentions from resume text, preserving first-seen casing."""
    found: dict[str, str] = {}
    for match in TECH_RE.finditer(resume_text or ""):
        raw = match.group(0).strip()
        key = raw.lower()
        if len(raw) >= _MIN_SKILL_LEN and key not in found:
            found[key] = raw
    return list(found.values())


def _missing_skills(ctx: AgentContext) -> list[str]:
    """Skills present in the resume but absent from the profile's skill list."""
    existing = {s.lower().strip() for s in ctx.profile_skills}
    # Normalise a few spellings so we don't propose near-duplicates.
    existing |= {s.replace(".", "").replace(" ", "") for s in existing}

    candidates = _skills_from_resume(ctx.resume_text)
    missing: list[str] = []
    for skill in candidates:
        key = skill.lower().strip()
        compact = key.replace(".", "").replace(" ", "")
        if key not in existing and compact not in existing:
            missing.append(skill)
    return missing


def _run_skill_profile_sync(obj: Objective, ctx: AgentContext, state: AgentState) -> CapabilityResult:
    """
    Add resume skills that are missing from the profile.

    Two-phase by design (settings.agent_confirm_writes):
      phase 1 — propose the exact list and stash it as a pending_action
      phase 2 — next turn, if the user confirms, write it

    Writes are additive only; nothing is ever deleted.
    """
    from app.core.config import settings

    log_tool_call(ctx.session_id, "skill_profile_sync")

    if not ctx.authorization:
        return CapabilityResult(
            objective_id=obj.id,
            capability=obj.capability,
            success=False,
            text="I need you to be signed in before I can update your profile.",
            error="no_auth",
        )

    if not ctx.has_resume:
        return CapabilityResult(
            objective_id=obj.id,
            capability=obj.capability,
            success=False,
            text="I couldn't find a parsed resume on your profile, so there are no skills to sync. Upload your resume and I'll take it from there.",
            error="no_resume",
        )

    # Explicit skill list passed in (e.g. confirmation turn) wins over extraction.
    explicit = obj.params.get("skills")
    skills = (
        [s for s in explicit if isinstance(s, str) and s.strip()]
        if isinstance(explicit, list)
        else _missing_skills(ctx)
    )
    skills = skills[:25]  # safety cap

    if not skills:
        return _ok(obj, "Your profile already lists every skill I can find in your resume — nothing to add.")

    confirmed = bool(obj.params.get("confirmed"))

    # ── Phase 1: propose ─────────────────────────────────────────────────
    if settings.agent_confirm_writes and not confirmed:
        preview = ", ".join(skills[:12])
        more = f" (+{len(skills) - 12} more)" if len(skills) > 12 else ""
        return _ok(
            obj,
            f"I found {len(skills)} skill(s) in your resume that aren't on your profile yet: "
            f"{preview}{more}.\n\nReply 'yes' and I'll add them.",
            pending_action={
                "type": "skill_profile_sync",
                "skills": skills,
                "category": "technical",
            },
        )

    # ── Phase 2: write ───────────────────────────────────────────────────
    outcome = add_user_skills(skills, category="technical", auth_token=ctx.authorization)
    added, failed = outcome["added"], outcome["failed"]

    log_tool_call(ctx.session_id, "skill_profile_sync", f"added={len(added)} failed={len(failed)}")

    if not added:
        return CapabilityResult(
            objective_id=obj.id,
            capability=obj.capability,
            success=False,
            text="I wasn't able to update your profile just now. Please try again in a moment.",
            error="write_failed",
        )

    text = f"Added {len(added)} skill(s) to your profile: {', '.join(added)}."
    if failed:
        text += f" {len(failed)} couldn't be saved."
    return _ok(obj, text)


register(
    Capability(
        name="skill_profile_sync",
        purpose="Update the user's profile by adding skills found in their resume that are missing from the profile.",
        handler=_run_skill_profile_sync,
        requires=("profile",),
        produces="text",
        parallel_safe=False,  # writes run alone
        writes=True,
        params_hint="skills (optional explicit list)",
    )
)


# ---------------------------------------------------------------------------
# Capability: general_answer
# ---------------------------------------------------------------------------


def _run_general_answer(obj: Objective, ctx: AgentContext, state: AgentState) -> CapabilityResult:
    """Career conversation, roadmaps, market questions, anything unstructured."""
    log_tool_call(ctx.session_id, "general_ai", f"objective={obj.goal[:40]}")
    text = ask_ai(
        _param_str(obj, "question", ctx.message),
        ctx.history,
        file_context=ctx.file_context,
        image_base64=ctx.image_base64,
    )
    return _ok(obj, text, "text")


register(
    Capability(
        name="general_answer",
        purpose="Answer career questions that need no tool — roadmaps, skills to learn, market trends, project ideas, general chat.",
        handler=_run_general_answer,
        requires=(),
        produces="text",
        params_hint="question",
    )
)


# ---------------------------------------------------------------------------
# Execution wrapper
# ---------------------------------------------------------------------------


def run_capability(objective: Objective, ctx: AgentContext, state: AgentState) -> CapabilityResult:
    """
    Execute one objective's capability, converting any failure into a result.

    A capability must never take down the turn — a failed objective becomes a
    failed CapabilityResult so the composer can still answer the others.
    """
    capability = get_capability(objective.capability)

    if capability is None:
        logger.warning("Unknown capability '%s' — routing to general_answer", objective.capability)
        capability = _REGISTRY["general_answer"]

    started = time.perf_counter()
    try:
        result = capability.handler(objective, ctx, state)
    except Exception as exc:  # noqa: BLE001 — isolate capability failures
        logger.exception("Capability '%s' failed", capability.name)
        result = CapabilityResult(
            objective_id=objective.id,
            capability=capability.name,
            success=False,
            text="",
            error=str(exc)[:300],
        )

    # Single voice choke point. Every capability's user-facing text passes
    # through here, so no tool — current or future — can leak recruiter-report
    # narration ("<Name> is a CS student who...") to the user, regardless of
    # what its own prompt does.
    if result.text:
        user_name = ctx.profile.get("full_name") or ctx.profile.get("username") if ctx.profile else None
        result.text = enforce_second_person(result.text, user_name)

    result.duration_ms = int((time.perf_counter() - started) * 1000)
    logger.info(
        "Capability done | %s | ok=%s | %dms",
        capability.name,
        result.success,
        result.duration_ms,
    )
    return result
