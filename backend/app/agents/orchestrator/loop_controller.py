"""
agents/orchestrator/loop_controller.py — Hybrid Planner bounded loop (v2).

Key fixes:
1. Plan-once reuse: current_plan consumed step-by-step; re-plan only on unexpected result.
2. Eligibility BEFORE confirmation: denied → respond immediately, no gate.
3. No implicit latest-order for sensitive actions.
4. Confirmation loaded from server-side state (persisted across HTTP turns).
5. Triple safety gate before action: ownership + confirmation + re-validate.
"""
from __future__ import annotations
import logging, re, time
from typing import Any

from app.agents.orchestrator.state import OrchestratorState, GoalState
from app.agents.orchestrator.routing_rules import next_tool, TOOL_SEQUENCE
from app.agents.orchestrator.stop_conditions import should_stop
from app.agents.orchestrator.required_slots import missing_slots, first_missing_entity
from app.agents.orchestrator.fast_path import should_use_fast_path
from app.agents.orchestrator.planner import call_planner
from app.agents.orchestrator.decision_validator import validate as validate_decision
from app.agents.orchestrator.observations import (
    build_order_observation, build_rag_observation,
    build_action_observation, build_error_observation,
)
from app.agents.orchestrator.progress import state_fingerprint, no_progress
from app.agents.action.action_evaluator import evaluate_eligibility
from app.monitoring.metrics import (
    FAST_PATH_USED, FALLBACK_USED,
    CONFIRMATION_REQUESTED, CONFIRMATION_ACCEPTED, CONFIRMATION_DECLINED,
    UNSAFE_ACTION_PROPOSALS, DECISION_CORRECTIONS, ELIGIBILITY_DENIALS,
    NO_PROGRESS_STOPS,
    LOOP_ITERATIONS, ORCHESTRATOR_COMPLETIONS, ORCHESTRATOR_DURATION,
    TOOLS_CALLED, TOOL_DURATION,
    CLARIFICATION_ASKED,
)
from app.config.settings import settings

logger = logging.getLogger("orchestrator.loop")

_SENSITIVE = {
    "refund_request","return_request","replacement_request",
    "cancel_order","warranty_claim","damaged_product",
}
_YES = frozenset({"yes","confirm","proceed","do it","go ahead","sure","ok",
                  "okay","yep","yup","please","yes please","y"})
_NO  = frozenset({"no","cancel","stop","dont","nope","negative","nevermind","n","abort"})

_MULTI_GOAL_RE = re.compile(
    r"\b(where is|track|tracking).{0,60}\b(return|refund|replace|cancel|warrant)\b"
    r"|\b(return|refund|replace|cancel|warrant).{0,60}\b(where is|track|tracking)\b",
    re.I,
)


def run_loop(state: OrchestratorState) -> OrchestratorState:
    started = time.perf_counter()
    try:
        return _run_loop_impl(state)
    finally:
        outcome = _completion_outcome(state)
        state.completion_reason = state.completion_reason or outcome
        ORCHESTRATOR_DURATION.labels(outcome=outcome).observe(time.perf_counter() - started)
        ORCHESTRATOR_COMPLETIONS.labels(outcome=outcome).inc()
        LOOP_ITERATIONS.labels(outcome=outcome).observe(state.iterations)


