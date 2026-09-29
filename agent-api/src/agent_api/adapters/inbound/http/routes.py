from typing import Annotated

from fastapi import APIRouter, Depends

from agent_api.adapters.inbound.http.dependencies import get_principal, get_query_documents
from agent_api.adapters.inbound.http.errors import ErrorResponse
from agent_api.adapters.inbound.http.schemas import QueryRequest, QueryResponse
from agent_api.application.use_cases.query_documents import QueryDocuments
from agent_api.domain.auth import Principal

router = APIRouter(prefix="/api/v1/docs", tags=["docs"])

_ERRORS = {code: {"model": ErrorResponse} for code in (400, 401, 403, 503)}


@router.post("/query", response_model=QueryResponse, responses=_ERRORS)
async def query_documents(
    request: QueryRequest,
    principal: Annotated[Principal, Depends(get_principal)],
    use_case: Annotated[QueryDocuments, Depends(get_query_documents)],
) -> QueryResponse:
    return QueryResponse.from_answer(await use_case.execute(request.to_command(), principal))
