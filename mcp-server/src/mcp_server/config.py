import os
from dataclasses import dataclass

TRANSPORTS = ("stdio", "streamable-http")


@dataclass(frozen=True)
class Settings:
    transport: str = "stdio"
    host: str = "127.0.0.1"
    port: int = 8000
    log_level: str = "INFO"

    @classmethod
    def from_env(cls) -> "Settings":
        transport = os.environ.get("MCP_TRANSPORT", cls.transport)
        if transport not in TRANSPORTS:
            raise ValueError(
                f"MCP_TRANSPORT inválido: {transport!r}. Valores permitidos: {', '.join(TRANSPORTS)}"
            )
        return cls(
            transport=transport,
            host=os.environ.get("MCP_HOST", cls.host),
            port=int(os.environ.get("MCP_PORT", cls.port)),
            log_level=os.environ.get("MCP_LOG_LEVEL", cls.log_level).upper(),
        )
