"""Regression: JSON parse failure fallback behavior.

Locks in the contract that:
- Jury returns score=0 on bad JSON
- Refine returns original prompt on bad JSON
Both via route.py endpoints AND optimize.py helpers.
"""

import json
import pytest
from unittest.mock import AsyncMock, patch

from tests.conftest import _make_generate_response
from llm.models import GenerateResponse, TokenUsage


class TestJuryJsonFallback:
    """Jury must return score=0 and a known message when JSON parsing fails."""

    def test_via_route_endpoint(self, client):
        mock_resp = _make_generate_response(content="totally not json")
        with patch("route.generate", new_callable=AsyncMock, return_value=mock_resp):
            resp = client.post("/api/jury", json={
                "juryModel": "gemini-3-flash-preview",
                "taskDescription": "Task",
                "row": {"query": "q", "expectedOutput": "e"},
                "actualOutput": "a",
            })
            body = resp.json()
            assert body["score"] == 0
            assert body["reasoning"] == "Error parsing jury response."

    @pytest.mark.asyncio
    async def test_via_optimize_helper(self):
        from optimize import _run_single_jury
        mock_resp = GenerateResponse(
            content="not json",
            model="m",
            usage=TokenUsage(prompt_tokens=5, completion_tokens=5, total_tokens=10),
        )
        with patch("optimize.generate", new_callable=AsyncMock, return_value=mock_resp):
            result = await _run_single_jury(
                jury={"id": "j1", "name": "judge", "model": "gemini-3-flash-preview", "settings": {}},
                task_desc="Task",
                row={"query": "q", "expectedOutput": "e"},
                actual_output="a",
            )
            assert result["score"] == 0
            assert result["reasoning"] == "Error parsing jury response."


class TestRefineJsonFallback:
    """Refine must return the original prompt when JSON parsing fails."""

    def test_via_route_endpoint(self, client):
        mock_resp = _make_generate_response(content="not json")
        with patch("route.generate", new_callable=AsyncMock, return_value=mock_resp):
            resp = client.post("/api/refine", json={
                "taskDescription": "Task",
                "currentPrompt": "My original prompt",
                "failures": "Row 1 failed",
            })
            body = resp.json()
            assert body["refinedPrompt"] == "My original prompt"
            assert body["explanation"] == "Failed to refine."
            assert body["deltaReasoning"] == "None"

    @pytest.mark.asyncio
    async def test_via_optimize_helper(self):
        from optimize import _run_refinement
        mock_resp = GenerateResponse(
            content="garbage",
            model="m",
            usage=TokenUsage(prompt_tokens=5, completion_tokens=5, total_tokens=10),
        )
        with patch("optimize.generate", new_callable=AsyncMock, return_value=mock_resp):
            result = await _run_refinement(
                task_desc="Task",
                prompt="Keep this prompt",
                failures="Some failures",
            )
            assert result["refinedPrompt"] == "Keep this prompt"
            assert result["explanation"] == "Failed to refine."
