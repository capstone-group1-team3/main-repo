"""
agents/action/action_evaluator.py — Phase 1: read-only eligibility check.

PHASE 1 (this file): pure read, no side effects, no Neo4j writes.
PHASE 2 (action handlers): execute only after eligible=True + user confirmed.

Called by loop_controller AFTER graph ownership verification,
BEFORE requesting user confirmation.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any


@dataclass
class EligibilityResult:
    eligible:            bool
    action:              str
    order_id:            str | None  = None
    reason:              str | None  = None
    amount:              float | None = None
    requirements:        list[str]   = field(default_factory=list)
    order_status:        str | None  = None
    days_since_delivery: int | None  = None


def evaluate_eligibility(
    intent: str,
    order_data: dict[str, Any],
    entities: dict[str, Any],
    rules: dict[str, Any],
) -> EligibilityResult:
    fn = _EVALUATORS.get(intent)
    if fn is None:
        return EligibilityResult(eligible=True, action=intent,
                                 order_id=order_data.get("order_id"))
    return fn(order_data, entities, rules)


def _days_since(value: Any) -> int | None:
    if not value:
        return None
    try:
        if isinstance(value, datetime):
            delivered = value.date()
        elif isinstance(value, date):
            delivered = value
        else:
            # Neo4j returns neo4j.time.Date. Its ISO string representation is
            # stable, but it is not an instance of datetime.date.
            delivered = date.fromisoformat(str(value)[:10])
        return (date.today() - delivered).days
    except (TypeError, ValueError):
        return None


def _eval_cancel(order_data, entities, rules) -> EligibilityResult:
    status    = order_data.get("status", "")
    order_id  = order_data.get("order_id")
    amount    = order_data.get("payment_value")
    threshold = rules["cancellation"]["allowed_before_status"]
    BLOCKED   = {threshold, "delivered", "canceled", "invoiced"}

    if status in BLOCKED:
        return EligibilityResult(
            eligible=False, action="cancel_order", order_id=order_id,
            reason=f"Order cannot be cancelled — current status is '{status}'.",
            order_status=status,
        )
    return EligibilityResult(
        eligible=True, action="cancel_order", order_id=order_id,
        amount=amount, order_status=status,
    )


def _eval_refund(order_data, entities, rules) -> EligibilityResult:
    r       = rules["refund"]
    window  = r["window_days"]
    order_id = order_data.get("order_id")
    amount  = order_data.get("payment_value")
    days    = _days_since(order_data.get("delivered_date"))

    if days is None:
        return EligibilityResult(
            eligible=False, action="refund_request", order_id=order_id,
            reason="The delivery date is unavailable, so refund eligibility cannot be verified.",
        )

    if days is not None and days > window:
        warranty_days = rules["warranty"]["period_months"] * 30
        in_warranty   = days <= warranty_days
        return EligibilityResult(
            eligible=False, action="refund_request", order_id=order_id,
            reason=(
                f"The {window}-day refund window has passed ({days} days since delivery)."
                + (" Your product may still be covered by warranty." if in_warranty else "")
            ),
            days_since_delivery=days,
        )
    reqs: list[str] = []
    if r.get("requires_photo_proof") and "damaged" in str(entities.get("issue", "")):
        reqs.append("photo_required")
    return EligibilityResult(
        eligible=True, action="refund_request", order_id=order_id,
        amount=amount, requirements=reqs, days_since_delivery=days,
    )


def _eval_return(order_data, entities, rules) -> EligibilityResult:
    r      = rules["return"]
    window = r["window_days"]
    days   = _days_since(order_data.get("delivered_date"))
    if days is None:
        return EligibilityResult(
            eligible=False, action="return_request",
            order_id=order_data.get("order_id"),
            reason="The delivery date is unavailable, so return eligibility cannot be verified.",
        )
    if days is not None and days > window:
        return EligibilityResult(
            eligible=False, action="return_request",
            order_id=order_data.get("order_id"),
            reason=f"The {window}-day return window has passed ({days} days since delivery).",
            days_since_delivery=days,
        )
    return EligibilityResult(eligible=True, action="return_request",
                             order_id=order_data.get("order_id"), days_since_delivery=days)


def _eval_replacement(order_data, entities, rules) -> EligibilityResult:
    r      = rules["replacement"]
    window = r["window_days"]
    days   = _days_since(order_data.get("delivered_date"))
    if days is None:
        return EligibilityResult(
            eligible=False, action="replacement_request",
            order_id=order_data.get("order_id"),
            reason="The delivery date is unavailable, so replacement eligibility cannot be verified.",
        )
    issue = str(entities.get("issue") or "")
    if r["requires_defect"] and issue not in {"damaged", "defective", "wrong_item"}:
        return EligibilityResult(
            eligible=False, action="replacement_request",
            order_id=order_data.get("order_id"),
            reason="A replacement requires a verified defective or wrong item.",
            days_since_delivery=days,
        )
    if days is not None and days > window:
        return EligibilityResult(
            eligible=False, action="replacement_request",
            order_id=order_data.get("order_id"),
            reason=f"The {window}-day replacement window has passed ({days} days since delivery).",
            days_since_delivery=days,
        )
    reqs = ["photo_required"] if r.get("requires_defect") else []
    return EligibilityResult(eligible=True, action="replacement_request",
                             order_id=order_data.get("order_id"),
                             requirements=reqs, days_since_delivery=days)


def _eval_warranty(order_data, entities, rules) -> EligibilityResult:
    r             = rules["warranty"]
    months        = r["period_months"]
    days          = _days_since(order_data.get("delivered_date"))
    warranty_days = months * 30
    if days is None:
        return EligibilityResult(
            eligible=False, action="warranty_claim",
            order_id=order_data.get("order_id"),
            reason="The delivery date is unavailable, so warranty eligibility cannot be verified.",
        )
    issue = str(entities.get("issue") or "")
    if issue in set(r["excludes"]):
        return EligibilityResult(
            eligible=False, action="warranty_claim",
            order_id=order_data.get("order_id"),
            reason="The reported issue is excluded from warranty coverage.",
            days_since_delivery=days,
        )
    if r["requires_defect"] and issue not in {"defective", "damaged", "manufacturing_defect"}:
        return EligibilityResult(
            eligible=False, action="warranty_claim",
            order_id=order_data.get("order_id"),
            reason="A manufacturing defect must be verified for warranty coverage.",
            days_since_delivery=days,
        )
    if days is not None and days > warranty_days:
        return EligibilityResult(
            eligible=False, action="warranty_claim",
            order_id=order_data.get("order_id"),
            reason=f"The {months}-month warranty has expired ({days} days since delivery).",
            days_since_delivery=days,
        )
    return EligibilityResult(eligible=True, action="warranty_claim",
                             order_id=order_data.get("order_id"),
                             requirements=["photo_required"], days_since_delivery=days)


_EVALUATORS = {
    "cancel_order":        _eval_cancel,
    "refund_request":      _eval_refund,
    "damaged_product":     _eval_refund,
    "return_request":      _eval_return,
    "replacement_request": _eval_replacement,
    "warranty_claim":      _eval_warranty,
}
