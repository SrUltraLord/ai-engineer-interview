import json
import logging

import pytest

from mcp_server.config import Settings
from mcp_server.observability import JsonFormatter, TextFormatter, configure_logging

ARGS = {"query": "tasas", "area_filter": "creditos", "classification_filter": "publico"}


def _record(msg="hola", exc_info=None, **extra):
    record = logging.LogRecord("mcp_server.x", logging.INFO, __file__, 1, msg, (), exc_info)
    record.__dict__.update(extra)
    return record


def test_json_formatter_includes_base_fields_and_extras():
    entry = json.loads(JsonFormatter().format(_record(request_id="abc", fields={"k": 1})))
    assert entry["level"] == "INFO" and entry["logger"] == "mcp_server.x" and entry["message"] == "hola"
    assert entry["request_id"] == "abc" and entry["k"] == 1 and entry["timestamp"]


def test_json_formatter_includes_exception_and_stays_single_line():
    try:
        raise RuntimeError("boom")
    except RuntimeError:
        import sys
        line = JsonFormatter().format(_record(exc_info=sys.exc_info()))
    assert "\n" not in line and "RuntimeError: boom" in json.loads(line)["exception"]


def test_text_formatter_appends_fields():
    line = TextFormatter().format(_record(port=8001))
    assert line.endswith("port=8001") and "INFO mcp_server.x hola" in line


def test_configure_logging_is_idempotent_and_replaces_fastmcp_handlers():
    class RichHandler(logging.Handler):  # mismo nombre que el de rich; no depende de tenerlo instalado
        def emit(self, record): ...

    root = logging.getLogger()
    fastmcp_handlers = [RichHandler(), logging.StreamHandler()]
    for h in fastmcp_handlers:
        root.addHandler(h)
    configure_logging("INFO", "json")
    configure_logging("INFO", "json")
    assert not any(h in root.handlers for h in fastmcp_handlers)
    assert sum(getattr(h, "_mcp_server_handler", False) for h in root.handlers) == 1


def test_settings_log_format(monkeypatch):
    assert Settings.from_env().log_format == "json"
    monkeypatch.setenv("MCP_LOG_FORMAT", "TEXT")
    assert Settings.from_env().log_format == "text"
    monkeypatch.setenv("MCP_LOG_FORMAT", "xml")
    with pytest.raises(ValueError, match="MCP_LOG_FORMAT"):
        Settings.from_env()


async def test_request_id_links_audit_event_and_error_payload(call_tool, audit_events):
    result = await call_tool(**{**ARGS, "area_filter": "rrhh"})
    (event,) = audit_events.events
    assert event["request_id"] == result.structuredContent["error"]["request_id"]
    assert event["backend"] == "InMemoryBackend"


async def test_request_ids_are_unique_per_call(call_tool, audit_events):
    await call_tool(**ARGS)
    await call_tool(**ARGS)
    ids = [e["request_id"] for e in audit_events.events]
    assert len(ids) == 2 and ids[0] != ids[1]


async def test_internal_error_is_logged_with_traceback_and_request_id(call_tool, caplog):
    class Broken:
        def search(self, *a, **k):
            raise RuntimeError("fallo db")

    with caplog.at_level(logging.ERROR, logger="mcp_server.server"):
        result = await call_tool(backend=Broken(), **ARGS)
    record = next(r for r in caplog.records if r.name == "mcp_server.server")
    assert record.request_id == result.structuredContent["error"]["request_id"]
    assert record.exc_info and "fallo db" in str(record.exc_info[1])
    assert "fallo db" not in result.content[0].text


async def test_audit_events_are_emitted_even_with_high_log_level(call_tool, audit_events):
    configure_logging("ERROR", "json")
    await call_tool(**ARGS)
    assert len(audit_events.events) == 1
