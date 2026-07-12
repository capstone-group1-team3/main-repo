from datetime import date, timedelta
from pathlib import Path
import os
import re
import sys

import yaml

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
from app.agents.action.action_evaluator import evaluate_eligibility
from app.agents.action.create_refund_request import _processing_days

ROOT = Path(__file__).resolve().parents[1]
RULES = yaml.safe_load((ROOT / "business_rules.yaml").read_text(encoding="utf-8"))


def order(days: int | None, status: str = "delivered"):
    return {
        "order_id": "TEST-ORDER", "status": status, "payment_value": 10,
        "delivered_date": None if days is None else (date.today() - timedelta(days=days)).isoformat(),
    }


def test_refund_boundary_and_missing_date_fail_closed():
    window = RULES["refund"]["window_days"]
    assert evaluate_eligibility("refund_request", order(window - 1), {}, RULES).eligible
    assert evaluate_eligibility("refund_request", order(window), {}, RULES).eligible
    assert not evaluate_eligibility("refund_request", order(window + 1), {}, RULES).eligible
    assert not evaluate_eligibility("refund_request", order(None), {}, RULES).eligible


def test_replacement_requires_defect_and_window():
    assert evaluate_eligibility("replacement_request", order(1), {"issue": "defective"}, RULES).eligible
    assert not evaluate_eligibility("replacement_request", order(1), {"issue": "changed_mind"}, RULES).eligible
    assert not evaluate_eligibility("replacement_request", order(RULES["replacement"]["window_days"] + 1), {"issue": "defective"}, RULES).eligible


def test_warranty_exclusions_and_boundary():
    boundary = RULES["warranty"]["period_months"] * 30
    assert evaluate_eligibility("warranty_claim", order(boundary), {"issue": "defective"}, RULES).eligible
    assert not evaluate_eligibility("warranty_claim", order(boundary + 1), {"issue": "defective"}, RULES).eligible
    for issue in RULES["warranty"]["excludes"]:
        assert not evaluate_eligibility("warranty_claim", order(20), {"issue": issue}, RULES).eligible


def test_cancellation_statuses():
    assert evaluate_eligibility("cancel_order", order(None, "approved"), {}, RULES).eligible
    for status in ("shipped", "delivered", "canceled"):
        assert not evaluate_eligibility("cancel_order", order(None, status), {}, RULES).eligible


def test_refund_processing_by_payment_method():
    refund = RULES["refund"]
    assert _processing_days("Credit Card", refund) == refund["processing_days_card"]
    assert _processing_days("Bank Slip", refund) == refund["processing_days_bank_slip"]
    assert _processing_days("Voucher", refund) == refund["processing_days_voucher"]


def test_policy_numbers_match_yaml():
    refund = (ROOT / "data/policies/refund_policy.md").read_text(encoding="utf-8")
    returns = (ROOT / "data/policies/return_policy.md").read_text(encoding="utf-8")
    warranty = (ROOT / "data/policies/warranty_policy.md").read_text(encoding="utf-8")
    assert f"**{RULES['refund']['window_days']} days**" in refund
    assert f"**{RULES['return']['window_days']} days**" in returns
    assert f"**{RULES['warranty']['period_months']}-month**" in warranty
