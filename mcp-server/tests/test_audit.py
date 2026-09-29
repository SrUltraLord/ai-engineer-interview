import hashlib

from mcp_server.corpus import DOCUMENTS

QUERY = "proveedor consulta crédito"
ARGS = {"query": QUERY, "area_filter": "creditos", "classification_filter": "interno"}


async def test_successful_call_is_audited(call_tool, audit_events):
    result = await call_tool(**ARGS)
    (event,) = audit_events.events
    returned = [d["id"] for d in result.structuredContent["result"]]
    assert event["tool"] == "mcp_search_documents" and event["status"] == "ok"
    assert event["area_filter"] == "creditos" and event["classification_filter"] == "interno"
    assert event["document_ids"] == returned and event["result_count"] == len(returned)
    assert event["latency_ms"] >= 0 and event["timestamp"]


async def test_log_has_no_plain_query_nor_document_text(call_tool, audit_events):
    await call_tool(**ARGS)
    raw = audit_events.raw[0]
    (event,) = audit_events.events
    assert QUERY not in raw
    assert event["query_length"] == len(QUERY)
    assert event["query_sha256"] == hashlib.sha256(QUERY.encode()).hexdigest()[:16]
    assert not any(d.text in raw for d in DOCUMENTS)


async def test_rejected_call_is_audited_with_error_code(call_tool, audit_events):
    await call_tool(**{**ARGS, "area_filter": "rrhh"})
    (event,) = audit_events.events
    assert event["status"] == "error" and event["error_code"] == "INVALID_FILTER"
    assert event["document_ids"] == []


async def test_log_is_single_line_json_even_with_hostile_input(call_tool, audit_events):
    await call_tool(**{**ARGS, "area_filter": "a\nFAKE LOG LINE" + "x" * 200})
    assert "\n" not in audit_events.raw[0]
    (event,) = audit_events.events
    assert len(event["area_filter"]) <= 64
