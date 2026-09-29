# Servidor MCP de Document Retrieval

Servidor MCP (SDK oficial de Python, `FastMCP`) que expone la tool `mcp_search_documents(query, area_filter, classification_filter)` sobre un corpus simulado. Las historias de usuario están en `../docs/HU-mcp-server.md`.

## Requisitos

- Python 3.11 o superior
- No necesita credenciales de Azure: el backend de búsqueda es en memoria.

## Instalación

Desde `mcp-server/`:

```bash
python3 -m venv .venv
source .venv/bin/activate          # fish: source .venv/bin/activate.fish
pip install -r requirements.txt
pip install -e .                   # instala el paquete mcp_server
```

## Configuración

Variables de entorno (ver `.env.example`; el servidor no carga el archivo `.env` por sí solo, exporta las variables o antepónlas al comando):

| Variable         | Por defecto | Descripción                            |
| ---------------- | ----------- | -------------------------------------- |
| `MCP_TRANSPORT`  | `stdio`     | `stdio` o `streamable-http`            |
| `MCP_HOST`       | `127.0.0.1` | Host (solo `streamable-http`)          |
| `MCP_PORT`       | `8000`      | Puerto (solo `streamable-http`)        |
| `MCP_LOG_LEVEL`  | `INFO`      | Nivel de log                           |

## Ejecución

**stdio** (un cliente MCP lanza el proceso; por sí solo queda esperando entrada):

```bash
python -m mcp_server
```

**streamable-http** (endpoint en `http://127.0.0.1:8000/mcp`):

```bash
MCP_TRANSPORT=streamable-http python -m mcp_server
# fish: env MCP_TRANSPORT=streamable-http python -m mcp_server
```

## Probar la tool

Con el servidor `streamable-http` levantado, en otra terminal:

```bash
python - <<'EOF'
import asyncio
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

async def main():
    async with streamablehttp_client("http://127.0.0.1:8000/mcp") as (r, w, _):
        async with ClientSession(r, w) as s:
            await s.initialize()
            res = await s.call_tool("mcp_search_documents", {
                "query": "créditos de consumo",
                "area_filter": "creditos",
                "classification_filter": "interno",
            })
            print(res.structuredContent)

asyncio.run(main())
EOF
```

`classification_filter` es el nivel máximo permitido (`publico` < `interno` < `confidencial`). Las áreas del corpus son `creditos`, `riesgos` y `tesoreria`.

Para inspeccionar el servidor de forma interactiva también sirve el MCP Inspector: `npx @modelcontextprotocol/inspector python -m mcp_server`.

## Tests

```bash
pytest
```
