from agent_api.adapters.outbound.audit.json_logger import JsonAuditLog
from agent_api.application.context import correlation_id


def test_event_has_correlation_id_and_drops_forbidden_fields(audit_events):
    token = correlation_id.set("abc123")
    try:
        JsonAuditLog().record("query", employee_id="E001", text="contenido completo", api_key="k", token="t")
    finally:
        correlation_id.reset(token)
    (event,) = audit_events.events
    assert event["correlation_id"] == "abc123" and event["employee_id"] == "E001"
    assert not {"text", "api_key", "token"} & set(event)
