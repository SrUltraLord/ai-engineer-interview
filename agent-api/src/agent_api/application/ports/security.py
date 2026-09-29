from typing import Protocol

from agent_api.domain.injection import Detection


class InjectionDetector(Protocol):
    """Detecta texto malicioso. Rangos sobre el texto ya normalizado.

    Implementaciones: heurística por patrones (dominio) y, opcionalmente, Azure Prompt Shields.
    """

    def detect(self, text: str) -> list[Detection]: ...
