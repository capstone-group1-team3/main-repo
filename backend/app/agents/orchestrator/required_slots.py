"""
agents/orchestrator/required_slots.py — required state fields per intent.

The loop controller checks these after each tool call. If any slot is still None,
the loop either calls another tool or asks the customer for the missing info.
"""
from __future__ import annotations

from typing import Any

# Minimum fields that must be non-None in OrchestratorState for each intent
# before the Action Agent can be called.
REQUIRED_FOR_ACTION: dict[str, list[str]] = {
    "refund_request":     ["order_data", "policy_evidence"],
    "return_request":     ["order_data", "policy_evidence"],
    "replacement_request":["order_data", "policy_evidence"],
    "warranty_claim":     ["order_data", "policy_evidence"],
    "damaged_product":    ["order_data", "policy_evidence"],
    "cancel_order":       ["order_data"],
    "payment_issue":      ["order_data"],
    "order_tracking":     ["order_data"],
    "ticket_status":      [],   # just needs graph lookup, no action
    "policy_question":    ["policy_evidence"],
}

# Slots we ask the customer for if they are missing from entities
CLARIFICATION_SLOTS: dict[str, list[tuple[str, str]]] = {
    "refund_request":      [("order_id", "Could you provide your order number?"),
                            ("issue", "What was the issue with the item?")],
    "return_request":      [("order_id", "Could you provide your order number?"),
                            ("product", "Which product would you like to return?")],
    "replacement_request": [("order_id", "Could you provide your order number?")],
    "warranty_claim":      [("order_id", "Could you provide your order number?"),
                            ("issue", "What fault did you notice?")],
    "cancel_order":        [("order_id", "Which order would you like to cancel?")],
    "payment_issue":       [("order_id", "Which order had the payment issue?")],
    "order_tracking":      [],   # latest order used as fallback
    "ticket_status":       [],
    "policy_question":     [],
    "damaged_product":     [("order_id", "Could you provide your order number?")],
}


def missing_slots(state: Any, intent: str) -> list[str]:
    """Return list of required state fields that are still None."""
    required = REQUIRED_FOR_ACTION.get(intent, [])
    return [slot for slot in required if getattr(state, slot, None) is None]


def first_missing_entity(entities: dict[str, Any], intent: str) -> tuple[str, str] | None:
    """Return (slot_name, clarification_question) for the first missing entity slot."""
    for slot, question in CLARIFICATION_SLOTS.get(intent, []):
        if not entities.get(slot):
            return slot, question
    return None
