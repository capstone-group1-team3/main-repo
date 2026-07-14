"""
agents/response/response_templates.py — deterministic reply builders.

Used for outcomes that don't need the LLM: clarifications, denials,
ownership errors, order tracking, errors.
"""
from __future__ import annotations

from typing import Any


def template_clarification(question: str) -> str:
    return question


def template_greeting(message: str) -> str:
    """Deterministic social response; no policy evidence or citations needed."""
    if message.strip().lower().startswith(("thanks", "thank you")):
        return "You're welcome! How can I help you today?"
    return "Hi! How can I help you today?"


def template_ownership_error() -> str:
    return (
        "I wasn't able to find that order in your account. "
        "Please double-check the order number, or contact us if you think there's an issue."
    )


def template_error(error: str) -> str:
    return (
        "Something went wrong while processing your request. "
        "Our team has been notified. Please try again in a moment."
    )


def template_order_tracking(order: dict[str, Any]) -> str:
    oid = order.get("order_id", "your order")
    status = order.get("status", "unknown")
    delivered = order.get("delivered_date")
    estimated = order.get("estimated_delivery_date")
    late = order.get("delivery_late", False)

    if status == "delivered" and delivered:
        return f"Your order ({oid}) was delivered on {delivered}. If you haven't received it, please let us know."

    if status == "shipped":
        est = f" The estimated delivery date is {estimated}." if estimated else ""
        note = " It looks like it may be running a bit late." if late else ""
        return f"Your order ({oid}) has been shipped and is on its way.{est}{note}"

    if status in ("created", "approved"):
        est = f" Expected delivery: {estimated}." if estimated else ""
        return f"Your order ({oid}) is being prepared for shipment.{est}"

    if status == "canceled":
        return f"Your order ({oid}) has been cancelled."

    return f"Your order ({oid}) has status: {status}."


def template_action_result(action_result: dict[str, Any], intent: str) -> str:
    action = action_result.get("action", "")

    if action == "refund_request_created":
        rid = action_result.get("request_id", "")
        status = action_result.get("status", "open")
        days = action_result.get("processing_days")
        next_step = action_result.get("next_step", "")
        base = f"Your refund request ({rid}) has been created. "
        if status == "pending_proof":
            base += next_step + " "
        if days == 0:
            base += "Once approved, voucher credit is restored immediately."
        elif days is not None:
            base += f"Once approved, refunds are processed within {days} business days."
        return base

    if action == "return_request_created":
        rid = action_result.get("request_id", "")
        who = action_result.get("return_shipping_paid_by", "customer")
        return (
            f"Your return request ({rid}) has been created. "
            f"Return shipping is covered by {'us' if who == 'company' else 'you'} in this case."
        )

    if action == "replacement_request_created":
        rid = action_result.get("request_id", "")
        next_step = action_result.get("next_step", "")
        return f"A replacement request ({rid}) has been opened. {next_step}"

    if action == "warranty_claim_created":
        rid = action_result.get("request_id", "")
        next_step = action_result.get("next_step", "")
        return f"Your warranty claim ({rid}) has been submitted. {next_step}"

    if action == "order_cancelled":
        oid = action_result.get("order_id", "your order")
        return f"Your order ({oid}) has been successfully cancelled."

    if action == "ticket_created":
        tid = action_result.get("ticket_id", "")
        return f"A support ticket ({tid}) has been created. Our team will follow up with you."

    if action in (
        "refund_denied", "return_denied", "replacement_denied",
        "warranty_claim_denied", "warranty_denied", "cancel_denied",
    ):
        reason = action_result.get("reason", "")
        suggest = action_result.get("suggest_warranty", False)
        base = f"Unfortunately we're unable to process this request: {reason}."
        if suggest:
            base += " However, this may be eligible as a warranty claim — would you like to proceed?"
        return base

    return "Your request has been processed."


def template_policy_only(evidence_context: str) -> str:
    return (
        "Based on our policy:\n\n"
        + evidence_context.split("\n")[0]   # first line only as fallback
    )
