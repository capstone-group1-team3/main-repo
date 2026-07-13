"""
agents/orchestrator/entity_extractor.py — entity extraction with history.

Updated: accepts conversation_history so entities mentioned in earlier
turns (order_id, product, issue) are carried forward automatically.

Example:
    Turn 1 → "My laptop arrived damaged"     → product=laptop, issue=damaged
    Turn 2 → "Can I get a refund for it?"    → product=laptop carried forward
"""
from __future__ import annotations

import re
import time
from typing import Any
from app.monitoring.metrics import ENTITY_DURATION, ENTITY_FAILURES, MISSING_SLOTS

_ORDER_ID_RE = re.compile(
    r"\b([A-Z]{2,6}\d{3,}|ORD-?\d{3,}|order[- #]?(\d{3,}))\b",
    re.I,
)

_ISSUE_KEYWORDS: dict[str, str] = {
    "damaged":    "damaged",
    "broken":     "damaged",
    "defective":  "defective",
    "wrong item": "wrong_item",
    "wrong size": "wrong_size",
    "late":       "late_delivery",
    "missing":    "missing_item",
    "payment":    "payment_issue",
    "water damage": "accidental_damage",
    "dropped":      "accidental_damage",
    "misuse":       "misuse",
    "normal wear":  "normal_wear",
    "worn out":     "normal_wear",
}

_PRODUCT_RE = re.compile(
    r"\b(laptop|phone|shirt|jacket|shoes|watch|tablet|headphones|"
    r"camera|bag|book|keyboard|mouse|chair|monitor|desk)\b",
    re.I,
)

_FALLBACK_PROMPT = """\
Extract entities from this customer support message.
Return a JSON object only, no markdown:
{{
  "order_id":         "<string or null>",
  "product":          "<string or null>",
  "issue":            "<string or null>",
  "requested_action": "<string or null>"
}}

Message: {message}
"""

_ACTION_MAP: dict[str, str] = {
    "refund_request":      "refund",
    "return_request":      "return",
    "replacement_request": "replacement",
    "warranty_claim":      "warranty",
    "cancel_order":        "cancel",
    "damaged_product":     "refund",
}


def extract_entities(
    message: str,
    intent: str = "",
    history: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    started = time.perf_counter()
    outcome = "success"
    entities: dict[str, Any] = {
        "order_id":         None,
        "product":          None,
        "issue":            None,
        "requested_action": None,
    }

    # ── 1. carry forward from history ─────────────────────
    if history:
        _inherit_from_history(entities, history)

    # ── 2. extract from current message (overrides history) ─
    m = _ORDER_ID_RE.search(message)
    if m:
        entities["order_id"] = m.group(0)

    pm = _PRODUCT_RE.search(message)
    if pm:
        entities["product"] = pm.group(0).lower()

    lm = message.lower()
    for keyword, issue in _ISSUE_KEYWORDS.items():
        if keyword in lm:
            entities["issue"] = issue
            break

    # ── 3. requested action from intent ───────────────────
    if intent in _ACTION_MAP:
        entities["requested_action"] = _ACTION_MAP[intent]

    # ── 4. LLM fallback for still-missing entities ─────────
    if not any([entities["order_id"], entities["product"], entities["issue"]]):
        try:
            entities = _llm_extract(message, entities)
        except Exception as exc:
            outcome = "fallback_failure"
            category = "timeout" if "timeout" in type(exc).__name__.lower() else "llm"
            ENTITY_FAILURES.labels(error_category=category).inc()

    for slot in ("order_id", "product", "issue", "requested_action"):
        if entities.get(slot) is None:
            MISSING_SLOTS.labels(slot=slot).inc()
    ENTITY_DURATION.labels(outcome=outcome).observe(time.perf_counter() - started)

    return entities


def _inherit_from_history(
    entities: dict[str, Any],
    history: list[dict[str, str]],
) -> None:
    """
    Walk the last 6 history turns (user messages only) and pull any
    entities that are still missing in the current message.
    Uses the same regex/keyword extractors — no LLM cost.
    """
    for turn in reversed(history[-6:]):
        if turn.get("role") != "user":
            continue
        text = turn["content"]

        if entities["order_id"] is None:
            m = _ORDER_ID_RE.search(text)
            if m:
                entities["order_id"] = m.group(0)

        if entities["product"] is None:
            pm = _PRODUCT_RE.search(text)
            if pm:
                entities["product"] = pm.group(0).lower()

        if entities["issue"] is None:
            lt = text.lower()
            for keyword, issue in _ISSUE_KEYWORDS.items():
                if keyword in lt:
                    entities["issue"] = issue
                    break

        # stop once everything is filled
        if all(v is not None for v in [
            entities["order_id"],
            entities["product"],
            entities["issue"],
        ]):
            break


def _llm_extract(
    message: str,
    base: dict[str, Any],
) -> dict[str, Any]:
    import json
    from app.llm.llm_client import chat_complete

    raw    = chat_complete(
        _FALLBACK_PROMPT.format(message=message),
        temperature=0,
    )
    parsed = json.loads(raw)
    # only overwrite None values
    for k in base:
        if base[k] is None and parsed.get(k):
            base[k] = parsed[k]
    return base
