"""Deterministic business-rule evaluation using the YAML source of truth."""
from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from typing import Any

import yaml

from app.agents.action.action_evaluator import evaluate_eligibility
from app.agents.action.create_refund_request import _processing_days


def evaluate(path: Path) -> dict[str, Any]:
    rules = yaml.safe_load(path.read_text(encoding="utf-8"))

    def order(days: int | None, status: str = "delivered"):
        return {
            "order_id": "EVAL-ORDER", "status": status, "payment_value": 1.0,
            "delivered_date": None if days is None else (date.today() - timedelta(days=days)).isoformat(),
        }

    refund = rules["refund"]["window_days"]
    returns = rules["return"]["window_days"]
    warranty = rules["warranty"]["period_months"] * 30
    checks = [
        ("refund_inside", evaluate_eligibility("refund_request", order(refund - 1), {}, rules).eligible),
        ("refund_boundary", evaluate_eligibility("refund_request", order(refund), {}, rules).eligible),
        ("refund_outside", not evaluate_eligibility("refund_request", order(refund + 1), {}, rules).eligible),
        ("refund_missing_date", not evaluate_eligibility("refund_request", order(None), {}, rules).eligible),
        ("return_boundary", evaluate_eligibility("return_request", order(returns), {}, rules).eligible),
        ("return_outside", not evaluate_eligibility("return_request", order(returns + 1), {}, rules).eligible),
        ("replacement_defect", evaluate_eligibility("replacement_request", order(1), {"issue": "defective"}, rules).eligible),
        ("replacement_non_defect", not evaluate_eligibility("replacement_request", order(1), {"issue": "changed_mind"}, rules).eligible),
        ("warranty_boundary", evaluate_eligibility("warranty_claim", order(warranty), {"issue": "defective"}, rules).eligible),
        ("warranty_outside", not evaluate_eligibility("warranty_claim", order(warranty + 1), {"issue": "defective"}, rules).eligible),
        ("warranty_exclusion", not evaluate_eligibility("warranty_claim", order(10), {"issue": "accidental_damage"}, rules).eligible),
        ("cancel_approved", evaluate_eligibility("cancel_order", order(None, "approved"), {}, rules).eligible),
        ("cancel_shipped", not evaluate_eligibility("cancel_order", order(None, "shipped"), {}, rules).eligible),
        ("card_timing", _processing_days("Credit Card", rules["refund"]) == rules["refund"]["processing_days_card"]),
        ("bank_timing", _processing_days("Bank Slip", rules["refund"]) == rules["refund"]["processing_days_bank_slip"]),
        ("voucher_timing", _processing_days("Voucher", rules["refund"]) == rules["refund"]["processing_days_voucher"]),
    ]
    results = [{"name": name, "pass": bool(passed)} for name, passed in checks]
    passed = sum(item["pass"] for item in results)
    return {"status": "pass" if passed == len(results) else "fail", "pass_rate": passed / len(results), "checks": results}
