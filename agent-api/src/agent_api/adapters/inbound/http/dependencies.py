from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from agent_api.application.use_cases.query_documents import QueryDocuments
from agent_api.domain.auth import Principal
from agent_api.domain.errors import UnauthorizedError

_bearer = HTTPBearer(auto_error=False, description="JWT del empleado")


def get_query_documents(request: Request) -> QueryDocuments:
    return request.app.state.container.query_documents


def get_principal(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> Principal:
    container = request.app.state.container
    try:
        return container.authenticator.authenticate(credentials.credentials if credentials else None)
    except UnauthorizedError:
        container.audit.record("auth_failed", path=request.url.path, has_credentials=credentials is not None)
        raise
