"""
agents/orchestrator/orchestrator_agent.py — top-level entry.

Loads server-side ConversationStateData → injects into OrchestratorState →
runs loop → saves updated state back.
"""
from __future__ import annotations
import uuid
from typing import Any

from app.agents.orchestrator.state import OrchestratorState
from app.agents.orchestrator.intent_detector import detect_intent
from app.agents.orchestrator.entity_extractor import extract_entities
from app.agents.orchestrator.loop_controller import run_loop
from app.agents.orchestrator.conversation_store import (
    get_store, new_conversation_id,
    ConversationStateData, PendingActionContext,
)


def run(
    message: str,
    customer_id: str,
    request_id: str | None = None,
    conversation_history: list[dict[str, str]] | None = None,
    conversation_id: str | None = None,
) -> OrchestratorState:
    rid     = request_id or uuid.uuid4().hex
    history = conversation_history or []
    store   = get_store()
    conv_id = conversation_id or new_conversation_id()

    # Load server-side state
    persisted: ConversationStateData | None = None
    if conversation_id:
        persisted = store.get(conversation_id, customer_id)
        if persisted and persisted.executed:
            persisted = None  # Replay protection

    # Intent + entities
    ir         = detect_intent(message, history=history)
    intent     = ir.get("intent", "policy_question")
    confidence = float(ir.get("confidence", 0.5))
    entities   = extract_entities(message, intent=intent, history=history)

    # Build state
    state = OrchestratorState(
        request_id=rid,
        customer_id=customer_id,
        conversation_id=conv_id,
        message=message,
        conversation_history=history,
        intent=intent,
        confidence=confidence,
        entities=entities,
    )

    # Inject persisted confirmation
    if persisted and persisted.confirmation_required and not persisted.executed:
        state.confirmation_required = True
        state.intent = persisted.intent or state.intent
        # Merge entities: user's new entities override persisted ones
        state.entities = {**persisted.entities, **entities}

        if persisted.pending_action:
            pa = persisted.pending_action
            state.pending_action = {
                "intent":       pa.intent,
                "order_id":     pa.order_id,
                "amount":       pa.amount,
                "order_status": pa.order_status,
                "requirements": pa.eligibility.get("requirements", []),
            }
            state.confirmation_context = {
                "intent":   pa.intent,
                "order_id": pa.order_id,
            }
            # Restore minimal order data for re-validation
            state.order_data = {
                "order_id":      pa.order_id,
                "status":        pa.order_status,
                "delivered_date": None,
                "payment_value":  pa.amount,
            }
        state.ownership_ok = True

    # Run the loop
    state = run_loop(state)

    # Persist / clear state
    if state.confirmation_required and not state.confirmation_received:
        pa_ctx = None
        if state.pending_action:
            pa = state.pending_action
            pa_ctx = PendingActionContext(
                intent=pa.get("intent", state.intent),
                order_id=pa.get("order_id"),
                amount=pa.get("amount"),
                order_status=pa.get("order_status"),
                eligibility={"requirements": pa.get("requirements", [])},
            )
        store.save(ConversationStateData(
            customer_id=customer_id,
            conversation_id=conv_id,
            intent=state.intent,
            entities=state.entities,
            pending_action=pa_ctx,
            confirmation_required=True,
            order_id=(state.order_data or {}).get("order_id"),
            order_status=(state.order_data or {}).get("status"),
        ))
    elif state.action_result:
        store.mark_executed(conv_id)
        store.delete(conv_id)
    else:
        store.delete(conv_id)

    return state
