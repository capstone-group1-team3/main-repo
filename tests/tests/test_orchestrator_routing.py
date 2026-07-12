from types import SimpleNamespace

from app.agents.orchestrator.routing_rules import next_tool


def test_policy_flow_returns_respond_after_rag_is_available():
    state = SimpleNamespace(
        tools_used=["rag_policy"],
        policy_evidence=[],
        candidate_ids=[],
        policy_sources=[],
    )

    assert next_tool(state, "policy_question") == "respond"


def test_tracking_flow_returns_respond_after_graph_is_available():
    state = SimpleNamespace(
        tools_used=["order_graph"],
        order_data={},
        orders=[],
        tickets=[],
        requests=[],
    )

    assert next_tool(state, "order_tracking") == "respond"