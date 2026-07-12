"""
main.py — FastAPI application factory.

Middleware order (added in reverse so RequestId runs first on the way in):
  MetricsMiddleware         (innermost — times the handler)
  StructuredLoggingMiddleware
  RequestIdMiddleware       (outermost — generates X-Request-ID)
"""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
import logging
import logging.config

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.monitoring.middleware import (
    MetricsMiddleware,
    StructuredLoggingMiddleware,
    RequestIdMiddleware,
)
from app.api.routes_auth import router as auth_router
from app.api.routes_chat import router as chat_router
from app.api.routes_orders import router as orders_router
from app.api.routes_health import health_router, metrics_router
from app.rag.embeddings import get_embedding_model

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Load process-wide resources before Uvicorn reports startup complete."""
    await asyncio.to_thread(get_embedding_model)
    yield

app = FastAPI(
    title="E-commerce AI Customer Support Platform",
    version="1.0.0",
    description="Agentic support system: hybrid RAG + Neo4j knowledge graph + bounded orchestrator loop.",
    redirect_slashes=False,   # prevents 307 redirect that strips Authorization header
    lifespan=lifespan,
)

# CORS (Next.js frontend on port 3000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Observability middlewares (reverse order: innermost last in add_middleware)
app.add_middleware(MetricsMiddleware)
app.add_middleware(StructuredLoggingMiddleware)
app.add_middleware(RequestIdMiddleware)

# Routers
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(orders_router)
app.include_router(health_router)
app.include_router(metrics_router)


@app.get("/")
def root():
    return {"service": "ecommerce-ai-support", "status": "running"}
