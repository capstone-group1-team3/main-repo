"""Security regression tests that do not require live services."""
import os
import sys
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.schemas.auth_schema import RegisterRequest
from app.auth import auth_service
from app.agents.orchestrator.state import OrchestratorState
from app.agents.orchestrator import loop_controller
from app.auth.auth_middleware import require_staff
from fastapi import HTTPException
from fastapi.testclient import TestClient
from app.main import app
from app.api import routes_auth


@pytest.mark.parametrize("role", ["staff", "admin"])
def test_public_registration_rejects_privileged_role(role):
    with pytest.raises(ValidationError):
        RegisterRequest(
            email="customer@example.com", password="secure-pass",
            customer_id="TEST-CUSTOMER", role=role,
        )


def test_public_registration_schema_has_no_role_field():
    request = RegisterRequest(
        email="customer@example.com", password="secure-pass",
        customer_id="TEST-CUSTOMER",
    )
    assert "role" not in request.model_dump()


def test_public_registration_api_rejects_role_field():
    response = TestClient(app).post("/auth/register", json={
        "email": "customer@example.com", "password": "secure-pass",
        "customer_id": "TEST-CUSTOMER", "role": "admin",
    })
    assert response.status_code == 422


def test_public_registration_api_assigns_customer_role(monkeypatch):
    captured = {}
    def fake_register(**kwargs):
        captured.update(kwargs)
        return auth_service.Identity(kwargs["customer_id"], kwargs["email"], kwargs["role"])
    monkeypatch.setattr(routes_auth, "register", fake_register)
    response = TestClient(app).post("/auth/register", json={
        "email": "customer@example.com", "password": "secure-pass",
        "customer_id": "TEST-CUSTOMER",
    })
    assert response.status_code == 201
    assert response.json()["role"] == "customer"
    assert captured["role"] == "customer"


def test_registration_cannot_create_phantom_customer(monkeypatch):
    calls = {}

    class FakeGraph:
        def read(self, *args, **kwargs):
            return [{"n": 0}]

        def write(self, cypher, **kwargs):
            calls["cypher"] = cypher
            return []

    monkeypatch.setattr(auth_service, "graph_client", FakeGraph())
    monkeypatch.setattr(auth_service, "hash_password", lambda _: "redacted-test-hash")
    with pytest.raises(auth_service.AuthError, match="could not be verified"):
        auth_service.register(
            "customer@example.com", "secure-pass", "DOES-NOT-EXIST"
        )
    assert "MATCH (c:Customer" in calls["cypher"]
    assert "MERGE (c:Customer" not in calls["cypher"]


def test_privileged_account_creation_has_no_public_service_path():
    with pytest.raises(auth_service.AuthError, match="not supported"):
        auth_service.register(
            "staff@example.com", "secure-pass", "TEST-CUSTOMER", role="staff"
        )


def test_confirmed_action_reloads_current_owned_order(monkeypatch):
    current = {
        "order_id": "TEST-ORDER", "status": "shipped",
        "delivered_date": None, "payment_value": 10.0, "items": [],
    }
    monkeypatch.setattr(
        "app.agents.order_graph.graph_service.get_order", lambda customer, order: current
    )
    state = OrchestratorState(
        customer_id="TEST-CUSTOMER", intent="cancel_order",
        entities={"order_id": "TEST-ORDER"},
        order_data={"order_id": "TEST-ORDER", "status": "approved"},
        pending_action={"order_id": "TEST-ORDER"},
    )
    assert loop_controller._reload_current_owned_order(state) is True
    assert state.order_data["status"] == "shipped"


def test_confirmed_action_rejects_cross_customer_order(monkeypatch):
    monkeypatch.setattr(
        "app.agents.order_graph.graph_service.get_order", lambda customer, order: None
    )
    state = OrchestratorState(
        customer_id="CUSTOMER-A", intent="refund_request",
        entities={"order_id": "CUSTOMER-B-ORDER"},
    )
    assert loop_controller._reload_current_owned_order(state) is False


def test_staff_visibility_uses_server_identity_role():
    with pytest.raises(HTTPException) as exc:
        require_staff(auth_service.Identity("C", "c@example.com", "customer"))
    assert exc.value.status_code == 403
    staff = auth_service.Identity("S", "s@example.com", "staff")
    assert require_staff(staff) is staff
