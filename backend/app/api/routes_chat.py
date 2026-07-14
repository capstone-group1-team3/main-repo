"""
api/routes_chat.py — POST /chat with conversation_id persistence.
"""
from __future__ import annotations
import re
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.auth.auth_middleware import get_current_identity
from app.auth.auth_service import Identity
from app.agents.orchestrator import orchestrator_agent
from app.agents.response import chatbot_response_agent
from app.agents.response.response_formatter import strip_citation_markup
from app.monitoring.metrics import (
    GROUNDING_ANSWERED, GROUNDING_PASSED, GROUNDING_SOURCE_MISMATCH,
    TASK_COMPLETED,
)
from app.config.settings import settings

router = APIRouter(prefix="/chat", tags=["chat"])
DECLINE = "I cannot answer this from the available sources."
logger = logging.getLogger("app.chat")

_CHUNK_ID_RE = re.compile(
    r'[\[【［](?:chunk_id[:\s]*[^\]】］]+|[^\]】］]*\.md::[^\]】］]*|'
    r'[^\]】］]{0,60}::\d+)[\]】］]',
    re.I,
)


class HistoryMessage(BaseModel):
    role:    str
    content: str


class ChatRequest(BaseModel):
    message:         str = Field(min_length=1, max_length=2000)
    history:         list[HistoryMessage] = Field(default_factory=list)
    conversation_id: str | None = None


class ActionCard(BaseModel):
    action:     str
    request_id: str | None = None
    ticket_id:  str | None = None
    order_id:   str | None = None
    amount:     float | None = None
    status:     str | None = None
    next_step:  str | None = None
    reason:     str | None = None
    success:    bool = True


class ChatResponse(BaseModel):
    request_id:          str
    conversation_id:     str
    answer:              str
    intent:              str
    citations:           list[dict]
    action_taken:        str | None
    action_card:         ActionCard | None = None
    confirmation_prompt: str | None = None
    tools_used:          list[str]
    iterations:          int
    history:             list[dict]
    evaluation:          dict[str, Any] | None = None


@router.post("",  response_model=ChatResponse)
@router.post("/", response_model=ChatResponse)
def chat(
    body: ChatRequest, request: Request,
    identity: Identity = Depends(get_current_identity),
):
    rid     = request.state.request_id
    history = [{"role": m.role, "content": m.content} for m in body.history]

    try:
        state = orchestrator_agent.run(
            message=body.message,
            customer_id=identity.customer_id,
            request_id=rid,
            conversation_history=history,
            conversation_id=body.conversation_id,
        )
    except Exception as exc:
        logger.exception(
            "Chat orchestration failed request_id=%s error_type=%s detail=%s",
            rid, type(exc).__name__, _safe_exception_detail(exc),
        )
        raise HTTPException(status_code=500, detail="Something went wrong. Please try again.")

    # Confirmation gate
    if state.confirmation_required and not state.confirmation_received:
        _set_observability(request, state)
        prompt  = _confirmation_prompt(state)
        updated = history + [
            {"role": "user",      "content": body.message},
            {"role": "assistant", "content": prompt},
        ]
        return ChatResponse(
            request_id=rid, conversation_id=state.conversation_id,
            answer=prompt, intent=state.intent, citations=[],
            action_taken=None, action_card=None, confirmation_prompt=prompt,
            tools_used=state.tools_used, iterations=state.iterations, history=updated,
            evaluation=_evaluation_metadata(state, []),
        )

    try:
        resp = chatbot_response_agent.run(state)
    except Exception as exc:
        logger.exception(
            "Chat response generation failed request_id=%s error_type=%s detail=%s",
            rid, type(exc).__name__, _safe_exception_detail(exc),
        )
        raise HTTPException(status_code=500, detail="Something went wrong preparing the response.")

    uses_rag = (
        state.intent == "policy_question"
        and bool(state.policy_evidence)
        and bool(state.candidate_ids)
    )
    answer = resp.get("answer", "")
    if uses_rag:
        answer = strip_citation_markup(answer).strip()
    citations = resp.get("citations", []) if uses_rag else []
    cand_ids  = set(state.candidate_ids)

    if uses_rag and answer != DECLINE:
        GROUNDING_ANSWERED.inc()
        if citations and all(c.get("chunk_id","") in cand_ids for c in citations):
            GROUNDING_PASSED.inc()
    if uses_rag and state.invalid_citation_ids:
        GROUNDING_SOURCE_MISMATCH.inc(len(state.invalid_citation_ids))

    if state.action_result:
        TASK_COMPLETED.inc()

    _set_observability(request, state)

    updated = history + [
        {"role": "user",      "content": body.message},
        {"role": "assistant", "content": answer},
    ]

    return ChatResponse(
        request_id=rid, conversation_id=state.conversation_id,
        answer=answer, intent=state.intent,
        citations=_clean_cits(citations, cand_ids),
        action_taken=resp.get("action_taken"),
        action_card=_action_card(state) if state.action_result else None,
        confirmation_prompt=None,
        tools_used=state.tools_used, iterations=state.iterations, history=updated,
        evaluation=_evaluation_metadata(state, citations),
    )


