"""
build_neo4j_graph.py — Phase 2 loader.

Loads the custom dataset and then repairs/creates the graph relationships so
the graph is connected consistently:

    Account -[:BELONGS_TO]-> Customer -[:PLACED]-> Order
    Order   -[:CONTAINS]-> Product -[:BELONGS_TO]-> Category
    Order   -[:PAID_WITH]-> Payment
    Order   -[:SHIPPED_AS]-> Shipment
    Customer-[:HAS_TICKET]-> Ticket
    Order   -[:ABOUT]-> Ticket
    Customer-[:HAS_REQUEST]-> ServiceRequest
    Order   -[:HAS_REQUEST]-> ServiceRequest
    Order   -[:HAS_ISSUE]-> PaymentIssue

Run:
    python scripts/build_neo4j_graph.py --with-schema
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.graph.neo4j_client import Neo4jClient
from app.graph import cypher_templates as T


def _text(value: Any) -> str | None:
    """Return a clean string, or None for empty/NaN values."""
    if pd.isna(value):
        return None
    value = str(value).strip()
    return value or None


def _number(value: Any, default: float = 0.0) -> float:
    """Convert a value to float without propagating NaN."""
    parsed = pd.to_numeric(value, errors="coerce")
    return default if pd.isna(parsed) else float(parsed)


def _integer(value: Any, default: int = 0) -> int:
    """Convert a value to int without propagating NaN."""
    parsed = pd.to_numeric(value, errors="coerce")
    return default if pd.isna(parsed) else int(parsed)


def _date(value: Any) -> str | None:
    """Convert a value to an ISO date string."""
    if pd.isna(value):
        return None
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        return None
    return parsed.date().isoformat()


def prep_customers(processed: Path) -> list[dict]:
    df = pd.read_csv(processed / "olist_customers_dataset.csv")
    return [
        {
            "customer_id": _text(row["customer_id"]),
            "customer_name": _text(row["customer_name"]),
            "customer_email": _text(row["customer_email"]),
            "customer_password_hash": _text(row["customer_password_hash"]),
        }
        for _, row in df.iterrows()
        if _text(row["customer_id"])
    ]


def prep_orders(processed: Path) -> list[dict]:
    df = pd.read_csv(processed / "olist_orders_dataset.csv")
    return [
        {
            "order_id": _text(row["order_id"]),
            "customer_id": _text(row["customer_id"]),
            "status": _text(row["order_status"]),
            "order_purchase_date": _date(row["order_purchase_date"]),
            "estimated_delivery_date": _date(row["estimated_delivery_date"]),
            "delivered_date": _date(row["delivered_date"]),
        }
        for _, row in df.iterrows()
        if _text(row["order_id"])
    ]


def prep_products(processed: Path) -> list[dict]:
    df = pd.read_csv(processed / "olist_products_dataset.csv")
    return [
        {
            "product_id": _text(row["product_id"]),
            "product_name": _text(row["product_name"]),
            "category": _text(row["product_category"]),
            "price": _number(row["price"]),
        }
        for _, row in df.iterrows()
        if _text(row["product_id"])
    ]


def prep_order_items(processed: Path) -> list[dict]:
    df = pd.read_csv(processed / "olist_order_items_dataset.csv")
    return [
        {
            "order_id": _text(row["order_id"]),
            "product_id": _text(row["product_id"]),
            "quantity": _integer(row["quantity"], default=1),
            "unit_price": _number(row["unit_price"]),
            "freight_value": _number(row["shipping_cost"]),
        }
        for _, row in df.iterrows()
        if _text(row["order_id"]) and _text(row["product_id"])
    ]


def prep_payments(processed: Path) -> list[dict]:
    df = pd.read_csv(processed / "olist_order_payments_dataset.csv")
    return [
        {
            "payment_id": _text(row["payment_id"]),
            "order_id": _text(row["order_id"]),
            "payment_type": _text(row["payment_method"]),
            "payment_status": _text(row["payment_status"]),
            "payment_value": _number(row["payment_amount"]),
            "payment_date": _date(row["payment_date"])
            if "payment_date" in df.columns
            else None,
            "installments": 1,
        }
        for _, row in df.iterrows()
        if _text(row["payment_id"]) and _text(row["order_id"])
    ]


def _load_json(seed: Path, filename: str) -> list[dict]:
    path = seed / filename
    if not path.exists():
        print(f"  (skip) {filename} not found")
        return []

    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"{path} must contain a JSON array.")
    return data


def _cypher_statements(text: str) -> list[str]:
    """
    Remove full-line // comments before splitting Cypher statements.

    The old implementation could skip a valid statement when the same block
    started with a documentation comment.
    """
    uncommented_lines = [
        line for line in text.splitlines()
        if not line.lstrip().startswith("//")
    ]
    return [
        statement.strip()
        for statement in "\n".join(uncommented_lines).split(";")
        if statement.strip()
    ]


def apply_schema(client: Neo4jClient, neo4j_dir: Path) -> None:
    for filename in ("constraints.cypher", "indexes.cypher"):
        path = neo4j_dir / filename
        if not path.exists():
            print(f"  (skip) {filename} not found")
            continue

        for statement in _cypher_statements(path.read_text(encoding="utf-8")):
            client.write(statement)

        print(f"  applied {filename}")


RELATIONSHIP_REPAIR_QUERIES: tuple[tuple[str, str], ...] = (
    (
        "accounts -> customers",
        """
        MATCH (c:Customer)
        WHERE c.customer_email IS NOT NULL
          AND trim(toString(c.customer_email)) <> ""
        WITH c, toLower(trim(toString(c.customer_email))) AS normalized_email
        MERGE (a:Account {email: normalized_email})
        SET a.password_hash = coalesce(
                c.customer_password_hash,
                a.password_hash
            ),
            a.role = coalesce(a.role, "customer")
        MERGE (a)-[:BELONGS_TO]->(c)
        """,
    ),
    (
        "customers -> orders",
        """
        MATCH (c:Customer), (o:Order)
        WHERE c.customer_id IS NOT NULL
          AND o.customer_id IS NOT NULL
          AND toString(c.customer_id) = toString(o.customer_id)
        MERGE (c)-[:PLACED]->(o)
        """,
    ),
    (
        "products -> categories",
        """
        MATCH (p:Product)
        WHERE coalesce(p.category, p.product_category) IS NOT NULL
          AND trim(toString(coalesce(p.category, p.product_category))) <> ""
        WITH p, trim(toString(coalesce(p.category, p.product_category))) AS category_name
        MERGE (category:Category {name: category_name})
        MERGE (p)-[:BELONGS_TO]->(category)
        """,
    ),
    (
        "orders -> payments",
        """
        MATCH (o:Order), (p:Payment)
        WHERE o.order_id IS NOT NULL
          AND p.order_id IS NOT NULL
          AND toString(o.order_id) = toString(p.order_id)
        MERGE (o)-[r:PAID_WITH]->(p)
        SET r.installments = coalesce(p.installments, r.installments, 1),
            r.value = coalesce(p.payment_value, p.value, r.value),
            r.sequential = coalesce(p.sequential, r.sequential)
        """,
    ),
    (
        "orders -> shipments",
        """
        MATCH (o:Order)
        WHERE o.order_id IS NOT NULL
        MERGE (s:Shipment {order_id: o.order_id})
        SET s.delivered_customer_date = coalesce(
                o.delivered_date,
                o.delivered_customer_date
            ),
            s.estimated_delivery_date = o.estimated_delivery_date,
            s.late =
                CASE
                    WHEN coalesce(o.delivered_date, o.delivered_customer_date) IS NULL
                      OR o.estimated_delivery_date IS NULL
                    THEN false
                    ELSE date(toString(coalesce(
                        o.delivered_date,
                        o.delivered_customer_date
                    ))) > date(toString(o.estimated_delivery_date))
                END
        MERGE (o)-[:SHIPPED_AS]->(s)
        """,
    ),
    (
        "customers -> tickets",
        """
        MATCH (t:Ticket), (c:Customer)
        WHERE t.customer_id IS NOT NULL
          AND c.customer_id IS NOT NULL
          AND toString(t.customer_id) = toString(c.customer_id)
        MERGE (c)-[:HAS_TICKET]->(t)
        """,
    ),
    (
        "orders -> tickets",
        """
        MATCH (t:Ticket), (o:Order)
        WHERE t.order_id IS NOT NULL
          AND o.order_id IS NOT NULL
          AND toString(t.order_id) = toString(o.order_id)
        MERGE (o)-[:ABOUT]->(t)
        """,
    ),
    (
        "customers -> service requests",
        """
        MATCH (request:ServiceRequest), (c:Customer)
        WHERE request.customer_id IS NOT NULL
          AND c.customer_id IS NOT NULL
          AND toString(request.customer_id) = toString(c.customer_id)
        MERGE (c)-[:HAS_REQUEST]->(request)
        """,
    ),
    (
        "orders -> service requests",
        """
        MATCH (request:ServiceRequest), (o:Order)
        WHERE request.order_id IS NOT NULL
          AND o.order_id IS NOT NULL
          AND toString(request.order_id) = toString(o.order_id)
        MERGE (o)-[:HAS_REQUEST]->(request)
        """,
    ),
    (
        "orders -> payment issues",
        """
        MATCH (issue:PaymentIssue), (o:Order)
        WHERE issue.order_id IS NOT NULL
          AND o.order_id IS NOT NULL
          AND toString(issue.order_id) = toString(o.order_id)
        MERGE (o)-[:HAS_ISSUE]->(issue)
        """,
    ),
)


def repair_graph_relationships(client: Neo4jClient) -> None:
    """
    Create any missing relationships after all nodes have been loaded.

    MERGE makes this step safe to run repeatedly.
    """
    print("repairing graph relationships...")
    for label, query in RELATIONSHIP_REPAIR_QUERIES:
        client.write(query)
        print(f"  linked {label}")


VALIDATION_QUERY = """
MATCH (n)
WITH count(n) AS total_nodes
CALL {
    MATCH ()-[r]->()
    RETURN count(r) AS total_relationships
}
CALL {
    MATCH (a:Account)-[:BELONGS_TO]->(c:Customer)
    RETURN count(*) AS account_customer_links
}
CALL {
    MATCH (c:Customer)-[:PLACED]->(o:Order)
    RETURN count(*) AS customer_order_links
}
CALL {
    MATCH (o:Order)-[:CONTAINS]->(p:Product)
    RETURN count(*) AS order_product_links
}
CALL {
    MATCH (o:Order)-[:PAID_WITH]->(p:Payment)
    RETURN count(*) AS order_payment_links
}
RETURN
    total_nodes,
    total_relationships,
    account_customer_links,
    customer_order_links,
    order_product_links,
    order_payment_links
