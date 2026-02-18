"""Tests for prompts/getPrompt.py."""

import pytest
from prompts.getPrompt import get_prompt


class TestGetPrompt:
    def test_reads_jury_prompt(self, clear_prompt_cache):
        text = get_prompt("jury")
        assert isinstance(text, str)
        assert len(text) > 0

    def test_reads_rewriter_prompt(self, clear_prompt_cache):
        text = get_prompt("rewriter")
        assert isinstance(text, str)
        assert len(text) > 0

    def test_reads_manager_prompt(self, clear_prompt_cache):
        text = get_prompt("manager")
        assert isinstance(text, str)
        assert len(text) > 0

    def test_cache_hit(self, clear_prompt_cache):
        first = get_prompt("jury")
        second = get_prompt("jury")
        assert first is second  # same object (cached)

    def test_missing_prompt_raises(self, clear_prompt_cache):
        with pytest.raises(FileNotFoundError):
            get_prompt("nonexistent_prompt_name")

    def test_cache_clear_behavior(self, clear_prompt_cache):
        first = get_prompt("jury")
        get_prompt.cache_clear()
        second = get_prompt("jury")
        # Content is same, but objects may differ after cache clear
        assert first == second
