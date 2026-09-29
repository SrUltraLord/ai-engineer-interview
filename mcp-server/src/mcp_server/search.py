import logging
import math
import re
from typing import Protocol

from mcp_server.config import Settings
from mcp_server.corpus import DOCUMENTS
from mcp_server.embeddings import AzureOpenAIEmbedder, Embedder
from mcp_server.models import CLASSIFICATION_LEVELS, Classification, Document

log = logging.getLogger(__name__)


class SearchBackend(Protocol):
    """Contrato de búsqueda. Una implementación sobre Azure AI Search debe traducir
    `area` y `max_classification` a un filtro OData aplicado antes de la búsqueda vectorial."""

    def search(
        self, query: str, area: str, max_classification: Classification, top_k: int
    ) -> list[Document]: ...


def _prefilter(
    documents: list[Document], area: str, max_classification: Classification
) -> list[Document]:
    max_level = CLASSIFICATION_LEVELS[max_classification]
    return [
        d
        for d in documents
        if d.area == area and CLASSIFICATION_LEVELS[d.classification] <= max_level
    ]


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"\w+", text.lower()))


def _doc_text(doc: Document) -> str:
    return f"{doc.title}. {doc.text}"


class InMemoryBackend:
    """Fallback sin credenciales: pre-filtro por metadatos y ranking por coincidencia de términos."""

    def __init__(self, documents: list[Document] | None = None) -> None:
        self._documents = DOCUMENTS if documents is None else documents

    def search(
        self, query: str, area: str, max_classification: Classification, top_k: int
    ) -> list[Document]:
        candidates = _prefilter(self._documents, area, max_classification)
        query_tokens = _tokens(query)
        scored = [(len(query_tokens & _tokens(_doc_text(d))), d) for d in candidates]
        scored = [item for item in scored if item[0] > 0]
        scored.sort(key=lambda item: item[0], reverse=True)
        return [d for _, d in scored[:top_k]]


def _cosine(a: list[float], b: list[float]) -> float:
    norm = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(x * x for x in b))
    return sum(x * y for x, y in zip(a, b)) / norm if norm else 0.0


class VectorBackend:
    """Vector store en memoria: pre-filtro por metadatos y similitud coseno solo sobre los candidatos.

    Los embeddings de documentos se calculan bajo demanda y se cachean, de modo que los
    documentos fuera de los filtros nunca se envían al servicio de embeddings."""

    def __init__(self, embedder: Embedder, documents: list[Document] | None = None) -> None:
        self._embedder = embedder
        self._documents = DOCUMENTS if documents is None else documents
        self._cache: dict[str, list[float]] = {}

    def search(
        self, query: str, area: str, max_classification: Classification, top_k: int
    ) -> list[Document]:
        candidates = _prefilter(self._documents, area, max_classification)
        if not candidates:
            return []
        missing = [d for d in candidates if d.id not in self._cache]
        log.debug(
            "vector_search",
            extra={"candidates": len(candidates), "embedded_now": len(missing), "cached": len(candidates) - len(missing)},
        )
        if missing:
            vectors = self._embedder.embed([_doc_text(d) for d in missing])
            self._cache.update({d.id: v for d, v in zip(missing, vectors)})
        query_vector = self._embedder.embed([query])[0]
        ranked = sorted(
            candidates, key=lambda d: _cosine(query_vector, self._cache[d.id]), reverse=True
        )
        return ranked[:top_k]


def create_backend(settings: Settings) -> SearchBackend:
    if settings.embeddings_enabled:
        return VectorBackend(AzureOpenAIEmbedder(settings))
    return InMemoryBackend()
