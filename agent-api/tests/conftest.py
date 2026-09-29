import json
import logging
from contextlib import asynccontextmanager

import pytest

from agent_api.adapters.outbound.audit.json_logger import configure_audit_logging


@pytest.fixture(autouse=True)
def isolated_env(monkeypatch):
    """Los tests no dependen del .env ni del entorno del desarrollador."""
    for var in (
        "LLM_PROVIDER", "AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_DEPLOYMENT", "AZURE_OPENAI_API_KEY",
        "AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "JWT_SECRET", "JWT_ISSUER", "JWT_AUDIENCE",
        "MCP_CLIENT_TRANSPORT", "MCP_SERVER_URL", "MCP_SERVER_COMMAND", "TOOL_ALLOWLIST",
        "APPLICATIONINSIGHTS_CONNECTION_STRING",
    ):
        monkeypatch.delenv(var, raising=False)


@pytest.fixture
def audit_events():
    class Collector(logging.Handler):
        def __init__(self):
            super().__init__()
            self.raw: list[str] = []

        def emit(self, record):
            self.raw.append(record.getMessage())

        @property
        def events(self) -> list[dict]:
            return [json.loads(m) for m in self.raw]

        def of(self, name: str) -> list[dict]:
            return [e for e in self.events if e["event"] == name]

    configure_audit_logging()
    handler = Collector()
    logger = logging.getLogger("agent_api.audit")
    logger.addHandler(handler)
    yield handler
    logger.removeHandler(handler)


@pytest.fixture
def mcp_session_factory():
    """Sesión en memoria contra el servidor MCP real (corpus simulado, sin Azure)."""
    pytest.importorskip("mcp_server")
    from mcp.shared.memory import create_connected_server_and_client_session
    from mcp_server.config import Settings as McpSettings
    from mcp_server.server import build_server

    @asynccontextmanager
    async def factory():
        server = build_server(McpSettings())
        async with create_connected_server_and_client_session(server._mcp_server) as client:
            yield client

    return factory
