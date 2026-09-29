# agent-api

API FastAPI del agente RAG sobre documentos internos. Historias de usuario en `../docs/HU-agente.md`.

## Requisitos

- Python 3.11 o superior

## Instalación

```bash
cd agent-api
python -m venv .venv
source .venv/bin/activate        # fish: source .venv/bin/activate.fish
pip install -r requirements.txt
pip install -e .                 # registra el paquete agent_api
```

## Ejecución

```bash
uvicorn agent_api.main:app --reload
```

La API queda en `http://127.0.0.1:8000`. Documentación interactiva en `http://127.0.0.1:8000/docs`.

Ejemplo de petición:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/docs/query \
  -H "Content-Type: application/json" \
  -d '{"employee_id": "E001", "role": "comercial", "area": "creditos", "query": "texto"}'
```

> Estado actual: solo está implementado HU-AG-01 (endpoint, validación y errores). El flujo del agente (HU-AG-07)
> y la autenticación (HU-AG-02) están pendientes, por lo que la petición anterior responde `500` hasta entonces.
> Los errores `400` (JSON inválido) y `422` (body inválido) ya funcionan.

## Tests

```bash
pytest
```
