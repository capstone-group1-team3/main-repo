"""
config/settings.py

Main model:    openai/gpt-oss-120b  via GROQ_API_KEY
Planner model: openai/gpt-oss-20b   via PLANNER_GROQ_API_KEY (separate account)
"""
from __future__ import annotations
from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Neo4j
    neo4j_uri:      str = Field(default="bolt://localhost:7687")
    neo4j_user:     str = Field(default="neo4j")
    neo4j_password: str = Field(default="password")
    neo4j_database: str = Field(default="neo4j")
    neo4j_connection_timeout_seconds: float = Field(default=5.0)

    # Weaviate
    weaviate_host:       str = Field(default="localhost")
    weaviate_http_port:  int = Field(default=18080)
    weaviate_grpc_port:  int = Field(default=50051)
    weaviate_collection: str = Field(default="PolicyChunk")

    # Embeddings
    embedding_model:     str = Field(default="BAAI/bge-m3")
    embedding_device:    str = Field(default="cpu")
    embedding_cache_dir: str | None = Field(default=None)

    # Main Groq — response generation ONLY
    groq_api_key: str = Field(default="")
    groq_model:   str = Field(default="openai/gpt-oss-120b")

    # Planner Groq — SEPARATE account + key
    planner_groq_api_key:     str   = Field(default="")
    planner_model:            str   = Field(default="openai/gpt-oss-20b")
    planner_reasoning_effort: str   = Field(default="low")
    planner_max_tokens:       int   = Field(default=180)
    planner_temperature:      float = Field(default=0.0)
    planner_min_confidence:   float = Field(default=0.75)
    planner_timeout_seconds:  int   = Field(default=5)

    # Auth
    jwt_secret:         str = Field(default="change-me-in-production")
    jwt_algorithm:      str = Field(default="HS256")
    jwt_expire_minutes: int = Field(default=120)

    # Loop limits
    max_iterations:      int = Field(default=5)
    max_tool_calls:      int = Field(default=4)
    max_same_tool_calls: int = Field(default=1)

    # Conversation state TTL
    conversation_ttl_seconds: int = Field(default=900)

    # Retrieval
    hybrid_alpha:    float = Field(default=0.5)
    retrieval_top_k: int   = Field(default=4)
    retrieval_min_score: float = Field(default=0.15)

    # Internal evaluation metadata is disabled for normal customer traffic.
    evaluation_metadata_enabled: bool = Field(default=False)
    readiness_timeout_seconds: float = Field(default=3.0)

    # Data paths (resolved relative to CWD — run from project root)
    processed_dir:       str = Field(default="data/processed")
    seed_dir:            str = Field(default="data/seed")
    policies_dir:        str = Field(default="data/policies")
    business_rules_path: str = Field(default="business_rules.yaml")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
