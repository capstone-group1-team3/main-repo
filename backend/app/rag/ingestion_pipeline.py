"""
rag/ingestion_pipeline.py — offline ingestion with incremental re-ingestion.

Flow: load policies -> chunk (section-level ids) -> embed (BGE-M3) -> upsert to
Weaviate. A JSON manifest maps chunk_id -> content hash. On re-run:
  - new chunk_id            -> embed + insert
  - existing id, hash same  -> SKIP (no re-embedding — saves BGE-M3 compute)
  - existing id, hash changed-> re-embed + upsert
  - id missing from source  -> delete from Weaviate (upserts_and_delete)

This is the "edit one policy, re-embed only what changed" behavior.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from app.config.settings import settings
from app.rag.chunking import load_policy_documents, chunk_documents
from app.rag.embeddings import embed_texts
from app.rag import vector_store as vs

MANIFEST_PATH = Path("vector_store/pipeline_storage/manifest.json")


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _load_manifest() -> dict[str, str]:
    if MANIFEST_PATH.exists():
        return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    return {}


def _save_manifest(manifest: dict[str, str]) -> None:
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def build_chunks(policies_dir: Path) -> list[dict[str, Any]]:
    docs = load_policy_documents(policies_dir)
    nodes = chunk_documents(docs)
    chunks = []
    for node in nodes:
        text = node.get_content()
        chunks.append({
            "chunk_id": node.id_,
            "text": text,
            "source": node.metadata.get("source", "unknown"),
            "section": node.metadata.get("section", "body"),
            "hash": _hash(text),
        })
    return chunks


def ingest(policies_dir: Path | None = None, full_rebuild: bool = False) -> dict[str, int]:
    policies_dir = policies_dir or Path(settings.policies_dir)
    chunks = build_chunks(policies_dir)
    current_ids = {c["chunk_id"] for c in chunks}
    manifest = {} if full_rebuild else _load_manifest()

    # decide what needs (re)embedding
    to_write = [
        c for c in chunks
        if full_rebuild or manifest.get(c["chunk_id"]) != c["hash"]
    ]
    skipped = len(chunks) - len(to_write)

    client = vs.connect()
    try:
        vs.ensure_collection(client)

        written = 0
        if to_write:
            vectors = embed_texts([c["text"] for c in to_write])
            written = vs.upsert_chunks(client, to_write, vectors)

        # remove chunks that disappeared from the source
        removed = vs.delete_missing(client, current_ids)

        total_in_store = vs.count_objects(client)
    finally:
        client.close()

    # update manifest
    new_manifest = {c["chunk_id"]: c["hash"] for c in chunks}
    _save_manifest(new_manifest)

    stats = {
        "total_chunks": len(chunks),
        "embedded_or_updated": written,
        "skipped_unchanged": skipped,
        "deleted": removed,
        "objects_in_store": total_in_store,
    }
    return stats