"""


def validate_graph(client: Neo4jClient) -> None:
    print("validating graph...")
    result = client.write(VALIDATION_QUERY)
    print("  ", result)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--processed",
        type=Path,
        default=Path("data/processed"),
    )
    parser.add_argument(
        "--seed",
        type=Path,
        default=Path("data/seed"),
    )
    parser.add_argument(
        "--neo4j-dir",
        type=Path,
        default=Path("neo4j"),
    )
    parser.add_argument(
        "--with-schema",
        action="store_true",
    )
    parser.add_argument(
        "--skip-repair",
        action="store_true",
        help="Skip the post-load relationship repair step.",
    )
    args = parser.parse_args()

    client = Neo4jClient()

    try:
        client.verify()
        print("connected to Neo4j.")

        if args.with_schema:
            apply_schema(client, args.neo4j_dir)

        print("loading customers...")
        print("  ", client.run_batch(
            T.LOAD_CUSTOMERS,
            prep_customers(args.processed),
        ))

        print("loading orders...")
        print("  ", client.run_batch(
            T.LOAD_ORDERS,
            prep_orders(args.processed),
        ))

        print("loading products...")
        print("  ", client.run_batch(
            T.LOAD_PRODUCTS,
            prep_products(args.processed),
        ))

        print("loading order items...")
        print("  ", client.run_batch(
            T.LOAD_ORDER_ITEMS,
            prep_order_items(args.processed),
        ))

        print("loading payments...")
        print("  ", client.run_batch(
            T.LOAD_PAYMENTS,
            prep_payments(args.processed),
        ))

        print("loading tickets...")
        print("  ", client.run_batch(
            T.LOAD_TICKETS,
            _load_json(args.seed, "tickets.json"),
        ))

        print("loading service requests...")
        print("  ", client.run_batch(
            T.LOAD_SERVICE_REQUESTS,
            _load_json(args.seed, "service_requests.json"),
        ))

        print("loading payment issues...")
        print("  ", client.run_batch(
            T.LOAD_PAYMENT_ISSUES,
            _load_json(args.seed, "payment_issues.json"),
        ))

        if not args.skip_repair:
            repair_graph_relationships(client)

        validate_graph(client)

    finally:
        client.close()

    print("\n======================================")
    print("Neo4j graph built successfully.")
    print("======================================")


if __name__ == "__main__":
    main()