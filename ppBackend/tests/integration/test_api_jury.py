"""Tests for POST /api/jury."""

import json
import pytest
from unittest.mock import AsyncMock, patch
from tests.conftest import _make_generate_response


class TestApiJury:
    def test_success_with_json_parse(self, client):
        mock_content = json.dumps({"score": 85, "reasoning": "Good answer"})
        mock_resp = _make_generate_response(content=mock_content)
        with patch("route.generate", new_callable=AsyncMock, return_value=mock_resp):
            resp = client.post("/api/jury", json={
                "juryModel": "gemini-3-flash-preview",
                "taskDescription": "Categorize feedback",
                "row": {"query": "input", "expectedOutput": "Product"},
                "actualOutput": "Product",
            })
            assert resp.status_code == 200
            body = resp.json()
            assert body["score"] == 85
            assert body["reasoning"] == "Good answer"

    def test_fallback_on_invalid_json(self, client):
        mock_resp = _make_generate_response(content="not valid json {{{")
        with patch("route.generate", new_callable=AsyncMock, return_value=mock_resp):
            resp = client.post("/api/jury", json={
                "juryModel": "gemini-3-flash-preview",
                "taskDescription": "Task",
                "row": {"query": "q", "expectedOutput": "e"},
                "actualOutput": "a",
            })
            assert resp.status_code == 200
            body = resp.json()
            assert body["score"] == 0
            assert body["reasoning"] == "Error parsing jury response."

    def test_response_format_used(self, client):
        mock_content = json.dumps({"score": 90, "reasoning": "fine"})
        mock_resp = _make_generate_response(content=mock_content)
        with patch("route.generate", new_callable=AsyncMock, return_value=mock_resp) as mock_gen:
            client.post("/api/jury", json={
                "juryModel": "gemini-3-flash-preview",
                "taskDescription": "Task",
                "row": {"query": "q", "expectedOutput": "e"},
                "actualOutput": "a",
            })
            call_kwargs = mock_gen.call_args.kwargs
            assert call_kwargs["response_format"] == {"type": "json_object"}

    def test_system_prompt_loaded(self, client):
        mock_content = json.dumps({"score": 90, "reasoning": "fine"})
        mock_resp = _make_generate_response(content=mock_content)
        with patch("route.generate", new_callable=AsyncMock, return_value=mock_resp) as mock_gen:
            client.post("/api/jury", json={
                "juryModel": "gemini-3-flash-preview",
                "taskDescription": "Task",
                "row": {"query": "q", "expectedOutput": "e"},
                "actualOutput": "a",
            })
            messages = mock_gen.call_args.kwargs["messages"]
            assert messages[0]["role"] == "system"
            assert len(messages[0]["content"]) > 0
