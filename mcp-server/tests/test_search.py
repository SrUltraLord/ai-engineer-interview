import re

import pytest

from mcp_server.config import Settings
from mcp_server.corpus import DOCUMENTS
from mcp_server.search import InMemoryBackend, VectorBackend, create_backend

VOCAB = ["crédito", "consumo", "liquidez", "riesgo", "scoring", "tasas", "operativo", "provisión"]


class FakeEmbedder:
    """Embedding determinista por conteo de palabras del vocabulario; registra lo que recibe."""

    def __init__(self):
        self.seen: list[str] = []

    def embed(self, texts):
        self.seen.extend(texts)
        return [[float(len(re.findall(w, t.lower()))) for w in VOCAB] for t in texts]


def test_vector_backend_ranks_by_similarity():
    backend = VectorBackend(FakeEmbedder())
    docs = backend.search("tasas de crédito", "creditos", "interno", top_k=5)
    assert docs[0].id == "DOC-002"


def test_vector_backend_prefilters_before_embedding():
    embedder = FakeEmbedder()
    docs = VectorBackend(embedder).search("liquidez", "tesoreria", "interno", top_k=5)
    assert {d.area for d in docs} == {"tesoreria"}
    assert "confidencial" not in {d.classification for d in docs}
    excluded = [d for d in DOCUMENTS if d.area != "tesoreria" or d.classification == "confidencial"]
    assert not any(d.text in " ".join(embedder.seen) for d in excluded)


def test_vector_backend_caches_document_embeddings():
    embedder = FakeEmbedder()
    backend = VectorBackend(embedder)
    backend.search("crédito", "creditos", "publico", top_k=3)
    first = len(embedder.seen)
    backend.search("consumo", "creditos", "publico", top_k=3)
    assert len(embedder.seen) == first + 1  # solo la nueva query


@pytest.mark.parametrize("backend_factory", [InMemoryBackend, lambda: VectorBackend(FakeEmbedder())])
def test_top_k_is_respected(backend_factory):
    docs = backend_factory().search("crédito consumo tasas", "creditos", "confidencial", top_k=2)
    assert len(docs) == 2


def test_create_backend_falls_back_without_credentials():
    assert isinstance(create_backend(Settings()), InMemoryBackend)


def test_create_backend_uses_vector_backend_with_credentials(monkeypatch):
    monkeypatch.setattr("mcp_server.search.AzureOpenAIEmbedder", lambda settings: FakeEmbedder())
    settings = Settings(
        azure_openai_endpoint="https://x.openai.azure.com",
        azure_openai_api_key="k",
        azure_openai_embedding_deployment="emb",
    )
    assert isinstance(create_backend(settings), VectorBackend)
