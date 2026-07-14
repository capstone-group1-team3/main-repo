"""
agents/orchestrator/conversation_store.py

Server-side confirmation state persistence across HTTP requests.

Security:
- get() always verifies customer_id ownership
- mark_executed() prevents replay (same confirmation cannot run twice)
- No API keys, tokens, or passwords stored here
- TTL = 15 min; entries silently discarded on expiry
- Warning emitted when using in-memory store (not for multi-worker prod)
"""
from __future__ import annotations

import hashlib
import logging
import threading
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from app.config.settings import settings

logger = logging.getLogger("conversation_store")

TTL_SECONDS = 15 * 60


@dataclass
class PendingActionContext:
    intent:              str
    order_id:            str | None
    amount:              float | None
    order_status:        str | None
    order_snapshot_hash: str | None = None
    eligibility:         dict[str, Any] = field(default_factory=dict)


@dataclass
class ConversationStateData:
    customer_id:           str
    conversation_id:       str
    intent:                str = ""
    entities:              dict[str, Any] = field(default_factory=dict)
    pending_action:        PendingActionContext | None = None
    confirmation_required: bool = False
    executed:              bool = False
    order_id:              str | None = None
    order_status:          str | None = None
    created_at:            float = field(default_factory=time.time)
    updated_at:            float = field(default_factory=time.time)

    def touch(self) -> None:
        self.updated_at = time.time()

    @staticmethod
    def order_hash(order_data: dict[str, Any]) -> str:
        key = (f"{order_data.get('order_id')}:"
               f"{order_data.get('status')}:"
               f"{order_data.get('delivered_date')}")
        return hashlib.sha256(key.encode()).hexdigest()[:16]


class AbstractConversationStore(ABC):
    @abstractmethod
    def get(self, conversation_id: str, customer_id: str) -> ConversationStateData | None: ...
    @abstractmethod
    def save(self, data: ConversationStateData) -> None: ...
    @abstractmethod
    def delete(self, conversation_id: str) -> None: ...
    @abstractmethod
    def mark_executed(self, conversation_id: str) -> None: ...


class InMemoryConversationStore(AbstractConversationStore):
    """Thread-safe in-memory store. NOT for multi-worker deployments."""

    _warned = False

    def __init__(self, ttl_seconds: int | None = None):
        if not InMemoryConversationStore._warned:
            logger.warning(
                "InMemoryConversationStore: not suitable for multi-worker deployments. "
                "Replace with Redis for production."
            )
            InMemoryConversationStore._warned = True
        self._store: dict[str, tuple[ConversationStateData, float]] = {}
        self._lock  = threading.Lock()
        self._ttl   = (
            settings.conversation_ttl_seconds
            if ttl_seconds is None else ttl_seconds
        )

    def get(self, conversation_id: str, customer_id: str) -> ConversationStateData | None:
        with self._lock:
            self._evict()
            entry = self._store.get(conversation_id)
            if entry is None:
                return None
            data, expires_at = entry
            if time.monotonic() > expires_at:
                del self._store[conversation_id]
                from app.monitoring.metrics import CONFIRMATION_EXPIRED
                CONFIRMATION_EXPIRED.inc()
                return None
            if data.customer_id != customer_id:
                logger.warning("Ownership mismatch for conv=%s", conversation_id[:8])
                return None
            return data

    def save(self, data: ConversationStateData) -> None:
        data.touch()
        with self._lock:
            self._store[data.conversation_id] = (
                data, time.monotonic() + self._ttl
            )

    def delete(self, conversation_id: str) -> None:
        with self._lock:
            self._store.pop(conversation_id, None)

    def mark_executed(self, conversation_id: str) -> None:
        with self._lock:
            entry = self._store.get(conversation_id)
            if entry:
                entry[0].executed = True

    def _evict(self) -> None:
        now = time.monotonic()
        expired = [k for k, (_, e) in self._store.items() if now > e]
        for k in expired:
            del self._store[k]
        if expired:
            from app.monitoring.metrics import CONFIRMATION_EXPIRED
            CONFIRMATION_EXPIRED.inc(len(expired))


_store: AbstractConversationStore = InMemoryConversationStore()


def get_store() -> AbstractConversationStore:
    return _store


def new_conversation_id() -> str:
    return uuid.uuid4().hex
