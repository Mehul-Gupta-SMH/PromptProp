"""Tests for dataset endpoints."""

import pytest


class TestDatasetUpload:
    def test_upload_without_autosplit(self, client, sample_experiment):
        resp = client.post("/api/dataset", json={
            "experimentId": sample_experiment.id,
            "rows": [
                {"query": "q1", "expectedOutput": "e1"},
                {"query": "q2", "expectedOutput": "e2"},
            ],
            "autoSplit": False,
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["experimentId"] == sample_experiment.id
        assert body["splits"]["total"] == 2
        assert body["splits"]["train"] == 2  # default split
        assert len(body["rowIds"]) == 2

    def test_upload_with_autosplit(self, client, sample_experiment):
        rows = [{"query": f"q{i}", "expectedOutput": f"e{i}"} for i in range(10)]
        resp = client.post("/api/dataset", json={
            "experimentId": sample_experiment.id,
            "rows": rows,
            "autoSplit": True,
            "trainRatio": 0.70,
            "valRatio": 0.15,
            "testRatio": 0.15,
        })
        assert resp.status_code == 200
        splits = resp.json()["splits"]
        assert splits["total"] == 10
        assert splits["train"] + splits["val"] + splits["test"] == 10

    def test_404_for_missing_experiment(self, client):
        resp = client.post("/api/dataset", json={
            "experimentId": "nonexistent-id",
            "rows": [{"query": "q", "expectedOutput": "e"}],
        })
        assert resp.status_code == 404


class TestDatasetStats:
    def test_get_stats(self, client, sample_experiment):
        # Upload first
        client.post("/api/dataset", json={
            "experimentId": sample_experiment.id,
            "rows": [
                {"query": "q1", "expectedOutput": "e1", "split": "train"},
                {"query": "q2", "expectedOutput": "e2", "split": "val"},
            ],
        })
        resp = client.get(f"/api/dataset/{sample_experiment.id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["train"] == 1
        assert body["val"] == 1
        assert body["test"] == 0
        assert body["total"] == 2

    def test_404_for_missing_experiment(self, client):
        resp = client.get("/api/dataset/nonexistent")
        assert resp.status_code == 404


class TestDatasetSplit:
    def test_get_split_rows(self, client, sample_experiment):
        client.post("/api/dataset", json={
            "experimentId": sample_experiment.id,
            "rows": [
                {"query": "q1", "expectedOutput": "e1", "split": "train"},
                {"query": "q2", "expectedOutput": "e2", "split": "train"},
                {"query": "q3", "expectedOutput": "e3", "split": "val"},
            ],
        })
        resp = client.get(f"/api/dataset/{sample_experiment.id}/train")
        assert resp.status_code == 200
        rows = resp.json()
        assert len(rows) == 2
        assert all(r["split"] == "train" for r in rows)

    def test_404_for_missing_experiment(self, client):
        resp = client.get("/api/dataset/nonexistent/train")
        assert resp.status_code == 404
