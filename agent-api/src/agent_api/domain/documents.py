from dataclasses import dataclass

from agent_api.domain.permissions import Classification


@dataclass(frozen=True)
class Document:
    id: str
    title: str
    area: str
    classification: Classification
    source: str
    text: str
