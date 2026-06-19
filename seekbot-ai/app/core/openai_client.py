"""
OpenAI client factory for SeekBot AI.

Provides a single shared OpenAI client configured from settings.
"""

from __future__ import annotations

import logging
import json
from typing import Optional, Any, Dict, List

# from openai import OpenAI
from huggingface_hub import InferenceClient

from app.core.config import settings

logger = logging.getLogger(__name__)

# _client: Optional[OpenAI] = None
_client = None

FALLBACK_MODELS = [
    "Qwen/Qwen2.5-7B-Instruct",
    "mistralai/Mistral-7B-Instruct-v0.3",
    "meta-llama/Llama-3.1-8B-Instruct",
]


def get_openai_client():
    """Return a shared AI client configured with the API key."""
    global _client

    if _client is not None:
        return _client

    if not settings.hf_token:
        logger.error("HF_TOKEN is not configured")
        raise RuntimeError("HF_TOKEN is not configured")
    
    # Omitting provider allows HuggingFace to auto-route to supported providers (e.g. Groq)
    _client = InferenceClient(
        api_key=settings.hf_token
    )
    return _client

def generate_chat_completion(messages: List[Dict[str, Any]], **kwargs) -> Any:
    """
    Central wrapper for chat completions with graceful fallbacks and structured logging.
    """
    client = get_openai_client()
    
    primary_model = settings.hf_model or "Qwen/Qwen3-14B"
    # User might pass model in kwargs, prioritize it
    target_model = kwargs.pop("model", primary_model)
    
    models_to_try = [target_model] + [m for m in FALLBACK_MODELS if m != target_model]
    
    try:
        payload_size = len(json.dumps(messages).encode("utf-8"))
    except Exception:
        payload_size = -1
    
    for attempt, model in enumerate(models_to_try):
        try:
            logger.info(f"Attempting chat completion | model={model} | payload_bytes={payload_size} | attempt={attempt + 1}")
            
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                **kwargs
            )
            
            logger.info(f"Chat completion successful | model={model} | status=success")
            return response
            
        except Exception as exc:
            logger.error(f"Chat completion failed | model={model} | error={exc} | attempt={attempt + 1}")
            if attempt == len(models_to_try) - 1:
                logger.critical("All fallback models failed.")
                raise RuntimeError(f"All models failed. Last error: {exc}") from exc
            
            logger.info("Falling back to next model...")
