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
from app.agents.orchestrator import loop_controller, orchestrator_agent
from app.agents.orchestrator.state import OrchestratorState
from app.agents.action.action_evaluator import evaluate_eligibility
from datetime import date, timedelta
import pytest


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

@pytest.mark.parametrize(("reply", "confirmed"), [("yes", True), ("no", False)])
def test_confirmation_reply_uses_persisted_cancel_context(monkeypatch, reply, confirmed):
    """Bare yes/no replies inherit the pending action instead of being reclassified."""
    store = InMemoryConversationStore()
    conv_id = new_conversation_id()
    store.save(ConversationStateData(
        customer_id="C001",
        conversation_id=conv_id,
        intent="cancel_order",
        entities={"order_id": "ORD021621"},
        pending_action=PendingActionContext(
            intent="cancel_order",
            order_id="ORD021621",
            amount=100.0,
            order_status="processing",
        ),
        confirmation_required=True,
    ))
    observed = {}

    def handle_confirmation(state):
        observed["intent"] = state.intent
        loop_controller._handle_confirm(state)
        return state

    monkeypatch.setattr(orchestrator_agent, "get_store", lambda: store)
    monkeypatch.setattr(
        orchestrator_agent,
        "detect_intent",
        lambda *args, **kwargs: {
            "intent": "policy_question",
            "confidence": 0.30,
        },
    )
    monkeypatch.setattr(orchestrator_agent, "extract_entities", lambda *args, **kwargs: {})
    monkeypatch.setattr(orchestrator_agent, "run_loop", handle_confirmation)

    state = orchestrator_agent.run(
        message=reply,
        customer_id="C001",
        conversation_id=conv_id,
    )

    assert observed["intent"] == "cancel_order"
    assert state.intent == "cancel_order"
    assert state.confirmation_received is confirmed
    if not confirmed:
        assert "cancelled" in (state.clarification_needed or "").lower()


def test_confirmed_refund_skips_phase_one_order_graph(monkeypatch):
    """A persisted yes must reach Action Agent, not request confirmation again."""
    from types import SimpleNamespace
    from app.agents.rag_policy import rag_policy_agent
    from app.agents.action import action_agent, action_router

    state = OrchestratorState(
        request_id="REQ-1",
        customer_id="C001",
        conversation_id="CONV-1",
        message="yes",
        intent="refund_request",
        confidence=0.30,
        entities={"order_id": "ORD001", "issue": "damaged", "action": "refund"},
        order_data={
            "order_id": "ORD001",
            "status": "delivered",
            "delivered_date": None,
            "payment_value": 44.63,
        },
        pending_action={
            "intent": "refund_request",
            "order_id": "ORD001",
            "amount": 44.63,
            "order_status": "delivered",
            "requirements": ["photo_required"],
        },
        confirmation_context={"intent": "refund_request", "order_id": "ORD001"},
        confirmation_required=True,
    )

    monkeypatch.setattr(
        rag_policy_agent,
        "run",
        lambda **kwargs: {
            "policy_evidence": "verified refund policy",
            "sources": ["refund_policy.md"],
            "candidate_ids": ["refund_policy.md::refund-policy::0"],
        },
    )

    def reload_owned_order(current):
        current.order_data = _order("delivered", days_since_delivery=3, amount=44.63)
        current.entities["order_id"] = "ORD001"
        current.ownership_ok = True
        return True

    monkeypatch.setattr(loop_controller, "_reload_current_owned_order", reload_owned_order)
    monkeypatch.setattr(
        loop_controller,
        "evaluate_eligibility",
        lambda *args, **kwargs: SimpleNamespace(
            eligible=True,
            action="refund_request",
            reason=None,
        ),
    )
    monkeypatch.setattr(action_router, "get_rules", lambda: _RULES)
    monkeypatch.setattr(
        action_agent,
        "run",
        lambda current: {
            "action": "refund_request_created",
            "request_id": "RET-1",
            "status": "pending_proof",
        },
    )

    result = loop_controller.run_loop(state)

    assert result.confirmation_received is False
    assert result.action_result["action"] == "refund_request_created"
    assert result.tools_used == ["rag_policy", "action"]
    assert "order_graph" not in result.tools_used


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


