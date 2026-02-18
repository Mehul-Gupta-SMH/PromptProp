"""Regression: compute_metrics() output contract.

Locks in that compute_metrics() always returns exactly 10 keys,
all floats, with valid ranges.
"""

import pytest
from resources.generateMetrics import compute_metrics

EXPECTED_KEYS = {
    "average_score",
    "pass_rate",
    "total_cases",
    "accuracy",
    "precision",
    "recall",
    "directness",
    "format_adherence",
    "consistency",
    "relevance",
}


class TestMetricsContract:
    def test_exactly_10_keys(self):
        results = [{"score": 80, "reasoning": "ok"}]
        m = compute_metrics(results)
        assert set(m.keys()) == EXPECTED_KEYS

    def test_all_values_are_floats(self):
        results = [{"score": 90, "reasoning": "fine"}, {"score": 60, "reasoning": "meh"}]
        m = compute_metrics(results)
        for k, v in m.items():
            assert isinstance(v, float), f"{k} is {type(v)}, expected float"

    def test_ranges_valid(self):
        results = [{"score": 75, "reasoning": ""}]
        m = compute_metrics(results)

        assert 0 <= m["average_score"] <= 100
        assert 0 <= m["pass_rate"] <= 1
        assert m["total_cases"] >= 1
        assert 0 <= m["accuracy"] <= 1
        assert 0 <= m["precision"] <= 1
        assert 0 <= m["recall"] <= 1
        assert 0 <= m["directness"] <= 1
        assert 0 <= m["format_adherence"] <= 1
        assert 0 <= m["consistency"] <= 1
        assert 0 <= m["relevance"] <= 1

    def test_empty_input_returns_empty_dict(self):
        assert compute_metrics([]) == {}

    def test_single_perfect_score(self):
        m = compute_metrics([{"score": 100, "reasoning": "perfect"}])
        assert m["average_score"] == 100.0
        assert m["pass_rate"] == 1.0
        assert m["accuracy"] == 1.0

    def test_single_zero_score(self):
        m = compute_metrics([{"score": 0, "reasoning": "terrible"}])
        assert m["average_score"] == 0.0
        assert m["pass_rate"] == 0.0
        assert m["accuracy"] == 0.0

    def test_large_dataset(self):
        results = [{"score": i, "reasoning": f"r{i}"} for i in range(100)]
        m = compute_metrics(results)
        assert set(m.keys()) == EXPECTED_KEYS
        assert m["total_cases"] == 100.0
