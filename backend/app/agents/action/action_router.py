"""
agents/action/action_router.py — reads business_rules.yaml and routes to handlers.

All rule numbers (windows, proof requirements, etc.) are read from business_rules.yaml
(the single source of truth). Nothing is hard-coded here.
"""
from __future__ import annotations

from pathlib import Path
from functools import lru_cache
from typing import Any
import yaml

from app.config.settings import settings


@lru_cache
def get_rules() -> dict[str, Any]:
    path = Path(settings.business_rules_path)
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def days_since_delivery(order_data: dict[str, Any]) -> int | None:
    """Return how many days ago the order was delivered, or None if unknown."""
    from datetime import date
    delivered = order_data.get("delivered_date")
    if not delivered:
        return None
    if isinstance(delivered, str):
        delivered = date.fromisoformat(delivered)
    return (date.today() - delivered).days


def route(intent: str, state: Any) -> dict[str, Any]:
    """Dispatch to the correct action handler based on intent."""
    from app.agents.action import (
        create_ticket,
        create_refund_request,
        create_return_request,
        create_replacement_request,
        cancel_order,
        create_warranty_claim,
    )

    handlers = {
        "refund_request":      create_refund_request.run,
        "damaged_product":     create_refund_request.run,   # same handler, photo required
        "return_request":      create_return_request.run,
        "replacement_request": create_replacement_request.run,
        "warranty_claim":      create_warranty_claim.run,
        "cancel_order":        cancel_order.run,
        "order_tracking":      create_ticket.run,
        "payment_issue":       create_ticket.run,
        "ticket_status":       None,  # read-only, no action needed
        "policy_question":     None,
    }

    handler = handlers.get(intent)
    if handler is None:
        return {"status": "no_action_needed"}

    return handler(state)
