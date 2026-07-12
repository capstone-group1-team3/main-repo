"""Convert the cleaned Olist data to FusionMind's simplified processed schema."""
from __future__ import annotations

import argparse
import json
import shutil
from datetime import date
from pathlib import Path

import pandas as pd


FILES = {
    "customers": "olist_customers_dataset.csv",
    "orders": "olist_orders_dataset.csv",
    "items": "olist_order_items_dataset.csv",
    "payments": "olist_order_payments_dataset.csv",
    "products": "olist_products_dataset.csv",
}

DEFAULT_PASSWORD_HASH = (
    "$2b$12$LQlmghUk8/7dE7QQkxN4D.FrGTfVdcQOW8qvepQy23bhMK4pvag2y"
)

PAYMENT_METHODS = {
    "credit_card": "Credit Card",
    "debit_card": "Debit Card",
    "bank_slip": "Bank Slip",
    "boleto": "Bank Slip",
    "voucher": "Voucher",
    "not_defined": "Unknown",
}

FEATURED_CUSTOMERS = [
    ("Mohammed Al-Shaikh", "mohammed@example.com"),
    ("Marwan Al-Masarat", "marwan@example.com"),
    ("Jineen Hourani", "jineen@example.com"),
    ("Rand Awad", "rand@example.com"),
    ("Diala Abdalqader", "diala@example.com"),
]


def _id_map(values: pd.Series, prefix: str, width: int) -> dict[str, str]:
    unique = pd.unique(values.dropna().astype(str))
    return {old: f"{prefix}{idx:0{width}d}" for idx, old in enumerate(unique, 1)}


def _date(series: pd.Series, shift_days: int = 0) -> pd.Series:
    parsed = pd.to_datetime(series, errors="coerce")
    if shift_days:
        parsed = parsed + pd.Timedelta(days=shift_days)
    return parsed.dt.strftime("%Y-%m-%d")


