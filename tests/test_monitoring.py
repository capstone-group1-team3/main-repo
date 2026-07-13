import json
import logging
import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from prometheus_client import generate_latest

from app.monitoring.middleware import (
    MetricsMiddleware, RequestIdMiddleware, StructuredLoggingMiddleware,
)
from app.api import routes_chat
from app.auth.auth_service import Identity
from app.agents.orchestrator.state import OrchestratorState


def _app():
    app = FastAPI()
    app.add_middleware(MetricsMiddleware)
    app.add_middleware(StructuredLoggingMiddleware)
    app.add_middleware(RequestIdMiddleware)

    @app.get("/items/{item_id}")
    def item(item_id: str, request: Request):
        return {"request_id": request.state.request_id}

    @app.get("/explode")
    def explode():
        raise RuntimeError("private detail")

    return app


def test_request_id_generated_and_agrees_with_response():
    response = TestClient(_app()).get("/items/private-order-id")
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == response.json()["request_id"]


def test_valid_incoming_request_id_is_preserved():
    response = TestClient(_app()).get(
        "/items/123", headers={"X-Request-ID": "eval-request-01"}
    )
    assert response.headers["X-Request-ID"] == "eval-request-01"


def test_invalid_request_id_is_replaced():
    bad = "contains spaces" + ("x" * 100)
    response = TestClient(_app()).get("/items/123", headers={"X-Request-ID": bad})
    assert response.headers["X-Request-ID"] != bad
    assert len(response.headers["X-Request-ID"]) <= 64


def test_metrics_use_route_template_and_exclude_identifier():
    TestClient(_app()).get("/items/private-order-id")
    text = generate_latest().decode()
    assert 'route="/items/{item_id}"' in text
    assert "private-order-id" not in text


def test_completion_log_omits_raw_path_and_private_error(caplog):
    client = TestClient(_app(), raise_server_exceptions=False)
    with caplog.at_level(logging.INFO, logger="app.request"):
        response = client.get("/explode")
    assert response.status_code == 500
    events = [json.loads(r.message) for r in caplog.records if r.name == "app.request"]
    assert events and events[-1]["route"] == "/explode"
    assert "private detail" not in caplog.text


def test_chat_response_uses_middleware_request_id(monkeypatch):
    state = OrchestratorState(
        request_id="http-request-1", customer_id="TEST-CUSTOMER",
        conversation_id="conversation", message="hello",
        intent="policy_question", done=True, completion_reason="completed",
    )
    monkeypatch.setattr(routes_chat.orchestrator_agent, "run", lambda **kwargs: state)
    monkeypatch.setattr(
        routes_chat.chatbot_response_agent, "run",
        lambda current: {"answer": "safe", "citations": [], "action_taken": None},
    )
    request = SimpleNamespace(state=SimpleNamespace(request_id="http-request-1"))
    response = routes_chat.chat(
        routes_chat.ChatRequest(message="hello"), request,
        Identity(customer_id="TEST-CUSTOMER", email="customer@example.com", role="customer"),
    )
    assert response.request_id == "http-request-1"
