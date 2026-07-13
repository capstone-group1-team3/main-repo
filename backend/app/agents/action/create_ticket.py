"""
agents/action/create_ticket.py — updated for customer_id schema.
"""
from __future__ import annotations

import uuid
from datetime import date
from typing import Any

from app.graph.neo4j_client import graph_client

_CYPHER = """
MATCH (c:Customer {customer_id: $customer_id})
      -[:PLACED]->(o:Order {order_id: $order_id})
MERGE (t:Ticket {ticket_id: $ticket_id})
  SET t.category   = $category,
      t.subject    = $subject,
      t.status     = $status,
      t.created_at = $created_at
MERGE (c)-[:HAS_TICKET]->(t)
MERGE (o)-[:ABOUT]->(t)
RETURN t.ticket_id AS ticket_id
"""


def run(state: Any) -> dict[str, Any]:
    order_data = state.order_data or {}
    order_id   = order_data.get("order_id") or state.entities.get("order_id", "")
    ticket_id  = "TCK-" + uuid.uuid4().hex[:8].upper()

    rows = graph_client.write(
        _CYPHER,
        customer_id=state.customer_id,      # was customer_unique_id
        ticket_id=ticket_id,
        category=state.intent,
        subject=f"Support request: {state.intent.replace('_', ' ')}",
        status="open",
        created_at=date.today().isoformat(),
        order_id=order_id,
        query_type="action_ticket",
    )
    if not rows:
        return {"action": "ticket_failed", "reason": "order ownership could not be verified"}
    return {"ticket_id": ticket_id, "status": "open", "action": "ticket_created"}
