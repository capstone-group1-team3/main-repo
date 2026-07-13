"""
agents/action/cancel_order.py — updated for customer_id schema.
"""
from __future__ import annotations

from typing import Any

from app.graph.neo4j_client import graph_client
from app.agents.action.action_router import get_rules

_CYPHER = """
MATCH (c:Customer {customer_id: $customer_id})
      -[:PLACED]->(o:Order {order_id: $order_id})
SET o.status = 'canceled'
RETURN o.order_id AS order_id, o.status AS status
"""


def run(state: Any) -> dict[str, Any]:
    rules          = get_rules()["cancellation"]
    order_data     = state.order_data or {}
    order_id       = order_data.get("order_id") or state.entities.get("order_id", "")
    current_status = order_data.get("status", "")

    blocked = {rules["allowed_before_status"], "delivered", "canceled"}
    if current_status in blocked:
        return {
            "action": "cancel_denied",
            "reason": (
                f"order cannot be cancelled — "
                f"current status is '{current_status}'"
            ),
        }

    rows = graph_client.write(
        _CYPHER,
        order_id=order_id,
        customer_id=state.customer_id,      # was customer_unique_id
        query_type="action_cancel",
    )
    if not rows:
        return {
            "action": "cancel_failed",
            "reason": "order not found in customer account",
        }
    return {
        "action":   "order_cancelled",
        "order_id": order_id,
        "status":   "canceled",
    }
