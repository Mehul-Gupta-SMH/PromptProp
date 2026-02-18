"""Tests for ppsecrets/getSecrets.py."""

from ppsecrets.getSecrets import Secrets


class TestSecrets:
    def test_get_types(self):
        s = Secrets()
        assert s.get_types() == ["llm_api"]

    def test_get_keys(self):
        s = Secrets()
        keys = s.get_keys("llm_api")
        assert "openai_api_key" in keys
        assert "gemini_api_key" in keys
        assert "anthropic_api_key" in keys
        assert "grok_api_key" in keys

    def test_get_keys_invalid_type(self):
        s = Secrets()
        assert s.get_keys("nonexistent") == []

    def test_get_secret_with_env(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-123")
        s = Secrets()
        assert s.get_secret("llm_api", "openai_api_key") == "sk-test-123"

    def test_get_secret_without_env(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        s = Secrets()
        assert s.get_secret("llm_api", "openai_api_key") is None

    def test_get_secret_invalid_key(self):
        s = Secrets()
        assert s.get_secret("llm_api", "nonexistent_key") is None

    def test_get_secret_invalid_type(self):
        s = Secrets()
        assert s.get_secret("nonexistent", "openai_api_key") is None

    def test_multiple_keys_set(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "gem-key")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "ant-key")
        s = Secrets()
        assert s.get_secret("llm_api", "gemini_api_key") == "gem-key"
        assert s.get_secret("llm_api", "anthropic_api_key") == "ant-key"
