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

Every chat turn:
1. Persists the user message to Django (`django_service.save_message`), passing through the caller's `Authorization` header.
2. Runs `services/intent_service.detect_intent()` — a two-stage classifier: fast keyword/phrase rules first (`detect_intent_rule`), falling back to an AI classification prompt (`detect_intent_ai`) only if no rule matches. When adding new intents or trigger phrases, rule ordering matters — e.g. `application_strategy` and `job_recommendation` triggers are checked before the more generic `job_search`/`resume_review` keyword sets, since substring checks would otherwise misclassify them.
3. Dispatches to a tool in `app/tools/` based on intent (`job_tool`, `resume_tool`, `resume_optimizer_tool`, `interview_tool`, `application_strategy_tool`, `career_progress_tool`, `personalized_job_recommender`) or falls back to a general chat completion (`ask_ai`).
4. Persists the assistant reply back to Django along with structured `metadata` (e.g. job cards, interview payloads) that the frontend renders based on `message_type`.

Tools that need user context (profile, resume text, skills) fetch it best-effort via `fetch_user_profile()` — failures are swallowed so the tool still runs with an empty profile rather than erroring the whole chat turn.

## Frontend (`frontend/`)

- `npm install`, then run the Vite dev script (see note above about its name in `package.json`), `npm run build`, `npm run lint`.
- React 19, React Router 7, Tailwind CSS 4 (via `@tailwindcss/vite`, no separate PostCSS config), `radix-ui` primitives, `shadcn` for component generation, `axios` for API calls, `gsap`/`motion`/`three` for animation.
- Talks to the Django backend directly (not to SeekBot AI directly) — chat messages are sent to Django's `/api/chat/` endpoints, which proxy to the FastAPI service server-side.

## Known repo issues worth knowing about

- `backend/config/settings.py` hardcodes a real Django `SECRET_KEY` plus live Google and GitHub OAuth client secrets directly in source, and a matching Google `client_secret_*.json` sits at the repo root — both are tracked in git, not gitignored. Treat any credential in that file as already leaked; if you touch OAuth config, move secrets into `.env` instead of adding more inline.
