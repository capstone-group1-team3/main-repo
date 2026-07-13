"""
clean_data.py  —  Phase 1, step 1.

Takes the raw Olist CSVs and produces clean, English-only, scope-trimmed CSVs:
  - product categories translated to English via the official Olist file
  - payment_type value  boleto -> bank_slip
  - geographic columns dropped from customers
  - physical product columns dropped
  - IDs kept exactly as-is (original Olist hashes)

Input : data/raw/olist_*.csv  (the 5 needed files + the translation file)
Output: data/processed/olist_*.csv  (5 cleaned files)

Run:  python scripts/clean_data.py
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

# columns we drop because they are out of scope for a support system
DROP_CUSTOMER_COLS = ["customer_zip_code_prefix", "customer_city", "customer_state"]
DROP_PRODUCT_COLS = [
    "product_name_lenght",
    "product_description_lenght",
    "product_photos_qty",
    "product_weight_g",
    "product_length_cm",
    "product_height_cm",
    "product_width_cm",
]

# payment_type normalization (only boleto is non-English)
PAYMENT_TYPE_MAP = {
    "boleto": "bank_slip",
    "credit_card": "credit_card",
    "debit_card": "debit_card",
    "voucher": "voucher",
    "not_defined": "unknown",
}

# two categories with no official English translation -> manual, faithful mapping
MANUAL_CATEGORY_MAP = {
    "pc_gamer": "pc_gamer",
    "portateis_cozinha_e_preparadores_de_alimentos": "portable_kitchen_and_food_preparators",
}


def _read(raw: Path, name: str) -> pd.DataFrame:
    path = raw / name
    if not path.exists():
        raise FileNotFoundError(
            f"Expected raw file not found: {path}\n"
            f"Download the Olist dataset from Kaggle into {raw}/ first."
        )
    return pd.read_csv(path)


def clean_customers(raw: Path) -> pd.DataFrame:
    df = _read(raw, "olist_customers_dataset.csv")
    keep = [c for c in df.columns if c not in DROP_CUSTOMER_COLS]
    return df[keep].copy()


def clean_orders(raw: Path) -> pd.DataFrame:
    # orders carry no Portuguese prose; kept as-is (status values are English)
    return _read(raw, "olist_orders_dataset.csv").copy()


def clean_order_items(raw: Path) -> pd.DataFrame:
    # seller_id / shipping_limit_date are left in the file but ignored at graph-build
    return _read(raw, "olist_order_items_dataset.csv").copy()


def clean_products(raw: Path) -> pd.DataFrame:
    df = _read(raw, "olist_products_dataset.csv")
    tr = _read(raw, "product_category_name_translation.csv")
    tmap = dict(
        zip(tr["product_category_name"], tr["product_category_name_english"])
    )
    tmap.update(MANUAL_CATEGORY_MAP)

    def translate(v):
        if pd.isna(v):
            return "other"
        return tmap.get(v, v)

    df = df.copy()
    df["product_category_name"] = df["product_category_name"].map(translate)
    keep = [c for c in df.columns if c not in DROP_PRODUCT_COLS]
    return df[keep].copy()


def clean_payments(raw: Path) -> pd.DataFrame:
    df = _read(raw, "olist_order_payments_dataset.csv").copy()
    df["payment_type"] = df["payment_type"].map(
        lambda v: PAYMENT_TYPE_MAP.get(v, v)
    )
    return df


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", type=Path, default=Path("data/raw"))
    parser.add_argument("--out", type=Path, default=Path("data/processed"))
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    outputs = {
        "olist_customers_dataset.csv": clean_customers(args.raw),
        "olist_orders_dataset.csv": clean_orders(args.raw),
        "olist_order_items_dataset.csv": clean_order_items(args.raw),
        "olist_products_dataset.csv": clean_products(args.raw),
        "olist_order_payments_dataset.csv": clean_payments(args.raw),
    }

    for name, df in outputs.items():
        dest = args.out / name
        df.to_csv(dest, index=False)
        print(f"wrote {dest}  ({len(df):,} rows, {len(df.columns)} cols)")

    print("clean_data: done.")


if __name__ == "__main__":
    main()
