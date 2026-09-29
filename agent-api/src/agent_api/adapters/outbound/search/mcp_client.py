import asyncio
import logging
import shlex
import sys
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamablehttp_client
from mcp.types import CallToolResult

from agent_api.domain.access import SearchFilters
from agent_api.domain.documents import Document
from agent_api.domain.errors import SearchRejectedError, ServiceUnavailableError
from agent_api.domain.tools import MCP_SEARCH_TOOL

log = logging.getLogger(__name__)

SessionFactory = Callable[[], AbstractAsyncContextManager[ClientSession]]
UNAVAILABLE = "El servicio de búsqueda no está disponible en este momento"


def stdio_session_factory(command: str | None = None, cwd: str | None = None) -> SessionFactory:
    argv = shlex.split(command) if command else [sys.executable, "-m", "mcp_server"]

    @asynccontextmanager
    async def factory():
        params = StdioServerParameters(command=argv[0], args=argv[1:], cwd=cwd)
        async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
            await session.initialize()
            yield session

    return factory


def http_session_factory(url: str) -> SessionFactory:
    @asynccontextmanager
    async def factory():
        async with streamablehttp_client(url) as (read, write, _), ClientSession(read, write) as session:
            await session.initialize()
            yield session

    return factory


class McpDocumentSearch:
    """Cliente del servidor MCP (`mcp_search_documents`) con timeout, reintentos y errores sin detalles internos."""

    def __init__(
        self,
        session_factory: SessionFactory,
        timeout_seconds: float = 10.0,
        max_retries: int = 2,
        backoff_seconds: float = 0.2,
    ) -> None:
        self._session_factory = session_factory
        self._timeout = timeout_seconds
        self._max_retries = max_retries
        self._backoff = backoff_seconds

    async def search(self, query: str, filters: SearchFilters) -> list[Document]:
        args = {
            "query": query,
            "area_filter": filters.area,
            "classification_filter": filters.classification,
        }
        for attempt in range(self._max_retries + 1):
            try:
                async with asyncio.timeout(self._timeout):
                    async with self._session_factory() as session:
                        result = await session.call_tool(MCP_SEARCH_TOOL, args)
                return self._parse(result)
            except SearchRejectedError:
                raise  # respuesta válida del servidor: no se reintenta
            except Exception:
                log.warning("Fallo al invocar %s (intento %d)", MCP_SEARCH_TOOL, attempt + 1, exc_info=True)
                if attempt < self._max_retries:
                    await asyncio.sleep(self._backoff * 2**attempt)
        raise ServiceUnavailableError(UNAVAILABLE)

    @staticmethod
    def _parse(result: CallToolResult) -> list[Document]:
        payload = result.structuredContent or {}
        if result.isError:
            error = payload.get("error") or {}
            code = str(error.get("code", "UNKNOWN"))
            if code == "INTERNAL_ERROR":
                raise RuntimeError("Error interno del servidor MCP")  # reintentable
            raise SearchRejectedError(code, str(error.get("message", "Petición rechazada")))
        try:
            return [
                Document(
                    id=d["id"],
                    title=d["title"],
                    area=d["area"],
                    classification=d["classification"],
                    source=d["source"],
                    text=d["text"],
                )
                for d in payload["result"]
            ]
        except (KeyError, TypeError) as e:
            raise RuntimeError("Respuesta MCP con formato inesperado") from e
