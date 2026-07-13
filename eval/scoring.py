from __future__ import annotations

from collections import defaultdict
from math import ceil
from typing import Any, Iterable


def safe_rate(numerator: int | float, denominator: int | float) -> float | None:
    return None if denominator == 0 else float(numerator) / float(denominator)


def classification_metrics(gold: list[str], predicted: list[str]) -> dict[str, Any]:
    if len(gold) != len(predicted):
        raise ValueError("gold and predicted lengths differ")
    labels = sorted(set(gold) | set(predicted))
    confusion = {label: {p: 0 for p in labels} for label in labels}
    for expected, actual in zip(gold, predicted):
        confusion[expected][actual] += 1
    per_label = {}
    for label in labels:
        tp = confusion[label][label]
        fp = sum(confusion[g][label] for g in labels if g != label)
        fn = sum(confusion[label][p] for p in labels if p != label)
        precision = safe_rate(tp, tp + fp) or 0.0
        recall = safe_rate(tp, tp + fn) or 0.0
        f1 = 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)
        per_label[label] = {"precision": precision, "recall": recall, "f1": f1, "support": sum(confusion[label].values())}
    total = len(gold)
    return {
        "count": total,
        "accuracy": safe_rate(sum(a == b for a, b in zip(gold, predicted)), total),
        "macro_precision": safe_rate(sum(v["precision"] for v in per_label.values()), len(labels)),
        "macro_recall": safe_rate(sum(v["recall"] for v in per_label.values()), len(labels)),
        "macro_f1": safe_rate(sum(v["f1"] for v in per_label.values()), len(labels)),
        "per_label": per_label, "confusion_matrix": confusion,
    }


def normalize_slot(value: Any) -> Any:
    return value.strip().lower().replace("-", "") if isinstance(value, str) else value


def entity_slot_metrics(expected: list[dict], actual: list[dict]) -> dict[str, Any]:
    totals = defaultdict(int); exact = defaultdict(int); normalized = defaultdict(int)
    for exp, got in zip(expected, actual):
        for slot, value in exp.items():
            totals[slot] += 1
            if got.get(slot) == value:
                exact[slot] += 1
            if normalize_slot(got.get(slot)) == normalize_slot(value):
                normalized[slot] += 1
    total = sum(totals.values())
    return {
        "count": total,
        "exact_match": safe_rate(sum(exact.values()), total),
        "normalized_match": safe_rate(sum(normalized.values()), total),
        "per_slot": {
            slot: {
                "count": count,
                "exact": safe_rate(exact[slot], count),
                "normalized": safe_rate(normalized[slot], count),
            } for slot, count in sorted(totals.items())
        },
    }


def retrieval_metrics(expected_sources: list[set[str]], rankings: list[list[str]]) -> dict[str, Any]:
    if len(expected_sources) != len(rankings):
        raise ValueError("expected and ranking lengths differ")
    top1 = top3 = reciprocal_sum = no_result = 0
    per_policy = defaultdict(lambda: [0, 0])
    for expected, ranking in zip(expected_sources, rankings):
        if not ranking:
            no_result += 1
        rank = next((i + 1 for i, source in enumerate(ranking) if source in expected), None)
        top1 += int(rank == 1); top3 += int(rank is not None and rank <= 3)
        reciprocal_sum += 0 if rank is None else 1 / rank
        for source in expected:
            per_policy[source][1] += 1
            per_policy[source][0] += int(rank is not None and rank <= 3)
    count = len(rankings)
    return {
        "count": count, "top_1": safe_rate(top1, count), "top_3": safe_rate(top3, count),
        "mrr": safe_rate(reciprocal_sum, count), "no_result_rate": safe_rate(no_result, count),
        "per_policy_top_3": {k: safe_rate(v[0], v[1]) for k, v in sorted(per_policy.items())},
    }


def tool_path_metrics(expected: list[list[str]], actual: list[list[str]], forbidden: list[list[str]] | None = None) -> dict[str, Any]:
    forbidden = forbidden or [[] for _ in expected]
    exact = required = required_total = unnecessary = actual_total = missing_critical = 0
    for exp, got, banned in zip(expected, actual, forbidden):
        exact += int(exp == got)
        required += sum(tool in got for tool in exp); required_total += len(exp)
        unnecessary += sum(tool not in exp for tool in got); actual_total += len(got)
        missing_critical += sum(tool not in got for tool in exp) + sum(tool in got for tool in banned)
    count = len(expected)
    return {
        "count": count, "exact_path_accuracy": safe_rate(exact, count),
        "required_tool_recall": safe_rate(required, required_total),
        "unnecessary_tool_rate": safe_rate(unnecessary, actual_total),
        "missing_critical_tool_rate": safe_rate(missing_critical, required_total),
    }


def grounding_metrics(records: list[dict[str, Any]]) -> dict[str, Any]:
    valid = cited = invalid = safe_no_evidence = no_evidence = grounded = 0
    for record in records:
        candidates = set(record.get("candidates") or [])
        accepted = list(record.get("accepted") or [])
        attempted_invalid = list(record.get("invalid") or [])
        cited += len(accepted); valid += sum(cid in candidates for cid in accepted)
        invalid += len(attempted_invalid)
        if not candidates:
            no_evidence += 1
            safe_no_evidence += int(bool(record.get("declined")))
        grounded += int(bool(record.get("supported")) and all(cid in candidates for cid in accepted))
    count = len(records)
    return {
        "count": count, "citation_validity": safe_rate(valid, cited),
        "unsupported_citation_count": invalid,
        "no_evidence_safety_pass_rate": safe_rate(safe_no_evidence, no_evidence),
        "grounding_pass_rate": safe_rate(grounded, count),
    }


def percentile(values: Iterable[float], quantile: float) -> float | None:
    ordered = sorted(values)
    if not ordered:
        return None
    index = max(0, min(len(ordered) - 1, ceil(quantile * len(ordered)) - 1))
    return ordered[index]
