"""Unit and regression tests for deterministic intent detection."""
from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.agents.orchestrator.intent_detector import detect_intent


POLICY_QUESTIONS = [
    "What is the refund policy?",
    "What is your return policy?",
    "How does your refund process work?",
    "How long do refunds take?",
    "What are the refund conditions?",
    "Am I eligible for a refund?",
    "Can you explain the cancellation policy?",
    "What are the warranty rules?",
    "How does the return process work?",
    "What happens if my order arrives late?",
    "Does the warranty cover water damage?",
    "What is the maximum time I have to claim warranty?",
]

ACTION_CASES = [
    ("I want a refund.", "refund_request"),
    ("Refund my order.", "refund_request"),
    ("I want my money back.", "refund_request"),
    ("Please refund order ORD004.", "refund_request"),
    ("I want to cancel my order.", "cancel_order"),
    ("Can I cancel my order?", "cancel_order"),
    ("Cancel ORD004.", "cancel_order"),
    ("I want to return this product.", "return_request"),
    ("Please replace my damaged product.", "replacement_request"),
    ("Where is my order?", "order_tracking"),
    ("Track order ORD005.", "order_tracking"),
    ("My laptop arrived damaged.", "damaged_product"),
    ("My payment was charged twice.", "payment_issue"),
    ("What is the status of my ticket?", "ticket_status"),
]

WARRANTY_CONTEXT_CASES = [
    "My phone screen cracked after 3 months of normal use. Is it covered?",
    "The watch I bought six months ago stopped working. What can I do?",
    "My laptop is broken after 8 months. Is it under warranty? And can I also get a refund?",
    "My tablet broke 13 months after delivery. Is that still covered?",
    "The camera stopped working after two months. Not from dropping it.",
    "My TV broke after 11 months. There was no damage. I want it repaired or replaced.",
]

PRIORITY_CASES = [
    (
        "My item arrived broken. I want a replacement not a refund.",
        "replacement_request",
    ),
    (
        "I received the right item but it's damaged. I want a refund not a replacement.",
        "refund_request",
    ),
    (
        "I see my refund request is still pending. What do I need to do?",
        "ticket_status",
    ),
    (
        "I've been waiting 3 weeks for my refund. Is this normal?",
        "ticket_status",
    ),
    (
        "The bag arrived damaged. How do I get a refund and how long will it take?",
        "refund_request",
    ),
    (
        "The product I received was a different brand from what I ordered.",
        "replacement_request",
    ),
    (
        "My order was supposed to arrive yesterday but it hasn't.",
        "order_tracking",
    ),
    (
        "I paid with a bank slip and haven't been charged yet.",
        "payment_issue",
    ),
]


@pytest.mark.parametrize("message", POLICY_QUESTIONS)
def test_policy_questions_classify_correctly(message: str) -> None:
    result = detect_intent(message, use_llm_fallback=False)
    assert result["intent"] == "policy_question"


@pytest.mark.parametrize(("message", "expected"), ACTION_CASES)
def test_action_requests_classify_correctly(message: str, expected: str) -> None:
    result = detect_intent(message, use_llm_fallback=False)
    assert result["intent"] == expected


@pytest.mark.parametrize("message", WARRANTY_CONTEXT_CASES)
def test_personal_failure_with_warranty_context_is_claim(message: str) -> None:
    result = detect_intent(message, use_llm_fallback=False)
    assert result["intent"] == "warranty_claim"


@pytest.mark.parametrize(("message", "expected"), PRIORITY_CASES)
def test_intent_priority_regressions(message: str, expected: str) -> None:
    result = detect_intent(message, use_llm_fallback=False)
    assert result["intent"] == expected


def test_policy_question_has_high_confidence() -> None:
    result = detect_intent("What is the refund policy?", use_llm_fallback=False)
    assert result["confidence"] >= 0.85


def test_refund_request_has_high_confidence() -> None:
    result = detect_intent("I want a refund.", use_llm_fallback=False)
    assert result["confidence"] >= 0.85


def test_unknown_message_uses_safe_default_without_llm() -> None:
    result = detect_intent("Hello there", use_llm_fallback=False)
    assert result["intent"] == "policy_question"
    assert result["confidence"] < 0.50