def _confirmation_prompt(state: Any) -> str:
    pa     = state.pending_action or {}
    oid    = pa.get("order_id","your order")
    amount = pa.get("amount")
    intent = state.intent.replace("_"," ")
    lines  = [f"**{oid}** is eligible for {intent}."]
    if amount:
        lines.append(f"Refund amount: **${amount:.2f}**")
    if "photo_required" in (pa.get("requirements") or []):
        lines.append("Note: photo evidence will be required.")
    lines.append("Reply **yes** to confirm or **no** to cancel.")
    return "\n\n".join(lines)


def _action_card(state: Any) -> ActionCard:
    r      = state.action_result or {}
    action = r.get("action","")
    order  = state.order_data or {}
    return ActionCard(
        action=action,
        request_id=r.get("request_id"),
        ticket_id=r.get("ticket_id"),
        # Handlers normally execute with a freshly reloaded order, but keep
        # the result contract self-contained for denied/failed outcomes and
        # any handler that reports its order explicitly.
        order_id=order.get("order_id") or r.get("order_id"),
        amount=order.get("payment_value") or r.get("amount"),
        status=r.get("status"),
        next_step=r.get("next_step"),
        reason=r.get("reason"),
        success=not(action.endswith("_denied") or action.endswith("_failed")),
    )


def _clean_cits(citations: list[dict], cand_ids: set[str]) -> list[dict]:
    clean: list[dict] = []; seen: set[str] = set()
    for c in citations:
        cid   = c.get("chunk_id","")
        if cid not in cand_ids:
            continue
        src   = cid.split("::")[0] if "::" in cid else cid
        title = src.replace("_"," ").replace(".md","").title()
        if title and title not in seen:
            clean.append({"source": src, "title": title}); seen.add(title)
    return clean


def _evaluation_metadata(state: Any, citations: list[dict]) -> dict[str, Any] | None:
    if not settings.evaluation_metadata_enabled:
        return None
    accepted = [c.get("chunk_id") for c in citations if c.get("chunk_id")]
    return {
        "retrieved_candidate_chunk_ids": list(state.candidate_ids),
        "accepted_citation_chunk_ids": accepted,
        "invalid_citation_chunk_ids": list(state.invalid_citation_ids),
        "evidence_used_chunk_ids": accepted,
        "tools_used": list(state.tools_used),
        "completion_reason": state.completion_reason,
        "eligibility_result": state.eligibility_result,
    }


def _safe_exception_detail(exc: BaseException) -> str:
    """Keep provider errors useful while preventing credential leakage."""
    detail = str(exc)
    for marker in ("Bearer ", "api_key=", "token=", "password="):
        match = re.search(re.escape(marker), detail, flags=re.I)
        if match:
            detail = detail[:match.start()] + match.group(0) + "<redacted>"
    return detail[:500]


def _set_observability(request: Request, state: Any) -> None:
    result = state.action_result or {}
    action = str(result.get("action", "")) or None
    status_value = str(result.get("status", "")) or (
        "failed" if action and action.endswith("_failed") else
        "rejected" if action and action.endswith("_denied") else None
    )
    request.state.observability = {
        "intent": state.intent,
        "tools_used": list(state.tools_used),
        "iterations": state.iterations,
        "orchestrator_outcome": state.completion_reason,
        "action_type": action,
        "action_status": status_value,
        "error_category": "orchestrator" if state.error else None,
    }
