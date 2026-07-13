"""
generate_support_layer.py — Phase 1, step 3.

Updated for the new dataset schema:
  - uses customer_id  (not customer_unique_id)
  - orders columns: order_status, order_purchase_date,
                    estimated_delivery_date, delivered_date
  - payments columns: payment_method, payment_status,
                      payment_amount, payment_date

Generates tickets, service_requests, and payment_issues
from real signals in the data (cancellations, late deliveries,
payment anomalies) consistent with business_rules.yaml.

Run:
    python scripts/generate_support_layer.py
"""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

import pandas as pd
import yaml


def _load_rules(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def _parse_dt(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, errors="coerce")


def _iso(ts) -> str | None:
    if pd.isna(ts):
        return None
    return pd.Timestamp(ts).date().isoformat()


def generate(
    processed: Path,
    rules_path: Path,
    out: Path,
    seed: int,
) -> None:
    rng = random.Random(seed)
    rules = _load_rules(rules_path)
    statuses       = rules["statuses"]
    return_window  = rules["return"]["window_days"]
    refund_window  = rules["refund"]["window_days"]
    warranty_days  = rules["warranty"]["period_months"] * 30

    # ── load ──────────────────────────────────────────────
    customers = pd.read_csv(processed / "olist_customers_dataset.csv")
    orders    = pd.read_csv(processed / "olist_orders_dataset.csv")
    payments  = pd.read_csv(processed / "olist_order_payments_dataset.csv")

    # build customer_id → customer_id map (trivial here, kept for symmetry)
    cust_ids = set(customers["customer_id"])

    orders = orders.copy()
    orders["delivered"] = _parse_dt(orders["delivered_date"])
    orders["estimated"] = _parse_dt(orders["estimated_delivery_date"])
    orders["purchase"]  = _parse_dt(orders["order_purchase_date"])

    tickets: list[dict]          = []
    service_requests: list[dict] = []
    payment_issues: list[dict]   = []
    t_seq = sr_seq = pi_seq = 0

    def next_id(prefix: str, n: int) -> str:
        return f"{prefix}-{n:05d}"

    def pick_status(bias_resolved: bool = True) -> str:
        weights = (
            [0.10, 0.12, 0.18, 0.45, 0.15]
            if bias_resolved
            else [0.30, 0.25, 0.20, 0.15, 0.10]
        )
        return rng.choices(statuses, weights=weights, k=1)[0]

    # payment lookup: orders paid via bank_slip or split
    pay_methods = payments.groupby("order_id")["payment_method"].apply(set)

    # ── iterate orders ─────────────────────────────────────
    for _, o in orders.iterrows():
        oid         = o["order_id"]
        cid         = o["customer_id"]
        status_val  = str(o["order_status"])
        delivered   = o["delivered"]
        estimated   = o["estimated"]
        purchase    = o["purchase"]

        if cid not in cust_ids:
            continue

        created_date = _iso(purchase)

        # ── canceled / unavailable → ticket ─────────────
        if status_val in ("canceled", "unavailable"):
            t_seq += 1
            tickets.append({
                "ticket_id":   next_id("TCK", t_seq),
                "customer_id": cid,
                "order_id":    oid,
                "category":    "cancellation" if status_val == "canceled" else "order_issue",
                "subject":     f"Order {status_val}",
                "status":      pick_status(),
                "created_at":  created_date,
            })
            # refund request 50 % of the time for canceled
            if status_val == "canceled" and rng.random() < 0.5:
                sr_seq += 1
                service_requests.append({
                    "request_id":  next_id("SR", sr_seq),
                    "customer_id": cid,
                    "order_id":    oid,
                    "type":        "refund",
                    "reason":      "order_canceled",
                    "status":      pick_status(),
                    "evidence":    None,
                    "created_at":  created_date,
                    "resolved_at": None,
                })

        # ── late delivery → order_tracking ticket ─────────
        if (
            pd.notna(delivered)
            and pd.notna(estimated)
            and delivered > estimated
        ):
            t_seq += 1
            tickets.append({
                "ticket_id":   next_id("TCK", t_seq),
                "customer_id": cid,
                "order_id":    oid,
                "category":    "order_tracking",
                "subject":     "Delivery arrived late",
                "status":      pick_status(),
                "created_at":  _iso(delivered),
            })

        # ── delivered orders → random service request ─────
        if status_val == "delivered" and pd.notna(delivered) and rng.random() < 0.50:
            roll = rng.random()
            if roll < 0.40:
                rtype, offset = "return",      rng.randint(1, return_window)
            elif roll < 0.65:
                rtype, offset = "refund",      rng.randint(1, refund_window)
            elif roll < 0.85:
                rtype, offset = "replacement", rng.randint(1, return_window)
            else:
                rtype, offset = "warranty",    rng.randint(
                    return_window + 1,
                    min(warranty_days, 300),
                )

            created_ts = pd.Timestamp(delivered) + pd.Timedelta(days=offset)
            st         = pick_status()
            resolved   = None
            if st in ("resolved", "approved", "rejected"):
                resolved = _iso(
                    created_ts + pd.Timedelta(days=rng.randint(1, 10))
                )

            needs_proof = rtype in ("refund", "replacement", "warranty")
            evidence    = None
            if needs_proof:
                evidence = (
                    "photo_provided"
                    if st != "pending_proof"
                    else "awaiting_photo"
                )

            reason = {
                "return":      "wrong_size",
                "refund":      "damaged_on_arrival",
                "replacement": "defective_item",
                "warranty":    "defect_after_use",
            }[rtype]

            sr_seq += 1
            service_requests.append({
                "request_id":  next_id("SR", sr_seq),
                "customer_id": cid,
                "order_id":    oid,
                "type":        rtype,
                "reason":      reason,
                "status":      st,
                "evidence":    evidence,
                "created_at":  _iso(created_ts),
                "resolved_at": resolved,
            })

        # ── payment issue ────────────────────────────────
        methods = pay_methods.get(oid, set())
        is_bank_slip = any(
            "bank" in m.lower() or "slip" in m.lower() or "boleto" in m.lower()
            for m in methods
        )
        if is_bank_slip and rng.random() < 0.40:
            pi_seq += 1
            payment_issues.append({
                "issue_id":    next_id("PI", pi_seq),
                "customer_id": cid,
                "order_id":    oid,
                "issue_type":  "bank_slip_not_confirmed",
                "status":      pick_status(bias_resolved=False),
                "created_at":  created_date,
            })

    # ── write outputs ──────────────────────────────────────
    out.mkdir(parents=True, exist_ok=True)
    (out / "tickets.json").write_text(
        json.dumps(tickets, indent=2), encoding="utf-8"
    )
    (out / "service_requests.json").write_text(
        json.dumps(service_requests, indent=2), encoding="utf-8"
    )
    (out / "payment_issues.json").write_text(
        json.dumps(payment_issues, indent=2), encoding="utf-8"
    )

    print(f"tickets:          {len(tickets):,}")
    print(f"service_requests: {len(service_requests):,}")
    print(f"payment_issues:   {len(payment_issues):,}")
    print("generate_support_layer: done.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--processed", type=Path, default=Path("data/processed")
    )
    parser.add_argument(
        "--rules", type=Path, default=Path("business_rules.yaml")
    )
    parser.add_argument(
        "--out", type=Path, default=Path("data/seed")
    )
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    generate(args.processed, args.rules, args.out, args.seed)


if __name__ == "__main__":
    main()
