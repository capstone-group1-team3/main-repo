from __future__ import annotations

import csv
from datetime import date
from pathlib import Path
from typing import Any

REQUIRED = {
    "olist_customers_dataset.csv": {"customer_id", "customer_name", "customer_email", "customer_password_hash"},
    "olist_orders_dataset.csv": {"order_id", "customer_id", "order_status", "order_purchase_date", "estimated_delivery_date", "delivered_date"},
    "olist_order_items_dataset.csv": {"order_id", "product_id", "quantity", "unit_price", "shipping_cost"},
    "olist_products_dataset.csv": {"product_id", "product_name", "product_category", "price"},
    "olist_order_payments_dataset.csv": {"payment_id", "order_id", "payment_method", "payment_status", "payment_amount", "payment_date"},
}


def _read(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def evaluate(processed: Path) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    tables: dict[str, list[dict[str, str]]] = {}
    for name, required in REQUIRED.items():
        path = processed / name
        if not path.exists():
            checks.append({"name": f"exists:{name}", "pass": False, "detail": "missing"})
            continue
        rows = _read(path); tables[name] = rows
        columns = set(rows[0]) if rows else set()
        checks.append({"name": f"columns:{name}", "pass": required <= columns, "detail": sorted(required - columns)})
    if len(tables) == len(REQUIRED):
        customers = {r["customer_id"] for r in tables["olist_customers_dataset.csv"]}
        orders = {r["order_id"] for r in tables["olist_orders_dataset.csv"]}
        products = {r["product_id"] for r in tables["olist_products_dataset.csv"]}
        checks.extend([
            {"name": "orders_without_customer", "pass": all(r["customer_id"] in customers for r in tables["olist_orders_dataset.csv"])},
            {"name": "items_without_order", "pass": all(r["order_id"] in orders for r in tables["olist_order_items_dataset.csv"])},
            {"name": "items_without_product", "pass": all(r["product_id"] in products for r in tables["olist_order_items_dataset.csv"])},
            {"name": "payments_without_order", "pass": all(r["order_id"] in orders for r in tables["olist_order_payments_dataset.csv"])},
        ])
        for name, key in (("olist_customers_dataset.csv", "customer_id"), ("olist_orders_dataset.csv", "order_id"), ("olist_products_dataset.csv", "product_id"), ("olist_order_payments_dataset.csv", "payment_id")):
            values = [r.get(key, "").strip() for r in tables[name]]
            checks.append({"name": f"unique_non_null:{name}:{key}", "pass": bool(values) and all(values) and len(values) == len(set(values))})
        required_ids = {
            "olist_orders_dataset.csv": ("order_id", "customer_id"),
            "olist_order_items_dataset.csv": ("order_id", "product_id"),
            "olist_order_payments_dataset.csv": ("payment_id", "order_id"),
            "olist_products_dataset.csv": ("product_id",),
        }
        for name, keys in required_ids.items():
            checks.append({
                "name": f"required_ids:{name}",
                "pass": all(all(str(row.get(key, "")).strip() for key in keys) for row in tables[name]),
            })
        item_pairs = [
            (r["order_id"], r["product_id"])
            for r in tables["olist_order_items_dataset.csv"]
        ]
        checks.append({"name": "duplicate_order_product_items", "pass": len(item_pairs) == len(set(item_pairs))})

        invalid_dates = delivery_before_purchase = 0
        for row in tables["olist_orders_dataset.csv"]:
            parsed = {}
            for field in ("order_purchase_date", "estimated_delivery_date", "delivered_date"):
                raw = row.get(field, "").strip()
                if not raw:
                    parsed[field] = None
                    continue
                try:
                    parsed[field] = date.fromisoformat(raw[:10])
                except ValueError:
                    parsed[field] = None; invalid_dates += 1
            if parsed["delivered_date"] and parsed["order_purchase_date"] and parsed["delivered_date"] < parsed["order_purchase_date"]:
                delivery_before_purchase += 1
        checks.append({"name": "invalid_order_dates", "pass": invalid_dates == 0, "violations": invalid_dates})
        checks.append({"name": "delivery_before_purchase", "pass": delivery_before_purchase == 0, "violations": delivery_before_purchase})
    passed = sum(bool(c["pass"]) for c in checks)
    return {"status": "pass" if passed == len(checks) else "fail", "pass_rate": passed / len(checks) if checks else None, "checks": checks}
