from typing import Protocol

from agent_api.domain.access import SearchFilters
from agent_api.domain.documents import Document


class DocumentSearchPort(Protocol):
    """Búsqueda documental. Los filtros se calculan en código y se aplican en origen.

    Lanza SearchRejectedError si el servidor rechaza la petición y ServiceUnavailableError
    si no está disponible.
    """

    async def search(self, query: str, filters: SearchFilters) -> list[Document]: ...
