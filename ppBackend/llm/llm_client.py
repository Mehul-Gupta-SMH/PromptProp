import os
import logging
from typing import Optional

import litellm

from llm.models import GenerateResponse, ModelSettings, TokenUsage
from ppsecrets.getSecrets import Secrets

logger = logging.getLogger(__name__)

_keys_configured = False


class LLMError(Exception):
    """Raised when an LLM call fails."""
    pass


def configure_api_keys() -> None:
    """
    Read API keys from the Secrets class and set them as environment
    variables so LiteLLM can discover them automatically.
    Idempotent — only runs once.
    """
    global _keys_configured
    if _keys_configured:
        return

    secrets_instance = Secrets()
    key_env_vars = {
        "gemini_api_key":    "GEMINI_API_KEY",
        "openai_api_key":    "OPENAI_API_KEY",
        "anthropic_api_key": "ANTHROPIC_API_KEY",
    }

    for secret_key, env_var in key_env_vars.items():
        value = secrets_instance.get_secret("llm_api", secret_key)
        if value:
            os.environ[env_var] = value
            logger.info(f"Configured API key: {env_var}")
        else:
            logger.warning(f"API key not found for: {env_var}")

    _keys_configured = True


async def generate(
    model: str,
    messages: list[dict],
    settings: Optional[ModelSettings] = None,
    response_format: Optional[dict] = None,
) -> GenerateResponse:
    """
    Send a completion request to any supported LLM via LiteLLM.

    Args:
        model: LiteLLM model identifier, e.g. "gemini/gemini-3-flash-preview",
               "openai/gpt-4o", "anthropic/claude-sonnet-4-20250514".
        messages: OpenAI-format messages list.
        settings: Generation parameters (temperature, top_p, top_k, max_tokens).
        response_format: Optional dict for structured JSON output.

    Returns:
        GenerateResponse with the model's text output and token usage.

    Raises:
        LLMError: On any failure during the LLM call.
    """
    configure_api_keys()

    if settings is None:
        settings = ModelSettings()

    kwargs: dict = {
        "model": model,
        "messages": messages,
        "temperature": settings.temperature,
    }

    if settings.top_p is not None:
        kwargs["top_p"] = settings.top_p
    if settings.max_tokens is not None:
        kwargs["max_tokens"] = settings.max_tokens
    if settings.top_k is not None:
        kwargs["top_k"] = settings.top_k
    if response_format is not None:
        kwargs["response_format"] = response_format

    logger.info(f"LLM generate: model={model}, temp={settings.temperature}")

    try:
        response = await litellm.acompletion(**kwargs)

        content = response.choices[0].message.content or ""
        usage_data = response.usage
        usage = TokenUsage(
            prompt_tokens=getattr(usage_data, "prompt_tokens", 0) or 0,
            completion_tokens=getattr(usage_data, "completion_tokens", 0) or 0,
            total_tokens=getattr(usage_data, "total_tokens", 0) or 0,
        )

        result = GenerateResponse(
            content=content,
            model=response.model or model,
            usage=usage,
        )

        logger.info(f"LLM response: model={result.model}, tokens={usage.total_tokens}")
        return result

    except litellm.exceptions.AuthenticationError as e:
        logger.error(f"Authentication failed for model {model}: {e}")
        raise LLMError(f"Authentication failed for {model}. Check API key.") from e
    except litellm.exceptions.RateLimitError as e:
        logger.error(f"Rate limit hit for model {model}: {e}")
        raise LLMError(f"Rate limit exceeded for {model}.") from e
    except litellm.exceptions.BadRequestError as e:
        logger.error(f"Bad request for model {model}: {e}")
        raise LLMError(f"Invalid request to {model}: {e}") from e
    except Exception as e:
        logger.error(f"LLM call failed for model {model}: {e}", exc_info=True)
        raise LLMError(f"LLM call failed: {e}") from e