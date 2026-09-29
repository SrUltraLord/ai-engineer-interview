from mcp_server.config import Settings
from mcp_server.server import build_server


def main() -> None:
    settings = Settings.from_env()
    build_server(settings).run(transport=settings.transport)


if __name__ == "__main__":
    main()
