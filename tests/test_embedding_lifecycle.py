import asyncio
from concurrent.futures import ThreadPoolExecutor
import os
from types import SimpleNamespace
import sys
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

# Keep these unit tests independent of the heavyweight optional model package.
# Production imports the real class; the tests replace it before construction.
try:
    from llama_index.embeddings.huggingface import HuggingFaceEmbedding as _unused
except ModuleNotFoundError:
    from types import ModuleType

    llama_index = ModuleType("llama_index")
    llama_embeddings = ModuleType("llama_index.embeddings")
    llama_huggingface = ModuleType("llama_index.embeddings.huggingface")
    llama_huggingface.HuggingFaceEmbedding = object
    sys.modules["llama_index"] = llama_index
    sys.modules["llama_index.embeddings"] = llama_embeddings
    sys.modules["llama_index.embeddings.huggingface"] = llama_huggingface

from app.api import routes_chat
from app.auth.auth_service import Identity
from app.agents.orchestrator.state import OrchestratorState
from app.rag import embeddings


class FakeEmbedding:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def get_text_embedding(self, text):
        return [float(len(text))]

    def get_text_embedding_batch(self, texts, show_progress=False):
        return [[float(len(text))] for text in texts]


@pytest.fixture(autouse=True)
def isolated_embedding_cache():
    embeddings.clear_embedding_model_cache()
    yield
    embeddings.clear_embedding_model_cache()


def test_provider_constructs_embedding_once(monkeypatch):
    created = []

    def construct(**kwargs):
        created.append(kwargs)
        return FakeEmbedding(**kwargs)

    monkeypatch.setattr(embeddings, "HuggingFaceEmbedding", construct)

    first = embeddings.get_embedding_model()
    second = embeddings.get_embedding_model()

    assert first is second
    assert len(created) == 1
    assert created[0] == {
        "model_name": embeddings.settings.embedding_model,
        "device": embeddings.settings.embedding_device,
        "normalize": True,
    }


def test_provider_uses_configured_persistent_cache(monkeypatch):
    created = []
    monkeypatch.setattr(
        embeddings.settings, "embedding_cache_dir", "/persistent/huggingface/hub"
    )
    monkeypatch.setattr(
        embeddings,
        "HuggingFaceEmbedding",
        lambda **kwargs: created.append(kwargs) or FakeEmbedding(**kwargs),
    )

    embeddings.get_embedding_model()

    assert created[0]["cache_folder"] == "/persistent/huggingface/hub"


def test_concurrent_first_calls_construct_embedding_once(monkeypatch):
    created = []

    def slow_construct(**kwargs):
        created.append(kwargs)
        time.sleep(0.05)
        return FakeEmbedding(**kwargs)

    monkeypatch.setattr(embeddings, "HuggingFaceEmbedding", slow_construct)

    with ThreadPoolExecutor(max_workers=8) as executor:
        models = list(executor.map(lambda _: embeddings.get_embedding_model(), range(16)))

    assert len(created) == 1
    assert all(model is models[0] for model in models)


def test_rag_embedding_calls_reuse_same_instance(monkeypatch):
    created = []

    def construct(**kwargs):
        model = FakeEmbedding(**kwargs)
        created.append(model)
        return model

    monkeypatch.setattr(embeddings, "HuggingFaceEmbedding", construct)

    assert embeddings.embed_text("first") == [5.0]
    assert embeddings.embed_text("second") == [6.0]
    assert embeddings.embed_texts(["third", "fourth"]) == [[5.0], [6.0]]
    assert len(created) == 1
    assert embeddings.get_embedding_model() is created[0]


def test_chat_requests_do_not_recreate_embedding(monkeypatch):
    created = []

    def construct(**kwargs):
        model = FakeEmbedding(**kwargs)
        created.append(model)
        return model

    def run_orchestrator(**kwargs):
        embeddings.embed_text(kwargs["message"])
        return OrchestratorState(
            request_id=kwargs["request_id"],
            customer_id=kwargs["customer_id"],
            conversation_id="conversation",
            message=kwargs["message"],
            intent="policy_question",
            done=True,
            completion_reason="completed",
        )

    monkeypatch.setattr(embeddings, "HuggingFaceEmbedding", construct)
    monkeypatch.setattr(routes_chat.orchestrator_agent, "run", run_orchestrator)
    monkeypatch.setattr(
        routes_chat.chatbot_response_agent,
        "run",
        lambda state: {"answer": "safe", "citations": [], "action_taken": None},
    )
    identity = Identity(
        customer_id="TEST-CUSTOMER", email="customer@example.com", role="customer"
    )

    for request_id in ("request-1", "request-2", "request-3"):
        response = routes_chat.chat(
            routes_chat.ChatRequest(message="What is the return policy?"),
            SimpleNamespace(state=SimpleNamespace(request_id=request_id)),
            identity,
        )
        assert response.answer == "safe"

    assert len(created) == 1


def test_fastapi_lifespan_warms_embedding_in_process(monkeypatch):
    from app import main

    calls = []
    monkeypatch.setattr(main, "get_embedding_model", lambda: calls.append("loaded"))

    async def exercise_lifespan():
        async with main.lifespan(main.app):
            assert calls == ["loaded"]

    asyncio.run(exercise_lifespan())
