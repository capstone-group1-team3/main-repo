"""
main.py — FastAPI application factory.

Middleware order (added in reverse so RequestId runs first on the way in):
  MetricsMiddleware         (innermost — times the handler)
  StructuredLoggingMiddleware
  RequestIdMiddleware       (outermost — generates X-Request-ID)
"""
from __future__ import annotations

from contextlib import asynccontextmanager
import logging
import logging.config
from time import perf_counter

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
from app.config.settings import settings
from app.rag.embeddings import embed_text

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Load and warm the embedding model before accepting any requests."""
    started_at = perf_counter()
    logger.info("Loading embedding model at startup: %s", settings.embedding_model)

    # Running one real embedding guarantees that model weights and the complete
    # inference path are ready before Uvicorn reports startup as complete.
    warmup_vector = embed_text("embedding model startup warmup")

    logger.info(
        "Embedding model ready: model=%s dimensions=%s startup_ms=%.2f",
        settings.embedding_model,
        len(warmup_vector),
        (perf_counter() - started_at) * 1000,
    )
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
