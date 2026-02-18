"""Tests for llm/models.py Pydantic models."""

import pytest
from pydantic import ValidationError
from llm.models import ModelSettings, TokenUsage, GenerateResponse, LLMProvider


class TestLLMProvider:
    def test_values(self):
        assert LLMProvider.GEMINI == "gemini"
        assert LLMProvider.OPENAI == "openai"
        assert LLMProvider.ANTHROPIC == "anthropic"

    def test_str_behavior(self):
        assert str(LLMProvider.GEMINI) == "LLMProvider.GEMINI"


class TestModelSettings:
    def test_defaults(self):
        s = ModelSettings()
        assert s.temperature == 0.7
        assert s.top_p is None
        assert s.top_k is None
        assert s.max_tokens is None

    def test_custom_values(self):
        s = ModelSettings(temperature=0.5, top_p=0.9, top_k=40, max_tokens=1024)
        assert s.temperature == 0.5
        assert s.top_p == 0.9
        assert s.top_k == 40
        assert s.max_tokens == 1024

    def test_temperature_boundary_low(self):
        s = ModelSettings(temperature=0.0)
        assert s.temperature == 0.0

    def test_temperature_boundary_high(self):
        s = ModelSettings(temperature=2.0)
        assert s.temperature == 2.0

    def test_temperature_out_of_range(self):
        with pytest.raises(ValidationError):
            ModelSettings(temperature=-0.1)
        with pytest.raises(ValidationError):
            ModelSettings(temperature=2.1)

    def test_top_p_boundary(self):
        ModelSettings(top_p=0.0)
        ModelSettings(top_p=1.0)
        with pytest.raises(ValidationError):
            ModelSettings(top_p=-0.1)

    def test_top_k_minimum(self):
        ModelSettings(top_k=1)
        with pytest.raises(ValidationError):
            ModelSettings(top_k=0)

    def test_max_tokens_minimum(self):
        ModelSettings(max_tokens=1)
        with pytest.raises(ValidationError):
            ModelSettings(max_tokens=0)


class TestTokenUsage:
    def test_defaults(self):
        u = TokenUsage()
        assert u.prompt_tokens == 0
        assert u.completion_tokens == 0
        assert u.total_tokens == 0

    def test_custom_values(self):
        u = TokenUsage(prompt_tokens=100, completion_tokens=200, total_tokens=300)
        assert u.total_tokens == 300


class TestGenerateResponse:
    def test_required_fields(self):
        r = GenerateResponse(content="hello", model="gpt-4o")
        assert r.content == "hello"
        assert r.model == "gpt-4o"
        assert r.usage.total_tokens == 0

    def test_with_usage(self):
        usage = TokenUsage(prompt_tokens=10, completion_tokens=20, total_tokens=30)
        r = GenerateResponse(content="hi", model="m", usage=usage)
        assert r.usage.total_tokens == 30

    def test_missing_required_fields(self):
        with pytest.raises(ValidationError):
            GenerateResponse(content="hi")
