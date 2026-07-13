"""Planner system prompt and context builder."""
import json
from typing import Any

SYSTEM_PROMPT = """You are a planning agent for an e-commerce customer support system.
Select exactly ONE next decision from: rag_policy, order_graph, action, ask_clarification, respond.
RULES:
1. Policy questions (what is, how does, how long, am I eligible) → rag_policy. Never ask for order ID.
2. Customer-specific order facts → order_graph.
3. Propose action ONLY when ownership verified AND user has not yet confirmed.
4. Use ask_clarification for one specific missing piece only.
5. NEVER invent facts, order IDs, amounts, or eligibility.
6. Return ONLY valid JSON matching the schema.
OUTPUT: {"decision":"...","corrected_intent":null,"reason":"...","confidence":0.0,"arguments":{}}"""

def build_planner_context(state: Any) -> str:
    last_obs = None
    if state.observations:
        o = state.observations[-1]
        last_obs = {"tool": o.get("tool"), "status": o.get("status")}
    history = state.conversation_history or []
    recent = history[-4:]
    summary = " | ".join(f"{t['role']}: {t['content'][:80]}" for t in recent)
    ctx = {
        "message": state.message,
        "initial_intent": state.intent,
        "intent_confidence": round(state.confidence, 3),
        "entities": {
            "order_id": state.entities.get("order_id"),
            "issue": state.entities.get("issue"),
        },
        "state_flags": {
            "has_policy_evidence": state.policy_evidence is not None,
            "has_order_data": state.order_data is not None,
            "ownership_verified": state.ownership_ok and state.order_data is not None,
            "confirmation_required": state.confirmation_required,
            "confirmation_received": state.confirmation_received,
        },
        "tools_used": state.tools_used,
        "iterations": state.iterations,
        "last_observation": last_obs,
        "conversation_summary": summary or None,
    }
    return json.dumps(ctx, ensure_ascii=False)
