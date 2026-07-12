"""Safe liveness, dependency readiness, and Prometheus exposition."""
from __future__ import annotations

import logging
import socket
from urllib.request import urlopen
from fastapi import APIRouter, Response, status
from fastapi.responses import PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.graph.neo4j_client import graph_client
from app.config.settings import settings

logger = logging.getLogger("app.readiness")
health_router = APIRouter(tags=["health"])


@health_router.get("/health")
def health():
    """Process liveness only; never performs dependency I/O."""
    return {"status": "ok"}


@health_router.get("/ready")
def ready(response: Response):
    dependencies = {"neo4j": "unavailable", "weaviate": "unavailable"}
    try:
        graph_client.read("RETURN 1", query_type="readiness")
        dependencies["neo4j"] = "ok"
    except Exception as exc:
        logger.warning("Neo4j readiness failed: %s", type(exc).__name__)

    try:
        url = (
            f"http://{settings.weaviate_host}:{settings.weaviate_http_port}"
            "/v1/.well-known/ready"
        )
        with urlopen(url, timeout=settings.readiness_timeout_seconds) as result:
            if result.status != 200:
                raise RuntimeError("not ready")
        with socket.create_connection(
            (settings.weaviate_host, settings.weaviate_grpc_port),
            timeout=settings.readiness_timeout_seconds,
        ):
            pass
        dependencies["weaviate"] = "ok"
    except Exception as exc:
        logger.warning("Weaviate readiness failed: %s", type(exc).__name__)

    is_ready = all(value == "ok" for value in dependencies.values())
    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {"status": "ready" if is_ready else "not_ready", "dependencies": dependencies}


metrics_router = APIRouter(tags=["metrics"])


@metrics_router.get("/metrics", response_class=PlainTextResponse)
def metrics():
    return PlainTextResponse(
        content=generate_latest().decode("utf-8"), media_type=CONTENT_TYPE_LATEST
    )
