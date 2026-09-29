import os
from dataclasses import dataclass

TRANSPORTS = ("stdio", "streamable-http")
LOG_FORMATS = ("json", "text")


@dataclass(frozen=True)
class Settings:
    transport: str = "stdio"
    host: str = "127.0.0.1"
    port: int = 8001
    log_level: str = "INFO"
    log_format: str = "json"
    top_k: int = 5
    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_api_version: str = "2024-10-21"
    azure_openai_embedding_deployment: str = ""

    @property
    def embeddings_enabled(self) -> bool:
        return bool(
            self.azure_openai_endpoint
            and self.azure_openai_api_key
            and self.azure_openai_embedding_deployment
        )

    @classmethod
    def from_env(cls) -> "Settings":
        transport = os.environ.get("MCP_TRANSPORT", cls.transport)
        if transport not in TRANSPORTS:
            raise ValueError(
                f"MCP_TRANSPORT inválido: {transport!r}. Valores permitidos: {', '.join(TRANSPORTS)}"
            )
        log_format = os.environ.get("MCP_LOG_FORMAT", cls.log_format).lower()
        if log_format not in LOG_FORMATS:
            raise ValueError(
                f"MCP_LOG_FORMAT inválido: {log_format!r}. Valores permitidos: {', '.join(LOG_FORMATS)}"
            )
        top_k = int(os.environ.get("MCP_TOP_K", cls.top_k))
        if top_k < 1:
            raise ValueError(f"MCP_TOP_K debe ser >= 1, recibido: {top_k}")
        return cls(
            transport=transport,
            host=os.environ.get("MCP_HOST", cls.host),
            port=int(os.environ.get("MCP_PORT", cls.port)),
            log_level=os.environ.get("MCP_LOG_LEVEL", cls.log_level).upper(),
            log_format=log_format,
            top_k=top_k,
            azure_openai_endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT", ""),
            azure_openai_api_key=os.environ.get("AZURE_OPENAI_API_KEY", ""),
            azure_openai_api_version=os.environ.get(
                "AZURE_OPENAI_API_VERSION", cls.azure_openai_api_version
            ),
            azure_openai_embedding_deployment=os.environ.get(
                "AZURE_OPENAI_EMBEDDING_DEPLOYMENT", ""
            ),
        )
