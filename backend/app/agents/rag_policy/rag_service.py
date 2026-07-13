"""
agents/rag_policy/rag_service.py — policy retrieval service.

Given a query (optionally hinted by intent), returns:
  - evidence: the top retrieved policy passages (text + source + section + chunk_id)
  - candidate_ids: the set of chunk_ids returned  -> used to enforce grounding
    (the Grounded Policy Response Rate metric: every citation must be here)

Intent is used to bias the query toward the right policy document when helpful.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.agents.rag_policy.retriever import retrieve
from app.config.settings import settings
from app.monitoring.metrics import RAG_EMPTY

# maps an intent to the policy file that should govern the answer
INTENT_POLICY_HINT = {
    "refund_request": "refund policy",
    "return_request": "return policy",
    "replacement_request": "replacement policy",
    "warranty_claim": "warranty policy",
    "damaged_product": "refund policy damaged item",
    "payment_issue": "payment policy",
    "order_tracking": "shipping policy delivery",
    "cancel_order": "shipping policy cancellation",
    "policy_question": "",
}


@dataclass
class PolicyEvidence:
    evidence: list[dict[str, Any]] = field(default_factory=list)
    candidate_ids: list[str] = field(default_factory=list)

    @property
    def top_source(self) -> str | None:
        return self.evidence[0]["source"] if self.evidence else None

    def as_context(self) -> str:
        """Join evidence into a prompt-ready context block with citation ids."""
        return "\n\n".join(
            f"[{c['chunk_id']}] ({c['source']} — {c['section']})\n{c['text']}"
            for c in self.evidence
        )


def get_policy_evidence(query: str, intent: str | None = None,
                        top_k: int | None = None) -> PolicyEvidence:
    hint = INTENT_POLICY_HINT.get(intent or "", "")
    search_query = f"{query} {hint}".strip()
    candidates = retrieve(search_query, top_k=top_k)
    # Weaviate relative-score fusion is normalized; a small configurable floor
    # prevents arbitrary top-k results from being treated as policy evidence.
    raw_candidates = candidates
    candidates = [
        c for c in candidates
        if c.get("score") is not None and float(c["score"]) >= settings.retrieval_min_score
    ]
    if raw_candidates and not candidates:
        RAG_EMPTY.labels(mode="hybrid").inc()
    return PolicyEvidence(
        evidence=candidates,
        candidate_ids=[c["chunk_id"] for c in candidates],
    )
