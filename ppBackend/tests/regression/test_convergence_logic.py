"""Regression: convergence trigger logic in optimize.py.

Tests the two independent convergence triggers:
1. Perfect score (avg >= perfectScore)
2. Small delta (abs(current - prev) < convergenceThreshold)
"""

import json
import pytest
from unittest.mock import AsyncMock, patch

from llm.models import GenerateResponse, TokenUsage


def _parse_sse_events(raw_text: str) -> list[dict]:
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


def _mock_gen_factory(jury_score):
    """Create a mock generate function that returns a fixed jury score."""
    jury_json = json.dumps({"score": jury_score, "reasoning": "test"})

    async def mock_gen(**kwargs):
        messages = kwargs.get("messages", [])
        user_content = messages[-1]["content"] if messages else ""
        if "AI OUTPUT TO EVALUATE" in user_content:
            return GenerateResponse(
                content=jury_json, model="m",
                usage=TokenUsage(prompt_tokens=5, completion_tokens=5, total_tokens=10))
        # Refinement response
        if "CRITIQUE" in user_content:
            refine_json = json.dumps({
                "explanation": "x", "refinedPrompt": "new prompt", "deltaReasoning": "d"
            })
            return GenerateResponse(
                content=refine_json, model="m",
                usage=TokenUsage(prompt_tokens=5, completion_tokens=5, total_tokens=10))
        return GenerateResponse(
            content="output", model="m",
            usage=TokenUsage(prompt_tokens=5, completion_tokens=5, total_tokens=10))

    return mock_gen


class TestConvergenceOnPerfectScore:
    def test_stops_at_iteration_1(self, client, mock_mlflow):
        with patch("optimize.generate", side_effect=_mock_gen_factory(100)):
            with patch("optimize.mlflow_register", return_value=None):
                resp = client.post("/api/optimize", json={
                    "taskDescription": "T",
                    "basePrompt": "P",
                    "dataset": [{"query": "q", "expectedOutput": "e"}],
                    "juryMembers": [{"name": "j", "model": "gemini-3-flash-preview"}],
                    "runnerModel": {"provider": "gemini", "model": "gemini-3-flash-preview"},
                    "maxIterations": 5,
                    "perfectScore": 98.0,
                })

        events = _parse_sse_events(resp.text)
        complete = [e for e in events if e["event"] == "complete"]
        assert len(complete) == 1
        assert complete[0]["data"]["totalIterations"] == 1


class TestConvergenceOnSmallDelta:
    def test_converges_when_score_stable(self, client, mock_mlflow):
        """Score of 50 each iteration: delta = 0 < 0.2 on iteration 2."""
        with patch("optimize.generate", side_effect=_mock_gen_factory(50)):
            with patch("optimize.mlflow_register", return_value=None):
                resp = client.post("/api/optimize", json={
                    "taskDescription": "T",
                    "basePrompt": "P",
                    "dataset": [{"query": "q", "expectedOutput": "e"}],
                    "juryMembers": [{"name": "j", "model": "gemini-3-flash-preview"}],
                    "runnerModel": {"provider": "gemini", "model": "gemini-3-flash-preview"},
                    "maxIterations": 5,
                    "convergenceThreshold": 0.2,
                    "passThreshold": 90.0,
                })

        events = _parse_sse_events(resp.text)
        complete = [e for e in events if e["event"] == "complete"]
        assert len(complete) == 1
        # Should converge on iteration 2 (delta between iter 1 and iter 2 is 0)
        assert complete[0]["data"]["totalIterations"] == 2


class TestMaxIterationsBoundary:
    def test_max_iterations_1(self, client, mock_mlflow):
        """With maxIterations=1, should always stop after 1 iteration."""
        with patch("optimize.generate", side_effect=_mock_gen_factory(50)):
            with patch("optimize.mlflow_register", return_value=None):
                resp = client.post("/api/optimize", json={
                    "taskDescription": "T",
                    "basePrompt": "P",
                    "dataset": [{"query": "q", "expectedOutput": "e"}],
                    "juryMembers": [{"name": "j", "model": "gemini-3-flash-preview"}],
                    "runnerModel": {"provider": "gemini", "model": "gemini-3-flash-preview"},
                    "maxIterations": 1,
                })

        events = _parse_sse_events(resp.text)
        complete = [e for e in events if e["event"] == "complete"]
        assert len(complete) == 1
        assert complete[0]["data"]["totalIterations"] == 1
