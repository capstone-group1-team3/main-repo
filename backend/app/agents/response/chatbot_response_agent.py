"""
agents/response/chatbot_response_agent.py — turn the final state into a reply.

Two-pass approach:
  1. Rule-based template for simple, deterministic outcomes (clarification,
     denial, ownership error, ticket created, etc.) — fast, no LLM cost.
  2. Groq LLM generation for the remaining cases where the answer needs to
     blend policy evidence + order facts + action result naturally.

GROUNDING ENFORCEMENT:
  The system prompt instructs the LLM to cite only chunk_ids from
  state.candidate_ids. The eval harness checks that every cited chunk_id is
  in candidate_ids (Grounded Policy Response Rate metric).
"""
from __future__ import annotations

import json
import logging
from typing import Any

from app.agents.response.response_formatter import format_grounded_reply
from app.agents.response.response_formatter import strip_citation_markup
from app.agents.response.response_templates import (
    template_clarification,
    template_greeting,
    template_ownership_error,
    template_policy_only,
    template_order_tracking,
    template_action_result,
    template_error,
)
from app.agents.orchestrator.intent_detector import is_greeting
from app.config.settings import settings

_POLICY_DECLINE = "I cannot answer this from the available sources."
_POLICY_SYSTEM = f"""You answer policy questions using only supplied evidence.
Return one JSON object with exactly these fields:
{{"answer": "...", "citation_chunk_ids": ["..."]}}
The answer must be 1-3 concise sentences and contain no citation brackets.
Every factual claim must be directly supported by the supplied evidence.
Copy citation_chunk_ids exactly from the allowed IDs. If evidence is
insufficient or unrelated, use answer={_POLICY_DECLINE!r} and an empty list.
Do not add conditions, dates, exceptions, guarantees, or procedures that the
evidence does not state."""

logger = logging.getLogger("chatbot_response")


def run(state: Any) -> dict[str, Any]:
    """
    Returns:
        {
          "answer":       str,
          "citations":    [{"chunk_id": ...}, ...],  # grounding citations
          "intent":       str,
          "action_taken": str | None,
        }
    """
    if state.intent == "greeting" or is_greeting(state.message):
        return {
            "answer": template_greeting(state.message),
            "citations": [],
            "intent": state.intent,
            "action_taken": None,
        }

    # ---- deterministic fast paths ----
    if state.clarification_needed:
        return {
            "answer": template_clarification(state.clarification_needed),
            "citations": [],
            "intent": state.intent,
            "action_taken": None,
        }

    if not state.ownership_ok:
        return {
            "answer": template_ownership_error(),
            "citations": [],
            "intent": state.intent,
            "action_taken": None,
        }

    if state.error:
        return {
            "answer": template_error(state.error),
            "citations": [],
            "intent": state.intent,
            "action_taken": None,
        }

    if state.intent == "ticket_status":
        return _ticket_status_answer(state)

    if state.intent == "policy_question" and not state.policy_evidence:
        return {
            "answer": "I cannot answer this from the available sources.",
            "citations": [], "intent": state.intent, "action_taken": None,
        }

    if state.action_result:
        # action result may still use policy evidence in the explanation
        answer, citations = format_grounded_reply(state)
        return {
            "answer": answer,
            "citations": citations,
            "intent": state.intent,
            "action_taken": state.action_result.get("action"),
        }

    if state.intent == "order_tracking" and state.order_data:
        return {
            "answer": template_order_tracking(state.order_data),
            "citations": [],
            "intent": state.intent,
            "action_taken": None,
        }

    if state.intent == "policy_question" and state.policy_evidence and not state.order_data:
        ans, cites = _policy_only_answer(state)
        return {
            "answer": ans,
            "citations": cites,
            "intent": state.intent,
            "action_taken": None,
        }

    # ---- LLM-generated grounded reply for all other cases ----
    answer, citations = format_grounded_reply(state)
    return {
        "answer": answer,
        "citations": citations,
        "intent": state.intent,
        "action_taken": state.action_result.get("action") if state.action_result else None,
    }


