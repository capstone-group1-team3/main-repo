"""Request identity, safe completion logging, and exception-safe HTTP metrics."""
from __future__ import annotations

import contextvars
import json
import logging
import re
import time
import uuid
from datetime import datetime, timezone

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.monitoring.metrics import (
    HTTP_DURATION, HTTP_ERRORS, HTTP_INFLIGHT, HTTP_REQUESTS,
)

request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "request_id", default="-"
)
logger = logging.getLogger("app.request")
_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$")


def valid_request_id(value: str | None) -> bool:
    return bool(value and _REQUEST_ID_RE.fullmatch(value))


def normalized_route(request: Request) -> str:
    """Return the registered route template, never an identifier-bearing raw path."""
    route = request.scope.get("route")
    template = getattr(route, "path", None)
    return template if isinstance(template, str) and template else "unmatched"


def _status_class(status: int) -> str:
    return f"{max(1, min(status // 100, 5))}xx"


def _error_category(exc: BaseException) -> str:
    name = type(exc).__name__.lower()
    if "timeout" in name:
        return "timeout"
    if "validation" in name:
        return "validation"
    if "connection" in name or "service" in name:
        return "dependency"
    return "unhandled"


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        incoming = request.headers.get("X-Request-ID")
        rid = incoming if valid_request_id(incoming) else uuid.uuid4().hex
        request.state.request_id = rid
        token = request_id_var.set(rid)
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = rid
            return response
        finally:
            request_id_var.reset(token)


class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        started = time.perf_counter()
        status = 500
        error_category = None
        try:
            response = await call_next(request)
            status = response.status_code
            return response
        except Exception as exc:
            error_category = _error_category(exc)
            raise
        finally:
            context = getattr(request.state, "observability", {}) or {}
            event = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "level": "ERROR" if status >= 500 else "INFO",
                "request_id": getattr(request.state, "request_id", request_id_var.get()),
                "method": request.method,
                "route": normalized_route(request),
                "status": status,
                "latency_ms": round((time.perf_counter() - started) * 1000, 2),
                "intent": context.get("intent"),
                "tools_used": context.get("tools_used", []),
                "iterations": context.get("iterations"),
                "orchestrator_outcome": context.get("orchestrator_outcome"),
                "action_type": context.get("action_type"),
                "action_status": context.get("action_status"),
                "error_category": error_category or context.get("error_category"),
            }
            logger.log(logging.ERROR if status >= 500 else logging.INFO, json.dumps(event))


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        method = request.method.upper()
        started = time.perf_counter()
        status = 500
        exception_recorded = False
        HTTP_INFLIGHT.inc()
        try:
            response = await call_next(request)
            status = response.status_code
            return response
        except Exception as exc:
            HTTP_ERRORS.labels(
                method=method, route=normalized_route(request),
                error_category=_error_category(exc),
            ).inc()
            exception_recorded = True
            raise
        finally:
            route = normalized_route(request)
            HTTP_INFLIGHT.dec()
            HTTP_DURATION.labels(method=method, route=route).observe(
                time.perf_counter() - started
            )
            HTTP_REQUESTS.labels(
                method=method, route=route, status_class=_status_class(status)
            ).inc()
            if status >= 500 and not exception_recorded:
                HTTP_ERRORS.labels(
                    method=method, route=route, error_category="server_response"
                ).inc()
