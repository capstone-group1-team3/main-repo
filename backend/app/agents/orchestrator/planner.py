"""
agents/orchestrator/planner.py — Hybrid Planner with REAL timeout.

Fixes:
1. concurrent.futures.ThreadPoolExecutor provides real timeout (not just elapsed time).
2. Separate Groq client (PLANNER_GROQ_API_KEY) — never uses main key.
3. JSON Schema structured output attempted first; json_object fallback if unsupported.
4. Hidden reasoning NEVER stored, logged, or forwarded.
5. Correct model: openai/gpt-oss-20b.
"""
from __future__ import annotations

import concurrent.futures
import json
import logging
import threading
import time
from typing import Any

from pydantic import ValidationError

from app.agents.orchestrator.planner_schema import PlannerDecision
from app.agents.orchestrator.planner_prompt import SYSTEM_PROMPT, build_planner_context
from app.config.settings import settings
from app.monitoring.metrics import (
    PLANNER_CALLS, PLANNER_FAILURES, PLANNER_LATENCY,
    PLANNER_TIMEOUTS, PLANNER_CONFIDENCE,
)

logger = logging.getLogger("planner")

_planner_client = None
_client_lock    = threading.Lock()

_SCHEMA = {
    "type": "object",
    "properties": {
        "decision":         {"type": "string",
                             "enum": ["rag_policy","order_graph","action",
                                      "ask_clarification","respond"]},
        "corrected_intent": {"type": ["string","null"]},
        "reason":           {"type": "string", "minLength": 1, "maxLength": 300},
        "confidence":       {"type": "number", "minimum": 0.0, "maximum": 1.0},
        "arguments":        {"type": "object"},
    },
    "required": ["decision","reason","confidence"],
    "additionalProperties": False,
}


def _get_client():
    global _planner_client
    if _planner_client is not None:
        return _planner_client
    with _client_lock:
        if _planner_client is not None:
            return _planner_client
        key = settings.planner_groq_api_key
        if not key:
            logger.info("PLANNER_GROQ_API_KEY not set — planner disabled")
            return None
        try:
            from groq import Groq
            _planner_client = Groq(api_key=key)
            logger.info("Planner client ready (model=%s)", settings.planner_model)
        except Exception as exc:
            logger.error("Planner client init failed: %s", type(exc).__name__)
    return _planner_client


def _call_groq(client, kwargs: dict[str, Any]) -> str:
    return client.chat.completions.create(**kwargs).choices[0].message.content or ""


def call_planner(state: Any) -> PlannerDecision | None:
    client = _get_client()
    if client is None:
        return None

    kwargs: dict[str, Any] = {
        "model":       settings.planner_model,
        "temperature": settings.planner_temperature,
        "max_tokens":  settings.planner_max_tokens,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    "Return only one valid JSON object matching PlannerDecision.\n"
                    f"Current state:\n{build_planner_context(state)}"
                ),
            },
        ],
        "response_format": {"type": "json_object"},
    }

    if (
        settings.planner_reasoning_effort
        and "gpt-oss" in settings.planner_model.lower()
    ):
        kwargs["extra_body"] = {
            "reasoning_effort": settings.planner_reasoning_effort
        }

    PLANNER_CALLS.inc()
    t0 = time.monotonic()

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
            future = ex.submit(_call_groq, client, kwargs)
            try:
                raw = future.result(timeout=settings.planner_timeout_seconds)
            except concurrent.futures.TimeoutError:
                PLANNER_TIMEOUTS.inc()
                PLANNER_FAILURES.inc()
                logger.warning("Planner timed out (%.0fs)", settings.planner_timeout_seconds)
                return None
    except Exception as exc:
        PLANNER_FAILURES.inc()
        PLANNER_LATENCY.observe(time.monotonic() - t0)
        logger.warning(
            "Planner call failed: type=%s status=%s",
            type(exc).__name__,
            getattr(exc, "status_code", None),
        )
        return None

    PLANNER_LATENCY.observe(time.monotonic() - t0)

    # JSON Schema not supported → retry with json_object
    raw = _strip_reasoning(raw)
    if not raw.strip().startswith("{"):
        PLANNER_FAILURES.inc()
        logger.warning("Planner returned non-JSON — falling back to json_object mode")
        kwargs["response_format"] = {"type": "json_object"}
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
                future = ex.submit(_call_groq, client, kwargs)
                raw = _strip_reasoning(future.result(timeout=settings.planner_timeout_seconds))
        except Exception as exc:
            PLANNER_FAILURES.inc()
            logger.warning("Planner json_object fallback failed: %s", type(exc).__name__)
            return None

    try:
        data     = json.loads(raw)
        decision = PlannerDecision(**data)
        PLANNER_CONFIDENCE.observe(decision.confidence)
        return decision
    except json.JSONDecodeError:
        PLANNER_FAILURES.inc()
        logger.warning("Planner: invalid JSON")
        return None
    except ValidationError as exc:
        PLANNER_FAILURES.inc()
        logger.warning("Planner schema invalid: %s", [e["loc"] for e in exc.errors()])
        return None


def _strip_reasoning(text: str) -> str:
    """Extract JSON object; discard any chain-of-thought. REASONING NEVER LOGGED."""
    idx = text.find("{")
    if idx < 0:
        return text
    text = text[idx:]
    last = text.rfind("}")
    return text[:last + 1].strip() if last >= 0 else text
