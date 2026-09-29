from mcp.server.fastmcp import FastMCP

from mcp_server.config import Settings
from mcp_server.models import Classification, Document
from mcp_server.search import InMemoryBackend, SearchBackend

TOP_K = 5


def build_server(settings: Settings | None = None, backend: SearchBackend | None = None) -> FastMCP:
    settings = settings or Settings.from_env()
    backend = backend or InMemoryBackend()
    mcp = FastMCP(
        "document-retrieval",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level,
    )

    @mcp.tool()
    def mcp_search_documents(
        query: str, area_filter: str, classification_filter: Classification
    ) -> list[Document]:
        """Busca documentos internos relevantes para la consulta.

        Los filtros se aplican antes de la búsqueda: solo se consideran documentos del área
        indicada y con clasificación igual o inferior a `classification_filter`
        (publico < interno < confidencial). Devuelve los documentos con sus metadatos.
        """
        return backend.search(query, area_filter, classification_filter, TOP_K)

    return mcp
