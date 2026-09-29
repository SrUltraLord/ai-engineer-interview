import json
import logging
import sys
from datetime import datetime, timezone

LOG_FORMATS = ("json", "text")
_MARK = "_mcp_server_handler"
_STANDARD = set(logging.LogRecord("", 0, "", 0, "", (), None).__dict__) | {"message", "asctime"}


def _fields(record: logging.LogRecord) -> dict:
    """Campos estructurados: todo lo pasado en `extra=` más el diccionario opcional `fields`."""
    extra = {k: v for k, v in record.__dict__.items() if k not in _STANDARD and k != "fields"}
    return {**getattr(record, "fields", {}), **extra}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "timestamp": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            **_fields(record),
        }
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(entry, ensure_ascii=False, default=str)


class TextFormatter(logging.Formatter):
    def __init__(self) -> None:
        super().__init__("%(asctime)s %(levelname)s %(name)s %(message)s")

    def format(self, record: logging.LogRecord) -> str:
        line = super().format(record)
        fields = " ".join(f"{k}={json.dumps(v, ensure_ascii=False, default=str)}" for k, v in _fields(record).items())
        return f"{line} {fields}".rstrip()


def _is_fastmcp_handler(handler: logging.Handler) -> bool:
    """FastMCP instala un RichHandler, o un StreamHandler plano si `rich` no está instalado."""
    return type(handler).__name__ == "RichHandler" or type(handler) is logging.StreamHandler


def configure_logging(level: str = "INFO", fmt: str = "json") -> None:
    """Un único handler en stderr (stdout queda libre para el protocolo stdio) para todo el proceso.

    Sustituye el handler que instala FastMCP, de modo que los logs de la librería y los de
    la aplicación salgan con el mismo formato. Es idempotente."""
    root = logging.getLogger()
    for handler in list(root.handlers):
        if getattr(handler, _MARK, False) or _is_fastmcp_handler(handler):
            root.removeHandler(handler)
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(JsonFormatter() if fmt == "json" else TextFormatter())
    setattr(handler, _MARK, True)
    root.addHandler(handler)
    root.setLevel(level)
    # La auditoría no se apaga con MCP_LOG_LEVEL: siempre emite INFO.
    logging.getLogger("mcp_server.audit").setLevel(logging.INFO)
