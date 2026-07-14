"""Intent detection for the FusionMind orchestrator.

The classifier uses deterministic, ordered rules first and an optional LLM
fallback second. The order is semantic rather than simply "policy first":

1. Existing ticket/request status
2. Explicit cancellation
3. Personal warranty/failure context
4. Explicit replacement/refund/return actions
5. Order tracking and payment issues
6. General policy questions
7. Generic damage and broad fallbacks

This prevents broad words such as ``refund``, ``return``, ``warranty`` and
``broken`` from overriding the user's actual requested action.
"""
from __future__ import annotations

import json
import re
import time
from typing import Any

from app.monitoring.metrics import INTENT_DETECTED, INTENT_DURATION, INTENT_FALLBACK

_ALLOWED_INTENTS = {
    "policy_question",
    "order_tracking",
    "refund_request",
    "return_request",
    "replacement_request",
    "cancel_order",
    "warranty_claim",
    "damaged_product",
    "payment_issue",
    "ticket_status",
}

_NUMBER_WORD = (
    r"(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten|"
    r"eleven|twelve|thirteen)"
)
_DURATION = rf"{_NUMBER_WORD}\s+(?:days?|weeks?|months?|years?)"

_TICKET_STATUS = re.compile(
    r"(?:"
    r"\b(?:ticket|case|request|claim)\b.{0,45}"
    r"\b(?:status|pending|update|progress|approved|what happened|waiting)\b"
    r"|"
    r"\b(?:status|pending|update|progress|what happened)\b.{0,45}"
    r"\b(?:ticket|case|request|claim)\b"
    r"|"
    r"\brefund request\b.{0,30}\b(?:pending|status|update|progress)\b"
    r"|"
    r"\bwaiting\s+\d+\s+(?:days?|weeks?)\s+for\s+(?:my\s+)?refund\b"
    r")",
    re.I,
)

_CANCEL_ACTION = re.compile(
    r"(?:"
    r"\b(?:can i|could i|please|i want to|i need to|i['’]?d like to)?"
    r"\s*cancel\b"
    r"|\bordered by mistake\b"
    r"|\b(?:stop|undo)\b.{0,25}\b(?:my\s+)?order\b"
    r"|\bdon['’]?t want\b.{0,25}\b(?:my\s+)?order\b"
    r")",
    re.I,
)

_FAILURE = re.compile(
    r"\b(?:broke|broken|cracked|stopped working|not working|doesn['’]?t work|"
    r"failed|malfunction(?:ed|ing)?|defect(?:ive)?|dead)\b",
    re.I,
)

_WARRANTY_CONTEXT = re.compile(
    rf"(?:"
    rf"\bafter\s+{_DURATION}\b"
    rf"|\b{_DURATION}\s+ago\b"
    r"|\bnormal use\b"
    r"|\bunder warranty\b"
    r"|\bstill covered\b"
    r"|\bis (?:it|this) covered\b"
    r"|\bno drops?\b"
    r"|\bnot from dropping\b"
    r"|\bno accidental damage\b"
    r"|\brepair(?:ed|ing)?\b"
    r"|\bwarranty claim\b"
    r")",
    re.I,
)

_WARRANTY_POLICY = re.compile(
    r"(?:"
    r"\b(?:maximum time|how long|how many|what is|what are)\b.{0,55}"
    r"\b(?:claim\s+)?warranty\b"
    r"|\bdoes (?:the )?warranty cover\b"
    r"|\bwhat (?:does|is).{0,30}\bwarranty\b.{0,30}\bcover\b"
    r"|\bwarranty\b.{0,30}\b(?:policy|rules?|terms?|period|coverage)\b"
    r")",
    re.I,
)

_REPLACEMENT_ACTION = re.compile(
    r"(?:"
    r"\breplac(?:e|ed|ement|ing)\b"
    r"|\bexchange(?:d|ment)?\b"
    r"|\bswap(?:ped|ping)?\b"
    r"|\bsend me (?:the )?(?:right|correct|new) one\b"
    r"|\bwant (?:a )?new one\b"
    r"|\bdifferent brand from what i ordered\b"
    r"|\bwrong item\b"
    r")",
    re.I,
)

_REFUND_ACTION = re.compile(
    r"\b(?:refund(?:ed|ing)?|money back|reimburse(?:ment|d)?|full refund)\b",
    re.I,
)

