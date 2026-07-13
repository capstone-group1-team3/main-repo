"""
agents/orchestrator/stop_conditions.py — when the loop must stop.

Checked at the top of every iteration before choosing the next tool.
"""
from __future__ import annotations

from typing import Any

from app.config.settings import settings


def should_stop(state: Any) -> tuple[bool, str]:
    """
    Returns (stop: bool, reason: str).
    Caller stops the loop when stop is True.
    """
    if state.done:
        return True, "already_done"

    if state.error:
        return True, "error"

    if not state.ownership_ok:
        return True, "ownership_violation"

    if state.clarification_needed:
        return True, "clarification_needed"

    if state.action_result is not None:
        return True, "action_complete"

    if state.iterations >= settings.max_iterations:
        return True, "max_iterations_reached"

    if len(state.tools_used) >= settings.max_tool_calls:
        return True, "max_tool_calls_reached"

    return False, ""