def _policy_only_answer(state: Any) -> tuple[str, list[dict]]:
    from app.llm.llm_client import chat_complete

    ids = ", ".join(state.candidate_ids)
    prompt = (
        f"CUSTOMER QUESTION:\n{state.message}\n\n"
        f"ALLOWED CHUNK IDS:\n{ids}\n\n"
        f"POLICY EVIDENCE:\n{state.policy_evidence}\n\n"
        "Return JSON only. Do not include citation markup in answer."
    )
    try:
        raw = chat_complete(
            prompt,
            system=_POLICY_SYSTEM,
            max_tokens=400,
            temperature=settings.policy_temperature,
        )
    except Exception as exc:
        # Provider throttling/outages must not become a 500 or an ungrounded
        # answer. The caller still returns a valid, safe policy response.
        logger.warning(
            "Policy generation unavailable; returning safe decline type=%s",
            type(exc).__name__,
        )
        state.invalid_citation_ids = []
        return _POLICY_DECLINE, []

    answer, requested_ids, structured = _decode_policy_output(raw)
    # Inline citation text is never promoted to the API's structured citation
    # field. Providers that ignore the JSON contract fail closed instead.
    if not structured:
        state.invalid_citation_ids = []
        return _POLICY_DECLINE, []
    citations, invalid = _resolve_policy_citations(requested_ids, state.candidate_ids)

    state.invalid_citation_ids = invalid
    answer = strip_citation_markup(answer).strip()
    if answer == _POLICY_DECLINE:
        return _POLICY_DECLINE, []
    # No valid structured citation, an invalid citation, or an empty answer is
    # unverified and therefore fails closed.
    if not answer or not citations or invalid:
        return _POLICY_DECLINE, []
    # De-duplicate structured citations while preserving retrieval order.
    seen: set[str] = set()
    unique: list[dict[str, str]] = []
    for citation in citations:
        chunk_id = citation["chunk_id"]
        if chunk_id not in seen:
            seen.add(chunk_id)
            unique.append(citation)
    citations = unique
    return answer, citations


def _decode_policy_output(raw: str) -> tuple[str, list[str], bool]:
    try:
        parsed = json.loads(raw)
    except (TypeError, ValueError, json.JSONDecodeError):
        return raw, [], False
    if not isinstance(parsed, dict):
        return raw, [], False
    answer = parsed.get("answer")
    ids = parsed.get("citation_chunk_ids")
    if not isinstance(answer, str) or not isinstance(ids, list):
        return raw, [], False
    return answer, [str(item) for item in ids if isinstance(item, str)], True


def _resolve_policy_citations(
    requested_ids: list[str], candidate_ids: list[str]
) -> tuple[list[dict[str, str]], list[str]]:
    citations: list[dict[str, str]] = []
    invalid: list[str] = []
    for token in requested_ids:
        normalized = _normalize_citation_id(token, candidate_ids)
        if normalized and normalized not in {c["chunk_id"] for c in citations}:
            citations.append({"chunk_id": normalized})
        elif not normalized and token not in invalid:
            invalid.append(token)
    return citations, invalid


def _normalize_citation_id(token: str, candidate_ids: list[str]) -> str | None:
    value = token.strip().strip("[]")
    if value in candidate_ids:
        return value
    value_source = value.split("::", 1)[0].lower()
    value_stem = value_source.removesuffix(".md")
    for candidate in candidate_ids:
        source = candidate.split("::", 1)[0].lower()
        if value_source == source or value_stem == source.removesuffix(".md"):
            return candidate
    return None


def _extract_citations(text: str, candidate_ids: list[str]) -> list[dict[str, str]]:
    import re
    found = re.findall(r"\[([^\]]+)\]", text)
    return [{"chunk_id": cid} for cid in found if cid in set(candidate_ids)]


def _ticket_status_answer(state: Any) -> dict[str, Any]:
    tickets = state.tickets or []
    requests = state.requests or []
    if not tickets and not requests:
        answer = "I couldn't find any tickets or service requests in your account."
    else:
        lines = []
        for item in tickets[:3]:
            lines.append(f"Ticket {item.get('ticket_id')} is {item.get('status', 'unknown')}.")
        for item in requests[:3]:
            lines.append(f"Request {item.get('request_id')} is {item.get('status', 'unknown')}.")
        answer = " ".join(lines)
    return {"answer": answer, "citations": [], "intent": state.intent, "action_taken": None}
