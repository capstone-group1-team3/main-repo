"""
rag/embeddings.py — BGE-M3 embeddings via LlamaIndex's HuggingFaceEmbedding.

Runs in-process (BYO vectors): we compute embeddings in the app and push them to
Weaviate, keeping full control of the model. BGE-M3 is 1024-dimensional.
"""
from __future__ import annotations

from functools import lru_cache
import logging
from threading import Lock

from llama_index.embeddings.huggingface import HuggingFaceEmbedding

from app.config.settings import settings

EMBED_DIM = 1024  # BGE-M3 output dimension
logger = logging.getLogger(__name__)
_embedding_model_lock = Lock()


@lru_cache(maxsize=1) # it loads the model BGE-M3 once
def _create_embedding_model() -> HuggingFaceEmbedding:
    logger.info("Loading embedding model %s...", settings.embedding_model)
    model_kwargs = {
        "model_name": settings.embedding_model,
        "device": settings.embedding_device,
        "normalize": True,
    }
    if settings.embedding_cache_dir:
        # LlamaIndex otherwise defaults to ~/.cache/llama_index, bypassing
        # HF_HOME and the persistent Docker volume.
        model_kwargs["cache_folder"] = settings.embedding_cache_dir
    model = HuggingFaceEmbedding(
        **model_kwargs,
    )
    logger.info("Embedding model ready.")
    return model


def get_embedding_model() -> HuggingFaceEmbedding:
    """Return the process-wide, thread-safe reusable embedding model."""
    # functools.lru_cache may invoke its wrapped function more than once when
    # concurrent callers miss an empty cache. Serialize the cache lookup and
    # construction so only one BGE-M3 instance can be created per process.
    with _embedding_model_lock:
        return _create_embedding_model()


def clear_embedding_model_cache() -> None:
    """Clear the provider cache safely (intended for isolated tests)."""
    with _embedding_model_lock:
        _create_embedding_model.cache_clear()


def embed_text(text: str) -> list[float]:
    """Embed a single query string -> a 1024-dim vector."""
    return get_embedding_model().get_text_embedding(text)


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a batch of strings."""
    return get_embedding_model().get_text_embedding_batch(texts, show_progress=False)
