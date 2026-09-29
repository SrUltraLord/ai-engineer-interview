import asyncio
from contextlib import asynccontextmanager

import pytest

from agent_api.adapters.outbound.search.mcp_client import McpDocumentSearch
from agent_api.domain.access import SearchFilters
from agent_api.domain.errors import SearchRejectedError, ServiceUnavailableError

F = SearchFilters("creditos", "interno")


async def test_search_against_real_server_respects_filters(mcp_session_factory):
    docs = await McpDocumentSearch(mcp_session_factory).search("crédito consumo provisión", F)
    assert docs and {d.area for d in docs} == {"creditos"}
    assert all(d.classification in ("publico", "interno") for d in docs)
    assert "DOC-003" not in {d.id for d in docs}  # confidencial


async def test_server_rejection_is_not_retried(mcp_session_factory):
    calls = 0

    @asynccontextmanager
    async def counting():
        nonlocal calls
        calls += 1
        async with mcp_session_factory() as s:
            yield s

    with pytest.raises(SearchRejectedError) as e:
        await McpDocumentSearch(counting, max_retries=2).search("   ", F)
    assert e.value.code == "INVALID_QUERY" and calls == 1


async def test_retries_then_succeeds(mcp_session_factory):
    attempts = 0

    @asynccontextmanager
    async def flaky():
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise ConnectionError("detalle interno secreto")
        async with mcp_session_factory() as s:
            yield s

    docs = await McpDocumentSearch(flaky, max_retries=2, backoff_seconds=0).search("crédito consumo", F)
    assert attempts == 3 and docs


async def test_unavailable_hides_internal_details():
    @asynccontextmanager
    async def down():
        raise ConnectionError("host interno 10.0.0.5 caído")
        yield  # pragma: no cover

    with pytest.raises(ServiceUnavailableError) as e:
        await McpDocumentSearch(down, max_retries=1, backoff_seconds=0).search("q", F)
    assert "10.0.0.5" not in e.value.message


async def test_timeout():
    @asynccontextmanager
    async def slow():
        await asyncio.sleep(5)
        yield None

    with pytest.raises(ServiceUnavailableError):
        await McpDocumentSearch(slow, timeout_seconds=0.05, max_retries=0).search("q", F)
