"""Tests for POST /api/optimize SSE streaming endpoint."""

import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from llm.models import GenerateResponse, TokenUsage
from llm.llm_client import LLMError


def _parse_sse_events(raw_text: str) -> list[dict]:
    """Parse SSE text into list of {event, data} dicts."""
    events = []
    current_event = None
    current_data = None
    for line in raw_text.split("\n"):
        if line.startswith("event: "):
            current_event = line[7:]
        elif line.startswith("data: "):
            current_data = line[6:]
        elif line == "" and current_event and current_data:
            events.append({"event": current_event, "data": json.loads(current_data)})
            current_event = None
            current_data = None
    return events


def _mock_generate_response(content="mock output"):
    return GenerateResponse(
        content=content,
        model="mock-model",
        usage=TokenUsage(prompt_tokens=10, completion_tokens=20, total_tokens=30),
    )


class TestApiOptimize:
    def test_inline_mode_event_sequence(self, client, mock_mlflow):
        # Mock generate to return perfect scores (converge immediately)
        jury_json = json.dumps({"score": 100, "reasoning": "perfect"})

        async def mock_gen(**kwargs):
            messages = kwargs.get("messages", [])
            user_content = messages[-1]["content"] if messages else ""
            if "EVALUATE" in user_content or "AI OUTPUT TO EVALUATE" in user_content:
                return _mock_generate_response(content=jury_json)
            return _mock_generate_response(content="inference output")

        with patch("optimize.generate", side_effect=mock_gen):
            with patch("optimize.mlflow_register", return_value="run-1"):
                resp = client.post("/api/optimize", json={
                    "taskDescription": "Categorize",
                    "basePrompt": "Classify input",
                    "dataset": [{"query": "q1", "expectedOutput": "e1"}],
                    "juryMembers": [{"name": "j1", "model": "gemini-3-flash-preview"}],
                    "runnerModel": {"provider": "gemini", "model": "gemini-3-flash-preview"},
                    "maxIterations": 2,
                    "perfectScore": 98.0,
                })

        assert resp.status_code == 200
        events = _parse_sse_events(resp.text)
        event_types = [e["event"] for e in events]

        assert "start" in event_types
        assert "iteration_start" in event_types
        assert "inference_result" in event_types
        assert "jury_result" in event_types
        assert "iteration_complete" in event_types
        assert "complete" in event_types

    def test_convergence_on_perfect_score(self, client, mock_mlflow):
        jury_json = json.dumps({"score": 100, "reasoning": "perfect"})

        async def mock_gen(**kwargs):
            messages = kwargs.get("messages", [])
            user_content = messages[-1]["content"] if messages else ""
            if "AI OUTPUT TO EVALUATE" in user_content:
                return _mock_generate_response(content=jury_json)
            return _mock_generate_response(content="output")

        with patch("optimize.generate", side_effect=mock_gen):
            with patch("optimize.mlflow_register", return_value=None):
                resp = client.post("/api/optimize", json={
                    "taskDescription": "Task",
                    "basePrompt": "Prompt",
                    "dataset": [{"query": "q", "expectedOutput": "e"}],
                    "juryMembers": [{"name": "j", "model": "gemini-3-flash-preview"}],
                    "runnerModel": {"provider": "gemini", "model": "gemini-3-flash-preview"},
                    "maxIterations": 5,
                    "perfectScore": 98.0,
                })

        events = _parse_sse_events(resp.text)
        complete_events = [e for e in events if e["event"] == "complete"]
        assert len(complete_events) == 1
        assert complete_events[0]["data"]["totalIterations"] == 1

    def test_error_event_on_llm_failure(self, client, mock_mlflow):
        with patch("optimize.generate", new_callable=AsyncMock,
                   side_effect=LLMError("API failure")):
            resp = client.post("/api/optimize", json={
                "taskDescription": "Task",
                "basePrompt": "Prompt",
                "dataset": [{"query": "q", "expectedOutput": "e"}],
                "juryMembers": [{"name": "j", "model": "gemini-3-flash-preview"}],
                "runnerModel": {"provider": "gemini", "model": "gemini-3-flash-preview"},
                "maxIterations": 1,
            })

        events = _parse_sse_events(resp.text)
        error_events = [e for e in events if e["event"] == "error"]
        assert len(error_events) >= 1
        assert "API failure" in error_events[0]["data"]["message"]
