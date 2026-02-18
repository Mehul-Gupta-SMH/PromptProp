"""Tests for health check and placeholder endpoints."""


class TestRoot:
    def test_root(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        body = resp.json()
        assert "message" in body
        assert "PromptProp" in body["message"]


class TestHealthCheck:
    def test_health_check(self, client):
        resp = client.get("/health-check")
        assert resp.status_code == 200
        assert resp.json() == {"status": "healthy"}


class TestPlaceholders:
    def test_jury_501(self, client):
        resp = client.get("/jury", params={"experiment_id": "x"})
        assert resp.status_code == 501

    def test_evaluate_501(self, client):
        resp = client.get("/evaluate", params={"experiment_id": "x"})
        assert resp.status_code == 501

    def test_evaluation_metrics_501(self, client):
        resp = client.get("/evaluation_metrics", params={"experiment_id": "x"})
        assert resp.status_code == 501
