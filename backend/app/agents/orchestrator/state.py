"""agents/orchestrator/state.py — per-request working memory (v2)."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass
class GoalState:
    type:   str
    status: str = "pending"
    result: dict[str, Any] | None = None


@dataclass
class OrchestratorState:
    # identity
    request_id:      str = ""
    customer_id:     str = ""
    conversation_id: str = ""
    message:         str = ""

    # conversation
    conversation_history: list[dict[str, str]] = field(default_factory=list)

    # detection
    intent:     str   = ""
    confidence: float = 0.0
    entities:   dict[str, Any] = field(default_factory=dict)

    # multi-goal
    goals: list[GoalState] = field(default_factory=list)

    # tool outputs
    policy_evidence: str | None            = None
    policy_sources:  list[str]             = field(default_factory=list)
    candidate_ids:   list[str]             = field(default_factory=list)
    order_data:      dict[str, Any] | None = None
    orders:          list[dict[str, Any]]  = field(default_factory=list)
    tickets:         list[dict[str, Any]]  = field(default_factory=list)
    requests:        list[dict[str, Any]]  = field(default_factory=list)
    ownership_ok:    bool                  = True
    action_result:   dict[str, Any] | None = None

    # Phase-1 eligibility (populated BEFORE showing confirmation)
    eligibility_result: dict[str, Any] | None = None

    # confirmation gate
    pending_action:        dict[str, Any] | None = None
    confirmation_required: bool                  = False
    confirmation_received: bool                  = False
    confirmation_context:  dict[str, Any] | None = None

    # plan reuse
    current_plan:  list[str] = field(default_factory=list)
    plan_valid:    bool       = False
    replan_needed: bool       = False

    # loop control
    tools_used:           list[str]  = field(default_factory=list)
    iterations:           int        = 0
    done:                 bool       = False
    clarification_needed: str | None = None
    error:                str | None = None
    completion_reason:    str | None = None
    asked_for_order_id:   bool       = False

    # observations + progress
    observations:       list[dict[str, Any]] = field(default_factory=list)
    state_fingerprints: list[str]            = field(default_factory=list)

    # planning trace (never send to customers)
    planning_trace: list[dict[str, Any]] = field(default_factory=list)
    invalid_citation_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        import dataclasses
        return dataclasses.asdict(self)

    def reset_confirmation(self) -> None:
        self.pending_action        = None
        self.confirmation_required = False
        self.confirmation_received = False
        self.confirmation_context  = None
        self.eligibility_result    = None

    def invalidate_if_context_changed(self) -> None:
        if not self.confirmation_context:
            return
        ctx_oid   = self.confirmation_context.get("order_id")
        state_oid = (self.order_data or {}).get("order_id")
        ctx_intent = self.confirmation_context.get("intent")
        if ctx_oid != state_oid or ctx_intent != self.intent:
            self.reset_confirmation()
