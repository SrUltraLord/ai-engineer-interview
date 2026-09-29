import json
from dataclasses import dataclass

from mcp.types import CallToolResult, TextContent

INVALID_QUERY = "INVALID_QUERY"
INVALID_FILTER = "INVALID_FILTER"
INTERNAL_ERROR = "INTERNAL_ERROR"


@dataclass
class ToolInputError(Exception):
    code: str
    message: str
    field: str | None = None


def error_result(
    code: str, message: str, field: str | None = None, request_id: str | None = None
) -> CallToolResult:
    """Error estructurado {"error": {code, message, field?, request_id?}} sin trazas internas."""
    error = {"code": code, "message": message}
    if field:
        error["field"] = field
    if request_id:
        error["request_id"] = request_id
    payload = {"error": error}
    return CallToolResult(
        isError=True,
        content=[TextContent(type="text", text=json.dumps(payload, ensure_ascii=False))],
        structuredContent=payload,
    )


def success_result(documents: list) -> CallToolResult:
    """Resultado {"result": [documentos]}, mismo formato que el structured output por defecto."""
    payload = {"result": [d.model_dump(mode="json") for d in documents]}
    return CallToolResult(
        content=[TextContent(type="text", text=json.dumps(payload, ensure_ascii=False))],
        structuredContent=payload,
    )
