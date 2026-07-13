"""
halve_data.py  —  Phase 1, step 2.

Reduces the dataset to ~50% WITHOUT breaking referential integrity.

Do NOT shuffle-and-cut each file independently: that orphans orders and dangles
items. Instead sample at the PERSON level (customer_unique_id) and cascade by ID,
so every retained customer -> order -> item / payment -> product link stays intact.

Input : data/processed/olist_*.csv   (output of clean_data.py)
Output: overwrites the same 5 files in data/processed/ with the halved version
        (use --out to write elsewhere)

Run:  python scripts/halve_data.py --frac 0.5
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def halve(processed: Path, out: Path, frac: float, seed: int) -> None:
    cust = pd.read_csv(processed / "olist_customers_dataset.csv")
    orders = pd.read_csv(processed / "olist_orders_dataset.csv")
    items = pd.read_csv(processed / "olist_order_items_dataset.csv")
    prods = pd.read_csv(processed / "olist_products_dataset.csv")
    pays = pd.read_csv(processed / "olist_order_payments_dataset.csv")

    before = {
        "customers": len(cust), "orders": len(orders), "items": len(items),
        "products": len(prods), "payments": len(pays),
    }

    # 1) sample a fraction of PERSONS (deterministic via seed)
    persons = cust["customer_unique_id"].drop_duplicates()
    half = set(persons.sample(frac=frac, random_state=seed))

    # 2) cascade by IDs so every retained record stays linked
    cust_h = cust[cust["customer_unique_id"].isin(half)]
    keep_customer_ids = set(cust_h["customer_id"])
    orders_h = orders[orders["customer_id"].isin(keep_customer_ids)]
    keep_order_ids = set(orders_h["order_id"])
    items_h = items[items["order_id"].isin(keep_order_ids)]
    pays_h = pays[pays["order_id"].isin(keep_order_ids)]
    keep_product_ids = set(items_h["product_id"])
    prods_h = prods[prods["product_id"].isin(keep_product_ids)]

    # 3) integrity assertions — fail loudly if any link breaks
    assert set(orders_h["customer_id"]).issubset(keep_customer_ids)
    assert set(items_h["order_id"]).issubset(keep_order_ids)
    assert set(pays_h["order_id"]).issubset(keep_order_ids)
    assert set(items_h["product_id"]).issubset(set(prods_h["product_id"]))

    out.mkdir(parents=True, exist_ok=True)
    frames = {
        "olist_customers_dataset.csv": cust_h,
        "olist_orders_dataset.csv": orders_h,
        "olist_order_items_dataset.csv": items_h,
        "olist_products_dataset.csv": prods_h,
        "olist_order_payments_dataset.csv": pays_h,
    }
    for name, df in frames.items():
        df.to_csv(out / name, index=False)

    after = {
        "customers": len(cust_h), "orders": len(orders_h), "items": len(items_h),
        "products": len(prods_h), "payments": len(pays_h),
    }
    print("before:", before)
    print("after :", after)
    print("integrity OK — every relationship preserved.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--processed", type=Path, default=Path("data/processed"))
    parser.add_argument("--out", type=Path, default=Path("data/processed"))
    parser.add_argument("--frac", type=float, default=0.5)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    halve(args.processed, args.out, args.frac, args.seed)


if __name__ == "__main__":
    main()
