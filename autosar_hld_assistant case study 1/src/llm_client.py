"""
LLM client module.

Provides a modular abstraction for LLM access. Currently uses Groq's
OpenAI-compatible API. The abstraction supports future swapping to
OpenAI, Ollama, or other compatible providers.
"""

import time
import logging
from typing import Optional

from openai import OpenAI, APIError, APIConnectionError, RateLimitError
import config

logger = logging.getLogger(__name__)

_client = None


class LLMError(Exception):
    """Custom exception for LLM-related errors."""
    pass


def normalize_model_name(model_name: Optional[str] = None) -> str:
    """Normalize model names and map common aliases/typos to exact provider model IDs."""
    if not model_name:
        model_name = getattr(config, "GROQ_MODEL", "openai/gpt-oss-120b")
    model_name = str(model_name).strip()

    alias_map = {
        "gpt-oss-120b": "openai/gpt-oss-120b",
        "gptoss120b": "openai/gpt-oss-120b",
        "gptoss120": "openai/gpt-oss-120b",
        "openai/gptoss120": "openai/gpt-oss-120b",
        "openai/gptoss120b": "openai/gpt-oss-120b",
        "gpt-oss-20b": "openai/gpt-oss-20b",
        "gptoss20b": "openai/gpt-oss-20b",
        "gptoss20": "openai/gpt-oss-20b",
        "openai/gptoss20": "openai/gpt-oss-20b",
        "openai/gptoss20b": "openai/gpt-oss-20b",
        "llama-3.1-8b": "llama-3.1-8b-instant",
        "llama3.1-8b": "llama-3.1-8b-instant",
        "llama-3.3-70b": "llama-3.3-70b-versatile",
        "llama3.3-70b": "llama-3.3-70b-versatile",
    }
    return alias_map.get(model_name.lower(), model_name)


def get_client() -> OpenAI:
    """Get or create the OpenAI-compatible client for Groq."""
    global _client
    api_key = config.GROQ_API_KEY
    if not api_key:
        raise LLMError(
            "GROQ_API_KEY is not set. Add it to your .env file "
            "(see .env.example) before running the app."
        )
    if _client is None or getattr(_client, "_last_api_key", None) != api_key:
        _client = OpenAI(
            api_key=api_key,
            base_url=config.GROQ_BASE_URL,
        )
        _client._last_api_key = api_key
    return _client


def chat_completion(
    system_prompt: str,
    user_prompt: str,
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    json_mode: bool = False,
) -> str:
    """
    Send a single-turn chat request and return the response text.
    Set json_mode=True for structured JSON output (used by entity extraction).

    Includes retry logic for transient API errors.
    """
    client = get_client()
    model = normalize_model_name(model or config.GROQ_MODEL)
    temperature = config.LLM_TEMPERATURE if temperature is None else temperature
    max_tokens = config.LLM_MAX_TOKENS if max_tokens is None else max_tokens

    kwargs = dict(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )

    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    max_retries = 2
    for attempt in range(max_retries + 1):
        try:
            start_time = time.time()
            response = client.chat.completions.create(**kwargs)
            elapsed = time.time() - start_time
            logger.info(f"LLM response in {elapsed:.2f}s (model={model})")

            content = response.choices[0].message.content
            if content is None:
                raise LLMError("LLM returned empty response")
            return content

        except RateLimitError as e:
            if attempt < max_retries:
                wait = 2 ** attempt
                logger.warning(f"Rate limited, retrying in {wait}s...")
                time.sleep(wait)
            else:
                raise LLMError(f"Rate limit exceeded after {max_retries} retries: {e}")

        except APIConnectionError as e:
            raise LLMError(
                f"Cannot connect to LLM API at {config.GROQ_BASE_URL}. "
                f"Check your internet connection and API configuration. Error: {e}"
            )

        except APIError as e:
            raise LLMError(f"LLM API error (model={model}): {e}")

        except Exception as e:
            raise LLMError(f"Unexpected LLM error (model={model}): {e}")


def check_api_status(model: Optional[str] = None) -> dict:
    """Check if the LLM API is accessible and the key is valid."""
    if not config.GROQ_API_KEY:
        return {"status": "error", "message": "API key not configured in .env"}

    target_model = normalize_model_name(model or config.GROQ_MODEL)
    try:
        client = get_client()
        # Minimal prompt to verify connectivity and model validity
        response = client.chat.completions.create(
            model=target_model,
            messages=[{"role": "user", "content": "Hi"}],
            max_tokens=5,
        )
        return {"status": "ok", "message": "API connected successfully", "model": target_model}
    except Exception as e:
        return {"status": "error", "message": str(e), "model": target_model}


test_connection = check_api_status


def list_available_chat_models() -> list:
    """Query available models from Groq API or return recommended defaults."""
    default_models = [
        "openai/gpt-oss-120b",
        "openai/gpt-oss-20b",
        "qwen/qwen3.8-27b",
        "allam-2-7b",
    ]
    if not config.GROQ_API_KEY:
        return default_models

    try:
        client = get_client()
        models_data = client.models.list()
        chat_models = [
            m.id for m in models_data.data
            if not m.id.startswith("whisper") and not "prompt-guard" in m.id
        ]
        return chat_models if chat_models else default_models
    except Exception:
        return default_models


def get_llm_info() -> dict:
    """Return info about the current LLM configuration."""
    active_model = normalize_model_name(config.GROQ_MODEL)
    return {
        "provider": "Groq",
        "model": active_model,
        "base_url": config.GROQ_BASE_URL,
        "temperature": config.LLM_TEMPERATURE,
        "max_tokens": config.LLM_MAX_TOKENS,
        "requires_api_key": True,
        "api_key_set": bool(config.GROQ_API_KEY),
    }
