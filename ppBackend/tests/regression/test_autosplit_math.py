"""Regression: auto-split math edge cases.

Tests the dataset upload auto-split logic for boundary conditions.
"""

import pytest
from route import DatasetUploadRequest, DatasetRowInput


def _make_rows(n: int) -> list[DatasetRowInput]:
    return [DatasetRowInput(query=f"q{i}", expectedOutput=f"e{i}") for i in range(n)]


class TestAutoSplitMath:
    def test_zero_rows(self, client, sample_experiment):
        resp = client.post("/api/dataset", json={
            "experimentId": sample_experiment.id,
            "rows": [],
            "autoSplit": True,
        })
        assert resp.status_code == 200
        assert resp.json()["splits"]["total"] == 0

    def test_one_row(self, client, sample_experiment):
        resp = client.post("/api/dataset", json={
            "experimentId": sample_experiment.id,
            "rows": [{"query": "q", "expectedOutput": "e"}],
            "autoSplit": True,
        })
        splits = resp.json()["splits"]
        assert splits["total"] == 1
        # With round(1 * 0.70) = round(0.70) = 1 train
        assert splits["train"] + splits["val"] + splits["test"] == 1

    def test_two_rows(self, client, sample_experiment):
        resp = client.post("/api/dataset", json={
            "experimentId": sample_experiment.id,
            "rows": [
                {"query": "q1", "expectedOutput": "e1"},
                {"query": "q2", "expectedOutput": "e2"},
            ],
            "autoSplit": True,
        })
        splits = resp.json()["splits"]
        assert splits["total"] == 2
        assert splits["train"] + splits["val"] + splits["test"] == 2

    def test_pre_assigned_rows_not_reshuffled(self, client, sample_experiment):
        resp = client.post("/api/dataset", json={
            "experimentId": sample_experiment.id,
            "rows": [
                {"query": "q1", "expectedOutput": "e1", "split": "val"},
                {"query": "q2", "expectedOutput": "e2"},
                {"query": "q3", "expectedOutput": "e3"},
            ],
            "autoSplit": True,
        })
        splits = resp.json()["splits"]
        assert splits["total"] == 3
        # The pre-assigned "val" row should remain val
        assert splits["val"] >= 1

    def test_ten_rows_default_ratios(self, client, sample_experiment):
        rows = [{"query": f"q{i}", "expectedOutput": f"e{i}"} for i in range(10)]
        resp = client.post("/api/dataset", json={
            "experimentId": sample_experiment.id,
            "rows": rows,
            "autoSplit": True,
        })
        splits = resp.json()["splits"]
        assert splits["total"] == 10
        # round(10 * 0.70) = 7 train, round(10 * 0.15) = 2 val, rest = 1 test
        assert splits["train"] == 7
        assert splits["val"] == 2
        assert splits["test"] == 1
