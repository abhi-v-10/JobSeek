import os

from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv(override=True)


class Settings(BaseModel):
	"""Application settings sourced from environment variables."""

	# openai_api_key: str | None = Field(default=None, description="OpenAI API key")
	# openai_model: str = Field(default="gpt-4o-mini", description="Default AI model")
	hf_token: str | None = Field(default=None, description="Hugging Face API token")
	hf_model: str = Field(default="Qwen/Qwen3-14B", description="Default HF AI model")
	django_api_base_url: str | None = Field(
		default=None, description="Base URL for Django API"
	)
	django_internal_token: str | None = Field(
		default=None, description="Internal token for Django calls"
	)

	# ── Agent pipeline ────────────────────────────────────────────────────────
	# "agent"  → objective-driven planner + parallel executor (new architecture)
	# "legacy" → original single-intent → single-tool dispatch chain
	agent_mode: str = Field(
		default="agent",
		description="Chat pipeline: 'agent' (objective-driven) or 'legacy' (single intent).",
	)
	agent_planner_enabled: bool = Field(
		default=True,
		description="Allow the LLM planner fallback. If False, only deterministic fast-path rules are used.",
	)
	agent_max_workers: int = Field(
		default=4,
		description="Max capabilities executed in parallel within one dependency wave.",
	)
	agent_max_objectives: int = Field(
		default=4,
		description="Hard cap on objectives per turn — protects latency and cost.",
	)
	agent_planner_max_tokens: int = Field(
		default=400,
		description="Token ceiling for the single structured planning call.",
	)
	agent_confirm_writes: bool = Field(
		default=True,
		description="Require explicit user confirmation before any profile write action.",
	)
	agent_debug_plan: bool = Field(
		default=False,
		description="Attach the internal execution plan to response metadata (development only).",
	)


def _env_bool(name: str, default: bool) -> bool:
	"""Parse a boolean env var tolerantly ('1', 'true', 'yes', 'on')."""
	raw = os.getenv(name)
	if raw is None:
		return default
	return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
	"""Parse an int env var, falling back to the default on bad input."""
	raw = os.getenv(name)
	if raw is None:
		return default
	try:
		return int(raw)
	except (TypeError, ValueError):
		return default


settings = Settings(
	# openai_api_key=os.getenv("OPENAI_API_KEY"),
	# openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
	hf_token=os.getenv("HF_TOKEN"),
	hf_model=os.getenv("HF_MODEL", "Qwen/Qwen3-14B"),
	django_api_base_url=os.getenv("DJANGO_API_BASE_URL"),
	django_internal_token=os.getenv("DJANGO_INTERNAL_TOKEN"),
	agent_mode=(os.getenv("SEEKBOT_AGENT_MODE") or "agent").strip().lower(),
	agent_planner_enabled=_env_bool("SEEKBOT_AGENT_PLANNER", True),
	agent_max_workers=_env_int("SEEKBOT_AGENT_MAX_WORKERS", 4),
	agent_max_objectives=_env_int("SEEKBOT_AGENT_MAX_OBJECTIVES", 4),
	agent_planner_max_tokens=_env_int("SEEKBOT_AGENT_PLANNER_MAX_TOKENS", 400),
	agent_confirm_writes=_env_bool("SEEKBOT_AGENT_CONFIRM_WRITES", True),
	agent_debug_plan=_env_bool("SEEKBOT_AGENT_DEBUG_PLAN", False),
)


# OPENAI_API_KEY = settings.openai_api_key
HF_TOKEN = settings.hf_token
DJANGO_API_BASE_URL = settings.django_api_base_url
DJANGO_INTERNAL_TOKEN = settings.django_internal_token

AGENT_MODE = settings.agent_mode
AGENT_ENABLED = settings.agent_mode != "legacy"
