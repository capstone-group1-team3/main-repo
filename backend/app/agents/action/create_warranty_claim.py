"""
agents/action/create_warranty_claim.py — updated for customer_id schema.
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
  SET sr.type       = 'warranty',
      sr.reason     = $reason,
      sr.status     = $status,
      sr.evidence   = 'photo_required',
      sr.created_at = $created_at
MERGE (c)-[:HAS_REQUEST]->(sr)
MERGE (o)-[:HAS_REQUEST]->(sr)
RETURN sr.request_id AS request_id
"""


def run(state: Any) -> dict[str, Any]:
    rules        = get_rules()["warranty"]
    order_data   = state.order_data or {}
    order_id     = order_data.get("order_id") or state.entities.get("order_id", "")
    issue        = state.entities.get("issue", "defect_after_use")
    warranty_days = rules["period_months"] * 30

    days = days_since_delivery(order_data)
    if days is not None and days > warranty_days:
        return {
            "action": "warranty_claim_denied",
            "reason": f"warranty period of {rules['period_months']} months has passed",
        }

    request_id = "SR-" + uuid.uuid4().hex[:8].upper()
    rows = graph_client.write(
        _CYPHER,
        customer_id=state.customer_id,
        order_id=order_id,
        request_id=request_id,
        reason=issue,
        status="pending_proof",
        created_at=date.today().isoformat(),
        query_type="action_warranty",
    )
    if not rows:
        return {"action": "warranty_failed", "reason": "order ownership could not be verified"}
    return {
        "action":     "warranty_claim_created",
        "request_id": request_id,
        "status":     "pending_proof",
        "next_step":  "Please describe the fault and upload a photo or video.",
    }
