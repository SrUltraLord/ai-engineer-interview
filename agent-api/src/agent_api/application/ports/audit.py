from typing import Any, Protocol

# Eventos de seguridad (se registran con nivel WARNING).
SECURITY_EVENTS = frozenset(
    {
        "auth_failed",
        "access_denied",
        "tool_denied",
        "filter_override_ignored",
        "out_of_scope_document_dropped",
        "injection_detected",
    }
)


class AuditLog(Protocol):
    def record(self, event: str, **fields: Any) -> None:
        """Registra un evento estructurado. Nunca recibe secretos ni texto completo de documentos."""
        ...
