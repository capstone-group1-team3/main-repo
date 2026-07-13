"""
graph/neo4j_client.py — thin wrapper around the official Neo4j Python driver.

Provides a single shared driver, simple read/write helpers, and a context-manager
close. Every graph query in the system goes through here.
"""
from __future__ import annotations

from typing import Any
import time

from neo4j import GraphDatabase, Driver

from app.config.settings import settings
from app.monitoring.metrics import NEO4J_DURATION, NEO4J_FAILURES, NEO4J_QUERIES


def _error_category(exc: BaseException) -> str:
    name = type(exc).__name__.lower()
    if "timeout" in name:
        return "timeout"
    if "auth" in name or "security" in name:
        return "authentication"
    if "service" in name or "session" in name or "connection" in name:
        return "unavailable"
    if "constraint" in name:
        return "constraint"
    return "database"


class Neo4jClient:
    def __init__(
        self,
        uri: str | None = None,
        user: str | None = None,
        password: str | None = None,
        database: str | None = None,
    ) -> None:
        self._uri = uri or settings.neo4j_uri
        self._auth = (user or settings.neo4j_user, password or settings.neo4j_password)
        self._database = database or settings.neo4j_database
        self._driver: Driver | None = None

    @property
    def driver(self) -> Driver:
        if self._driver is None:
            self._driver = GraphDatabase.driver(
                self._uri, auth=self._auth,
                connection_timeout=settings.neo4j_connection_timeout_seconds,
                connection_acquisition_timeout=settings.neo4j_connection_timeout_seconds,
            )
        return self._driver

    def verify(self) -> None:
        """Raise if the database is unreachable."""
        self.driver.verify_connectivity()

    def read(
        self, cypher: str, *, query_type: str = "unspecified", **params: Any
    ) -> list[dict[str, Any]]:
        return self._instrumented("read", query_type, lambda: self._read(cypher, params))

    def _read(self, cypher: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        with self.driver.session(database=self._database) as session:
            return [record.data() for record in session.run(cypher, **params)]

    def write(
        self, cypher: str, *, query_type: str = "unspecified", **params: Any
    ) -> list[dict[str, Any]]:
        def operation():
            with self.driver.session(database=self._database) as session:
                return session.execute_write(
                    lambda tx: [r.data() for r in tx.run(cypher, **params)]
                )
        return self._instrumented("write", query_type, operation)

    def run_batch(
        self, cypher: str, rows: list[dict[str, Any]], batch_size: int = 1000,
        *, query_type: str = "batch",
    ) -> int:
        """Run a parameterized write over a list of rows using UNWIND batching."""
        def operation():
            total = 0
            with self.driver.session(database=self._database) as session:
                for i in range(0, len(rows), batch_size):
                    chunk = rows[i : i + batch_size]
                    session.execute_write(lambda tx: tx.run(cypher, rows=chunk).consume())
                    total += len(chunk)
            return total
        return self._instrumented("batch", query_type, operation)

    @staticmethod
    def _instrumented(operation: str, query_type: str, func):
        # query_type comes from code, never user data. Collapse unexpected values.
        safe_type = query_type if query_type.replace("_", "").isalnum() and len(query_type) <= 48 else "other"
        started = time.perf_counter()
        outcome = "success"
        try:
            return func()
        except Exception as exc:
            outcome = "failure"
            NEO4J_FAILURES.labels(
                operation=operation, error_category=_error_category(exc)
            ).inc()
            raise
        finally:
            elapsed = time.perf_counter() - started
            NEO4J_QUERIES.labels(
                operation=operation, query_type=safe_type, outcome=outcome
            ).inc()
            NEO4J_DURATION.labels(
                operation=operation, query_type=safe_type, outcome=outcome
            ).observe(elapsed)

    def close(self) -> None:
        if self._driver is not None:
            self._driver.close()
            self._driver = None

    def __enter__(self) -> "Neo4jClient":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()


# module-level shared client for the running app
graph_client = Neo4jClient()
