from typing import Annotated

from fastapi import APIRouter, Depends

from agent_api.errors import ErrorResponse
from agent_api.schemas import QueryRequest, QueryResponse
from agent_api.service import QueryService, get_query_service

router = APIRouter(prefix="/api/v1/docs", tags=["docs"])

_ERRORS = {code: {"model": ErrorResponse} for code in (400, 401, 403)}


@router.post("/query", response_model=QueryResponse, responses=_ERRORS)
async def query_documents(
    request: QueryRequest,
    service: Annotated[QueryService, Depends(get_query_service)],
) -> QueryResponse:
    return await service.answer(request)
