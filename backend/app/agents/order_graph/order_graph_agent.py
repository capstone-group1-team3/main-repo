"""
agents/order_graph/order_graph_agent.py — the Order / Graph Agent.

Updated: uses customer_id (not customer_unique_id).

Fetches customer/order/product facts from Neo4j based on intent + entities.
Every read is scoped by customer_id — ownership is enforced in the Cypher
query itself, not just in application code.
"""
from __future__ import annotations

from typing import Any

from app.agents.order_graph.graph_service import (
    get_orders, get_order, get_tickets, get_requests, latest_order,
)
from app.agents.order_graph.graph_mapper import (
    map_order, map_orders, map_ticket, map_request,
)


def run(
    customer_id: str,           # was customer_unique_id
    intent: str,
    entities: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Returns:
        order_data    — single mapped order or None
        orders        — list of mapped orders
        tickets       — list of mapped tickets
        requests      — list of mapped requests
        ownership_ok  — False when a requested order_id does not belong to this customer
        error         — human-readable string on failure
    """
    entities = entities or {}
    order_id: str | None = entities.get("order_id")

    result: dict[str, Any] = {
        "order_data":   None,
        "orders":       [],
        "tickets":      [],
        "requests":     [],
        "ownership_ok": True,
        "error":        None,
    }

    # ── order-centric intents ─────────────────────────────
    if intent in (
        "order_tracking", "refund_request", "return_request",
        "replacement_request", "warranty_claim", "damaged_product",
        "cancel_order",
    ):
        if order_id:
            row = get_order(customer_id, order_id)
            if row is None:
                result["ownership_ok"] = False
                result["error"] = (
                    f"Order {order_id} was not found in this customer's account."
                )
                return result
            result["order_data"] = map_order(row)
        else:
            latest = latest_order(customer_id)
            if latest:
                result["order_data"] = map_order(latest)

    # ── ticket / request status ───────────────────────────
    elif intent == "ticket_status":
        result["tickets"]  = [map_ticket(r) for r in get_tickets(customer_id)]
        result["requests"] = [map_request(r) for r in get_requests(customer_id)]

    # ── payment issue ─────────────────────────────────────
    elif intent == "payment_issue":
        if order_id:
            row = get_order(customer_id, order_id)
            if row is None:
                result["ownership_ok"] = False
                result["error"] = (
                    f"Order {order_id} was not found in this customer's account."
                )
                return result
            result["order_data"] = map_order(row)
        result["requests"] = [map_request(r) for r in get_requests(customer_id)]

    # ── generic / policy question → still pull latest order ─
    else:
        latest = latest_order(customer_id)
        if latest:
            result["order_data"] = map_order(latest)
        result["orders"] = map_orders(get_orders(customer_id))

    return result
