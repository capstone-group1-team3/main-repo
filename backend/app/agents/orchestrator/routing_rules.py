"""
agents/orchestrator/routing_rules.py — maps intent to the ordered tool sequence.

The loop controller uses this to decide which tool to call next when the state
is still incomplete. Tools are listed in the order they should be called.
"""
from __future__ import annotations

# Per-intent tool sequence.  The loop calls the first tool whose output is still
# missing from the state, then re-evaluates.
TOOL_SEQUENCE: dict[str, list[str]] = {
    "policy_question":     ["rag_policy", "response"],
    "order_tracking":      ["order_graph", "response"],
    "refund_request":      ["rag_policy", "order_graph", "action", "response"],
    "return_request":      ["rag_policy", "order_graph", "action", "response"],
    "replacement_request": ["rag_policy", "order_graph", "action", "response"],
    "warranty_claim":      ["rag_policy", "order_graph", "action", "response"],
    "damaged_product":     ["rag_policy", "order_graph", "action", "response"],
    "cancel_order":        ["order_graph", "action", "response"],
    "payment_issue":       ["order_graph", "rag_policy", "action", "response"],
    "ticket_status":       ["order_graph", "response"],
}

# Tools that produce each state field (used by the loop to skip already-done tools)
TOOL_PRODUCES: dict[str, list[str]] = {
    "rag_policy":  ["policy_evidence", "candidate_ids", "policy_sources"],
    "order_graph": ["order_data", "orders", "tickets", "requests"],
    "action":      ["action_result"],
    "response":    [],   # always last — no state field
}


def next_tool(state: "OrchestratorState", intent: str) -> str | None:  # noqa: F821
    """
    Return the next executable tool.

    The sequence uses "response" as a symbolic final step, while the loop
    controller uses "respond" as the terminal decision. Therefore, reaching
    the response step must return "respond", not "response".
    """
    sequence = TOOL_SEQUENCE.get(intent, ["response"])

    for tool in sequence:
        if tool == "response":
            return "respond"

        produced = TOOL_PRODUCES.get(tool, [])
        if any(getattr(state, field, None) is None for field in produced):
            return tool

    return "respond"
