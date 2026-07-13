"""
agents/action/action_agent.py — the Action Agent (orchestrator-facing).

Validates business rules, dispatches to the correct handler, and returns the
action result written into state.action_result.
"""
from __future__ import annotations

from typing import Any
import time

from app.agents.action.action_router import route
from app.monitoring.metrics import ACTION_ATTEMPTS, ACTION_DURATION, ACTION_RESULTS

_ACTION_NAMES = {
    "refund_request": "refund", "damaged_product": "refund",
    "return_request": "return", "replacement_request": "replacement",
    "warranty_claim": "warranty", "cancel_order": "cancel",
    "payment_issue": "ticket", "order_tracking": "ticket",
}


def run(state: Any) -> dict[str, Any]:
    action = _ACTION_NAMES.get(state.intent, "none")
    started = time.perf_counter()
    ACTION_ATTEMPTS.labels(action=action).inc()
    outcome = "failed"
    try:
        result = route(state.intent, state)
        name = str(result.get("action", ""))
        status = str(result.get("status", ""))
        if name.endswith("_denied"):
            outcome = "rejected"
        elif name.endswith("_failed"):
            outcome = "unauthorized" if "ownership" in str(result.get("reason", "")) else "failed"
        elif status == "pending_proof":
            outcome = "pending_proof"
        else:
            outcome = "success"
        return result
    except Exception:
        outcome = "failed"
        raise
    finally:
        ACTION_DURATION.labels(action=action, outcome=outcome).observe(
            time.perf_counter() - started
        )
        ACTION_RESULTS.labels(action=action, outcome=outcome).inc()
