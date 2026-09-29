import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

from agent_api.domain.errors import (
    BadRequestError,
    DomainError,
    ForbiddenError,
    ServiceUnavailableError,
    UnauthorizedError,
)

log = logging.getLogger(__name__)


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: list[dict] | None = None


class ErrorResponse(BaseModel):
    error: ErrorDetail


# tipo de error de dominio -> (status, código)
_DOMAIN_ERRORS: dict[type[DomainError], tuple[int, str]] = {
    BadRequestError: (400, "bad_request"),
    UnauthorizedError: (401, "unauthorized"),
    ForbiddenError: (403, "forbidden"),
    ServiceUnavailableError: (503, "service_unavailable"),
}
_HTTP_CODES = {400: "bad_request", 401: "unauthorized", 403: "forbidden", 404: "not_found"}


def _response(
    status: int, code: str, message: str, details: list[dict] | None = None, headers: dict | None = None
) -> JSONResponse:
    body = ErrorResponse(error=ErrorDetail(code=code, message=message, details=details))
    return JSONResponse(status_code=status, content=body.model_dump(exclude_none=True), headers=headers)


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def _domain_error(_: Request, exc: DomainError) -> JSONResponse:
        for cls in type(exc).__mro__:
            if cls in _DOMAIN_ERRORS:
                status, code = _DOMAIN_ERRORS[cls]
                headers = {"WWW-Authenticate": "Bearer"} if status == 401 else None
                return _response(status, code, exc.message, headers=headers)
        log.error("Error de dominio sin mapeo HTTP: %s", type(exc).__name__)
        return _response(500, "internal_error", "Error interno del servidor")

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        # JSON malformado -> 400; esquema inválido -> 422.
        if any(e["type"] == "json_invalid" for e in exc.errors()):
            return _response(400, "bad_request", "El cuerpo de la petición no es JSON válido")
        details = [{"field": ".".join(str(p) for p in e["loc"][1:]), "message": e["msg"]} for e in exc.errors()]
        return _response(422, "validation_error", "La petición no es válida", details)

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        return _response(exc.status_code, _HTTP_CODES.get(exc.status_code, "http_error"), str(exc.detail))

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception) -> JSONResponse:
        log.error("Error no controlado", exc_info=exc)
        return _response(500, "internal_error", "Error interno del servidor")
