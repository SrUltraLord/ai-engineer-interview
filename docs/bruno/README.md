# Colección Bruno — Agente RAG

Colección para probar `POST /api/v1/docs/query` con [Bruno](https://www.usebruno.com/). Abre Bruno → *Open Collection* → carpeta `docs/bruno`.

## Preparación

1. Arranca la API (ver `agent-api/README.md`): `uvicorn agent_api.main:app --reload`. Si usas otro puerto, cambia `baseUrl` en el entorno.
2. Selecciona el entorno **local**.
3. Genera los JWT de desarrollo (usan el `JWT_SECRET` de `agent-api/.env`) y pégalos como variables secretas del entorno:

```bash
cd agent-api
python -m agent_api.adapters.inbound.cli.issue_token E001   # -> tokenE001
python -m agent_api.adapters.inbound.cli.issue_token E002   # -> tokenE002
python -m agent_api.adapters.inbound.cli.issue_token E004   # -> tokenE004
```

Los tokens duran 1 hora. Los secretos de Bruno se guardan solo en tu máquina (no van al repositorio).

## Requests

| # | Request | Espera |
| - | ------- | ------ |
| 01 | Consulta OK (E001) | 200, solo DOC-001/002/006 |
| 02 | Prompt injection neutralizada | 200, DOC-006 citable, sin documentos fuera de permiso |
| 03 | Practicante (E004) | 200, solo DOC-002 (público) |
| 04 | Analista de riesgos (E002) | 200, DOC-004 (confidencial de su área) |
| 05 | Sin credenciales | 401 `unauthorized` |
| 06 | Rol declarado distinto | 403 `forbidden` |
| 07 | Área no permitida | 403 `forbidden` |
| 08 | Employee id ajeno | 403 `forbidden` |
| 09 | Body inválido | 422 `validation_error` |

Cada request incluye asserts/tests. Con el CLI, desde `docs/bruno`:

```bash
npx @usebruno/cli run --env local \
  --env-var tokenE001=<jwt> --env-var tokenE002=<jwt> --env-var tokenE004=<jwt>
```

**400 (JSON malformado):** Bruno no puede enviar un cuerpo JSON inválido (lo normaliza o cambia el `Content-Type`, y la API responde 422), por lo que no hay request para ese caso. Pruébalo con curl:

```bash
curl -i -X POST http://127.0.0.1:8000/api/v1/docs/query \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"employee_id": '
```

El audit log (eventos `access_denied`, `injection_detected`, etc.) se ve en la terminal donde corre `uvicorn`.

Nota: con `LLM_PROVIDER=fake` la respuesta es determinista y las citas dependen de la búsqueda; con Azure OpenAI el texto varía, pero las citas siguen limitadas a los documentos permitidos.
