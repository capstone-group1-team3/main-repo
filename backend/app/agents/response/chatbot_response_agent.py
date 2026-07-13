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

from typing import Any

from app.agents.response.response_formatter import format_grounded_reply
from app.agents.response.response_formatter import citation_audit
from app.agents.response.response_templates import (
    template_clarification,
    template_ownership_error,
    template_policy_only,
    template_order_tracking,
    template_action_result,
    template_error,
)


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
        f"Answer the customer's question using ONLY the policy evidence below.\n"
        f"Cite each chunk you use by including [chunk_id] inline. "
        f"Only use chunk_ids from this list: {ids}.\n\n"
        f"Evidence:\n{state.policy_evidence}\n\n"
        f"Customer question: {state.message}"
    )
    answer = chat_complete(prompt, max_tokens=400)
    citations, invalid = citation_audit(answer, state.candidate_ids)
    state.invalid_citation_ids = invalid
    return answer, citations


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
