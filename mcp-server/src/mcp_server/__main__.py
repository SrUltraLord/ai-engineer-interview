import logging

from dotenv import find_dotenv, load_dotenv

from mcp_server.config import Settings
from mcp_server.server import build_server


def main() -> None:
    # Lee .env (desde el directorio actual hacia arriba); no pisa variables ya exportadas.
    load_dotenv(find_dotenv(usecwd=True))
    settings = Settings.from_env()
    server = build_server(settings)
    logging.getLogger("mcp_server").info(
        "server_start",
        extra={
            "transport": settings.transport,
            "host": settings.host,
            "port": settings.port,
            "top_k": settings.top_k,
            "log_level": settings.log_level,
            "embeddings_enabled": settings.embeddings_enabled,
        },
    )
    server.run(transport=settings.transport)


if __name__ == "__main__":
    main()
