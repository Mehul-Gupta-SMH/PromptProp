"""
Metric computation for PromptProp optimization iterations.

Produces a flat dict of metrics compatible with registerMetrics.register().
"""

from __future__ import annotations
from typing import Sequence


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

# Each result is a dict with at minimum:
#   score: float          — jury average score (0-100)
#   reasoning: str        — jury combined feedback
# Optional enrichment fields (populated when jury returns structured scores):
#   accuracy_score: float
#   relevance_score: float
#   completeness_score: float
IterationResult = dict


# ---------------------------------------------------------------------------
# Traditional metrics (binary pass/fail from jury scores)
# ---------------------------------------------------------------------------

def traditional_metrics(
    results: Sequence[IterationResult],
    pass_threshold: float = 90.0,
) -> dict[str, float]:
    """Compute Accuracy, Precision, and Recall from jury scores.

    Each test case is treated as a binary classification:
      - "positive" = case where we expect a good answer (all cases)
      - "pass" = jury score >= pass_threshold

    Accuracy  = correct / total
    Precision = true_pass / predicted_pass  (all are predicted positive)
    Recall    = true_pass / actual_positive (all are actual positive)

    Since every case is a "positive" example (we always expect a good
    answer), precision == recall == accuracy == pass_rate.  We still
    report them separately so downstream consumers (MLflow, dashboards)
    have the standard metric names.
    """
    if not results:
        return {"accuracy": 0.0, "precision": 0.0, "recall": 0.0}

    passed = sum(1 for r in results if r.get("score", 0) >= pass_threshold)
    total = len(results)
    rate = passed / total

    return {
        "accuracy": round(rate, 4),
        "precision": round(rate, 4),
        "recall": round(rate, 4),
    }


# ---------------------------------------------------------------------------
# Non-traditional metrics (from manager.prompt spec)
# ---------------------------------------------------------------------------

def _avg(values: list[float]) -> float:
    return round(sum(values) / len(values), 4) if values else 0.0


def non_traditional_metrics(
    results: Sequence[IterationResult],
) -> dict[str, float]:
    """Compute non-traditional metrics derived from jury evaluations.

    - Directness:        average score (higher score = more direct path to objective)
    - Format Adherence:  fraction of results that don't mention format issues in reasoning
    - Consistency:       1 - (stdev of scores / 100), measures score uniformity
    - Relevance:         average score (jury already evaluates relevance)
    """
    if not results:
        return {
            "directness": 0.0,
            "format_adherence": 0.0,
            "consistency": 0.0,
            "relevance": 0.0,
        }

    scores = [r.get("score", 0) for r in results]
    reasonings = [r.get("reasoning", "").lower() for r in results]

    # Directness — normalized average score
    directness = _avg(scores) / 100.0

    # Format Adherence — fraction without format complaints
    format_keywords = ["format", "structure", "layout", "template", "schema"]
    format_issues = sum(
        1 for text in reasonings
        if any(kw in text for kw in format_keywords)
    )
    format_adherence = round(1.0 - (format_issues / len(results)), 4)

    # Consistency — 1 - normalized standard deviation
    mean = sum(scores) / len(scores)
    variance = sum((s - mean) ** 2 for s in scores) / len(scores)
    stdev = variance ** 0.5
    consistency = round(1.0 - (stdev / 100.0), 4)

    # Relevance — normalized average score
    relevance = _avg(scores) / 100.0

    return {
        "directness": round(directness, 4),
        "format_adherence": format_adherence,
        "consistency": consistency,
        "relevance": round(relevance, 4),
    }


# ---------------------------------------------------------------------------
# Combined
# ---------------------------------------------------------------------------

def compute_metrics(
    results: Sequence[IterationResult],
    pass_threshold: float = 90.0,
) -> dict[str, float]:
    """Compute all metrics for an iteration. Returns a flat dict
    compatible with registerMetrics.register().

    Also includes:
      - average_score: the raw average jury score (0-100)
      - pass_rate: fraction of cases scoring >= threshold
      - total_cases: number of test cases evaluated
    """
    if not results:
        return {}

    scores = [r.get("score", 0) for r in results]
    avg_score = sum(scores) / len(scores)
    passed = sum(1 for s in scores if s >= pass_threshold)

    metrics: dict[str, float] = {
        "average_score": round(avg_score, 2),
        "pass_rate": round(passed / len(scores), 4),
        "total_cases": float(len(scores)),
    }
    metrics.update(traditional_metrics(results, pass_threshold))
    metrics.update(non_traditional_metrics(results))

    return metrics
