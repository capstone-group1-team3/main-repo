from __future__ import annotations
from eval.scoring import safe_rate


def score(expected: list[dict], actual: list[dict]):
    total = len(expected)
    matches = sum(
        e.get("action") == a.get("action") and e.get("status") == a.get("status")
        for e, a in zip(expected, actual)
    )
    return {"count": total, "action_accuracy": safe_rate(matches, total)}