_RETURN_ACTION = re.compile(
    r"\b(?:return(?:ed|ing)?|send back|bring back)\b",
    re.I,
)

_ORDER_TRACKING = re.compile(
    r"(?:"
    r"\b(?:where is|where['’]s) my order\b"
    r"|\btrack(?:ing)?(?: my| the)? (?:order|shipment)\b"
    r"|\bhow do i track my shipment\b"
    r"|\bwhen will.{0,30}arrive\b"
    r"|\bsupposed to arrive\b"
    r"|\b(?:hasn['’]?t|haven['’]?t|didn['’]?t) arrive\b"
    r"|\bnever received\b"
    r"|\b(?:didn['’]?t|not) receive(?:d)?\b"
    r"|\bdelivery is late\b"
    r"|\border is late\b"
    r"|\bmarked as unavailable\b"
    r"|\bshows delivered\b"
    r"|\bhas shipped\b"
    r"|\bdidn['’]?t arrive at all\b"
    r")",
    re.I,
)

_PAYMENT_ISSUE = re.compile(
    r"(?:"
    r"\bpayment (?:failed|pending|issue|problem)\b"
    r"|\bcharg(?:e|ed) twice\b"
    r"|\bduplicate charge\b"
    r"|\bbilling (?:issue|problem)\b"
    r"|\bbank slip\b.{0,45}\b(?:not|hasn['’]?t|haven['’]?t)\b.{0,25}"
    r"\b(?:confirmed|charged)\b"
    r"|\bcard declined\b"
    r"|\bvoucher\b.{0,25}\bnot applied\b"
    r")",
    re.I,
)

_CLEAR_POLICY = re.compile(
    r"(?:"
    r"\b(?:what is|what are)\b.{0,60}\b(?:policy|policies|rules?|conditions?|terms?|guidelines?|requirements?|window|period|timeline)\b"
    r"|\b(?:am i|is my|are my|would i)\b.{0,60}\b(?:eligible|qualify|covered|allowed|entitled|able to)\b"
    r"|\b(?:can you explain|tell me about|describe|clarify)\b.{0,50}\b(?:policy|rule|process|condition|guideline|term)\b"
    r")",
    re.I,
)

_POLICY_QUESTION = re.compile(
    r"(?:"
    r"\b(?:what is|what are|what['’]?s|what does|what do|does|do you|is there|"
    r"who pays|how does|how do|how long|how many|what happens|can you explain|"
    r"tell me about|describe|clarify|what documents|what shipping methods)\b"
    r"|\b(?:policy|policies|rules?|conditions?|terms?|guidelines?|requirements?|"
    r"restocking fee|free return shipping|maximum time)\b"
    r")",
    re.I,
)

_DELIVERY_DAMAGE = re.compile(
    r"\b(?:arrived|delivered|received)\b.{0,45}"
    r"\b(?:damaged|broken|cracked|smashed|crushed|defective)\b",
    re.I,
)

_GENERIC_DAMAGE = re.compile(
    r"\b(?:damaged|broken|broke|defect(?:ive)?|smashed|cracked|crushed|"
    r"stopped working|not working)\b",
    re.I,
)

_NEGATED_REFUND = re.compile(
    r"\b(?:not (?:asking for|looking for|want(?:ing)?) (?:a )?refund|"
    r"don['’]?t want (?:a )?refund)\b",
    re.I,
)

_INDECISION = re.compile(
    r"(?:\bdo not know\b|\bdon'?t know\b|\bnot sure\b|\bcannot decide\b|"
    r"\bcan'?t decide\b|\bwhether\b.{0,100}\bor\b|\bshould i\b)",
    re.I,
)

_CONDITIONAL_RETURN = re.compile(
    r"(?:\b(?:can|could|would) i return\b.{0,80}\b(?:if|when|in case)\b|"
    r"\breturn\b.{0,60}\bif\b)",
    re.I,
)

_GREETING = re.compile(
    r"^\s*(?:hi|hello|hey|thanks|thank you)"
    r"(?:\s+(?:there|so much|for your help))?[!.?]*\s*$",
    re.I,
)


def is_greeting(message: str) -> bool:
    """Recognize stand-alone social turns before intent/RAG processing."""
    return bool(_GREETING.fullmatch(message or ""))


