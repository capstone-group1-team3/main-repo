import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.agents.response import chatbot_response_agent


DECLINE = "I cannot answer this from the available sources."


def _state():
    return SimpleNamespace(
        candidate_ids=["refund_policy.md::body::0"],
        policy_evidence=(
            "[refund_policy.md::body::0] (refund_policy.md - body)\n"
            "Refunds are available within the stated window."
        ),
        message="What is the refund policy?",
        invalid_citation_ids=[],
    )


def test_policy_answer_requires_a_valid_citation(monkeypatch):
    monkeypatch.setattr(
        "app.llm.llm_client.chat_complete",
        lambda *args, **kwargs: '{"answer":"Refunds are available.","citation_chunk_ids":[]}',
    )

    answer, citations = chatbot_response_agent._policy_only_answer(_state())

    assert answer == DECLINE
    assert citations == []


def test_policy_answer_keeps_supported_citation_and_uses_zero_temperature(
    monkeypatch,
):
    captured = {}

    def complete(*args, **kwargs):
        captured.update(kwargs)
        return '{"answer":"Refunds are available.","citation_chunk_ids":["refund_policy.md::body::0"]}'

    monkeypatch.setattr("app.llm.llm_client.chat_complete", complete)
    answer, citations = chatbot_response_agent._policy_only_answer(_state())

    assert answer.startswith("Refunds are available")
    assert citations == [{"chunk_id": "refund_policy.md::body::0"}]
    assert captured["temperature"] == 0.0
    assert "insufficient or unrelated" in captured["system"]


def test_policy_answer_declines_invalid_citation(monkeypatch):
    monkeypatch.setattr(
        "app.llm.llm_client.chat_complete",
        lambda *args, **kwargs: '{"answer":"Refunds are available.","citation_chunk_ids":["made-up::chunk"]}',
    )
    state = _state()

    answer, citations = chatbot_response_agent._policy_only_answer(state)

    assert answer == DECLINE
    assert citations == []
    assert state.invalid_citation_ids == ["made-up::chunk"]