def _run_loop_impl(state: OrchestratorState) -> OrchestratorState:
    from app.agents.rag_policy import rag_policy_agent
    from app.agents.order_graph import order_graph_agent
    from app.agents.action import action_agent
    from app.agents.action.action_router import get_rules

    _snap(state)

    # Handle confirmation reply first (state loaded from ConversationStateData)
    if state.confirmation_required:
        _handle_confirm(state)
        if state.done:
            return state

    _setup_goals(state)

    while True:
        stop, reason = should_stop(state)
        if stop:
            logger.debug("stop: %s (iter=%d)", reason, state.iterations)
            state.completion_reason = reason
            if reason in ("max_iterations_reached", "max_tool_calls_reached"):
                state.error = "The request could not be completed safely within the processing limit."
            state.done = True
            break

        if no_progress(state):
            NO_PROGRESS_STOPS.inc()
            logger.warning("No progress — stopping")
            state.done = True
            state.completion_reason = "no_progress"
            break

        tool, corrected = _pick_tool(state)

        if tool in (None, "respond"):
            state.completion_reason = "completed"
            state.done = True; break
        if tool == "clarification":
            CLARIFICATION_ASKED.labels(reason="missing_information").inc()
            state.completion_reason = "clarification_required"
            state.done = True; break
        if tool == "confirmation_gate":
            state.confirmation_required = True
            CONFIRMATION_REQUESTED.inc()
            state.completion_reason = "confirmation_required"
            state.done = True; break

        # Apply intent correction
        if corrected and corrected != state.intent:
            logger.info("Intent: %s → %s", state.intent, corrected)
            DECISION_CORRECTIONS.labels(type="intent").inc()
            state.intent = corrected
            state.current_plan = []; state.plan_valid = False

        # SAFETY: no implicit latest-order for sensitive actions
        if (tool in ("order_graph","action")
                and state.intent in _SENSITIVE
                and not state.entities.get("order_id")
                and state.order_data is None):
            state.clarification_needed = (
                "Which order would you like me to help with? Please provide the order number."
            )
            state.asked_for_order_id = True
            CLARIFICATION_ASKED.labels(reason="missing_order_id").inc()
            state.completion_reason = "clarification_required"
            logger.info("Blocked implicit order for intent '%s'", state.intent)
            state.done = True; break

        state.iterations += 1
        state.tools_used.append(tool)
        tool_started = time.perf_counter()
        tool_outcome = "success"
        obs: dict[str, Any] = {}

        try:
            if tool == "rag_policy":
                r = rag_policy_agent.run(query=state.message, intent=state.intent)
                state.policy_evidence = r["policy_evidence"]
                state.policy_sources  = r["sources"]
                state.candidate_ids   = r["candidate_ids"]
                obs = build_rag_observation(r)
                _check_replan(state, obs)

            elif tool == "order_graph":
                r = order_graph_agent.run(
                    customer_id=state.customer_id,
                    intent=state.intent,
                    entities=state.entities,
                )
                state.order_data   = r.get("order_data")
                state.orders       = r.get("orders", [])
                state.tickets      = r.get("tickets", [])
                state.requests     = r.get("requests", [])
                state.ownership_ok = r.get("ownership_ok", True)
                obs = build_order_observation(r)

                if not state.ownership_ok:
                    state.error = r.get("error")
                    state.observations.append(obs); _snap(state)
                    state.done = True; break

                # Phase-1 eligibility BEFORE confirmation
                if state.intent in _SENSITIVE and state.order_data:
                    elig = evaluate_eligibility(
                        state.intent, state.order_data, state.entities, get_rules()
                    )
                    state.eligibility_result = {
                        "eligible":    elig.eligible,
                        "action":      elig.action,
                        "order_id":    elig.order_id,
                        "reason":      elig.reason,
                        "amount":      elig.amount,
                        "requirements":elig.requirements,
                        "order_status":elig.order_status,
                        "days_since_delivery": elig.days_since_delivery,
                    }
                    if not elig.eligible:
                        ELIGIBILITY_DENIALS.labels(action=elig.action).inc()
                        logger.info("Denied: %s — %s", elig.action, elig.reason)
                        denied_action = {
                            "refund_request": "refund_denied",
                            "damaged_product": "refund_denied",
                            "return_request": "return_denied",
                            "replacement_request": "replacement_denied",
                            "warranty_claim": "warranty_denied",
                            "cancel_order": "cancel_denied",
                        }.get(state.intent, "no_action_needed")
                        state.action_result = {
                            "action": denied_action,
                            "order_id": elig.order_id,
                            "reason": elig.reason or "This order is not eligible.",
                            "suggest_warranty": (
                                state.intent in ("refund_request", "damaged_product")
                                and bool(elig.reason)
                                and "warranty" in elig.reason.lower()
                            ),
                        }
                        state.observations.append(obs); _snap(state)
                        state.done = True; break

                    # Eligible → set confirmation gate
                    state.pending_action = {
                        "intent":       state.intent,
                        "order_id":     elig.order_id,
                        "amount":       elig.amount,
                        "requirements": elig.requirements,
                        "order_status": elig.order_status,
                    }
                    state.confirmation_context = {
                        "intent":   state.intent,
                        "order_id": elig.order_id,
                    }
                    state.confirmation_required = True
                    CONFIRMATION_REQUESTED.inc()
                    state.observations.append(obs); _snap(state)
                    break

                _check_replan(state, obs)

            elif tool == "action":
                # Confirmation is authorization for an intent, never a trusted
                # data snapshot. Reload the currently owned order before every
                # mutation so status, delivery date, and ownership are current.
                if not _reload_current_owned_order(state):
                    state.ownership_ok = False
                    state.error = "The order could not be verified for this account."
                    state.completion_reason = "ownership_denied"
                    state.done = True; break

                # Triple safety gate
                if not state.ownership_ok or state.order_data is None:
                    UNSAFE_ACTION_PROPOSALS.labels(reason="no_ownership").inc()
                    logger.warning("Action blocked: no ownership")
                    state.done = True; break

                if not state.confirmation_received:
                    UNSAFE_ACTION_PROPOSALS.labels(reason="no_confirmation").inc()
                    logger.warning("Action blocked: no confirmation")
                    state.confirmation_required = True
                    CONFIRMATION_REQUESTED.inc()
                    state.done = True; break

                # Re-validate after confirmation
                elig2 = evaluate_eligibility(
                    state.intent, state.order_data, state.entities, get_rules()
                )
                if not elig2.eligible:
                    ELIGIBILITY_DENIALS.labels(action=elig2.action).inc()
                    logger.warning("Re-validation failed: %s", elig2.reason)
                    state.action_result = {
                        "action": f"{state.intent}_denied",
                        "reason": elig2.reason or "Order state changed.",
                    }
                    state.reset_confirmation()
                    obs = {"tool":"action","status":"revalidation_failed","summary":{}}
                    state.observations.append(obs); _snap(state)
                    state.done = True; break

                missing = missing_slots(state, state.intent)
                if missing:
                    state.done = True; break

                r = action_agent.run(state)
                state.action_result = r
                state.reset_confirmation()
                obs = build_action_observation(r)

        except Exception as exc:
            tool_outcome = "failure"
            logger.exception("Tool %s raised: %s", tool, type(exc).__name__)
            obs = build_error_observation(tool, exc)
            state.observations.append(obs)
            state.error = "A service error occurred. Please try again."
            state.completion_reason = "failed"
            state.done = True; break
        finally:
            TOOLS_CALLED.labels(tool=tool, outcome=tool_outcome).inc()
            TOOL_DURATION.labels(tool=tool, outcome=tool_outcome).observe(
                time.perf_counter() - tool_started
            )

        state.observations.append(obs)
        _snap(state)

        # Consume from plan
        if state.plan_valid and state.current_plan:
            if state.current_plan and state.current_plan[0] == tool:
                state.current_plan.pop(0)
            if state.replan_needed:
                state.plan_valid = False

    return state


