import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from fastapi import Response
from app.api import routes_health


class ReadyClient:
    def is_ready(self):
        return True

    def close(self):
        pass


class ReadyHttp:
    status = 200
    def __enter__(self): return self
    def __exit__(self, *args): return None


class ReadySocket:
    def __enter__(self): return self
    def __exit__(self, *args): return None


def test_health_is_lightweight_and_safe():
    assert routes_health.health() == {"status": "ok"}


def test_ready_dependencies(monkeypatch):
    monkeypatch.setattr(routes_health.graph_client, "read", lambda *a, **k: [{"ok": 1}])
    monkeypatch.setattr(routes_health, "urlopen", lambda *a, **k: ReadyHttp())
    monkeypatch.setattr(routes_health.socket, "create_connection", lambda *a, **k: ReadySocket())
    response = Response()
    body = routes_health.ready(response)
    assert body == {"status": "ready", "dependencies": {"neo4j": "ok", "weaviate": "ok"}}
    assert response.status_code == 200


def test_ready_failure_is_503_without_exception_text(monkeypatch):
    def fail(*args, **kwargs):
        raise RuntimeError("secret-host-and-private-detail")

    monkeypatch.setattr(routes_health.graph_client, "read", fail)
    monkeypatch.setattr(routes_health, "urlopen", fail)
    response = Response()
    body = routes_health.ready(response)
    assert response.status_code == 503
    assert "secret-host" not in str(body)
    assert body["dependencies"] == {"neo4j": "unavailable", "weaviate": "unavailable"}


def test_metrics_exposes_fusionmind_collectors():
    response = routes_health.metrics()
    text = response.body.decode()
    assert "fusionmind_http_requests_total" in text
    assert "fusionmind_rag_retrieval" in text
    assert "fusionmind_neo4j_queries" in text
