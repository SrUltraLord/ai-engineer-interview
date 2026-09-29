from mcp_server.errors import INVALID_FILTER, INVALID_QUERY, ToolInputError
from mcp_server.models import AREAS, CLASSIFICATION_LEVELS

MAX_QUERY_LENGTH = 1000


def validate_query(query: str | None) -> str:
    query = (query or "").strip()
    if not query:
        raise ToolInputError(INVALID_QUERY, "query no puede estar vacío", "query")
    if len(query) > MAX_QUERY_LENGTH:
        raise ToolInputError(
            INVALID_QUERY, f"query excede el máximo de {MAX_QUERY_LENGTH} caracteres", "query"
        )
    return query


def _validate_filter(value: str | None, field: str, catalog: tuple[str, ...]) -> str:
    value = (value or "").strip()
    if not value:
        raise ToolInputError(
            INVALID_FILTER, f"{field} es obligatorio; valores permitidos: {', '.join(catalog)}", field
        )
    if value not in catalog:
        raise ToolInputError(
            INVALID_FILTER, f"{field} inválido; valores permitidos: {', '.join(catalog)}", field
        )
    return value


def validate_area(value: str | None) -> str:
    return _validate_filter(value, "area_filter", AREAS)


def validate_classification(value: str | None) -> str:
    return _validate_filter(value, "classification_filter", tuple(CLASSIFICATION_LEVELS))
