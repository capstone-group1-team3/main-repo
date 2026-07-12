from pathlib import Path
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.agents.action import (
    cancel_order, create_refund_request, create_replacement_request,
    create_return_request, create_ticket, create_warranty_claim,
)
from app.graph import cypher_templates

ROOT = Path(__file__).resolve().parents[1]


def test_executable_constraints_use_active_keys():
    text = (ROOT / "neo4j" / "constraints.cypher").read_text(encoding="utf-8")
    assert "c.customer_id IS UNIQUE" in text
    assert "c.customer_unique_id IS UNIQUE" not in text
    assert "p.payment_id IS UNIQUE" in text
    assert "s.order_id IS UNIQUE" in text


def test_every_action_mutation_enforces_customer_order_relationship():
    modules = [
        cancel_order, create_refund_request, create_return_request,
        create_replacement_request, create_warranty_claim, create_ticket,
    ]
    for module in modules:
        compact = " ".join(module._CYPHER.split())
        assert "Customer {customer_id: $customer_id}" in compact
        assert "-[:PLACED]->" in compact, module.__name__
        assert "Order {order_id: $order_id}" in compact


def test_order_queries_aggregate_payments_before_returning_items():
    query = cypher_templates.GET_ORDER_FOR_CUSTOMER
    assert "collect(payments)" not in query  # guard against an accidental nested list
    assert "collect(pay) AS payments" in query
    assert "delivery_late" in query
    assert "reduce(total = 0.0" in query


def test_customer_reads_are_ownership_scoped():
    for query in (
        cypher_templates.GET_CUSTOMER_ORDERS,
        cypher_templates.GET_ORDER_FOR_CUSTOMER,
        cypher_templates.GET_CUSTOMER_TICKETS,
        cypher_templates.GET_CUSTOMER_REQUESTS,
    ):
        assert "Customer {customer_id: $customer_id}" in query
