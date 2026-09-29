# agent-api

API FastAPI del agente RAG sobre documentos internos, con RBAC, allowlist de tools y defensa contra prompt injection indirecta. Historias de usuario en `../docs/HU-agente.md`. Diagrama en `../docs/architecture-to-be.drawio`.

## Requisitos

- Python 3.11 o superior
- El servidor MCP de `../mcp-server` (se lanza solo por `stdio`; no necesita credenciales de Azure)

## Instalación

```bash
cd agent-api
python -m venv .venv
source .venv/bin/activate        # fish: source .venv/bin/activate.fish
pip install -r requirements.txt
pip install -e .                 # registra el paquete agent_api
pip install -e ../mcp-server     # servidor MCP (stdio local) y tests e2e
cp .env.example .env             # y ajusta JWT_SECRET
```

## Ejecución

```bash
uvicorn agent_api.main:app --reload
```

La API queda en `http://127.0.0.1:8000` (docs interactivas en `/docs`). Si el puerto está ocupado: `--port 8010`.

Con `LLM_PROVIDER=fake` (por defecto) no se necesita Azure. Emite un JWT de desarrollo y consulta:

```bash
TOKEN=$(python -m agent_api.adapters.inbound.cli.issue_token E001)

curl -X POST http://127.0.0.1:8000/api/v1/docs/query \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"employee_id": "E001", "role": "comercial", "area": "creditos", "query": "condiciones del proveedor de scoring"}'
```

Empleados simulados (`adapters/outbound/permissions/in_memory.py`):

| Empleado | Rol              | Áreas       | Clasificación máx. |
| -------- | ---------------- | ----------- | ------------------ |
| E001     | comercial        | creditos    | interno            |
| E002     | analista_riesgos | riesgos     | confidencial       |
| E003     | tesorero         | tesoreria   | interno            |
| E004     | practicante      | creditos    | publico            |

Respuestas: `200 {answer, citations}`. Errores con formato `{"error": {"code", "message", "details?"}}`:
`400` JSON inválido, `401` sin credenciales válidas, `403` identidad declarada distinta de la autenticada, `422` body inválido, `503` LLM o servidor MCP no disponible. Cada respuesta incluye `X-Correlation-ID` (se acepta uno entrante).

## Configuración

Se lee de `.env` (python-dotenv, sin pisar variables ya exportadas). Ver `.env.example`.

| Variable | Descripción |
| --- | --- |
| `LLM_PROVIDER` | `fake` (local) o `azure_openai` (requiere `AZURE_OPENAI_ENDPOINT`, `_DEPLOYMENT`, `_API_KEY`) |
| `JWT_SECRET` | Obligatoria (≥ 32 caracteres). `JWT_ISSUER` / `JWT_AUDIENCE` opcionales |
| `MCP_CLIENT_TRANSPORT` | `stdio` (lanza `python -m mcp_server`) o `streamable-http` (`MCP_SERVER_URL`, por defecto `http://127.0.0.1:8001/mcp`) |
| `MCP_TIMEOUT_SECONDS`, `MCP_MAX_RETRIES` | Timeout por intento y reintentos (backoff exponencial) |
| `TOOL_ALLOWLIST` | JSON `{"rol": ["tool"]}`; vacío = valores por defecto (`mcp_search_documents` para los 4 roles) |
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | Envía el audit log a Application Insights (requiere `pip install -e ".[azure]"`) |

## Arquitectura (puertos y adaptadores)

```
src/agent_api/
  domain/          entidades, errores, reglas de acceso, allowlist, detección de injection (sin frameworks)
  application/
    ports/         LLMPort, DocumentSearchPort, PermissionsRepository, Authenticator, AuditLog, InjectionDetector
    use_cases/     QueryDocuments: flujo del agente (solo depende de puertos)
    prompts.py     prompt de sistema y bloques <documento> escapados (contenido no confiable)
    sanitizer.py   redacción de injection
  adapters/
    inbound/http/  FastAPI: rutas, auth bearer, correlation id, manejo de errores
    inbound/cli/   emisión de JWT de desarrollo
    outbound/      llm/ (LangChain, Azure OpenAI, fake), search/ (cliente MCP), auth/ (JWT),
                   audit/ (JSON + App Insights), permissions/, agent_tools/
  config.py        variables de entorno
  bootstrap.py     raíz de composición: elige las implementaciones concretas
```

`tests/unit/test_architecture.py` verifica que `domain` y `application` no importen frameworks ni adaptadores.

### Flujo de una consulta

1. **Autenticación** (JWT) → `Principal`. Sin credenciales válidas: 401 y evento `auth_failed`.
2. **Identidad**: `employee_id`, `role` y `area` del body deben coincidir con el token y los permisos; si no, 403 y evento `access_denied`.
3. **Filtros**: `area_filter` y `classification_filter` se calculan en código desde los permisos.
4. **Agente**: el LLM recibe el prompt de sistema y solo las tools de la allowlist de su rol. Cada tool call se valida **antes** de ejecutarse (`tool_denied` si no está permitida). El modelo solo ve el parámetro `query`; si propone filtros se ignoran (`filter_override_ignored`).
5. **Búsqueda MCP** con los filtros del empleado. Los documentos fuera de alcance que devolviera el servidor se descartan igualmente.
6. **Sanitización**: patrones de injection (es/en, con normalización Unicode) redactan la oración sospechosa y conservan el resto (`injection_detected`). Los documentos se entregan en bloques `<documento id="...">` con `&`, `<` y `>` escapados, marcados como datos no confiables.
7. **Respuesta** con citas: solo ids de documentos recuperados con los filtros del empleado y mencionados en la respuesta.

### Auditoría

Una línea JSON por evento en el logger `agent_api.audit` (stderr) con `correlation_id`. Eventos de seguridad (nivel WARNING): `auth_failed`, `access_denied`, `tool_denied`, `filter_override_ignored`, `out_of_scope_document_dropped`, `injection_detected`. Por petición: `query` con empleado, rol, área, hash y longitud de la query, filtros, ids recuperados y citados. Nunca se registran secretos ni texto de documentos.

### Cambiar de modelo

`LangChainChatLLM` acepta cualquier `BaseChatModel` de LangChain con soporte de tools. Para otro proveedor, crea `build_<proveedor>_llm` en `adapters/outbound/llm/`, añade su valor a `LLM_PROVIDERS` en `config.py` y una rama en `bootstrap.build_llm`. Si no está en LangChain, implementa `LLMPort.generate` directamente.

## Tests

```bash
pytest
```

- `tests/unit`: dominio, JWT, cliente MCP (reintentos, timeout, errores), injection, adaptadores LLM, regla de dependencia.
- `tests/integration`: contrato HTTP (400/401/403/422/503, correlation id).
- `tests/e2e`: HTTP + casos de uso + **servidor MCP real en memoria**; solo el LLM es falso. Cubre filtros por área/clasificación, allowlist, filtros propuestos por el LLM, injection y auditoría. Se omiten si `mcp_server` no está instalado.

## Pendiente / límites conocidos

- Autenticación con Entra ID (validación JWKS/RS256): hoy hay un adaptador JWT HS256 simulado detrás del puerto `Authenticator`.
- Azure Prompt Shields: el puerto `InjectionDetector` admite añadirlo; solo hay detección por patrones.
- Envío a Application Insights y despliegue en Container Apps no se han probado contra Azure.
- El flujo del agente es un bucle propio sobre `LLMPort` (no LangGraph), para no acoplar la aplicación a LangChain.
