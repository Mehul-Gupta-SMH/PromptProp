"""
Dynamic model discovery for PromptProp.

Queries each LLM provider's API to fetch available chat/generation models,
filtered to useful ones. Results are cached for 10 minutes.
"""

import logging
import os
import time
from typing import Optional

import httpx

from llm.llm_client import configure_api_keys

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------

_cache: Optional[dict] = None
_cache_ts: float = 0
CACHE_TTL = 600  # 10 minutes


# ---------------------------------------------------------------------------
# Provider fetchers
# ---------------------------------------------------------------------------

async def _fetch_gemini_models(api_key: str) -> list[dict]:
    """Fetch models from Google Gemini / Generative Language API."""
    url = "https://generativelanguage.googleapis.com/v1beta/models"
    models = []
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, params={"key": api_key})
            resp.raise_for_status()
            data = resp.json()

        for m in data.get("models", []):
            name = m.get("name", "")  # e.g. "models/gemini-2.0-flash"
            model_id = name.replace("models/", "")
            display = m.get("displayName", model_id)
            methods = m.get("supportedGenerationMethods", [])

            # Only include models that support content generation
            if "generateContent" not in methods:
                continue

            models.append({"id": model_id, "name": display})

    except Exception as e:
        logger.warning(f"Failed to fetch Gemini models: {e}")

    return models


async def _fetch_openai_models(api_key: str) -> list[dict]:
    """Fetch models from OpenAI /v1/models."""
    url = "https://api.openai.com/v1/models"
    models = []

    # Prefixes for chat-capable models we care about
    CHAT_PREFIXES = ("gpt-4", "gpt-3.5", "o1", "o3", "o4")
    EXCLUDE = ("instruct", "realtime", "audio", "search", "tts", "whisper", "dall-e", "embedding")

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, headers={"Authorization": f"Bearer {api_key}"})
            resp.raise_for_status()
            data = resp.json()

        for m in data.get("data", []):
            mid = m.get("id", "")
            if not any(mid.startswith(p) for p in CHAT_PREFIXES):
                continue
            if any(ex in mid for ex in EXCLUDE):
                continue
            models.append({"id": mid, "name": mid})

    except Exception as e:
        logger.warning(f"Failed to fetch OpenAI models: {e}")

    return models


async def _fetch_anthropic_models(api_key: str) -> list[dict]:
    """Fetch models from Anthropic /v1/models."""
    url = "https://api.anthropic.com/v1/models"
    models = []
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                url,
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                },
                params={"limit": 100},
            )
            resp.raise_for_status()
            data = resp.json()

        for m in data.get("data", []):
            mid = m.get("id", "")
            display = m.get("display_name", mid)
            models.append({"id": mid, "name": display})

    except Exception as e:
        logger.warning(f"Failed to fetch Anthropic models: {e}")

    return models


# ---------------------------------------------------------------------------
# Sort helper — prefer newer / flagship models first
# ---------------------------------------------------------------------------

def _sort_models(models: list[dict]) -> list[dict]:
    """Sort models so newer/major versions appear first."""
    return sorted(models, key=lambda m: m["id"], reverse=True)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def get_available_models(force_refresh: bool = False) -> dict:
    """Return available models grouped by provider.

    Response format::

        {
            "providers": [
                {
                    "provider": "gemini",
                    "label": "Google Gemini",
                    "models": [{"id": "gemini-2.0-flash", "name": "Gemini 2.0 Flash"}, ...]
                },
                ...
            ]
        }
    """
    global _cache, _cache_ts

    if not force_refresh and _cache and (time.time() - _cache_ts) < CACHE_TTL:
        return _cache

    # Ensure API keys are in env
    configure_api_keys()

    providers = []

    gemini_key = os.getenv("GEMINI_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")

    if gemini_key:
        models = await _fetch_gemini_models(gemini_key)
        if models:
            providers.append({
                "provider": "gemini",
                "label": "Google Gemini",
                "models": _sort_models(models),
            })

    if openai_key:
        models = await _fetch_openai_models(openai_key)
        if models:
            providers.append({
                "provider": "openai",
                "label": "OpenAI",
                "models": _sort_models(models),
            })

    if anthropic_key:
        models = await _fetch_anthropic_models(anthropic_key)
        if models:
            providers.append({
                "provider": "anthropic",
                "label": "Anthropic",
                "models": _sort_models(models),
            })

    result = {"providers": providers}
    _cache = result
    _cache_ts = time.time()

    return result
