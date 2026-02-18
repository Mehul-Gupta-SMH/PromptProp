"""Tests for POST /api/refine."""

import json
from unittest.mock import AsyncMock, patch
from tests.conftest import _make_generate_response


class TestApiRefine:
    def test_success(self, client):
        mock_content = json.dumps({
            "explanation": "Added specificity",
            "refinedPrompt": "Better prompt",
            "deltaReasoning": "Targets weak areas",
        })
        mock_resp = _make_generate_response(content=mock_content)
        with patch("route.generate", new_callable=AsyncMock, return_value=mock_resp):
            resp = client.post("/api/refine", json={
                "taskDescription": "Categorize",
                "currentPrompt": "Original prompt",
                "failures": "Row 1 scored 40",
            })
            assert resp.status_code == 200
            body = resp.json()
            assert body["refinedPrompt"] == "Better prompt"
            assert body["explanation"] == "Added specificity"

    def test_json_fallback_preserves_original(self, client):
        mock_resp = _make_generate_response(content="not json at all")
        with patch("route.generate", new_callable=AsyncMock, return_value=mock_resp):
            resp = client.post("/api/refine", json={
                "taskDescription": "Task",
                "currentPrompt": "Keep this prompt",
                "failures": "some failures",
            })
            assert resp.status_code == 200
            body = resp.json()
            assert body["refinedPrompt"] == "Keep this prompt"
            assert body["explanation"] == "Failed to refine."

    def test_hardcoded_model_and_temp(self, client):
        mock_content = json.dumps({
            "explanation": "x", "refinedPrompt": "y", "deltaReasoning": "z"
        })
        mock_resp = _make_generate_response(content=mock_content)
        with patch("route.generate", new_callable=AsyncMock, return_value=mock_resp) as mock_gen:
            client.post("/api/refine", json={
                "taskDescription": "Task",
                "currentPrompt": "Prompt",
                "failures": "failures",
            })
            call_kwargs = mock_gen.call_args.kwargs
            assert call_kwargs["model"] == "gemini/gemini-3-pro-preview"
            assert call_kwargs["settings"].temperature == 0.2
