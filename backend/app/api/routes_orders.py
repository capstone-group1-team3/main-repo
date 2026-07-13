"""
api/routes_orders.py — customer order, ticket, and request history endpoints.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.auth.auth_middleware import get_current_identity, require_staff
from app.auth.auth_service import Identity
from app.agents.order_graph.graph_service import (
    get_orders, get_tickets, get_requests, get_all_tickets,
)
from app.agents.order_graph.graph_mapper import (
    map_orders, map_ticket, map_request,
)

router = APIRouter(prefix="/orders", tags=["orders"])


@router.get("")    # handles /orders
@router.get("/")   # handles /orders/
def my_orders(identity: Identity = Depends(get_current_identity)):
    return map_orders(get_orders(identity.customer_id))


@router.get("/tickets")
def my_tickets(identity: Identity = Depends(get_current_identity)):
    return [map_ticket(t) for t in get_tickets(identity.customer_id)]


@router.get("/requests")
def my_requests(identity: Identity = Depends(get_current_identity)):
    return [map_request(r) for r in get_requests(identity.customer_id)]


@router.get("/admin/tickets")
def all_tickets(identity: Identity = Depends(require_staff)):
    return get_all_tickets()