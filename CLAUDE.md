# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

JobSeek is a job portal with three independent services that must run concurrently in development:

1. **`backend/`** — Django 6 REST API (the system of record: users, jobs, applications, messaging). Runs on port 8000.
2. **`frontend/`** — React 19 + TypeScript + Vite SPA. Runs on port 5173.
3. **`seekbot-ai/`** — Standalone FastAPI service ("SeekBot AI") that powers the AI career-assistant chat. Runs on port 8001. It has **no direct database access** — it calls back into the Django API over HTTP for any user/job/application data (see `seekbot-ai/app/services/django_service.py`), and forwards the caller's `Authorization` header to Django so requests stay scoped to that user.

`PROJECT_DOCUMENTATION.md` documents an earlier Supabase-based prototype of the frontend and is out of date — the app has since been migrated to a self-hosted Django backend. `seekbot-ai/seekbot-ai.md` describes the product vision/roadmap for SeekBot AI (some described features are aspirational/planned, not all implemented).

## Running the stack

`start-dev.bat` opens three Windows Terminal tabs, one per service. Equivalent manual commands:

```
# Django backend (port 8000)
cd backend
.venv\Scripts\activate
python manage.py runserver

# React frontend (port 5173)
cd frontend
npm run dev      # NOTE: as of writing this script is misnamed in package.json — check the "scripts" block

# SeekBot AI (port 8001)
cd seekbot-ai
.aivenv\Scripts\activate
uvicorn app.main:app --reload --port 8001
```

Each service has its own virtualenv (`backend/.venv`, `seekbot-ai/.aivenv`) and its own `.env` file (`backend/.env`, `seekbot-ai/.env`, `frontend/.env`). CORS on both the Django and FastAPI sides is hardcoded to allow only `http://localhost:5173` / `http://127.0.0.1:5173`.

## Backend (Django)

- Dependencies: `pip install -r backend/django_requirements.txt`
- Migrations: `python manage.py makemigrations` / `python manage.py migrate`
- Tests: `python manage.py test` (whole suite) or `python manage.py test apps.applications.tests.test_api` (single module). Most apps use a flat `tests.py`; `apps/applications` uses a `tests/` package with separate files for API, models, permissions, and validators.
- Django REST Framework + SimpleJWT for auth, `django-allauth` for Google/GitHub OAuth, `channels`/`daphne` (ASGI) for the messaging websocket consumer.
- Auth uses a custom `KeyRotationJWTAuthentication` (`apps/users/auth.py`): each issued JWT embeds a `jwt_key` claim that must match `Profile.jwt_key`. Rotating the profile's key (e.g. on password change) instantly invalidates all previously issued tokens without needing a blacklist lookup.
- SQLite (`db.sqlite3`) is the dev database.

### App layout (`backend/apps/`)

| App | Responsibility |
|---|---|
| `users` | Custom `User` model, `Profile`, auth (JWT + allauth), password reset via OTP, resume upload + parsing (`utils/resume_parser.py`, `management/commands/parse_resumes.py`) |
| `jobs` | `Job` model (single-table for both "corporate" and "domestic" job types, discriminated by `job_type`), search/filtering (`services/job_search_service.py`), saved/viewed job tracking, interaction stats |
| `applications` | Full application lifecycle tracking (`JobApplication` state machine, `ApplicationTimeline`, `ApplicationNote`, `InterviewRound`, `Offer`) — this is the data SeekBot AI reads to generate strategy/progress advice. Status transitions are validated in `validators.py` and enforced in `services/application_service.py`; most timeline events are auto-created via `signals.py`. |
| `messaging` | Real-time one-to-one messaging via Django Channels (`consumers.py`, `routing.py`) |
| `ai_chat` | Django-side persistence for SeekBot chat sessions/messages — this is what `seekbot-ai`'s `django_service.py` reads and writes over HTTP |

Routing is centralized in `backend/config/urls.py`; each app owns its own `urls.py` included under `/api/<app>/`.

## SeekBot AI (`seekbot-ai/`)

