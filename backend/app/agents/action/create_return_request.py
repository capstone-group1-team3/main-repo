"""
agents/action/create_return_request.py — updated for customer_id schema.
"""
from __future__ import annotations

import uuid
from datetime import date
from typing import Any

from app.graph.neo4j_client import graph_client
from app.agents.action.action_router import get_rules, days_since_delivery

_CYPHER = """
MATCH (c:Customer {customer_id: $customer_id})
      -[:PLACED]->(o:Order {order_id: $order_id})
MERGE (sr:ServiceRequest {request_id: $request_id})
  SET sr.type       = 'return',
      sr.reason     = $reason,
      sr.status     = 'open',
      sr.created_at = $created_at
MERGE (c)-[:HAS_REQUEST]->(sr)
MERGE (o)-[:HAS_REQUEST]->(sr)
RETURN sr.request_id AS request_id
"""


def run(state: Any) -> dict[str, Any]:
    rules      = get_rules()["return"]
    order_data = state.order_data or {}
    order_id   = order_data.get("order_id") or state.entities.get("order_id", "")
    issue      = state.entities.get("issue", "changed_mind")

    days = days_since_delivery(order_data)
    if days is not None and days > rules["window_days"]:
        return {
            "action": "return_denied",
            "reason": (
                f"return window of {rules['window_days']} days has passed "
                f"({days} days since delivery)"
            ),
        }

    shipping_paid_by = rules["return_shipping_paid_by"].get(
        issue, rules["return_shipping_paid_by"]["changed_mind"]
    )
    request_id = "SR-" + uuid.uuid4().hex[:8].upper()
    rows = graph_client.write(
        _CYPHER,
        customer_id=state.customer_id,
        order_id=order_id,
        request_id=request_id,
        reason=issue,
        created_at=date.today().isoformat(),
        query_type="action_return",
    )
    if not rows:
        return {"action": "return_failed", "reason": "order ownership could not be verified"}
    return {
        "action":                 "return_request_created",
        "request_id":             request_id,
        "status":                 "open",
        "return_shipping_paid_by": shipping_paid_by,
        "restocking_fee_pct":     rules["restocking_fee_pct"],
    }
