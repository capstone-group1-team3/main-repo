"""
rag/vector_store.py — Weaviate v4 client: collection setup, upsert, hybrid search.

Design decisions baked in:
  - v4 client uses gRPC under the hood -> both ports must be reachable
    (HTTP 8080 + gRPC 50051). See docker-compose.
  - BYO vectors: we pass our own BGE-M3 vectors on insert and on query; Weaviate
    stores them and also runs BM25 over the text for hybrid search.
  - vectorizer is set to 'none' because we bring our own vectors.
"""
from __future__ import annotations

from typing import Any

import weaviate
from weaviate.classes.config import Configure, DataType, Property
from weaviate.classes.init import AdditionalConfig, Timeout
from weaviate.classes.query import HybridFusion, MetadataQuery

from app.config.settings import settings
from app.rag.embeddings import EMBED_DIM


def connect(*, readiness: bool = False) -> weaviate.WeaviateClient:
    """Connect to a local Weaviate over HTTP + gRPC."""
    additional_config = None
    if readiness:
        timeout = settings.readiness_timeout_seconds
        additional_config = AdditionalConfig(
            timeout=Timeout(init=timeout, query=timeout, insert=timeout)
        )
    return weaviate.connect_to_local(
        host=settings.weaviate_host,
        port=settings.weaviate_http_port,
        grpc_port=settings.weaviate_grpc_port,
        additional_config=additional_config,
    )


def ensure_collection(client: weaviate.WeaviateClient) -> None:
    """Create the PolicyChunk collection if it does not exist (BYO vectors)."""
    name = settings.weaviate_collection
    if client.collections.exists(name):
        return
    client.collections.create(
        name=name,
        vectorizer_config=Configure.Vectorizer.none(),
        properties=[
            Property(name="text", data_type=DataType.TEXT),
            Property(name="source", data_type=DataType.TEXT),
            Property(name="section", data_type=DataType.TEXT),
            Property(name="chunk_id", data_type=DataType.TEXT),
        ],
    )


def upsert_chunks(
    client: weaviate.WeaviateClient,
    chunks: list[dict[str, Any]],
    vectors: list[list[float]],
) -> int:
    """Insert/replace chunks with their precomputed vectors. Deterministic UUID
    from chunk_id makes this an upsert (re-ingesting the same chunk overwrites)."""
    import uuid

    coll = client.collections.get(settings.weaviate_collection)
    written = 0
    with coll.batch.dynamic() as batch:
        for chunk, vector in zip(chunks, vectors):
            obj_uuid = uuid.uuid5(uuid.NAMESPACE_URL, chunk["chunk_id"])
            batch.add_object(
                properties={
                    "text": chunk["text"],
                    "source": chunk["source"],
                    "section": chunk["section"],
                    "chunk_id": chunk["chunk_id"],
                },
                uuid=obj_uuid,
                vector=vector,
            )
            written += 1
    return written


def delete_missing(client: weaviate.WeaviateClient, keep_chunk_ids: set[str]) -> int:
    """Remove chunks no longer present in the source (upserts_and_delete behavior)."""
    from weaviate.classes.query import Filter

    coll = client.collections.get(settings.weaviate_collection)
    removed = 0
    for obj in coll.iterator():
        cid = obj.properties.get("chunk_id")
        if cid and cid not in keep_chunk_ids:
            coll.data.delete_by_id(obj.uuid)
            removed += 1
    return removed


def hybrid_search(
    client: weaviate.WeaviateClient,
    query: str,
    query_vector: list[float],
    top_k: int | None = None,
    alpha: float | None = None,
) -> list[dict[str, Any]]:
    """Hybrid BM25 + vector search. alpha=0.5 balances keyword and semantic."""
    coll = client.collections.get(settings.weaviate_collection)
    response = coll.query.hybrid(
        query=query,
        vector=query_vector,
        alpha=alpha if alpha is not None else settings.hybrid_alpha,
        limit=top_k or settings.retrieval_top_k,
        fusion_type=HybridFusion.RELATIVE_SCORE,
        return_metadata=MetadataQuery(score=True),
    )
    results = []
    for obj in response.objects:
        results.append({
            "chunk_id": obj.properties.get("chunk_id"),
            "text": obj.properties.get("text"),
            "source": obj.properties.get("source"),
            "section": obj.properties.get("section"),
            "score": obj.metadata.score,
        })
    return results


def count_objects(client: weaviate.WeaviateClient) -> int:
    coll = client.collections.get(settings.weaviate_collection)
    return coll.aggregate.over_all(total_count=True).total_count
