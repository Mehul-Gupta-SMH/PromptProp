"""Tests for _resolve_model() in both route.py and optimize.py."""

import pytest
from route import _resolve_model as route_resolve
from optimize import _resolve_model as opt_resolve


@pytest.mark.parametrize("func", [route_resolve, opt_resolve], ids=["route", "optimize"])
class TestResolveModel:
    def test_gemini_prefix(self, func):
        assert func("gemini-3-flash-preview") == "gemini/gemini-3-flash-preview"

    def test_gemini_pro(self, func):
        assert func("gemini-3-pro-preview") == "gemini/gemini-3-pro-preview"

    def test_openai_gpt4(self, func):
        assert func("gpt-4o") == "openai/gpt-4o"

    def test_openai_gpt35(self, func):
        assert func("gpt-3.5-turbo") == "openai/gpt-3.5-turbo"

    def test_openai_o1(self, func):
        assert func("o1-preview") == "openai/o1-preview"

    def test_openai_o3(self, func):
        assert func("o3-mini") == "openai/o3-mini"

    def test_anthropic_claude(self, func):
        assert func("claude-sonnet-4-20250514") == "anthropic/claude-sonnet-4-20250514"

    def test_passthrough_already_prefixed(self, func):
        assert func("openai/gpt-4o") == "openai/gpt-4o"

    def test_unknown_model_passthrough(self, func):
        assert func("mistral-7b") == "mistral-7b"

    def test_empty_string(self, func):
        assert func("") == ""
