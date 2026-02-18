"""Tests for _sse() helper in optimize.py."""

import json
from optimize import _sse


class TestSSE:
    def test_event_format(self):
        result = _sse("test_event", {"key": "value"})
        lines = result.split("\n")
        assert lines[0] == "event: test_event"
        assert lines[1].startswith("data: ")

    def test_json_serialization(self):
        data = {"score": 95.5, "name": "test"}
        result = _sse("event", data)
        json_part = result.split("data: ")[1].split("\n")[0]
        parsed = json.loads(json_part)
        assert parsed == data

    def test_double_newline_terminator(self):
        result = _sse("e", {})
        assert result.endswith("\n\n")

    def test_nested_data(self):
        data = {"outer": {"inner": [1, 2, 3]}}
        result = _sse("e", data)
        json_part = result.split("data: ")[1].split("\n")[0]
        assert json.loads(json_part) == data