def _pick_tool(state):
    # 1. Plan reuse
    if state.plan_valid and state.current_plan and not state.replan_needed:
        step = state.current_plan[0]
        logger.debug("Plan reuse → %s", step)
        _trace(state, step, None, "plan reuse", 1.0, False, False)
        return step, None

    # 2. Fast path
    use_fp, fp_reason = should_use_fast_path(state)
    if use_fp:
        FAST_PATH_USED.inc()
        tool = next_tool(state, state.intent)
        _build_plan(state)
        _trace(state, tool or "respond", None, fp_reason, 1.0, False, True)
        return tool, None

    # 3. Planner
    import time as _t
    t0 = _t.monotonic()
    decision = call_planner(state)
    elapsed  = _t.monotonic() - t0

    if decision is None:
        FALLBACK_USED.inc()
        tool = next_tool(state, state.intent)
        logger.warning("Planner failed (%.2fs) → fallback %s", elapsed, tool)
        _trace(state, tool or "respond", None, "planner unavailable", 0.0, True, False)
        return tool, None

    if decision.confidence < settings.planner_min_confidence:
        FALLBACK_USED.inc()
        tool = next_tool(state, state.intent)
        _trace(state, tool or "respond", decision.corrected_intent,
               f"low-conf fallback: {decision.reason}", decision.confidence, True, False)
        return tool, decision.corrected_intent

    approved, corrected, args = validate_decision(decision, state)
    if approved != decision.decision:
        DECISION_CORRECTIONS.labels(type="validator").inc()
        logger.info("Validator: %s → %s", decision.decision, approved)

    _trace(state, approved, corrected, decision.reason, decision.confidence, False, False)

    # Build plan from approved decision's sequence
    if approved not in ("respond","ask_clarification","confirmation_gate"):
        seq = TOOL_SEQUENCE.get(corrected or state.intent, [])
        rem = [t for t in seq if t not in state.tools_used and t != "response"]
        if rem:
            state.current_plan = rem; state.plan_valid = True

    if approved == "respond":
        return "respond", corrected
    if approved == "ask_clarification":
        if args.get("_confirmation_gate"):
            return "confirmation_gate", corrected
        state.clarification_needed = args.get("question") or _clarify(state)
        return "clarification", corrected

    return approved, corrected


