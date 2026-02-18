"""Tests for llm/llm_client.py."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

import litellm

from llm.llm_client import generate, configure_api_keys, LLMError
from llm.models import ModelSettings


class TestConfigureApiKeys:
    def test_idempotent(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        import llm.llm_client as mod
        mod._keys_configured = False
        configure_api_keys()
        assert mod._keys_configured is True
        # Second call should be a no-op
        configure_api_keys()
        assert mod._keys_configured is True


class TestGenerate:
    @pytest.mark.asyncio
    async def test_success_path(self, mock_generate):
        result = await generate(
            model="gemini/gemini-3-flash-preview",
            messages=[{"role": "user", "content": "hello"}],
        )
        assert result.content == "mock output"
        assert result.model == "mock-model"
        assert result.usage.total_tokens == 30
        mock_generate.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_settings_propagation(self, mock_generate):
        settings = ModelSettings(temperature=0.2, top_p=0.9, top_k=40, max_tokens=512)
        await generate(
            model="openai/gpt-4o",
            messages=[{"role": "user", "content": "test"}],
            settings=settings,
        )
        call_kwargs = mock_generate.call_args.kwargs
        assert call_kwargs["temperature"] == 0.2
        assert call_kwargs["top_p"] == 0.9
        assert call_kwargs["top_k"] == 40
        assert call_kwargs["max_tokens"] == 512

    @pytest.mark.asyncio
    async def test_response_format_passthrough(self, mock_generate):
        await generate(
            model="openai/gpt-4o",
            messages=[{"role": "user", "content": "test"}],
            response_format={"type": "json_object"},
        )
        call_kwargs = mock_generate.call_args.kwargs
        assert call_kwargs["response_format"] == {"type": "json_object"}

    @pytest.mark.asyncio
    async def test_default_settings_applied(self, mock_generate):
        await generate(
            model="openai/gpt-4o",
            messages=[{"role": "user", "content": "test"}],
        )
        call_kwargs = mock_generate.call_args.kwargs
        assert call_kwargs["temperature"] == 0.7  # default
        assert "top_p" not in call_kwargs  # None omitted

    @pytest.mark.asyncio
    async def test_auth_error(self):
        with patch("litellm.acompletion", new_callable=AsyncMock,
                   side_effect=litellm.exceptions.AuthenticationError(
                       message="bad key", model="m", llm_provider="openai")):
            with pytest.raises(LLMError, match="Authentication failed"):
                await generate("openai/gpt-4o", [{"role": "user", "content": "hi"}])

    @pytest.mark.asyncio
    async def test_rate_limit_error(self):
        with patch("litellm.acompletion", new_callable=AsyncMock,
                   side_effect=litellm.exceptions.RateLimitError(
                       message="too many", model="m", llm_provider="openai")):
            with pytest.raises(LLMError, match="Rate limit"):
                await generate("openai/gpt-4o", [{"role": "user", "content": "hi"}])

    @pytest.mark.asyncio
    async def test_bad_request_error(self):
        with patch("litellm.acompletion", new_callable=AsyncMock,
                   side_effect=litellm.exceptions.BadRequestError(
                       message="invalid", model="m", llm_provider="openai")):
            with pytest.raises(LLMError, match="Invalid request"):
                await generate("openai/gpt-4o", [{"role": "user", "content": "hi"}])

    @pytest.mark.asyncio
    async def test_generic_error(self):
        with patch("litellm.acompletion", new_callable=AsyncMock,
                   side_effect=RuntimeError("something broke")):
            with pytest.raises(LLMError, match="LLM call failed"):
                await generate("openai/gpt-4o", [{"role": "user", "content": "hi"}])