- Dependencies: `pip install -r seekbot-ai/ai_requirements.txt`
- Run: `uvicorn app.main:app --reload --port 8001` (from `seekbot-ai/`)
- Tests are plain scripts, not pytest-discovered — there's no `conftest.py`/pytest config, and each file exposes a `run_tests()` guarded by `if __name__ == "__main__"`. Run individually, e.g. `python tests/test_routing.py`.
- Uses a Hugging Face-hosted model (`HF_TOKEN`/`HF_MODEL` in `app/core/config.py`), not OpenAI, despite the `openai` package being a dependency (`app/core/openai_client.py` wraps the HF endpoint using the OpenAI-compatible client interface) and despite `openai_service.py`'s naming.

### Chat request flow (`app/api/chat.py`)

`chat.py` is a thin endpoint: it parses any attachment, persists the user message, loads history, runs the turn, and persists the reply. How the turn is run depends on `SEEKBOT_AGENT_MODE`:

- **`agent`** (default) — the objective-driven pipeline in `app/agent/`.
- **`legacy`** — the original single-intent → single-tool dispatch chain, preserved verbatim in `_legacy_turn()`. This is the instant-revert path; do not add new behaviour to it.

#### Agent pipeline (`app/agent/`)

    build_plan() → load_context() → execute_plan() → verify() → compose()

| Module | Responsibility |
|---|---|
| `planner.py` | Turns the message into **objectives**, not keywords. Three tiers, first hit wins: **Tier 0** confirmation of a pending write; **Tier 1** deterministic segmentation + the existing rule layer (0 LLM calls, handles multi-objective messages); **Tier 2** one structured-JSON LLM call. Never returns an empty plan. |
| `capabilities.py` | The registry. Uniform adapters over `app/tools/` — no scoring/parsing/matching logic is duplicated here. The planner prompt is **generated from this registry**, so a new `Capability` entry becomes plannable automatically. |
| `context.py` | Fetches only the Django data the plan declared (`profile`, `dashboard`, `analytics`, `interviews`) **in parallel**, best-effort. Failures degrade to empty values recorded in `missing`. |
| `executor.py` | Resolves `depends_on` into execution waves; each wave runs on a thread pool. Capabilities with `parallel_safe=False` (writes, and `career_progress`, which is already a heavy internal orchestrator) get a wave to themselves. |
| `completion.py` | One deterministic pre-response check — zero LLM calls. Flags silently-skipped objectives and the only two blocking conditions (`no_resume`, `no_auth`). |
| `composer.py` | Merges all outputs into one reply. Multi-objective turns keep the existing frontend contract: the richest capability's `message_type` leads, and every payload is merged into `metadata` (`jobs`, `interview`, ...). |

LLM budget: **0 calls** for a fast-path plan with deterministic capabilities, **1** if the planner falls through to Tier 2 or a capability needs generation. The orchestrator itself never calls the model.

Intent → capability mapping lives in `planner._INTENT_CAPABILITY`. Every intent the rule layer can emit is mapped there — including `career_roadmap`, `market_insights`, `skill_guidance` and `project_suggestions`, which the legacy chain classified but then silently dropped into general chat.

Rule ordering in `intent_service.detect_intent_rule` still matters and is unchanged — `application_strategy` and `job_recommendation` triggers are checked before the more generic `job_search`/`resume_review` keyword sets. Note that `"show ... jobs"` deliberately resolves to `job_recommendation`, not `job_search`.

`planner._rule_intent` adds one more override on top of `detect_intent_rule`: a message that hedges doubt about being "good enough" (`"I'm interested in python jobs but I'm not sure if my resume is good enough"`) routes to the `readiness_check` capability instead of whatever generic keyword (e.g. bare "jobs") happened to match first. This exists because such messages are a single segment (no "and"/"then" boundary), so Tier 1 would otherwise trust its first keyword hit and never consider the rest of the sentence. `readiness_check` reuses `application_strategy_tool`'s deterministic readiness scoring but returns a short conversational summary (score, top gaps, job count) instead of the tool's full markdown report — `application_strategy` stays reserved for when the user explicitly asks for a plan ("what should I apply to first", "am I ready to apply?").

