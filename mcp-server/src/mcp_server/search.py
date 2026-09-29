import re
from typing import Protocol

from mcp_server.corpus import DOCUMENTS
from mcp_server.models import CLASSIFICATION_LEVELS, Classification, Document


class SearchBackend(Protocol):
    def search(
        self, query: str, area: str, max_classification: Classification, top_k: int
    ) -> list[Document]: ...


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"\w+", text.lower()))


class InMemoryBackend:
    """Backend simulado: filtra por metadatos primero y luego ordena por coincidencia de términos."""

    def __init__(self, documents: list[Document] | None = None) -> None:
        self._documents = DOCUMENTS if documents is None else documents

    def search(
        self, query: str, area: str, max_classification: Classification, top_k: int
    ) -> list[Document]:
        max_level = CLASSIFICATION_LEVELS[max_classification]
        candidates = [
            d
            for d in self._documents
            if d.area == area and CLASSIFICATION_LEVELS[d.classification] <= max_level
        ]
        query_tokens = _tokens(query)
        scored = [(len(query_tokens & _tokens(f"{d.title} {d.text}")), d) for d in candidates]
        scored = [item for item in scored if item[0] > 0]
        scored.sort(key=lambda item: item[0], reverse=True)
        return [d for _, d in scored[:top_k]]