def _handle_confirm(state):
    msg = state.message.lower().strip().rstrip("!.,")
    if msg in _YES or any(w in msg for w in ("yes","proceed","confirm")):
        state.confirmation_received = True
        state.confirmation_required = False
        CONFIRMATION_ACCEPTED.inc()
        if state.pending_action:
            state.intent = state.pending_action.get("intent", state.intent)
        return
    if msg in _NO or any(w in msg for w in ("no ","nope","stop","cancel","abort")):
        state.reset_confirmation()
        CONFIRMATION_DECLINED.inc()
        state.clarification_needed = (
            "No problem — the action was cancelled. Is there anything else I can help with?"
        )
        state.done = True
        return
    state.clarification_needed = (
        "Please reply 'yes' to confirm or 'no' to cancel."
    )
    state.done = True


def _setup_goals(state):
    if not state.goals and _MULTI_GOAL_RE.search(state.message):
        state.goals = [
            GoalState(type="order_tracking", status="pending"),
            GoalState(type="policy_question",  status="pending"),
        ]


def _build_plan(state):
    seq = TOOL_SEQUENCE.get(state.intent, [])
    rem = [t for t in seq if t not in state.tools_used and t != "response"]
    if rem:
        state.current_plan = rem; state.plan_valid = True


def _check_replan(state, obs):
    if obs.get("status") in ("failed","ownership_failed","revalidation_failed"):
        state.replan_needed = True; state.plan_valid = False


def _clarify(state) -> str:
    slot = first_missing_entity(state.entities, state.intent)
    return slot[1] if slot else "Could you provide more details?"


def _trace(state, decision, corrected, reason, confidence, fallback, fast_path):
    state.planning_trace.append({
        "initial_intent":   state.intent,
        "corrected_intent": corrected,
        "decision":         decision,
        "reason":           reason,
        "confidence":       round(confidence, 3),
        "fallback_used":    fallback,
        "fast_path_used":   fast_path,
    })


def _snap(state):
    state.state_fingerprints.append(state_fingerprint(state))


def _completion_outcome(state: OrchestratorState) -> str:
    reason = state.completion_reason or ""
    if reason in ("max_iterations_reached", "max_iterations"):
        return "max_iterations"
    if reason in ("max_tool_calls_reached", "max_tool_calls"):
        return "max_tool_calls"
    if not state.ownership_ok or reason == "ownership_denied":
        return "ownership_denied"
    if state.error:
        return "failed"
    if state.confirmation_required and not state.confirmation_received:
        return "confirmation_required"
    if state.clarification_needed:
        return "clarification_required"
    return "completed"


def _reload_current_owned_order(state: OrchestratorState) -> bool:
    """Reload a full, customer-scoped Order immediately before mutation."""
    from app.agents.order_graph.graph_service import get_order
    from app.agents.order_graph.graph_mapper import map_order

    order_id = (
        (state.pending_action or {}).get("order_id")
        or state.entities.get("order_id")
        or (state.order_data or {}).get("order_id")
    )
    if not order_id:
        return False
    row = get_order(state.customer_id, order_id)
    if row is None:
        return False
    current = map_order(row)
    if not current.get("order_id"):
        return False
    state.order_data = current
    state.entities["order_id"] = current["order_id"]
    state.ownership_ok = True
    return True
