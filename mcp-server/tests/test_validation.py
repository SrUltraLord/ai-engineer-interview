import pytest

VALID = {"query": "crédito consumo", "area_filter": "creditos", "classification_filter": "interno"}


def _error(result):
    assert result.isError
    return result.structuredContent["error"]


@pytest.mark.parametrize("query", ["", "   ", "x" * 1001])
async def test_invalid_query_is_rejected(call_tool, query):
    error = _error(await call_tool(**{**VALID, "query": query}))
    assert error["code"] == "INVALID_QUERY" and error["field"] == "query"


@pytest.mark.parametrize("field", ["area_filter", "classification_filter"])
async def test_missing_filter_is_rejected(call_tool, field):
    args = {k: v for k, v in VALID.items() if k != field}
    error = _error(await call_tool(**args))
    assert error["code"] == "INVALID_FILTER" and error["field"] == field


@pytest.mark.parametrize("field,value", [
    ("area_filter", ""),
    ("area_filter", "rrhh"),
    ("classification_filter", ""),
    ("classification_filter", "secreto"),
])
async def test_filter_outside_catalog_is_rejected(call_tool, field, value):
    error = _error(await call_tool(**{**VALID, field: value}))
    assert error["code"] == "INVALID_FILTER" and error["field"] == field


async def test_error_content_is_json_text_without_traces(call_tool):
    result = await call_tool(**{**VALID, "area_filter": "rrhh"})
    text = result.content[0].text
    assert text.startswith('{"error"') and "Traceback" not in text


async def test_backend_failure_returns_internal_error_without_details(call_tool):
    class Broken:
        def search(self, *a, **k):
            raise RuntimeError("secreto interno: conexión db://x")

    result = await call_tool(backend=Broken(), **VALID)
    error = _error(result)
    assert error["code"] == "INTERNAL_ERROR"
    assert "secreto" not in result.content[0].text


async def test_valid_call_still_succeeds(call_tool):
    result = await call_tool(**VALID)
    assert not result.isError and result.structuredContent["result"]
