from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

WRITE_INTENTS = {
    "refund_request", "return_request", "replacement_request", "warranty_claim",
    "damaged_product", "cancel_order", "payment_issue",
}


@dataclass(frozen=True)
class EvaluationCase:
    id: str
    message: str
    expected_intent: str
    expected_entities: dict[str, Any] = field(default_factory=dict)
    expected_tools: tuple[str, ...] = ()
    forbidden_tools: tuple[str, ...] = ()
    expected_policy_sources: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)
    performs_write: bool = False

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "EvaluationCase":
        case_id = str(raw.get("id", "")).strip()
        message = str(raw.get("message", raw.get("input", ""))).strip()
        intent = str(raw.get("expected_intent", "")).strip()
        if not case_id or not message or not intent:
            raise ValueError("fixture requires id, message/input, and expected_intent")
        sources = raw.get("expected_policy_sources") or []
        if raw.get("expected_policy_source"):
            sources = [raw["expected_policy_source"]]
        performs_write = bool(raw.get("performs_write", intent in WRITE_INTENTS))
        return cls(
            id=case_id, message=message, expected_intent=intent,
            expected_entities=dict(raw.get("expected_entities") or {}),
            expected_tools=tuple(raw.get("expected_tools") or ()),
            forbidden_tools=tuple(raw.get("forbidden_tools") or ()),
            expected_policy_sources=tuple(sources),
            metadata=dict(raw.get("metadata") or {}), performs_write=performs_write,
        )
