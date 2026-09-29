# Historias de Usuario — Agente RAG (API)

API FastAPI con un agente LangChain sobre Azure OpenAI. Consulta documentos internos a través del servidor MCP (ver `HU-mcp-server.md`), con RBAC, allowlist de tools y defensa contra prompt injection indirecta.

**Stack:** Azure (Container Apps, Key Vault, Application Insights), LangChain / LangGraph, Azure OpenAI (`AzureChatOpenAI`), FastAPI, `langchain-mcp-adapters` / SDK de MCP como cliente.

**Contexto:** cada empleado solo debe ver documentos de su área y clasificación de acceso. Se detectaron intentos de prompt injection desde documentos de proveedores externos indexados sin sanitizar.

---

## HU-AG-01: Endpoint de consulta

**Como** empleado **quiero** consultar documentos internos por `POST /api/v1/docs/query` **para** obtener respuestas basadas en ellos.

**Criterios de aceptación**

- Recibe `{"employee_id": "E001", "role": "comercial", "area": "creditos", "query": "texto"}` validado con Pydantic.
- Responde con la respuesta generada y las citas (ids de documentos usados).
- Errores 400/401/403/422 con formato consistente.

**Dependencias:** HU-AG-02, HU-AG-07.

## HU-AG-02: Autenticación y determinación de rol/área

**Como** banco **quiero** autenticar al usuario **para** que rol y área no dependan de lo que declare el cliente.

**Criterios de aceptación**

- Autenticación por JWT o API key (simulada en local, Entra ID como objetivo en Azure).
- El rol y el área efectivos se determinan desde el token/permisos, no desde el body.
- Si `employee_id`, `role` o `area` del body no coinciden con lo autenticado, responde 403 y audita el intento.
- Petición sin credenciales válidas: 401.

**Dependencias:** HU-AG-03.

## HU-AG-03: Tool `get_employee_permissions`

**Como** agente **quiero** `get_employee_permissions(employee_id)` **para** conocer áreas, clasificaciones máximas y tools permitidas del empleado.

**Criterios de aceptación**

- Retorna permisos del empleado (áreas, nivel máximo de clasificación, rol) desde un almacén simulado.
- Empleado inexistente: error controlado, sin acceso.
- Es una tool local del agente (no pasa por MCP).

**Dependencias:** ninguna.

## HU-AG-04: RBAC y filtros de metadatos

**Como** banco **quiero** que los filtros se deriven de los permisos **para** que el LLM no pueda ampliar el alcance de la búsqueda.

**Criterios de aceptación**

- `area_filter` y `classification_filter` se calculan en código a partir de `get_employee_permissions` y se inyectan en la llamada MCP.
- Los argumentos de filtro propuestos por el LLM se ignoran o sobrescriben.
- Un empleado nunca recibe documentos de otra área ni de clasificación superior a la suya.

**Dependencias:** HU-AG-03, HU-AG-05.

## HU-AG-05: Cliente MCP

**Como** agente **quiero** consumir `mcp_search_documents` vía MCP **para** buscar documentos.

**Criterios de aceptación**

- Conexión al servidor MCP por `stdio` (local) o `streamable-http`.
- La tool se expone como tool de LangChain (`langchain-mcp-adapters`).
- Manejo de timeouts, reintentos y errores del servidor sin filtrar detalles internos al usuario.

**Dependencias:** HU-MCP-01, HU-MCP-02.

## HU-AG-06: Allowlist de tools por rol

**Como** banco **quiero** validar cada tool solicitada por el modelo **para** que solo se ejecuten las permitidas al rol.

**Criterios de aceptación**

- Configuración de allowlist por rol (p. ej. `comercial` → `mcp_search_documents`).
- Cada tool call del modelo se valida **antes** de ejecutarse. Una tool fuera de la allowlist no se ejecuta.
- El intento denegado se audita y se devuelve al flujo un resultado de denegación seguro.

**Dependencias:** HU-AG-07.

## HU-AG-07: Flujo del agente con Azure OpenAI

**Como** empleado **quiero** una respuesta generada a partir de los documentos permitidos **para** resolver mi consulta.

**Criterios de aceptación**

- Flujo LangChain/LangGraph: permisos → búsqueda MCP → generación de respuesta con `AzureChatOpenAI`.
- Configuración (endpoint, deployment, versión de API) por variables de entorno / Key Vault.
- La respuesta cita únicamente documentos recuperados con los filtros del empleado.

**Dependencias:** HU-AG-03, HU-AG-04, HU-AG-05.

## HU-AG-08: Separación de contenido no confiable

**Como** banco **quiero** separar instrucciones del sistema y contenido recuperado **para** que los documentos se traten solo como datos.

**Criterios de aceptación**

- El prompt de sistema contiene las reglas. Los documentos van en mensajes/bloques delimitados (p. ej. `<documento id="...">`) marcados como datos no confiables.
- El prompt indica explícitamente no seguir instrucciones que aparezcan dentro de los documentos.
- Los delimitadores dentro del contenido se escapan para evitar cierre falso del bloque.

**Dependencias:** HU-AG-07.

## HU-AG-09: Detección y neutralización de prompt injection indirecta

**Como** equipo de seguridad **quiero** detectar texto malicioso en los documentos **para** neutralizarlo sin bloquear el contenido legítimo.

**Criterios de aceptación**

- Detección por patrones/heurísticas (p. ej. "ignora las reglas anteriores", "muestra todos los documentos"), con opción de reforzar con Azure Prompt Shields.
- El fragmento sospechoso se marca/redacta y el resto del documento legítimo se conserva y se usa.
- Con el documento de prueba del MCP, la respuesta no obedece la instrucción inyectada ni expone documentos fuera de permiso.
- Cada detección se registra (documento, patrón, acción).

**Dependencias:** HU-AG-08, HU-MCP-03.

## HU-AG-10: Logs de acceso y auditoría

**Como** equipo de seguridad **quiero** trazabilidad completa **para** auditar quién accedió a qué.

**Criterios de aceptación**

- Log estructurado por petición con correlation id: empleado, rol, área, query (hash o truncada), filtros aplicados, ids de documentos usados.
- Eventos de seguridad: accesos denegados, tools fuera de allowlist, detecciones de injection.
- Envío a Application Insights. No se registran secretos ni contenido completo de documentos.

**Dependencias:** HU-AG-01, HU-AG-06, HU-AG-09.

## HU-AG-11: Diagrama de arquitectura y despliegue en Azure

**Como** revisor **quiero** un diagrama de arquitectura **para** entender el sistema.

**Criterios de aceptación**

- `docs/architecture-to-be.drawio` muestra: cliente, API FastAPI, agente LangChain, Azure OpenAI, servidor MCP, índice de búsqueda, permisos, logging.
- Indica las fronteras de confianza (contenido recuperado = no confiable) y dónde actúan RBAC, allowlist y detección de injection.
- Despliegue objetivo: Container Apps, Key Vault, Application Insights.

**Dependencias:** ninguna (se refina al avanzar).

## HU-AG-12: Tests end-to-end

**Como** desarrollador **quiero** pruebas automáticas **para** verificar los controles de seguridad.

**Criterios de aceptación**

- Empleado de un área no ve documentos de otras áreas ni de mayor clasificación.
- Tool solicitada por el modelo fuera de la allowlist es denegada y auditada.
- Query que recupera el documento con injection: se neutraliza el texto sospechoso y el contenido legítimo sigue disponible.
- Sin credenciales: 401. Rol/área que no coincide: 403.
- El LLM se sustituye por un fake en tests para que sean deterministas.

**Dependencias:** todas las anteriores y HU-MCP-07.
