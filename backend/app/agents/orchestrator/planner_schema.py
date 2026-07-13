from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel, Field

class PlannerDecision(BaseModel):
    decision: Literal["rag_policy","order_graph","action","ask_clarification","respond"]
    corrected_intent: Literal[
        "policy_question","order_tracking","refund_request","return_request",
        "replacement_request","cancel_order","warranty_claim","damaged_product",
        "payment_issue","ticket_status",
    ] | None = None
    reason:     str = Field(min_length=1, max_length=300)
    confidence: float = Field(ge=0.0, le=1.0)
    arguments:  dict[str, Any] = Field(default_factory=dict)

class PlannerTrace(BaseModel):
    initial_intent:   str
    corrected_intent: str | None
    decision:         str
    reason:           str
    confidence:       float
    fallback_used:    bool = False
    fast_path_used:   bool = False
