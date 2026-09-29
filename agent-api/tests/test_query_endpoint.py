import pytest
from fastapi.testclient import TestClient

from agent_api.errors import ForbiddenError, UnauthorizedError
from agent_api.main import create_app
from agent_api.schemas import QueryRequest, QueryResponse
from agent_api.service import get_query_service

VALID = {"employee_id": "E001", "role": "comercial", "area": "creditos", "query": "texto"}


class FakeService:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error

    async def answer(self, request: QueryRequest) -> QueryResponse:
        if self.error:
            raise self.error
        return QueryResponse(answer=f"resp: {request.query}", citations=["DOC-1"])


def client_with(service) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_query_service] = lambda: service
    return TestClient(app, raise_server_exceptions=False)


def test_ok():
    r = client_with(FakeService()).post("/api/v1/docs/query", json=VALID)
    assert r.status_code == 200
    assert r.json() == {"answer": "resp: texto", "citations": ["DOC-1"]}


def test_malformed_json_is_400():
    r = client_with(FakeService()).post(
        "/api/v1/docs/query", content="{no", headers={"content-type": "application/json"}
    )
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "bad_request"


@pytest.mark.parametrize("patch", [{"query": ""}, {"employee_id": "E 1;"}, {"extra": 1}, {"role": None}])
def test_invalid_body_is_422(patch):
    r = client_with(FakeService()).post("/api/v1/docs/query", json={**VALID, **patch})
    assert r.status_code == 422
    body = r.json()["error"]
    assert body["code"] == "validation_error" and body["details"]


def test_missing_field_is_422():
    body = {k: v for k, v in VALID.items() if k != "query"}
    r = client_with(FakeService()).post("/api/v1/docs/query", json=body)
    assert r.status_code == 422
    assert r.json()["error"]["details"][0]["field"] == "query"


@pytest.mark.parametrize(
    "exc,status,code",
    [(UnauthorizedError("no"), 401, "unauthorized"), (ForbiddenError("no"), 403, "forbidden")],
)
def test_domain_errors_use_common_format(exc, status, code):
    r = client_with(FakeService(exc)).post("/api/v1/docs/query", json=VALID)
    assert r.status_code == status
    assert r.json() == {"error": {"code": code, "message": "no"}}


def test_unhandled_error_does_not_leak():
    r = client_with(FakeService(RuntimeError("secreto interno"))).post("/api/v1/docs/query", json=VALID)
    assert r.status_code == 500
    assert "secreto" not in r.text


def test_unknown_route_uses_common_format():
    r = client_with(FakeService()).get("/nope")
    assert r.status_code == 404 and r.json()["error"]["code"] == "not_found"
