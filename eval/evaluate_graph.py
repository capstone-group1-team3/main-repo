"""Read-only graph-integrity checks. No records are created or changed."""
from __future__ import annotations

from typing import Any

REQUIRED_CONSTRAINTS = {
    ("Customer", "customer_id"), ("Account", "email"), ("Order", "order_id"),
    ("Product", "product_id"), ("Category", "name"), ("Payment", "payment_id"),
    ("Shipment", "order_id"), ("Ticket", "ticket_id"),
    ("ServiceRequest", "request_id"), ("PaymentIssue", "issue_id"),
}

COUNT_CHECKS = {
    "duplicate_customer_ids": "MATCH (n:Customer) WITH n.customer_id AS k, count(*) AS n WHERE k IS NULL OR n > 1 RETURN count(*) AS violations",
    "duplicate_order_ids": "MATCH (n:Order) WITH n.order_id AS k, count(*) AS n WHERE k IS NULL OR n > 1 RETURN count(*) AS violations",
    "orders_without_customer": "MATCH (o:Order) WHERE NOT (:Customer)-[:PLACED]->(o) RETURN count(o) AS violations",
    "tickets_without_customer": "MATCH (t:Ticket) WHERE NOT (:Customer)-[:HAS_TICKET]->(t) RETURN count(t) AS violations",
    "requests_without_customer": "MATCH (r:ServiceRequest) WHERE NOT (:Customer)-[:HAS_REQUEST]->(r) RETURN count(r) AS violations",
    "requests_without_order": "MATCH (r:ServiceRequest) WHERE NOT (:Order)-[:HAS_REQUEST]->(r) RETURN count(r) AS violations",
    "payment_issues_without_order": "MATCH (i:PaymentIssue) WHERE NOT (:Order)-[:HAS_ISSUE]->(i) RETURN count(i) AS violations",
    "duplicate_relationship_groups": "MATCH (a)-[r]->(b) WITH elementId(a) AS a, type(r) AS t, elementId(b) AS b, count(*) AS n WHERE n > 1 RETURN count(*) AS violations",
}


def evaluate(client: Any) -> dict[str, Any]:
    checks = []
    rows = client.read(
        "SHOW CONSTRAINTS YIELD labelsOrTypes, properties "
        "RETURN labelsOrTypes, properties",
        query_type="eval_constraints",
    )
    existing = {
        (str(row["labelsOrTypes"][0]), str(row["properties"][0]))
        for row in rows if row.get("labelsOrTypes") and row.get("properties")
    }
    missing = sorted(REQUIRED_CONSTRAINTS - existing)
    checks.append({"name": "required_constraints", "pass": not missing, "missing": missing})
    for name, query in COUNT_CHECKS.items():
        rows = client.read(query, query_type=f"eval_{name}"[:48])
        violations = int(rows[0]["violations"]) if rows else -1
        checks.append({"name": name, "pass": violations == 0, "violations": violations})
    passed = sum(c["pass"] for c in checks)
    return {
        "status": "pass" if passed == len(checks) else "fail",
        "pass_rate": passed / len(checks) if checks else None, "checks": checks,
    }