def _action_option_count(text: str) -> int:
    """Count distinct actions mentioned as possible next steps."""
    return sum(bool(pattern.search(text)) for pattern in (
        _REPLACEMENT_ACTION, _REFUND_ACTION, _RETURN_ACTION,
    ))

_LLM_PROMPT = """\
You are a customer-support intent classifier. Distinguish personal requests from
questions about general policy.

Priority guidance:
- Asking about an existing ticket/request/claim status -> ticket_status
- A product that failed after use or is being checked for warranty coverage -> warranty_claim
- Explicit requested action (refund, return, replace, cancel) -> that action intent
- A product damaged on arrival without another explicit requested action -> damaged_product
- General rules, timing, coverage, requirements, or process -> policy_question

{history_block}

Classify into ONE of: policy_question, order_tracking, refund_request, return_request,
replacement_request, cancel_order, warranty_claim, damaged_product, payment_issue, ticket_status.

Return ONLY JSON (no markdown): {{"intent": "<intent>", "confidence": <0-1>, "reason": "<sentence>"}}

Message: {message}"""


def detect_intent(
    message: str,
    history: list[dict[str, str]] | None = None,
    use_llm_fallback: bool = True,
) -> dict[str, Any]:
    """Classify a customer message into one supported intent."""
    started = time.perf_counter()
    text = " ".join(message.strip().split())

    # 1. Existing records/status must win over words such as refund/warranty.
    if _TICKET_STATUS.search(text):
        return _result("ticket_status", 0.96, "existing-request status", started)

    # 2. Explicit contrast resolves messages such as "refund, not replacement".
    if re.search(r"\brefund\b.{0,25}\bnot (?:a )?replacement\b", text, re.I):
        return _result("refund_request", 0.97, "explicit refund preference", started)
    if re.search(r"\breplacement\b.{0,25}\bnot (?:a )?refund\b", text, re.I):
        return _result("replacement_request", 0.97, "explicit replacement preference", started)

    # 3. Cancellation is an operational request even when phrased as a question.
    if _CANCEL_ACTION.search(text):
        return _result("cancel_order", 0.95, "cancellation request", started)

    # 4. A known mixed defective return/warranty flow maps to replacement handling.
    if (
        re.search(r"\bdefective\b", text, re.I)
        and re.search(r"\breturn\b", text, re.I)
        and re.search(r"\bwarranty\b", text, re.I)
    ):
        return _result(
            "replacement_request",
            0.90,
            "defective-item replacement flow",
            started,
        )

    # 5. General warranty timing/coverage questions are policy, not claims.
    if _WARRANTY_POLICY.search(text):
        return _result("policy_question", 0.95, "warranty policy question", started)

    # 6. Personal product failure plus time/use/coverage context is a warranty claim.
    if _FAILURE.search(text) and _WARRANTY_CONTEXT.search(text):
        return _result("warranty_claim", 0.95, "product failure with warranty context", started)
    if (
        re.search(r"\b(?:under warranty|warranty claim|claim warranty)\b", text, re.I)
        and re.search(r"\b(?:my|the|this|it)\b", text, re.I)
    ):
        return _result("warranty_claim", 0.94, "explicit personal warranty claim", started)

    # Multiple possible actions plus indecision describe the issue; they do not
    # authorize any one action.
    if (
        (_DELIVERY_DAMAGE.search(text) or _GENERIC_DAMAGE.search(text))
        and _INDECISION.search(text)
        and _action_option_count(text) >= 2
    ):
        return _result("damaged_product", 0.94, "damaged item with undecided action", started)

    # 7. Unambiguous general policy phrasing before action keywords.
    if _CLEAR_POLICY.search(text):
        return _result("policy_question", 0.95, "clear policy question", started)

    # 8. Explicit requested actions. Negated alternatives do not take priority.
    if _REPLACEMENT_ACTION.search(text) and not re.search(
        r"\bnot (?:a )?replacement\b", text, re.I
    ):
        return _result("replacement_request", 0.94, "replacement request", started)

    if _REFUND_ACTION.search(text) and not _NEGATED_REFUND.search(text):
        policy_timing = re.search(
            r"\b(?:how long|how many days|how does|what happens|policy|process|"
            r"when returning|if i return)\b",
            text,
            re.I,
        )
        explicit_get_refund = re.search(
            r"\b(?:how do i get|i want|i need|please|give me|get my|"
            r"haven['’]?t received|money back|full refund)\b",
            text,
            re.I,
        )
        if policy_timing and not explicit_get_refund:
            return _result("policy_question", 0.94, "refund policy question", started)
        return _result("refund_request", 0.94, "refund request", started)

    # A hypothetical return condition must not override an active tracking goal.
    if _ORDER_TRACKING.search(text) and _CONDITIONAL_RETURN.search(text):
        return _result("order_tracking", 0.95, "tracking request with conditional return", started)

    if _RETURN_ACTION.search(text):
        return_policy = re.search(
            r"\b(?:policy|free return shipping|restocking fee|who pays|how long do i have|"
            r"how long|does that affect|can i return a product i opened|what happens|"
            r"how does)\b",
            text,
            re.I,
        )
        if return_policy:
            return _result("policy_question", 0.94, "return policy question", started)
        return _result("return_request", 0.93, "return request", started)

    # 9. Read-only operational intents.
    if _ORDER_TRACKING.search(text):
        return _result("order_tracking", 0.94, "order tracking or delivery issue", started)

    if _PAYMENT_ISSUE.search(text):
        return _result("payment_issue", 0.94, "payment problem", started)

    # 10. General policy questions are checked after personal operational context.
    if _POLICY_QUESTION.search(text):
        return _result("policy_question", 0.93, "general policy question", started)

    # 11. Damage without an explicit requested action.
    if _DELIVERY_DAMAGE.search(text) or _GENERIC_DAMAGE.search(text):
        return _result("damaged_product", 0.88, "product damage report", started)

    # 12. Conservative broad fallbacks.
    broad_patterns: tuple[tuple[re.Pattern[str], str], ...] = (
        (re.compile(r"\brefund\b", re.I), "refund_request"),
        (re.compile(r"\breturn\b", re.I), "return_request"),
        (re.compile(r"\bcancel\b", re.I), "cancel_order"),
        (re.compile(r"\bwarranty\b", re.I), "warranty_claim"),
        (re.compile(r"\bpayment\b", re.I), "payment_issue"),
    )
    for pattern, intent in broad_patterns:
        if pattern.search(text):
            return _result(intent, 0.75, "broad keyword fallback", started)

    # 13. Optional LLM fallback.
    if use_llm_fallback:
        result = _llm_detect(text, history or [])
        outcome = "failure" if result.get("reason") == "llm fallback failed" else "success"
        INTENT_FALLBACK.labels(outcome=outcome).inc()
        return _record(result, started, outcome)

    return _result("policy_question", 0.30, "safe default fallback", started)


