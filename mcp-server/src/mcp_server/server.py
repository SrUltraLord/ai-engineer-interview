import logging
import time
import uuid

from mcp.server.fastmcp import FastMCP
from mcp.types import CallToolResult

from mcp_server.audit import log_tool_call
from mcp_server.config import Settings
from mcp_server.errors import INTERNAL_ERROR, ToolInputError, error_result, success_result
from mcp_server.models import Document
from mcp_server.observability import configure_logging
from mcp_server.search import SearchBackend, create_backend
from mcp_server.validation import validate_area, validate_classification, validate_query

TOOL_NAME = "mcp_search_documents"
log = logging.getLogger(__name__)


def build_server(settings: Settings | None = None, backend: SearchBackend | None = None) -> FastMCP:
    settings = settings or Settings.from_env()
    backend = backend or create_backend(settings)
    mcp = FastMCP(
        "document-retrieval",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level,
    )
    # Tras crear FastMCP, que instala su propio handler de logging.
    configure_logging(settings.log_level, settings.log_format)
    backend_name = type(backend).__name__

    @mcp.tool(name=TOOL_NAME)
    def mcp_search_documents(
        query: str, area_filter: str | None = None, classification_filter: str | None = None
    ) -> CallToolResult:
        """Busca documentos internos relevantes para la consulta.

        `area_filter` y `classification_filter` son obligatorios. Los filtros se aplican antes
        de la búsqueda: solo se consideran documentos del área indicada (creditos, riesgos,
        tesoreria) y con clasificación igual o inferior a `classification_filter`
        (publico < interno < confidencial). Devuelve {"result": [documentos con sus metadatos]}.
        Ante entradas inválidas responde un error estructurado {"error": {code, message, field}}.
        """
        start = time.perf_counter()
        request_id = uuid.uuid4().hex[:12]
        documents: list[Document] = []
        error_code = None
        result: CallToolResult
        try:
            clean_query = validate_query(query)
            area = validate_area(area_filter)
            classification = validate_classification(classification_filter)
            documents = backend.search(clean_query, area, classification, settings.top_k)  # type: ignore[arg-type]
            result = success_result(documents)
        except ToolInputError as e:
            error_code = e.code
            result = error_result(e.code, e.message, e.field, request_id)
        except Exception:
            log.exception("Fallo interno en %s", TOOL_NAME, extra={"request_id": request_id, "backend": backend_name})
            error_code = INTERNAL_ERROR
            result = error_result(INTERNAL_ERROR, "Error interno del servidor", request_id=request_id)
        finally:
            log_tool_call(
                tool=TOOL_NAME,
                query=query,
                area_filter=area_filter,
                classification_filter=classification_filter,
                document_ids=[d.id for d in documents],
                latency_ms=(time.perf_counter() - start) * 1000,
                request_id=request_id,
                backend=backend_name,
                error_code=error_code,
            )
        return result

    return mcp
