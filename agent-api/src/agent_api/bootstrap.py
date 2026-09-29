"""Raíz de composición: único lugar que conoce las implementaciones concretas."""

from dataclasses import dataclass

from agent_api.adapters.outbound.audit.app_insights import configure_app_insights
from agent_api.adapters.outbound.audit.json_logger import JsonAuditLog, configure_audit_logging
from agent_api.adapters.outbound.auth.jwt_auth import JwtAuthenticator
from agent_api.adapters.outbound.llm.fake import FakeLLM
from agent_api.adapters.outbound.permissions.in_memory import InMemoryPermissionsRepository
from agent_api.adapters.outbound.search.mcp_client import (
    McpDocumentSearch,
    http_session_factory,
    stdio_session_factory,
)
from agent_api.application.ports.audit import AuditLog
from agent_api.application.ports.auth import Authenticator
from agent_api.application.ports.llm import LLMPort
from agent_api.application.ports.search import DocumentSearchPort
from agent_api.application.sanitizer import DocumentSanitizer
from agent_api.application.use_cases.query_documents import QueryDocuments
from agent_api.config import Settings
from agent_api.domain.injection import PatternInjectionDetector
from agent_api.domain.tools import ToolAllowlist


@dataclass
class Container:
    query_documents: QueryDocuments
    authenticator: Authenticator
    audit: AuditLog


def build_llm(settings: Settings) -> LLMPort:
    if settings.llm_provider == "azure_openai":
        from agent_api.adapters.outbound.llm.azure_openai import build_azure_openai_llm

        return build_azure_openai_llm(settings)
    # Para otro proveedor: añadir su adaptador y una rama aquí.
    return FakeLLM()


def build_search(settings: Settings) -> DocumentSearchPort:
    if settings.mcp_transport == "streamable-http":
        factory = http_session_factory(settings.mcp_server_url)
    else:
        factory = stdio_session_factory(settings.mcp_server_command, settings.mcp_server_cwd)
    return McpDocumentSearch(factory, settings.mcp_timeout_seconds, settings.mcp_max_retries)


def build_authenticator(settings: Settings) -> Authenticator:
    if not settings.jwt_secret:
        raise ValueError("Falta JWT_SECRET (ver .env.example)")
    return JwtAuthenticator(settings.jwt_secret, settings.jwt_issuer, settings.jwt_audience)


def build_container(settings: Settings) -> Container:
    configure_audit_logging()
    configure_app_insights(settings.appinsights_connection_string)
    audit = JsonAuditLog()
    use_case = QueryDocuments(
        permissions=InMemoryPermissionsRepository(),
        search=build_search(settings),
        llm=build_llm(settings),
        audit=audit,
        allowlist=ToolAllowlist(settings.tool_allowlist),
        sanitizer=DocumentSanitizer([PatternInjectionDetector()], audit),
    )
    return Container(use_case, build_authenticator(settings), audit)
