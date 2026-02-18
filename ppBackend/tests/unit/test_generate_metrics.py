"""Tests for resources/generateMetrics.py."""

import pytest
from resources.generateMetrics import (
    traditional_metrics,
    non_traditional_metrics,
    compute_metrics,
)


class TestTraditionalMetrics:
    def test_empty_input(self):
        result = traditional_metrics([])
        assert result == {"accuracy": 0.0, "precision": 0.0, "recall": 0.0}

    def test_all_pass(self):
        results = [{"score": 95}, {"score": 100}, {"score": 90}]
        m = traditional_metrics(results, pass_threshold=90.0)
        assert m["accuracy"] == 1.0
        assert m["precision"] == 1.0
        assert m["recall"] == 1.0

    def test_all_fail(self):
        results = [{"score": 10}, {"score": 50}, {"score": 89.9}]
        m = traditional_metrics(results, pass_threshold=90.0)
        assert m["accuracy"] == 0.0

    def test_threshold_edge_exact(self):
        results = [{"score": 90}]
        m = traditional_metrics(results, pass_threshold=90.0)
        assert m["accuracy"] == 1.0

    def test_threshold_edge_below(self):
        results = [{"score": 89.99}]
        m = traditional_metrics(results, pass_threshold=90.0)
        assert m["accuracy"] == 0.0

    def test_mixed(self):
        results = [{"score": 95}, {"score": 50}]
        m = traditional_metrics(results)
        assert m["accuracy"] == 0.5


class TestNonTraditionalMetrics:
    def test_empty_input(self):
        result = non_traditional_metrics([])
        assert result["directness"] == 0.0
        assert result["format_adherence"] == 0.0
        assert result["consistency"] == 0.0
        assert result["relevance"] == 0.0

    def test_perfect_scores(self):
        results = [{"score": 100, "reasoning": "great"}, {"score": 100, "reasoning": "perfect"}]
        m = non_traditional_metrics(results)
        assert m["directness"] == 1.0
        assert m["consistency"] == 1.0
        assert m["format_adherence"] == 1.0
        assert m["relevance"] == 1.0

    def test_format_keywords_detected(self):
        results = [
            {"score": 80, "reasoning": "Bad format and structure"},
            {"score": 80, "reasoning": "Good response"},
        ]
        m = non_traditional_metrics(results)
        assert m["format_adherence"] == 0.5

    def test_consistency_with_variance(self):
        results = [{"score": 0, "reasoning": ""}, {"score": 100, "reasoning": ""}]
        m = non_traditional_metrics(results)
        # stdev = 50, consistency = 1 - 50/100 = 0.5
        assert m["consistency"] == 0.5

    def test_missing_score_defaults_to_zero(self):
        results = [{"reasoning": "no score field"}]
        m = non_traditional_metrics(results)
        assert m["directness"] == 0.0


class TestComputeMetrics:
    def test_empty_returns_empty_dict(self):
        assert compute_metrics([]) == {}

    def test_output_shape(self):
        results = [{"score": 80, "reasoning": "ok"}]
        m = compute_metrics(results)
        expected_keys = {
            "average_score", "pass_rate", "total_cases",
            "accuracy", "precision", "recall",
            "directness", "format_adherence", "consistency", "relevance",
        }
        assert set(m.keys()) == expected_keys

    def test_total_cases(self):
        results = [{"score": 50, "reasoning": ""}, {"score": 75, "reasoning": ""}]
        assert compute_metrics(results)["total_cases"] == 2.0

    def test_average_score(self):
        results = [{"score": 60, "reasoning": ""}, {"score": 80, "reasoning": ""}]
        assert compute_metrics(results)["average_score"] == 70.0

    def test_all_values_are_floats(self):
        results = [{"score": 95, "reasoning": "fine"}]
        m = compute_metrics(results)
        for k, v in m.items():
            assert isinstance(v, float), f"{k} is not float"
