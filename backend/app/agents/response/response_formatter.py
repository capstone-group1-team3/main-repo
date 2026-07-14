"""
agents/response/response_formatter.py — LLM-generated grounded reply.

Builds a prompt that includes policy evidence (with chunk_ids) + order facts +
action result, and instructs Groq to cite only chunk_ids from candidate_ids.
The grounding contract: every [chunk_id] in the answer must be in candidate_ids.
"""
from __future__ import annotations

import re
from typing import Any

from app.agents.response.response_templates import template_action_result
from app.llm.llm_client import chat_complete
from app.config.settings import settings

_SYSTEM = """You are a friendly, precise e-commerce customer support agent.
Rules:
1. Answer ONLY from the evidence and facts provided — never invent information.
2. When you cite policy evidence, include the chunk_id inline as [chunk_id].
3. Only cite chunk_ids explicitly listed in ALLOWED CITATION IDS.
4. If the action result is provided, explain what was done and what happens next.
5. Keep the reply concise — 2-4 sentences unless more detail is genuinely needed.
6. Tone: warm, clear, professional."""


def format_grounded_reply(state: Any) -> tuple[str, list[dict[str, str]]]:
    """
    Returns (answer_text, citations_list).
    citations_list = [{"chunk_id": ...}] for every [chunk_id] found in the answer
    that is also in state.candidate_ids.
    """
    parts: list[str] = []

    if state.policy_evidence:
        ids_str = ", ".join(state.candidate_ids)
        parts.append(f"ALLOWED CITATION IDS: {ids_str}")
        parts.append(f"POLICY EVIDENCE:\n{state.policy_evidence}")

    if state.order_data:
        parts.append(f"ORDER FACTS:\n{_order_summary(state.order_data)}")

    if state.action_result:
        action = state.action_result.get("action", "")
        if action in ("refund_denied", "return_denied", "replacement_denied",
                      "warranty_claim_denied", "warranty_denied",
                      "cancel_denied", "no_action_needed"):
            # deterministic outcome — no LLM needed
            return template_action_result(state.action_result, state.intent), []
        parts.append(f"ACTION TAKEN:\n{_action_summary(state.action_result)}")

    parts.append(f"CUSTOMER MESSAGE:\n{state.message}")
    prompt = "\n\n".join(parts)

    temperature = (
        settings.policy_temperature
        if state.intent == "policy_question" and state.policy_evidence
        else 0.2
    )
    answer = chat_complete(prompt, system=_SYSTEM, max_tokens=512, temperature=temperature)
    citations, invalid = citation_audit(answer, state.candidate_ids)
    state.invalid_citation_ids = invalid
    return answer, citations


def _order_summary(order: dict[str, Any]) -> str:
    lines = [
        f"order_id: {order.get('order_id')}",
        f"status: {order.get('status')}",
        f"delivered: {order.get('delivered_date')}",
        f"estimated: {order.get('estimated_delivery_date')}",
        f"payment_type: {order.get('payment_type')}",
        f"payment_value: {order.get('payment_value')}",
        f"late: {order.get('delivery_late')}",
    ]
    items = order.get("items") or []
    if items:
        lines.append("items: " + "; ".join(
            f"{i.get('category', 'product')} x{i.get('quantity', 1)}"
            for i in items[:3]
        ))
    return "\n".join(lines)


def _action_summary(result: dict[str, Any]) -> str:
    return "\n".join(f"{k}: {v}" for k, v in result.items())


def citation_audit(
    text: str, candidate_ids: list[str]
) -> tuple[list[dict[str, str]], list[str]]:
    found = re.findall(r"\[([^\]]+)\]", text)
    seen: set[str] = set()
    citations: list[dict[str, str]] = []
    invalid: list[str] = []
    allowed = set(candidate_ids)
    for cid in found:
        if cid in allowed and cid not in seen:
            citations.append({"chunk_id": cid})
            seen.add(cid)
        elif cid not in allowed and cid not in invalid:
            invalid.append(cid)
    return citations, invalid


_CITATION_MARKUP_RE = re.compile(r"\[[^\]\n]{0,240}(?:\]|$)")


def strip_citation_markup(text: str) -> str:
    """Remove model-authored citation brackets before UI rendering."""
    cleaned = _CITATION_MARKUP_RE.sub("", text or "")
    return re.sub(r"\s+([,.;!?])", r"\1", cleaned)


def _extract_citations(text: str, candidate_ids: list[str]) -> list[dict[str, str]]:
    """Backward-compatible helper used by older tests/callers."""
    return citation_audit(text, candidate_ids)[0]
