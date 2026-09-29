import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any

from agent_api.application.context import correlation_id
from agent_api.application.ports.audit import SECURITY_EVENTS

logger = logging.getLogger("agent_api.audit")

# Campos que nunca deben registrarse aunque un llamador los pase por error.
_FORBIDDEN_FIELDS = frozenset({"text", "document_text", "content", "password", "secret", "token", "api_key", "authorization"})


def configure_audit_logging() -> None:
    """JSON de una línea por evento en stderr. Con Application Insights, el handler de OpenTelemetry
    engancha este mismo logger."""
    if any(getattr(h, "_audit", False) for h in logger.handlers):
        return
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("%(message)s"))
    handler._audit = True  # type: ignore[attr-defined]
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


class JsonAuditLog:
    def record(self, event: str, **fields: Any) -> None:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "correlation_id": correlation_id.get(),
            **{k: v for k, v in fields.items() if k not in _FORBIDDEN_FIELDS},
        }
        level = logging.WARNING if event in SECURITY_EVENTS else logging.INFO
        logger.log(level, json.dumps(payload, ensure_ascii=False, default=str))