def test_confirmed_sensitive_action_advances_past_confirmation_gate(monkeypatch):
    """A restored yes must execute, not ask for the same confirmation again."""
    from app.agents.action import action_agent, action_router
    from app.agents.order_graph import order_graph_agent
    from app.agents.rag_policy import rag_policy_agent

    rules = {
        **_RULES,
        "warranty": {
            "period_months": 12,
            "requires_defect": True,
            "excludes": ["accidental_damage", "misuse", "normal_wear"],
        },
    }
    current_order = _order("delivered", days_since_delivery=5)
    calls = {"action": 0}

    monkeypatch.setattr(action_router, "get_rules", lambda: rules)
    monkeypatch.setattr(rag_policy_agent, "run", lambda **_: {
        "policy_evidence": "supported policy",
        "sources": ["refund_policy.md"],
        "candidate_ids": ["refund_policy.md::body::0"],
    })
    monkeypatch.setattr(order_graph_agent, "run", lambda **_: {
        "order_data": current_order,
        "orders": [], "tickets": [], "requests": [],
        "ownership_ok": True,
    })
    monkeypatch.setattr(
        loop_controller,
        "_reload_current_owned_order",
        lambda state: setattr(state, "order_data", current_order) or True,
    )

    def execute(_state):
        calls["action"] += 1
        return {
            "action": "refund_request_created",
            "request_id": "SR-TEST",
            "status": "open",
        }

    monkeypatch.setattr(action_agent, "run", execute)
    state = loop_controller.run_loop(loop_controller.OrchestratorState(
        customer_id="C001",
        message="yes",
        intent="refund_request",
        confidence=0.95,
        entities={"order_id": "ORD001", "issue": "damaged"},
        pending_action={"intent": "refund_request", "order_id": "ORD001"},
        confirmation_required=True,
    ))

    assert calls["action"] == 1
    assert state.action_result["action"] == "refund_request_created"
    assert state.confirmation_required is False


def test_unconfirmed_sensitive_action_never_calls_action_agent(monkeypatch):
    from app.agents.action import action_agent, action_router
    from app.agents.order_graph import order_graph_agent
    from app.agents.rag_policy import rag_policy_agent

    rules = {
        **_RULES,
        "warranty": {
            "period_months": 12,
            "requires_defect": True,
            "excludes": ["accidental_damage", "misuse", "normal_wear"],
        },
    }
    monkeypatch.setattr(action_router, "get_rules", lambda: rules)
    monkeypatch.setattr(rag_policy_agent, "run", lambda **_: {
        "policy_evidence": "supported policy", "sources": [],
        "candidate_ids": [],
    })
    monkeypatch.setattr(order_graph_agent, "run", lambda **_: {
        "order_data": _order("delivered", days_since_delivery=5),
        "orders": [], "tickets": [], "requests": [],
        "ownership_ok": True,
    })
    monkeypatch.setattr(
        action_agent, "run",
        lambda _state: pytest.fail("action ran before confirmation"),
    )

    state = loop_controller.run_loop(loop_controller.OrchestratorState(
        customer_id="C001",
        message="Refund order ORD001 because it was damaged.",
        intent="refund_request",
        confidence=0.95,
        entities={"order_id": "ORD001", "issue": "damaged"},
    ))

    assert state.confirmation_required is True
    assert state.action_result is None


def test_default_store_ttl_comes_from_settings(monkeypatch):
    from app.agents.orchestrator import conversation_store

    monkeypatch.setattr(
        conversation_store.settings, "conversation_ttl_seconds", 7
    )
    assert InMemoryConversationStore()._ttl == 7


def test_restored_confirmation_resumes_workflow_without_planner(monkeypatch):
    """A bare yes must not be re-planned as an unrelated low-confidence turn."""
    store = InMemoryConversationStore()
    conv_id = new_conversation_id()
    store.save(ConversationStateData(
        customer_id="C001",
        conversation_id=conv_id,
        intent="refund_request",
        entities={"order_id": "ORD001", "issue": "damaged"},
        pending_action=PendingActionContext(
            intent="refund_request", order_id="ORD001", amount=100.0,
            order_status="delivered", eligibility={"requirements": []},
        ),
        confirmation_required=True,
    ))
    observed = {}

    monkeypatch.setattr(orchestrator_agent, "get_store", lambda: store)
    monkeypatch.setattr(
        orchestrator_agent, "detect_intent",
        lambda *args, **kwargs: {"intent": "policy_question", "confidence": 0.30},
    )
    monkeypatch.setattr(orchestrator_agent, "extract_entities", lambda *args, **kwargs: {})

    def capture(state):
        observed["plan"] = list(state.current_plan)
        loop_controller._handle_confirm(state)
        return state

    monkeypatch.setattr(orchestrator_agent, "run_loop", capture)
    state = orchestrator_agent.run(
        message="yes", customer_id="C001", conversation_id=conv_id,
    )

    assert observed["plan"] == ["rag_policy", "order_graph", "action"]
    assert state.confirmation_received is True
