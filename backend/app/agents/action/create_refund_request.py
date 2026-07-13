"""
agents/action/create_refund_request.py — updated for customer_id schema.
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
  SET sr.type       = 'refund',
      sr.reason     = $reason,
      sr.status     = $status,
      sr.evidence   = $evidence,
      sr.created_at = $created_at
MERGE (c)-[:HAS_REQUEST]->(sr)
MERGE (o)-[:HAS_REQUEST]->(sr)
RETURN sr.request_id AS request_id
"""


def run(state: Any) -> dict[str, Any]:
    rules      = get_rules()["refund"]
    order_data = state.order_data or {}
    order_id   = order_data.get("order_id") or state.entities.get("order_id", "")
    issue      = state.entities.get("issue", "")

    # window check
    days = days_since_delivery(order_data)
    if days is not None and days > rules["window_days"]:
        return {
            "action": "refund_denied",
            "reason": (
                f"refund window of {rules['window_days']} days has passed "
                f"({days} days since delivery)"
            ),
            "suggest_warranty": days <= get_rules()["warranty"]["period_months"] * 30,
        }

    needs_proof = rules["requires_photo_proof"] and "damaged" in (issue or "")
    status      = "pending_proof" if needs_proof else "open"
    evidence    = "photo_required" if needs_proof else None
    request_id  = "SR-" + uuid.uuid4().hex[:8].upper()

    rows = graph_client.write(
        _CYPHER,
        customer_id=state.customer_id,      # was customer_unique_id
        order_id=order_id,
        request_id=request_id,
        reason=issue or "customer_request",
        status=status,
        evidence=evidence,
        created_at=date.today().isoformat(),
        query_type="action_refund",
    )

    if not rows:
        return {"action": "refund_failed", "reason": "order ownership could not be verified"}

    result: dict[str, Any] = {
        "action":          "refund_request_created",
        "request_id":      request_id,
        "status":          status,
        "processing_days": _processing_days(
            order_data.get("payment_type"), rules
        ),
    }
    if needs_proof:
        result["next_step"] = (
            "Please upload a photo of the damaged item to proceed."
        )
    return result


def _processing_days(payment_type: str | None, rules: dict[str, Any]) -> int:
    method = (payment_type or "").lower()
    if "bank" in method or "slip" in method:
        return int(rules["processing_days_bank_slip"])
    if "voucher" in method or "store credit" in method:
        return int(rules["processing_days_voucher"])
    return int(rules["processing_days_card"])
