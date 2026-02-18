"""Tests for GET /api/models."""

import pytest
from unittest.mock import AsyncMock, patch


class TestApiModels:
    def test_returns_providers_structure(self, client, reset_models_cache, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        mock_models = [{"id": "gemini-2.0-flash", "name": "Gemini 2.0 Flash"}]
        with patch("models_list._fetch_gemini_models", new_callable=AsyncMock,
                   return_value=mock_models):
            resp = client.get("/api/models", params={"refresh": "true"})
            assert resp.status_code == 200
            body = resp.json()
            assert "providers" in body
            assert len(body["providers"]) == 1
            assert body["providers"][0]["provider"] == "gemini"
            assert len(body["providers"][0]["models"]) == 1

    def test_empty_when_no_keys(self, client, reset_models_cache, monkeypatch):
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        resp = client.get("/api/models", params={"refresh": "true"})
        assert resp.status_code == 200
        assert resp.json()["providers"] == []

    def test_multiple_providers(self, client, reset_models_cache, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "gk")
        monkeypatch.setenv("OPENAI_API_KEY", "ok")
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        with patch("models_list._fetch_gemini_models", new_callable=AsyncMock,
                   return_value=[{"id": "gem", "name": "Gem"}]):
            with patch("models_list._fetch_openai_models", new_callable=AsyncMock,
                       return_value=[{"id": "gpt", "name": "GPT"}]):
                resp = client.get("/api/models", params={"refresh": "true"})
                providers = resp.json()["providers"]
                provider_names = [p["provider"] for p in providers]
                assert "gemini" in provider_names
                assert "openai" in provider_names
