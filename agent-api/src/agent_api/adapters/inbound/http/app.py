import re

from fastapi import FastAPI, Request

from agent_api.adapters.inbound.http.errors import register_error_handlers
from agent_api.adapters.inbound.http.routes import router
from agent_api.application.context import correlation_id, new_correlation_id
from agent_api.bootstrap import Container, build_container
from agent_api.config import Settings

CORRELATION_HEADER = "X-Correlation-ID"
_VALID_ID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


def create_app(container: Container | None = None) -> FastAPI:
    app = FastAPI(title="Agente RAG - Documentos internos", version="0.1.0")
    app.state.container = container or build_container(Settings.from_env())
    register_error_handlers(app)
    app.include_router(router)

    @app.middleware("http")
    async def correlation_middleware(request: Request, call_next):
        incoming = request.headers.get(CORRELATION_HEADER, "")
        token = correlation_id.set(incoming if _VALID_ID.match(incoming) else new_correlation_id())
        try:
            response = await call_next(request)
            response.headers[CORRELATION_HEADER] = correlation_id.get()
            return response
        finally:
            correlation_id.reset(token)

    return app
