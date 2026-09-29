from typing import Protocol

from agent_api.schemas import QueryRequest, QueryResponse


class QueryService(Protocol):
    async def answer(self, request: QueryRequest) -> QueryResponse: ...


class NotImplementedQueryService:
    """Marcador hasta integrar el flujo del agente (HU-AG-07)."""

    async def answer(self, request: QueryRequest) -> QueryResponse:
        raise NotImplementedError("Flujo del agente pendiente (HU-AG-07)")


def get_query_service() -> QueryService:
    return NotImplementedQueryService()
