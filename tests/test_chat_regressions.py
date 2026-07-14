import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.agents.orchestrator import orchestrator_agent
from app.agents.orchestrator.state import OrchestratorState
from app.agents.response import chatbot_response_agent
from app.api import routes_chat
from app.auth.auth_service import Identity


CHUNK = "refund_policy.md::body::0"


def _policy_state(message="What is the refund policy?"):
    return SimpleNamespace(
        intent="policy_question",
        message=message,
        candidate_ids=[CHUNK],
        policy_evidence=f"[{CHUNK}] (refund_policy.md — body)\nRefunds are available within 14 days.",
        invalid_citation_ids=[],
        policy_sources=["refund_policy.md"],
        order_data=None,
        clarification_needed=None,
        ownership_ok=True,
        error=None,
        action_result=None,
    )


def test_greeting_does_not_call_rag(monkeypatch):
    from app.agents.rag_policy import rag_policy_agent

    monkeypatch.setattr(
        rag_policy_agent,
        "run",
        lambda **_: (_ for _ in ()).throw(AssertionError("greeting called RAG")),
    )
    state = orchestrator_agent.run("hello", "CUST00001")
    assert state.intent == "greeting"
    assert state.done is True
    assert state.tools_used == []


def test_greeting_does_not_require_citations():
    state = SimpleNamespace(intent="greeting", message="thanks")
    result = chatbot_response_agent.run(state)
    assert result["citations"] == []
    assert "How can I help" in result["answer"]


def test_refund_policy_returns_success_and_refund_source(monkeypatch):
    state = OrchestratorState(
        request_id="request-1", customer_id="CUST00001",
        conversation_id="conversation-1", message="What is the refund policy?",
        intent="policy_question", done=True, completion_reason="completed",
        policy_evidence=f"[{CHUNK}] (refund_policy.md — body)\nRefunds are available within 14 days.",
        candidate_ids=[CHUNK], policy_sources=["refund_policy.md"],
    )
    monkeypatch.setattr(routes_chat.orchestrator_agent, "run", lambda **_: state)
    monkeypatch.setattr(
        routes_chat.chatbot_response_agent,
        "run",
        lambda current: {
            "answer": "Refunds are available [refund_policy.md::body::0].",
            "citations": [{"chunk_id": CHUNK}], "action_taken": None,
        },
    )
    response = routes_chat.chat(
        routes_chat.ChatRequest(message="What is the refund policy?"),
        SimpleNamespace(state=SimpleNamespace(request_id="request-1")),
        Identity(customer_id="CUST00001", email="demo@example.com", role="customer"),
    )
    assert response.answer == "Refunds are available."
    assert response.citations == [{"source": "refund_policy.md", "title": "Refund Policy"}]


def test_malformed_generated_citation_is_normalized(monkeypatch):
    monkeypatch.setattr(
        "app.llm.llm_client.chat_complete",
        lambda *args, **kwargs: "Refunds are available [refund_policy",
    )
    answer, citations = chatbot_response_agent._policy_only_answer(_policy_state())
    assert "[" not in answer
    assert answer == "I cannot answer this from the available sources."
    assert citations == []


def test_fresh_policy_requests_are_consistent(monkeypatch):
    calls = []

    def complete(*args, **kwargs):
        calls.append(kwargs["temperature"])
        return '{"answer":"Refunds are available within 14 days.","citation_chunk_ids":["refund_policy.md::body::0"]}'

    monkeypatch.setattr("app.llm.llm_client.chat_complete", complete)
    first = chatbot_response_agent._policy_only_answer(_policy_state())[0:2]
    second = chatbot_response_agent._policy_only_answer(_policy_state())[0:2]
    assert first == second
    assert calls == [0.0, 0.0]


def test_unsupported_policy_claim_fails_closed(monkeypatch):
    monkeypatch.setattr(
        "app.llm.llm_client.chat_complete",
        lambda *args, **kwargs: '{"answer":"All refunds are guaranteed instantly.","citation_chunk_ids":["made-up::0"]}',
    )
    answer, citations = chatbot_response_agent._policy_only_answer(_policy_state())
    assert answer == "I cannot answer this from the available sources."
    assert citations == []
