"""
config/settings.py — central configuration, read from environment / .env.

Extended with planner settings (PLANNER_GROQ_API_KEY, PLANNER_MODEL, etc.)
and updated loop limits for the Hybrid Planner.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Neo4j ──────────────────────────────────────────────────────────────
    neo4j_uri:      str = Field(default="bolt://localhost:7687")
    neo4j_user:     str = Field(default="neo4j")
    neo4j_password: str = Field(default="password")
    neo4j_database: str = Field(default="neo4j")

    # ── Weaviate ───────────────────────────────────────────────────────────
    weaviate_host:       str = Field(default="localhost")
    weaviate_http_port:  int = Field(default=18080)
    weaviate_grpc_port:  int = Field(default=50051)
    weaviate_collection: str = Field(default="PolicyChunk")

    # ── Embeddings ─────────────────────────────────────────────────────────
    embedding_model:  str = Field(default="BAAI/bge-m3")
    embedding_device: str = Field(default="cpu")

    # ── Main Groq LLM (response generation) ───────────────────────────────
    groq_api_key: str = Field(default="")
    groq_model:   str = Field(default="openai/gpt-oss-120b")

    # ── Planner Groq LLM (separate account + key) ─────────────────────────
    # Uses a smaller / faster model with structured JSON output.
    # When PLANNER_GROQ_API_KEY is absent the planner is disabled and the
    # system falls back to deterministic fixed routing automatically.
    planner_groq_api_key:     str   = Field(default="")
    planner_model:            str   = Field(default="llama-3.3-70b-versatile")
    planner_reasoning_effort: str   = Field(default="low")
    planner_max_tokens:       int   = Field(default=180)
    planner_temperature:      float = Field(default=0.0)
    planner_min_confidence:   float = Field(default=0.75)
    planner_timeout_seconds:  int   = Field(default=5)

    # ── Auth ───────────────────────────────────────────────────────────────
    jwt_secret:         str = Field(default="change-me-in-production")
    jwt_algorithm:      str = Field(default="HS256")
    jwt_expire_minutes: int = Field(default=120)

    # ── Orchestrator loop limits ───────────────────────────────────────────
    max_iterations:     int = Field(default=5)
    max_tool_calls:     int = Field(default=4)
    max_same_tool_calls: int = Field(default=1)

    # ── Retrieval ──────────────────────────────────────────────────────────
    hybrid_alpha:    float = Field(default=0.5)
    retrieval_top_k: int   = Field(default=4)

    # ── Data paths ─────────────────────────────────────────────────────────
    processed_dir:       str = Field(default="data/processed")
    seed_dir:            str = Field(default="data/seed")
    policies_dir:        str = Field(default="data/policies")
    business_rules_path: str = Field(default="business_rules.yaml")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
