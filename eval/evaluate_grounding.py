from __future__ import annotations
from typing import Any
from eval.scoring import grounding_metrics


def score(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Score candidates, accepted/invalid citations, support, and safe declines."""
    return grounding_metrics(records)
