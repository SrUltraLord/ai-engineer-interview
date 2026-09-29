import hashlib
import logging

logger = logging.getLogger("mcp_server.audit")
_MAX_FIELD = 64


def _short(value: object) -> object:
    return value[:_MAX_FIELD] if isinstance(value, str) else value


def log_tool_call(
    *,
    tool: str,
    query: str | None,
    area_filter: str | None,
    classification_filter: str | None,
    document_ids: list[str],
    latency_ms: float,
    request_id: str,
    backend: str,
    error_code: str | None = None,
) -> None:
    """Registra la invocación sin texto de documentos ni la query en claro (solo hash y longitud)."""
    query = query or ""
    event = {
        "event": "tool_call",
        "request_id": request_id,
        "backend": backend,
        "tool": tool,
        "status": "error" if error_code else "ok",
        "area_filter": _short(area_filter),
        "classification_filter": _short(classification_filter),
        "query_sha256": hashlib.sha256(query.encode()).hexdigest()[:16],
        "query_length": len(query),
        "document_ids": document_ids,
        "result_count": len(document_ids),
        "latency_ms": round(latency_ms, 2),
    }
    if error_code:
        event["error_code"] = error_code
    logger.info("tool_call", extra={"fields": event})