def prepare(
    source: Path,
    output: Path,
    package: Path | None = None,
    anchor_date: date | None = None,
) -> dict:
    raw = {key: pd.read_csv(source / name) for key, name in FILES.items()}
    customers = raw["customers"]
    orders = raw["orders"]
    items = raw["items"]
    payments = raw["payments"]
    products = raw["products"]

    # Preserve every real interval while moving the historical Olist timeline
    # into the current demo period. The latest date across the full order
    # lifecycle becomes anchor_date, so generated data never lies in the future.
    anchor_date = anchor_date or date.today()
    lifecycle_columns = [
        "order_purchase_timestamp",
        "order_approved_at",
        "order_delivered_carrier_date",
        "order_delivered_customer_date",
        "order_estimated_delivery_date",
    ]
    latest_source_date = max(
        pd.to_datetime(orders[column], errors="coerce").max()
        for column in lifecycle_columns
    ).date()
    shift_days = (anchor_date - latest_source_date).days

    customer_map = _id_map(customers["customer_unique_id"], "CUST", 5)
    order_map = _id_map(orders["order_id"], "ORD", 6)
    product_map = _id_map(products["product_id"], "PROD", 5)

    original_customer_to_person = dict(
        zip(customers["customer_id"].astype(str), customers["customer_unique_id"].astype(str))
    )
    original_customer_to_new = {
        old: customer_map[person] for old, person in original_customer_to_person.items()
    }

    # One Customer row per real person. Names/emails are deterministic demo identities.
    people = customers.drop_duplicates("customer_unique_id", keep="first").copy()
    people["customer_id"] = people["customer_unique_id"].astype(str).map(customer_map)
    people["customer_name"] = people["customer_id"].map(lambda x: f"Customer {x[4:]}")
    people["customer_email"] = people["customer_id"].map(
        lambda x: f"{x.lower()}@example.com"
    )
    customers_out = people[
        ["customer_id", "customer_name", "customer_email"]
    ].copy()
    customers_out["customer_password_hash"] = DEFAULT_PASSWORD_HASH
    for index, (name, email) in enumerate(FEATURED_CUSTOMERS):
        customers_out.loc[index, "customer_name"] = name
        customers_out.loc[index, "customer_email"] = email

    orders_out = pd.DataFrame({
        "order_id": orders["order_id"].astype(str).map(order_map),
        "customer_id": orders["customer_id"].astype(str).map(original_customer_to_new),
        "order_status": orders["order_status"].astype(str).str.lower(),
        "order_purchase_date": _date(orders["order_purchase_timestamp"], shift_days),
        "estimated_delivery_date": _date(orders["order_estimated_delivery_date"], shift_days),
        "delivered_date": _date(orders["order_delivered_customer_date"], shift_days),
    })

    item_work = items.assign(
        order_id=items["order_id"].astype(str).map(order_map),
        product_id=items["product_id"].astype(str).map(product_map),
        price=pd.to_numeric(items["price"], errors="coerce").fillna(0.0),
        freight_value=pd.to_numeric(items["freight_value"], errors="coerce").fillna(0.0),
    )
    items_out = (
        item_work.groupby(["order_id", "product_id"], sort=False, as_index=False)
        .agg(quantity=("order_item_id", "count"), unit_price=("price", "mean"),
             shipping_cost=("freight_value", "sum"))
    )
    items_out["unit_price"] = items_out["unit_price"].round(2)
    items_out["shipping_cost"] = items_out["shipping_cost"].round(2)

    product_prices = item_work.groupby("product_id")["price"].median()
    product_ids = products["product_id"].astype(str).map(product_map)
    categories = products["product_category_name"].fillna("other").astype(str)
    category_labels = categories.str.replace("_", " ", regex=False).str.title()
    products_out = pd.DataFrame({
        "product_id": product_ids,
        "product_name": [
            f"{category} Product {pid[4:]}"
            for category, pid in zip(category_labels, product_ids)
        ],
        "product_category": category_labels,
        "price": product_ids.map(product_prices).fillna(0.0).round(2),
    })

    purchase_by_order = dict(zip(
        orders["order_id"].astype(str),
        _date(orders["order_purchase_timestamp"], shift_days),
    ))
    payments_out = pd.DataFrame({
        "payment_id": [f"PAY{i:06d}" for i in range(1, len(payments) + 1)],
        "order_id": payments["order_id"].astype(str).map(order_map),
        "payment_method": payments["payment_type"].astype(str).map(
            lambda x: PAYMENT_METHODS.get(x, x.replace("_", " ").title())
        ),
        "payment_status": "Paid",
        "payment_amount": pd.to_numeric(payments["payment_value"], errors="coerce").fillna(0.0).round(2),
        "payment_date": payments["order_id"].astype(str).map(purchase_by_order),
    })

    outputs = {
        FILES["customers"]: customers_out,
        FILES["orders"]: orders_out,
        FILES["items"]: items_out,
        FILES["payments"]: payments_out,
        FILES["products"]: products_out,
    }
    output.mkdir(parents=True, exist_ok=True)
    for filename, frame in outputs.items():
        frame.to_csv(output / filename, index=False, encoding="utf-8", lineterminator="\n")

    # This mapping is useful only while auditing the conversion. It is deliberately
    # excluded from the final processed dataset because the application never uses it.
    stale_mapping = output / "customer_id_mapping.csv"
    if stale_mapping.exists():
        stale_mapping.unlink()

    report = {
        "source": str(source),
        "default_demo_password": "FusionMind@2026",
        "date_shift": {
            "source_latest_date": latest_source_date.isoformat(),
            "anchor_date": anchor_date.isoformat(),
            "shift_days": shift_days,
        },
        "rows": {filename: int(len(frame)) for filename, frame in outputs.items()},
        "unified_customer_records": int(len(customers) - len(customers_out)),
        "integrity": {
            "orders_without_customer": int((~orders_out.customer_id.isin(customers_out.customer_id)).sum()),
            "items_without_order": int((~items_out.order_id.isin(orders_out.order_id)).sum()),
            "payments_without_order": int((~payments_out.order_id.isin(orders_out.order_id)).sum()),
            "items_without_product": int((~items_out.product_id.isin(products_out.product_id)).sum()),
        },
    }
    (output / "transformation_report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )

    if package:
        package.parent.mkdir(parents=True, exist_ok=True)
        archive_base = str(package.with_suffix(""))
        made = Path(shutil.make_archive(archive_base, "zip", root_dir=output))
        if made != package:
            made.replace(package)
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("data/processed_full"))
    parser.add_argument("--package", type=Path)
    parser.add_argument(
        "--anchor-date",
        type=date.fromisoformat,
        default=date.today(),
        help="Latest date in the generated dataset (YYYY-MM-DD).",
    )
    args = parser.parse_args()
    print(json.dumps(
        prepare(args.source, args.output, args.package, args.anchor_date),
        indent=2,
    ))


if __name__ == "__main__":
    main()