def _result(
    intent: str,
    confidence: float,
    reason: str,
    started: float,
) -> dict[str, Any]:
    return _record(
        {"intent": intent, "confidence": confidence, "reason": reason},
        started,
    )


def _record(
    result: dict[str, Any],
    started: float,
    outcome: str = "success",
) -> dict[str, Any]:
    intent = str(result.get("intent", ""))
    if intent not in _ALLOWED_INTENTS:
        result = {
            "intent": "policy_question",
            "confidence": 0.25,
            "reason": "invalid classifier output",
        }
        intent = "policy_question"
        outcome = "failure"

    INTENT_DURATION.labels(outcome=outcome).observe(time.perf_counter() - started)
    INTENT_DETECTED.labels(intent=intent, outcome=outcome).inc()
    return result


def _llm_detect(message: str, history: list[dict[str, str]]) -> dict[str, Any]:
    try:
        from app.llm.llm_client import chat_complete

        history_block = ""
        if history:
            turns = history[-4:]
            history_block = "Conversation:\n" + "\n".join(
                f"{turn['role'].upper()}: {turn['content']}" for turn in turns
            ) + "\n"

        raw = chat_complete(
            _LLM_PROMPT.format(history_block=history_block, message=message),
            temperature=0,
        )
        parsed = json.loads(raw)
        if not isinstance(parsed, dict):
            raise ValueError("LLM intent response must be an object")
        return parsed
    except (ImportError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return {
            "intent": "policy_question",
            "confidence": 0.25,
            "reason": "llm fallback failed",
        }
    except Exception:
        # Keep network/provider failures from breaking the request path.
        return {
            "intent": "policy_question",
            "confidence": 0.25,
            "reason": "llm fallback failed",
        }
