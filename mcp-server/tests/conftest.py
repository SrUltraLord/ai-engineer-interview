import json
import logging

import pytest
from mcp.shared.memory import create_connected_server_and_client_session

from mcp_server.config import Settings
from mcp_server.observability import JsonFormatter
from mcp_server.server import build_server


@pytest.fixture(autouse=True)
def no_azure_credentials(monkeypatch):
    """Los tests nunca usan Azure: fuerzan el fallback simulado."""
    for var in (
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_API_KEY",
        "AZURE_OPENAI_API_VERSION",
        "AZURE_OPENAI_EMBEDDING_DEPLOYMENT",
    ):
        monkeypatch.delenv(var, raising=False)


@pytest.fixture
def call_tool():
    async def _call(backend=None, **args):
        server = build_server(Settings(), backend=backend)
        async with create_connected_server_and_client_session(server._mcp_server) as client:
            return await client.call_tool("mcp_search_documents", args)

    return _call


@pytest.fixture
def audit_events():
    class Collector(logging.Handler):
        def __init__(self):
            super().__init__()
            self.formatter_ = JsonFormatter()
            self.raw: list[str] = []

        def emit(self, record):
            self.raw.append(self.formatter_.format(record))

        @property
        def events(self):
            return [json.loads(m) for m in self.raw]

    handler = Collector()
    logger = logging.getLogger("mcp_server.audit")
    logger.addHandler(handler)
    yield handler
    logger.removeHandler(handler)
