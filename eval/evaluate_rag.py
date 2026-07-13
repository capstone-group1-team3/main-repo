from __future__ import annotations
from typing import Any
from eval.scoring import percentile, retrieval_metrics


def score(cases: list[dict[str, Any]]) -> dict[str, Any]:
    metrics = retrieval_metrics(
        [set(case.get("expected_sources") or []) for case in cases],
        [list(case.get("retrieved_sources") or []) for case in cases],
    )
    timings = [float(case["latency_seconds"]) for case in cases if case.get("latency_seconds") is not None]
    metrics["p50_latency_seconds"] = percentile(timings, .50)
    metrics["p95_latency_seconds"] = percentile(timings, .95)
    return metrics
