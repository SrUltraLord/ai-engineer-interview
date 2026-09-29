from fastapi import FastAPI

from agent_api.api import docs
from agent_api.errors import register_error_handlers


def create_app() -> FastAPI:
    app = FastAPI(title="Agente RAG - Documentos internos", version="0.1.0")
    register_error_handlers(app)
    app.include_router(docs.router)
    return app


app = create_app()
