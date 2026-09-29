import json
import os
from dataclasses import dataclass

LLM_PROVIDERS = ("azure_openai", "fake")
MCP_TRANSPORTS = ("stdio", "streamable-http")


@dataclass(frozen=True)
class Settings:
    llm_provider: str = "fake"
    azure_openai_endpoint: str | None = None
    azure_openai_deployment: str | None = None
    azure_openai_api_version: str = "2024-10-21"
    azure_openai_api_key: str | None = None  # En Azure: referencia a Key Vault

    jwt_secret: str | None = None  # En Azure: referencia a Key Vault
    jwt_issuer: str | None = None
    jwt_audience: str | None = None

    mcp_transport: str = "stdio"
    mcp_server_url: str = "http://127.0.0.1:8001/mcp"
    mcp_server_command: str | None = None  # por defecto: <python> -m mcp_server
    mcp_server_cwd: str | None = None
    mcp_timeout_seconds: float = 10.0
    mcp_max_retries: int = 2

    tool_allowlist: dict[str, frozenset[str]] | None = None  # None = valores por defecto
    appinsights_connection_string: str | None = None

    @classmethod
    def from_env(cls) -> "Settings":
        env = os.environ.get
        provider = env("LLM_PROVIDER", cls.llm_provider)
        if provider not in LLM_PROVIDERS:
            raise ValueError(f"LLM_PROVIDER inválido: {provider!r}. Permitidos: {', '.join(LLM_PROVIDERS)}")
        transport = env("MCP_CLIENT_TRANSPORT", cls.mcp_transport)
        if transport not in MCP_TRANSPORTS:
            raise ValueError(
                f"MCP_CLIENT_TRANSPORT inválido: {transport!r}. Permitidos: {', '.join(MCP_TRANSPORTS)}"
            )
        return cls(
            llm_provider=provider,
            azure_openai_endpoint=env("AZURE_OPENAI_ENDPOINT") or None,
            azure_openai_deployment=env("AZURE_OPENAI_DEPLOYMENT") or None,
            azure_openai_api_version=env("AZURE_OPENAI_API_VERSION") or cls.azure_openai_api_version,
            azure_openai_api_key=env("AZURE_OPENAI_API_KEY") or None,
            jwt_secret=env("JWT_SECRET") or None,
            jwt_issuer=env("JWT_ISSUER") or None,
            jwt_audience=env("JWT_AUDIENCE") or None,
            mcp_transport=transport,
            mcp_server_url=env("MCP_SERVER_URL") or cls.mcp_server_url,
            mcp_server_command=env("MCP_SERVER_COMMAND") or None,
            mcp_server_cwd=env("MCP_SERVER_CWD") or None,
            mcp_timeout_seconds=float(env("MCP_TIMEOUT_SECONDS") or cls.mcp_timeout_seconds),
            mcp_max_retries=int(env("MCP_MAX_RETRIES") or cls.mcp_max_retries),
            tool_allowlist=_parse_allowlist(env("TOOL_ALLOWLIST")),
            appinsights_connection_string=env("APPLICATIONINSIGHTS_CONNECTION_STRING") or None,
        )


def _parse_allowlist(raw: str | None) -> dict[str, frozenset[str]] | None:
    """TOOL_ALLOWLIST='{"comercial": ["mcp_search_documents"]}'."""
    if not raw:
        return None
    try:
        data = json.loads(raw)
        return {str(role): frozenset(map(str, tools)) for role, tools in data.items()}
    except (ValueError, AttributeError, TypeError):
        raise ValueError('TOOL_ALLOWLIST inválido: se espera JSON {"rol": ["tool", ...]}') from None
