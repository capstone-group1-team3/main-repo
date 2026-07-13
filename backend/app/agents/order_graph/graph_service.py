"""
agents/order_graph/graph_service.py — customer-scoped reads from Neo4j.

Updated: all queries use customer_id (not customer_unique_id).
Every function is scoped so a customer can only retrieve their own data.
"""
from __future__ import annotations

from typing import Any

from app.graph.neo4j_client import graph_client
from app.graph import cypher_templates as T


def get_orders(customer_id: str) -> list[dict[str, Any]]:
    return graph_client.read(
        T.GET_CUSTOMER_ORDERS,
        customer_id=customer_id,
        query_type="customer_orders",
    )


def get_order(customer_id: str, order_id: str) -> dict[str, Any] | None:
    rows = graph_client.read(
        T.GET_ORDER_FOR_CUSTOMER,
        customer_id=customer_id,
        order_id=order_id,
        query_type="customer_order",
    )
    return rows[0] if rows else None


def get_tickets(customer_id: str) -> list[dict[str, Any]]:
    return graph_client.read(
        T.GET_CUSTOMER_TICKETS,
        customer_id=customer_id,
        query_type="customer_tickets",
    )


def get_requests(customer_id: str) -> list[dict[str, Any]]:
    return graph_client.read(
        T.GET_CUSTOMER_REQUESTS,
        customer_id=customer_id,
        query_type="customer_requests",
    )


def get_all_tickets() -> list[dict[str, Any]]:
    """Staff / admin only — caller must check role before calling."""
    return graph_client.read(T.GET_ALL_TICKETS, query_type="all_tickets")


def latest_order(customer_id: str) -> dict[str, Any] | None:
    """Most recent order — fallback when no order_id is given."""
    orders = get_orders(customer_id)
    return orders[0] if orders else None
