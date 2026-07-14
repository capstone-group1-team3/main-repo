"""Seed deterministic records, but only inside an explicitly isolated stack."""

from __future__ import annotations

import os
import sys
from datetime import date, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.graph.neo4j_client import Neo4jClient  # noqa: E402
from build_neo4j_graph import apply_schema  # noqa: E402


CUSTOMERS = [
    {"customer_id": "EVAL-CUSTOMER-A", "name": "Evaluation Customer A", "email": "eval-a@example.com"},
    {"customer_id": "EVAL-CUSTOMER-B", "name": "Evaluation Customer B", "email": "eval-b@example.com"},
]


def _order(order_id: str, customer_id: str, status: str, delivered_days: int | None) -> dict:
    today = date.today()
    delivered = None if delivered_days is None else (today - timedelta(days=delivered_days)).isoformat()
    return {
        "order_id": order_id,
        "customer_id": customer_id,
        "status": status,
        "purchase_date": (today - timedelta(days=(delivered_days or 0) + 7)).isoformat(),
        "delivered_date": delivered,
        "estimated_date": (today - timedelta(days=max((delivered_days or 0) - 1, 0))).isoformat(),
        "payment_id": f"PAY-{order_id}",
        "shipment_id": f"SHIP-{order_id}",
        "value": 125.50,
    }


ORDERS = [
    _order("EVAL1001", "EVAL-CUSTOMER-A", "delivered", 5),
    _order("EVAL1002", "EVAL-CUSTOMER-A", "delivered", 10),
    _order("EVAL1003", "EVAL-CUSTOMER-A", "delivered", 5),
    _order("EVAL1004", "EVAL-CUSTOMER-A", "delivered", 60),
    _order("EVAL1005", "EVAL-CUSTOMER-A", "created", None),
    _order("EVAL1006", "EVAL-CUSTOMER-A", "approved", None),
    _order("EVAL1007", "EVAL-CUSTOMER-A", "delivered", 45),
    _order("EVAL1008", "EVAL-CUSTOMER-A", "shipped", None),
    _order("EVAL2001", "EVAL-CUSTOMER-B", "created", None),
]


def main() -> None:
    if os.getenv("FUSIONMIND_EVAL_ISOLATED", "").lower() != "true":
        raise SystemExit("Refusing to seed: FUSIONMIND_EVAL_ISOLATED=true is required")

    with Neo4jClient() as client:
        client.verify()
        apply_schema(client, ROOT / "neo4j")
        # Action-created records intentionally use the production schema and
        # therefore do not carry an evaluation marker.  This script can remove
        # them safely only because the isolation gate above is mandatory and
        # the evaluation stack has its own Neo4j volume.
        client.write(
            "MATCH (n) WHERE n:ServiceRequest OR n:Ticket OR n:PaymentIssue DETACH DELETE n",
            query_type="eval_cleanup_action_records",
        )
        client.write(
            "MATCH (a:Account)-[:BELONGS_TO]->(c:Customer) "
            "WHERE c.customer_id STARTS WITH 'EVAL-' DETACH DELETE a",
            query_type="eval_cleanup_accounts",
        )
        client.write(
            "MATCH (n) WHERE n.evaluation_record = true DETACH DELETE n",
            query_type="eval_cleanup_records",
        )
        client.write(
            "UNWIND $rows AS row "
            "CREATE (c:Customer {customer_id: row.customer_id, customer_name: row.name, "
            "customer_email: row.email, evaluation_record: true})",
            rows=CUSTOMERS,
            query_type="eval_seed_customers",
        )
        client.write(
            "CREATE (:Category {name: 'evaluation', evaluation_record: true})",
            query_type="eval_seed_category",
        )
        client.write(
            "UNWIND $rows AS row "
            "MATCH (c:Customer {customer_id: row.customer_id}), (cat:Category {name: 'evaluation'}) "
            "CREATE (o:Order {order_id: row.order_id, status: row.status, "
            "order_purchase_date: date(row.purchase_date), delivered_date: CASE WHEN row.delivered_date IS NULL THEN NULL ELSE date(row.delivered_date) END, "
            "estimated_delivery_date: date(row.estimated_date), evaluation_record: true}) "
            "CREATE (p:Product {product_id: 'PROD-' + row.order_id, product_name: 'Evaluation product', evaluation_record: true}) "
            "CREATE (pay:Payment {payment_id: row.payment_id, payment_type: 'credit_card', payment_value: row.value, installments: 1, evaluation_record: true}) "
            "CREATE (s:Shipment {order_id: row.order_id, shipment_id: row.shipment_id, late: false, evaluation_record: true}) "
            "CREATE (c)-[:PLACED]->(o) "
            "CREATE (o)-[:CONTAINS {quantity: 1, unit_price: row.value}]->(p) "
            "CREATE (p)-[:BELONGS_TO]->(cat) "
            "CREATE (o)-[:PAID_WITH]->(pay) "
            "CREATE (o)-[:SHIPPED_AS]->(s)",
            rows=ORDERS,
            query_type="eval_seed_orders",
        )
        client.write(
            "MATCH (c:Customer {customer_id: 'EVAL-CUSTOMER-A'}), "
            "(o:Order {order_id: 'EVAL1006'}) "
            "CREATE (t:Ticket {ticket_id: 'EVAL-TICKET-1', category: 'payment_issue', "
            "subject: 'Controlled evaluation ticket', status: 'open', created_at: date(), evaluation_record: true}) "
            "CREATE (c)-[:HAS_TICKET]->(t) CREATE (o)-[:ABOUT]->(t)",
            query_type="eval_seed_ticket",
        )
        counts = client.read(
            "MATCH (n) WHERE n.evaluation_record = true "
            "RETURN count(n) AS nodes",
            query_type="eval_seed_counts",
        )
    print(f"Seeded isolated evaluation records: nodes={counts[0]['nodes']}")


if __name__ == "__main__":
    main()
