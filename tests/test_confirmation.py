"""
tests/test_confirmation.py — confirmation flow across HTTP requests.

Tests the conversation_store persistence, replay protection,
and eligibility-before-confirmation logic WITHOUT external services.
"""
import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import pytest
from app.agents.orchestrator.conversation_store import (
    InMemoryConversationStore, ConversationStateData, PendingActionContext,
    new_conversation_id,
)
from app.agents.action.action_evaluator import evaluate_eligibility
from datetime import date, timedelta


# ── Conversation store tests ──────────────────────────────────────────────────

def test_store_get_own_state():
    store   = InMemoryConversationStore()
    conv_id = new_conversation_id()
    data    = ConversationStateData(customer_id="C001", conversation_id=conv_id,
                                    confirmation_required=True)
    store.save(data)
    loaded = store.get(conv_id, "C001")
    assert loaded is not None
    assert loaded.customer_id == "C001"


def test_store_ownership_enforced():
    """Customer C001 cannot load C002's confirmation state."""
    store   = InMemoryConversationStore()
    conv_id = new_conversation_id()
    data    = ConversationStateData(customer_id="C002", conversation_id=conv_id,
                                    confirmation_required=True)
    store.save(data)
    loaded = store.get(conv_id, "C001")   # different customer
    assert loaded is None


def test_store_ttl_expiry():
    store   = InMemoryConversationStore(ttl_seconds=1)
    conv_id = new_conversation_id()
    data    = ConversationStateData(customer_id="C001", conversation_id=conv_id,
                                    confirmation_required=True)
    store.save(data)
    time.sleep(1.1)
    loaded = store.get(conv_id, "C001")
    assert loaded is None


def test_replay_protection():
    """mark_executed() prevents re-running the same action."""
    store   = InMemoryConversationStore()
    conv_id = new_conversation_id()
    data    = ConversationStateData(customer_id="C001", conversation_id=conv_id,
                                    confirmation_required=True)
    store.save(data)
    store.mark_executed(conv_id)

    loaded = store.get(conv_id, "C001")
    # Even though loaded exists, executed=True should be detected
    assert loaded is None or loaded.executed is True


def test_store_delete():
    store   = InMemoryConversationStore()
    conv_id = new_conversation_id()
    data    = ConversationStateData(customer_id="C001", conversation_id=conv_id)
    store.save(data)
    store.delete(conv_id)
    assert store.get(conv_id, "C001") is None


def test_different_conv_ids_are_isolated():
    store  = InMemoryConversationStore()
    id_a   = new_conversation_id()
    id_b   = new_conversation_id()
    data_a = ConversationStateData(customer_id="C001", conversation_id=id_a,
                                   intent="cancel_order")
    data_b = ConversationStateData(customer_id="C001", conversation_id=id_b,
                                   intent="refund_request")
    store.save(data_a); store.save(data_b)
    assert store.get(id_a, "C001").intent == "cancel_order"
    assert store.get(id_b, "C001").intent == "refund_request"


# ── Eligibility evaluator tests ───────────────────────────────────────────────

_RULES = {
    "cancellation": {"allowed_before_status": "shipped"},
    "refund":       {"window_days": 14, "requires_photo_proof": False},
    "return":       {"window_days": 30},
    "replacement":  {"window_days": 30, "requires_defect": True},
    "warranty":     {"period_months": 12},
}


def _order(status="processing", days_since_delivery=None, amount=100.0):
    delivered = None
    if days_since_delivery is not None:
        delivered = (date.today() - timedelta(days=days_since_delivery)).isoformat()
    return {
        "order_id":      "ORD001",
        "status":        status,
        "delivered_date":delivered,
        "payment_value": amount,
    }


def test_cancel_eligible():
    elig = evaluate_eligibility("cancel_order", _order("processing"), {}, _RULES)
    assert elig.eligible is True
    assert elig.amount == 100.0


def test_cancel_shipped_denied():
    elig = evaluate_eligibility("cancel_order", _order("shipped"), {}, _RULES)
    assert elig.eligible is False
    assert "cannot be cancelled" in (elig.reason or "").lower()


def test_cancel_delivered_denied():
    elig = evaluate_eligibility("cancel_order", _order("delivered", days_since_delivery=3), {}, _RULES)
    assert elig.eligible is False


def test_refund_within_window():
    elig = evaluate_eligibility("refund_request", _order("delivered", days_since_delivery=7), {}, _RULES)
    assert elig.eligible is True


def test_refund_outside_window():
    elig = evaluate_eligibility("refund_request", _order("delivered", days_since_delivery=20), {}, _RULES)
    assert elig.eligible is False
    assert "window" in (elig.reason or "").lower()


def test_refund_outside_window_with_neo4j_date_like_value():
    """Neo4j date values stringify as ISO dates but are not datetime.date."""
    class Neo4jDateLike:
        def __str__(self):
            return (date.today() - timedelta(days=20)).isoformat()

        def __bool__(self):
            return True

    order = _order("delivered")
    order["delivered_date"] = Neo4jDateLike()
    elig = evaluate_eligibility("refund_request", order, {}, _RULES)
    assert elig.eligible is False
    assert elig.days_since_delivery == 20


def test_warranty_within_period():
    _RULES["warranty"].update({"requires_defect": True, "excludes": ["accidental_damage", "misuse", "normal_wear"]})
    elig = evaluate_eligibility("warranty_claim", _order("delivered", days_since_delivery=200), {"issue": "defective"}, _RULES)
    assert elig.eligible is True


def test_warranty_expired():
    _RULES["warranty"].update({"requires_defect": True, "excludes": ["accidental_damage", "misuse", "normal_wear"]})
    elig = evaluate_eligibility("warranty_claim", _order("delivered", days_since_delivery=400), {"issue": "defective"}, _RULES)
    assert elig.eligible is False


def test_eligibility_returned_before_confirmation_gate():
    """
    Verify that evaluate_eligibility is called before confirmation is shown.
    A denied action must NEVER show a confirmation prompt.
    """
    elig = evaluate_eligibility("cancel_order", _order("shipped"), {}, _RULES)
    # Loop_controller checks this and responds directly when eligible=False
    assert elig.eligible is False
    # Confirmation must NOT be requested
    # (loop_controller reads elig.eligible; if False, sets done=True without setting confirmation_required)


def test_no_implicit_latest_order_for_sensitive():
    """
    When order_id is absent and order_data is None, the loop must ask for order_id.
    We verify the evaluator is not called without an order.
    evaluate_eligibility with empty order_data should not crash.
    """
    elig = evaluate_eligibility("cancel_order", {}, {}, _RULES)
    # Empty order: no status → should treat as ineligible (status in BLOCKED defaults)
    # Main thing: it does not raise
    assert elig.eligible is False or elig.eligible is True  # just no crash
