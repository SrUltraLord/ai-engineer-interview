import hashlib
import logging
from collections.abc import Sequence

from agent_api.application.ports.audit import AuditLog
from agent_api.application.ports.llm import LLMPort
from agent_api.application.ports.permissions import PermissionsRepository
from agent_api.application.ports.search import DocumentSearchPort
from agent_api.application.prompts import SYSTEM_PROMPT, render_documents
from agent_api.application.sanitizer import DocumentSanitizer
from agent_api.domain.access import SearchFilters, build_search_filters, check_identity, is_within_scope
from agent_api.domain.auth import Principal
from agent_api.domain.chat import ChatMessage, LLMResponse, ToolCall, ToolSpec
from agent_api.domain.documents import Document
from agent_api.domain.errors import (
    DomainError,
    EmployeeNotFoundError,
    ForbiddenError,
    SearchRejectedError,
    ServiceUnavailableError,
)
from agent_api.domain.permissions import EmployeePermissions
from agent_api.domain.query import Answer, QueryCommand
from agent_api.domain.tools import MCP_SEARCH_TOOL, ToolAllowlist

log = logging.getLogger(__name__)

MAX_TOOL_ROUNDS = 3
_FILTER_ARGS = ("area_filter", "classification_filter")

# El modelo solo ve `query`: los filtros los impone el código, nunca el LLM.
TOOL_SPECS: dict[str, ToolSpec] = {
    MCP_SEARCH_TOOL: ToolSpec(
        name=MCP_SEARCH_TOOL,
        description="Busca documentos internos relevantes para la consulta. Solo devuelve los que el empleado puede ver.",
        parameters={
            "type": "object",
            "properties": {"query": {"type": "string", "description": "Texto de búsqueda"}},
            "required": ["query"],
        },
    ),
}

DENIED_TOOL_RESULT = "Herramienta no permitida para este usuario. No se ejecutó."
UNAVAILABLE = "El servicio no está disponible en este momento"


def _digest(text: str) -> dict[str, object]:
    return {"query_sha256": hashlib.sha256(text.encode()).hexdigest()[:16], "query_length": len(text)}


class QueryDocuments:
    """Flujo del agente: identidad → permisos → filtros → LLM con tools validadas → respuesta citada.

    Depende solo de puertos: no conoce FastAPI, MCP ni Azure.
    """

    def __init__(
        self,
        permissions: PermissionsRepository,
        search: DocumentSearchPort,
        llm: LLMPort,
        audit: AuditLog,
        allowlist: ToolAllowlist,
        sanitizer: DocumentSanitizer,
    ) -> None:
        self._permissions = permissions
        self._search = search
        self._llm = llm
        self._audit = audit
        self._allowlist = allowlist
        self._sanitizer = sanitizer

    async def execute(self, command: QueryCommand, principal: Principal) -> Answer:
        base = {"employee_id": principal.employee_id, **_digest(command.query)}
        try:
            permissions = self._permissions.get(principal.employee_id)
        except EmployeeNotFoundError:
            self._audit.record("access_denied", reason="unknown_employee", **base)
            raise ForbiddenError("Empleado sin permisos") from None
        try:
            check_identity(principal, permissions, command)
            filters = build_search_filters(permissions, command.area)
        except ForbiddenError:
            self._audit.record(
                "access_denied",
                reason="identity_mismatch",
                declared_role=command.role[:64],
                declared_area=command.area[:64],
                declared_employee_id=command.employee_id[:32],
                **base,
            )
            raise

        retrieved: dict[str, Document] = {}
        try:
            answer_text = await self._run_agent(command, permissions, filters, retrieved)
        except DomainError:
            raise
        except Exception:
            log.exception("Fallo del agente")
            raise ServiceUnavailableError(UNAVAILABLE) from None

        citations = [doc_id for doc_id in retrieved if doc_id in answer_text]
        self._audit.record(
            "query",
            role=permissions.role,
            area=filters.area,
            classification_filter=filters.classification,
            retrieved_ids=list(retrieved),
            citations=citations,
            **base,
        )
        return Answer(answer=answer_text, citations=citations)

    async def _run_agent(
        self,
        command: QueryCommand,
        permissions: EmployeePermissions,
        filters: SearchFilters,
        retrieved: dict[str, Document],
    ) -> str:
        role = permissions.role
        tools = [TOOL_SPECS[t] for t in sorted(self._allowlist.for_role(role)) if t in TOOL_SPECS]
        messages: list[ChatMessage] = [
            ChatMessage("system", SYSTEM_PROMPT),
            ChatMessage("user", command.query),
        ]
        for _ in range(MAX_TOOL_ROUNDS):
            response = await self._generate(messages, tools)
            if not response.tool_calls:
                return response.content
            messages.append(ChatMessage("assistant", response.content, response.tool_calls))
            for call in response.tool_calls:
                result = await self._execute_tool(call, role, filters, command, retrieved)
                messages.append(ChatMessage("tool", result, tool_call_id=call.id))
        # Rondas agotadas: se fuerza una respuesta final sin tools.
        return (await self._generate(messages, ())).content

    async def _generate(self, messages: Sequence[ChatMessage], tools: Sequence[ToolSpec]) -> LLMResponse:
        try:
            return await self._llm.generate(messages, tools)
        except DomainError:
            raise
        except Exception:
            log.exception("Fallo del LLM")
            raise ServiceUnavailableError(UNAVAILABLE) from None

    async def _execute_tool(
        self,
        call: ToolCall,
        role: str,
        filters: SearchFilters,
        command: QueryCommand,
        retrieved: dict[str, Document],
    ) -> str:
        # La allowlist se valida ANTES de ejecutar cualquier tool.
        if not self._allowlist.allows(role, call.name):
            self._audit.record("tool_denied", tool=call.name[:64], role=role, employee_id=command.employee_id)
            return DENIED_TOOL_RESULT

        proposed = {k: call.arguments[k] for k in _FILTER_ARGS if k in call.arguments}
        if proposed:
            # Los filtros propuestos por el LLM se ignoran: siempre se usan los del empleado.
            self._audit.record(
                "filter_override_ignored",
                tool=call.name,
                proposed={k: str(v)[:64] for k, v in proposed.items()},
                applied={"area_filter": filters.area, "classification_filter": filters.classification},
            )
        query = call.arguments.get("query")
        if not isinstance(query, str) or not query.strip():
            return "Argumentos inválidos: se requiere `query` de texto."

        try:
            found = await self._search.search(query, filters)
        except SearchRejectedError as e:
            self._audit.record("search_rejected", code=e.code)
            return f"La búsqueda fue rechazada ({e.code}). Reformula la consulta."

        visible: list[Document] = []
        for doc in found:
            if not is_within_scope(doc, filters):
                self._audit.record("out_of_scope_document_dropped", document_id=doc.id)
                continue
            clean = self._sanitizer.sanitize(doc)
            retrieved[clean.id] = clean
            visible.append(clean)
        return render_documents(visible)
