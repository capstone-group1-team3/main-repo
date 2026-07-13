"""
agents/rag_policy/rag_policy_agent.py — the RAG Policy Agent.

Orchestrator-facing tool. Given the customer's query + detected intent, it
retrieves the governing policy evidence and returns a structured result the
Orchestrator writes into state:

    {
      "policy_evidence": "<joined context with [chunk_id] citations>",
      "sources": ["refund_policy.md", ...],
      "candidate_ids": ["refund_policy.md::...::0", ...],
      "top_source": "refund_policy.md"
    }

candidate_ids is the grounding set: a response is "grounded" only if every
citation it makes is one of these ids (enforced by the Response Agent / eval).
"""
from __future__ import annotations

from typing import Any

from app.agents.rag_policy.rag_service import get_policy_evidence


def run(query: str, intent: str | None = None, top_k: int | None = None) -> dict[str, Any]:
    evidence = get_policy_evidence(query, intent=intent, top_k=top_k)
    sources: list[str] = []
    for c in evidence.evidence:
        if c["source"] not in sources:
            sources.append(c["source"])
    return {
        "policy_evidence": evidence.as_context(),
        "sources": sources,
        "candidate_ids": evidence.candidate_ids,
        "top_source": evidence.top_source,
    }
