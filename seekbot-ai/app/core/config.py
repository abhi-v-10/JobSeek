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


settings = Settings(
	# openai_api_key=os.getenv("OPENAI_API_KEY"),
	# openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
	hf_token=os.getenv("HF_TOKEN"),
	hf_model=os.getenv("HF_MODEL", "Qwen/Qwen3-14B"),
	django_api_base_url=os.getenv("DJANGO_API_BASE_URL"),
	django_internal_token=os.getenv("DJANGO_INTERNAL_TOKEN"),
)


# OPENAI_API_KEY = settings.openai_api_key
HF_TOKEN = settings.hf_token
DJANGO_API_BASE_URL = settings.django_api_base_url
DJANGO_INTERNAL_TOKEN = settings.django_internal_token
