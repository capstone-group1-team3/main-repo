"""
tests/test_planner_schema.py — PlannerDecision schema + validator unit tests.
No external services required.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import pytest
from pydantic import ValidationError
from app.agents.orchestrator.planner_schema import PlannerDecision


def test_valid_decision():
    d = PlannerDecision(
        decision="rag_policy", reason="General policy question.", confidence=0.95
    )
    assert d.decision == "rag_policy"
    assert d.corrected_intent is None


def test_valid_corrected_intent():
    d = PlannerDecision(
        decision="rag_policy", corrected_intent="policy_question",
        reason="User asked about policy.", confidence=0.98,
    )
    assert d.corrected_intent == "policy_question"


def test_invalid_decision_rejected():
    with pytest.raises(ValidationError):
        PlannerDecision(decision="invent_tool", reason="bad", confidence=0.9)


def test_confidence_out_of_range():
    with pytest.raises(ValidationError):
        PlannerDecision(decision="respond", reason="ok", confidence=1.5)


def test_empty_reason_rejected():
    with pytest.raises(ValidationError):
        PlannerDecision(decision="respond", reason="", confidence=0.9)


def test_reason_too_long_rejected():
    with pytest.raises(ValidationError):
        PlannerDecision(decision="respond", reason="x" * 301, confidence=0.9)


def test_invalid_corrected_intent_rejected():
    with pytest.raises(ValidationError):
        PlannerDecision(
            decision="rag_policy", corrected_intent="hack_database",
            reason="test", confidence=0.9,
        )


def test_arguments_default_empty():
    d = PlannerDecision(decision="respond", reason="done", confidence=0.99)
    assert d.arguments == {}


# ── Decision Validator tests ──────────────────────────────────────────────────
from app.agents.orchestrator.decision_validator import validate
from app.agents.orchestrator.state import OrchestratorState


def _make_state(**kwargs):
    s = OrchestratorState()
    for k, v in kwargs.items():
        setattr(s, k, v)
    return s


def test_validator_blocks_policy_to_order_graph():
    decision = PlannerDecision(decision="order_graph", reason="policy q",
                               confidence=0.95, corrected_intent="policy_question")
    state    = _make_state(intent="policy_question", tools_used=[])
    approved, corrected, args = validate(decision, state)
    assert approved == "rag_policy"


def test_validator_blocks_action_without_ownership():
    decision = PlannerDecision(decision="action", reason="refund", confidence=0.95)
    state    = _make_state(intent="refund_request", ownership_ok=False,
                           order_data=None, tools_used=[])
    approved, _, _ = validate(decision, state)
    assert approved == "order_graph"


def test_validator_blocks_action_without_confirmation():
    decision = PlannerDecision(decision="action", reason="cancel", confidence=0.95)
    state    = _make_state(
        intent="cancel_order",
        ownership_ok=True,
        order_data={"order_id": "ORD001", "status": "processing"},
        confirmation_received=False,
        tools_used=[],
    )
    approved, _, _ = validate(decision, state)
    assert approved == "ask_clarification"


def test_validator_strips_customer_id_from_args():
    decision = PlannerDecision(
        decision="order_graph", reason="test", confidence=0.9,
        arguments={"customer_id": "EVIL_ID", "order_id": "ORD001"},
    )
    state = _make_state(intent="order_tracking", tools_used=[])
    _, _, args = validate(decision, state)
    assert "customer_id" not in args
    assert args.get("order_id") == "ORD001"
