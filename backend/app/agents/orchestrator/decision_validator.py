"""Deterministic validator between planner and execution."""
import logging
from typing import Any
from app.agents.orchestrator.planner_schema import PlannerDecision

logger = logging.getLogger("validator")
ALLOWED_DECISIONS = {"rag_policy","order_graph","action","ask_clarification","respond"}
ALLOWED_INTENTS   = {
    "policy_question","order_tracking","refund_request","return_request",
    "replacement_request","cancel_order","warranty_claim","damaged_product",
    "payment_issue","ticket_status",
}

def validate(decision: PlannerDecision, state: Any) -> tuple[str, str, dict]:
    proposed = decision.decision
    intent   = decision.corrected_intent or state.intent
    args     = dict(decision.arguments)
    # Strip sensitive fields
    for k in ("customer_id","customer_unique_id","password","token"):
        args.pop(k, None)
    if proposed not in ALLOWED_DECISIONS:
        return "respond", intent, {}
    if intent not in ALLOWED_INTENTS:
        intent = state.intent
    # Policy → never order_graph
    if intent == "policy_question" and proposed == "order_graph":
        return "rag_policy", intent, {}
    # Policy → never ask for order_id
    if intent == "policy_question" and proposed == "ask_clarification":
        if "order" in str(args.get("question","")).lower():
            return "rag_policy", intent, {}
    # Action without ownership → order_graph
    if proposed == "action" and (not state.ownership_ok or state.order_data is None):
        return "order_graph", intent, {}
    # Action without confirmation → ask_clarification (confirmation gate)
    if proposed == "action" and not state.confirmation_received:
        args["_confirmation_gate"] = True
        return "ask_clarification", intent, args
    # Repeated same tool
    from app.config.settings import settings
    limit = getattr(settings, "max_same_tool_calls", 1)
    if proposed not in ("respond","ask_clarification"):
        if sum(1 for t in state.tools_used if t == proposed) >= limit:
            return "respond", intent, {}
    return proposed, intent, args
