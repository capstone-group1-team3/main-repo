"""
agents/rag_policy/retriever.py — query-time hybrid retrieval.

Embeds the query with BGE-M3 (same model as ingestion) and runs Weaviate hybrid
search (BM25 + vector, alpha=0.5). Returns candidate chunks with their chunk_id
so the caller can enforce grounding (every citation must be in this candidate set).
"""
from __future__ import annotations

from typing import Any
import time

from app.config.settings import settings
from app.rag.embeddings import embed_text
from app.rag import vector_store as vs
from app.monitoring.metrics import (
    RAG_DURATION, RAG_EMPTY, RAG_FAILURES, RAG_REQUESTS, RAG_RESULT_COUNT,
)


def retrieve(query: str, top_k: int | None = None, alpha: float | None = None) -> list[dict[str, Any]]:
    mode = "hybrid"
    started = time.perf_counter()
    client = None
    try:
        query_vector = embed_text(query)
        client = vs.connect()
        candidates = vs.hybrid_search(
            client,
            query=query,
            query_vector=query_vector,
            top_k=top_k or settings.retrieval_top_k,
            alpha=alpha if alpha is not None else settings.hybrid_alpha,
        )
        RAG_REQUESTS.labels(mode=mode, outcome="success").inc()
        RAG_RESULT_COUNT.labels(mode=mode).observe(len(candidates))
        if not candidates:
            RAG_EMPTY.labels(mode=mode).inc()
        return candidates
    except Exception as exc:
        RAG_REQUESTS.labels(mode=mode, outcome="failure").inc()
        category = "timeout" if "timeout" in type(exc).__name__.lower() else "dependency"
        RAG_FAILURES.labels(error_category=category).inc()
        raise
    finally:
        RAG_DURATION.labels(mode=mode).observe(time.perf_counter() - started)
        if client is not None:
            client.close()
