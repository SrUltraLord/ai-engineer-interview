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

Las variables se leen de un archivo `.env` con `python-dotenv` (cópialo con `cp .env.example .env` dentro de `mcp-server/`). Las variables ya exportadas en el shell tienen prioridad sobre el `.env`:

| Variable         | Por defecto | Descripción                            |
| ---------------- | ----------- | -------------------------------------- |
| `MCP_TRANSPORT`  | `stdio`     | `stdio` o `streamable-http`            |
| `MCP_HOST`       | `127.0.0.1` | Host (solo `streamable-http`)          |
| `MCP_PORT`       | `8001`      | Puerto (solo `streamable-http`)        |
| `MCP_LOG_LEVEL`  | `INFO`      | Nivel de log                           |
| `MCP_LOG_FORMAT` | `json`      | `json` o `text`                        |
| `MCP_TOP_K`      | `5`         | Máximo de documentos por búsqueda      |

Embeddings con Azure OpenAI (opcionales): si están definidas `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY` y `AZURE_OPENAI_EMBEDDING_DEPLOYMENT` (más `AZURE_OPENAI_API_VERSION`, por defecto `2024-10-21`), la búsqueda usa similitud vectorial en memoria. Si falta alguna, usa un ranking simple por coincidencia de términos, sin credenciales.

## Ejecución

**stdio** (un cliente MCP lanza el proceso; por sí solo queda esperando entrada):

```bash
python -m mcp_server
```

**streamable-http** (endpoint en `http://127.0.0.1:8001/mcp`):

```bash
# con MCP_TRANSPORT=streamable-http en .env:
python -m mcp_server

# o sin .env (fish: env MCP_TRANSPORT=streamable-http python -m mcp_server):
MCP_TRANSPORT=streamable-http python -m mcp_server
```

## Probar la tool

Con el servidor `streamable-http` levantado, en otra terminal:

```bash
python - <<'EOF'
import asyncio
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

async def main():
    async with streamablehttp_client("http://127.0.0.1:8001/mcp") as (r, w, _):
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

## Errores y auditoría

Las entradas inválidas devuelven `isError: true` con `{"error": {"code", "message", "field", "request_id"}}` y sin trazas internas. Códigos: `INVALID_QUERY` (vacía o de más de 1000 caracteres), `INVALID_FILTER` (filtro ausente o fuera del catálogo) e `INTERNAL_ERROR`. Los filtros son obligatorios: nunca se busca sin ellos.

## Logging y observabilidad

Todo el proceso (aplicación y librería MCP) escribe en **stderr** con un único handler, porque stdout queda libre para el protocolo `stdio`. Con `MCP_LOG_FORMAT=json` cada evento es una línea JSON con `timestamp`, `level`, `logger`, `message` y sus campos; con `text` es una línea legible con `clave=valor`. Los logs propios de uvicorn (líneas `INFO:` de arranque) siguen en texto plano. En Azure Container Apps stderr llega a Log Analytics / Application Insights.

- **Arranque:** evento `server_start` con transporte, host, puerto, `top_k`, nivel de log y si los embeddings están activos (sin secretos).
- **Auditoría** (logger `mcp_server.audit`, evento `tool_call`): una línea por invocación, exitosa o rechazada, con `request_id`, `backend`, `tool`, `status`, filtros, `query_sha256` y `query_length` (nunca la query en claro), `document_ids`, `result_count`, `latency_ms` y `error_code`. No incluye texto de documentos. Los eventos de auditoría se emiten siempre, aunque `MCP_LOG_LEVEL` sea alto.
- **Correlación:** cada llamada tiene un `request_id`. Se devuelve al cliente en los errores, así que un reporte de soporte se puede cruzar con el log.
- **Errores internos:** se registran con traza completa (campo `exception`) y `request_id`; el cliente solo recibe el mensaje genérico.
- **Depuración:** con `MCP_LOG_LEVEL=DEBUG` el backend vectorial registra candidatos, embeddings calculados y aciertos de caché.

## Tests

```bash
pytest
```

Los tests no requieren credenciales de Azure: usan siempre el fallback simulado, aunque haya variables `AZURE_OPENAI_*` definidas.
