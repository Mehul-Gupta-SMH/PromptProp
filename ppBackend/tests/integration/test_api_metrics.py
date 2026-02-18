"""Tests for POST /api/metrics."""

from unittest.mock import patch


class TestApiMetrics:
    def test_metrics_shape(self, client, mock_mlflow):
        with patch("route.mlflow_register", return_value="run-123"):
            resp = client.post("/api/metrics", json={
                "experimentId": "exp-1",
                "iteration": 1,
                "results": [
                    {"score": 95, "reasoning": "good"},
                    {"score": 85, "reasoning": "ok"},
                ],
            })
            assert resp.status_code == 200
            body = resp.json()
            metrics = body["metrics"]
            expected_keys = {
                "average_score", "pass_rate", "total_cases",
                "accuracy", "precision", "recall",
                "directness", "format_adherence", "consistency", "relevance",
            }
            assert set(metrics.keys()) == expected_keys

    def test_mlflow_run_id_returned(self, client):
        with patch("route.mlflow_register", return_value="run-456"):
            resp = client.post("/api/metrics", json={
                "experimentId": "exp-1",
                "iteration": 1,
                "results": [{"score": 90, "reasoning": "fine"}],
            })
            assert resp.json()["mlflowRunId"] == "run-456"

    def test_mlflow_returns_none_gracefully(self, client):
        with patch("route.mlflow_register", return_value=None):
            resp = client.post("/api/metrics", json={
                "experimentId": "exp-1",
                "iteration": 1,
                "results": [{"score": 80, "reasoning": "ok"}],
            })
            assert resp.status_code == 200
            assert resp.json()["mlflowRunId"] is None

    def test_all_metric_values_are_floats(self, client):
        with patch("route.mlflow_register", return_value=None):
            resp = client.post("/api/metrics", json={
                "experimentId": "exp-1",
                "iteration": 1,
                "results": [{"score": 90, "reasoning": ""}],
            })
            for k, v in resp.json()["metrics"].items():
                assert isinstance(v, (int, float)), f"{k} is not numeric"
