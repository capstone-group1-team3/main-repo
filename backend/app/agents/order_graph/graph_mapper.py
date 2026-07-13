"""
agents/order_graph/graph_mapper.py — maps raw Neo4j records into clean typed dicts.

The Orchestrator state expects a consistent shape regardless of which Cypher
template was called. This mapper normalises the raw rows.
"""
from __future__ import annotations

from typing import Any


def map_order(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "order_id": raw.get("order_id"),
        "status": raw.get("status"),
        "purchase_date": raw.get("purchase_date"),
        "delivered_date": raw.get("delivered_date"),
        "estimated_delivery_date": raw.get("estimated_delivery_date"),
        "payment_type": raw.get("payment_type"),
        "payment_value": raw.get("payment_value"),
        "installments": raw.get("installments"),
        "payments": raw.get("payments") or [],
        "delivery_late": bool(raw.get("delivery_late", False)),
        "items": raw.get("items") or [],
    }


def map_orders(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [map_order(r) for r in rows]


def map_ticket(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "ticket_id": raw.get("ticket_id"),
        "category": raw.get("category"),
        "subject": raw.get("subject"),
        "status": raw.get("status"),
        "created_at": raw.get("created_at"),
        "order_id": raw.get("order_id"),
    }


def map_request(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "request_id": raw.get("request_id"),
        "type": raw.get("type"),
        "reason": raw.get("reason"),
        "status": raw.get("status"),
        "evidence": raw.get("evidence"),
        "created_at": raw.get("created_at"),
        "resolved_at": raw.get("resolved_at"),
        "order_id": raw.get("order_id"),
    }
