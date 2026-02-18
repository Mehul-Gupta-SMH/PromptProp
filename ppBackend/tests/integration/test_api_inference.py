"""Tests for POST /api/inference."""

import pytest
from unittest.mock import AsyncMock, patch

from llm.llm_client import LLMError


class TestApiInference:
    def test_success(self, client, mock_generate):
        resp = client.post("/api/inference", json={
            "model": "gemini-3-flash-preview",
            "taskDescription": "Categorize feedback",
            "promptTemplate": "Classify the input",
            "query": "The product broke",
        })
        assert resp.status_code == 200
        assert resp.json()["output"] == "mock output"

    def test_model_resolution(self, client, mock_generate):
        client.post("/api/inference", json={
            "model": "gpt-4o",
            "taskDescription": "Task",
            "promptTemplate": "Prompt",
            "query": "Input",
        })
        call_kwargs = mock_generate.call_args.kwargs
        assert call_kwargs["model"] == "openai/gpt-4o"

    def test_settings_forwarded(self, client, mock_generate):
        client.post("/api/inference", json={
            "model": "gemini-3-flash-preview",
            "taskDescription": "Task",
            "promptTemplate": "Prompt",
            "query": "Input",
            "settings": {"temperature": 0.3, "topP": 0.8},
        })
        call_kwargs = mock_generate.call_args.kwargs
        assert call_kwargs["temperature"] == 0.3

    def test_llm_error_returns_502(self, client):
        with patch("route.generate", new_callable=AsyncMock,
                   side_effect=LLMError("API down")):
            resp = client.post("/api/inference", json={
                "model": "gemini-3-flash-preview",
                "taskDescription": "Task",
                "promptTemplate": "Prompt",
                "query": "Input",
            })
            assert resp.status_code == 502

    def test_missing_fields_422(self, client):
        resp = client.post("/api/inference", json={"model": "gpt-4o"})
        assert resp.status_code == 422