#### Voice (`app/core/voice.py`)

SeekBot talks **to** the user, never **about** them. `VOICE_RULES` is a prompt fragment every generative tool appends (`openai_service.SYSTEM_PROMPT`, `application_strategy_tool`), so the instruction lives in one place.

Prompt instructions alone proved unreliable — models slip into recruiter-report narration ("`<Name>` is a Computer Science student with strong backend experience...") especially when the payload carries the user's name. So `capabilities.run_capability()` applies `enforce_second_person()` to **every** capability's text before it leaves the agent. That is the single voice choke point: no tool, current or future, can leak third-person copy regardless of what its own prompt does. `application_strategy_tool` additionally guards its structured fields (`career_summary`, `why_recommended`, advice, next steps) via `_enforce_strategy_voice()`.

If you add a generative capability, you get the guard for free — do not bypass `run_capability`.

#### Evidence-based recommendations

`skill_utils.filter_demonstrated_skills()` drops proposed gaps the user already demonstrates, checking direct matches, alias implications (`gemini`/`elevenlabs` ⇒ `generative ai`, `llm`), and literal resume text. Matching is word-boundary, not substring — `orm` is a substring of `terraform`, and a Django user's implied ORM knowledge must not suppress a genuine Terraform gap. `readiness_check` runs every gap through this filter before display; recommending "learn GenAI" to someone who shipped a Gemini integration destroys trust in every other recommendation in the reply.

Skills display through `canonical_skill_name()` — `str.title()` mangles technology names ("Fastapi", "Ci/Cd", "Node.Js").

#### Write actions

`skill_profile_sync` is the only capability that mutates user data. It is **additive only** — writes go one-at-a-time through `POST /users/skills/`, never `POST /users/skills/bulk/`, because the bulk endpoint deletes every existing skill before recreating. It is two-phase when `SEEKBOT_AGENT_CONFIRM_WRITES=1` (default): phase 1 proposes the exact skill list and stashes it as `metadata.pending_action`; phase 2 executes it on the next turn if the user confirms. Django round-trips that metadata, so no extra state store is needed.

#### Agent environment flags (all optional, `seekbot-ai/.env`)

`SEEKBOT_AGENT_MODE` (`agent`|`legacy`), `SEEKBOT_AGENT_PLANNER` (enable Tier 2), `SEEKBOT_AGENT_MAX_WORKERS`, `SEEKBOT_AGENT_MAX_OBJECTIVES`, `SEEKBOT_AGENT_PLANNER_MAX_TOKENS`, `SEEKBOT_AGENT_CONFIRM_WRITES`, `SEEKBOT_AGENT_DEBUG_PLAN` (attaches `_plan`/`_state` to response metadata).

Agent tests: `python tests/test_agent_planner.py` and `python tests/test_agent_pipeline.py`. Both run fully offline — the planner suite forces Tier 1, the pipeline suite stubs capabilities with instrumented fakes.

Tools that need user context (profile, resume text, skills) still fetch it best-effort — under the agent pipeline this is centralized in `context.py`, so a tool receives an already-loaded profile rather than making its own call.

## Frontend (`frontend/`)

- `npm install`, then run the Vite dev script (see note above about its name in `package.json`), `npm run build`, `npm run lint`.
- React 19, React Router 7, Tailwind CSS 4 (via `@tailwindcss/vite`, no separate PostCSS config), `radix-ui` primitives, `shadcn` for component generation, `axios` for API calls, `gsap`/`motion`/`three` for animation.
- Talks to the Django backend directly (not to SeekBot AI directly) — chat messages are sent to Django's `/api/chat/` endpoints, which proxy to the FastAPI service server-side.

## Known repo issues worth knowing about

- `backend/config/settings.py` hardcodes a real Django `SECRET_KEY` plus live Google and GitHub OAuth client secrets directly in source, and a matching Google `client_secret_*.json` sits at the repo root — both are tracked in git, not gitignored. Treat any credential in that file as already leaked; if you touch OAuth config, move secrets into `.env` instead of adding more inline.
