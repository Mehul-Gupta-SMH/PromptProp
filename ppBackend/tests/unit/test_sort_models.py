"""Tests for _sort_models() in models_list.py."""

from models_list import _sort_models


class TestSortModels:
    def test_empty(self):
        assert _sort_models([]) == []

    def test_single(self):
        models = [{"id": "a", "name": "A"}]
        assert _sort_models(models) == models

    def test_reverse_alpha_ordering(self):
        models = [
            {"id": "a-model", "name": "A"},
            {"id": "z-model", "name": "Z"},
            {"id": "m-model", "name": "M"},
        ]
        sorted_models = _sort_models(models)
        ids = [m["id"] for m in sorted_models]
        assert ids == ["z-model", "m-model", "a-model"]

    def test_version_ordering(self):
        models = [
            {"id": "gemini-1.0-pro", "name": "G1"},
            {"id": "gemini-2.0-flash", "name": "G2"},
            {"id": "gemini-1.5-pro", "name": "G15"},
        ]
        sorted_models = _sort_models(models)
        ids = [m["id"] for m in sorted_models]
        assert ids == ["gemini-2.0-flash", "gemini-1.5-pro", "gemini-1.0-pro"]
