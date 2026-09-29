import pytest
from fastapi.testclient import TestClient

from agent_api.adapters.inbound.http.app import create_app
from agent_api.adapters.outbound.auth.jwt_auth import JwtAuthenticator
from agent_api.bootstrap import Container
from agent_api.domain.errors import ForbiddenError, ServiceUnavailableError
from agent_api.domain.query import Answer, QueryCommand

VALID = {"employee_id": "E001", "role": "comercial", "area": "creditos", "query": "texto"}
auth = JwtAuthenticator("s" * 40)
HEADERS = {"Authorization": f"Bearer {auth.issue('E001')}"}


class FakeUseCase:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.calls = []

    async def execute(self, command: QueryCommand, principal) -> Answer:
        self.calls.append((command, principal))
        if self.error:
            raise self.error
        return Answer(answer=f"resp: {command.query}", citations=["DOC-1"])


def client_with(use_case, audit=None) -> TestClient:
    class NullAudit:
        def record(self, event, **fields): ...

    return TestClient(create_app(Container(use_case, auth, audit or NullAudit())), raise_server_exceptions=False)


def post(client, json=VALID, headers=HEADERS, **kw):
    return client.post("/api/v1/docs/query", json=json, headers=headers, **kw)


def test_ok_maps_request_to_command_and_principal():
    uc = FakeUseCase()
    r = post(client_with(uc))
    assert r.status_code == 200
    assert r.json() == {"answer": "resp: texto", "citations": ["DOC-1"]}
    command, principal = uc.calls[0]
    assert command == QueryCommand("E001", "comercial", "creditos", "texto") and principal.employee_id == "E001"


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer basura"}, {"Authorization": "Basic abc"}])
def test_missing_or_invalid_credentials_is_401(headers):
    uc = FakeUseCase()
    r = post(client_with(uc), headers=headers)
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "unauthorized" and uc.calls == []


def test_401_is_audited():
    events = []

    class A:
        def record(self, event, **fields):
            events.append(event)

    post(client_with(FakeUseCase(), A()), headers={})
    assert events == ["auth_failed"]


def test_malformed_json_is_400():
    r = client_with(FakeUseCase()).post(
        "/api/v1/docs/query", content="{no", headers={**HEADERS, "content-type": "application/json"}
    )
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "bad_request"


@pytest.mark.parametrize("patch", [{"query": ""}, {"employee_id": "E 1;"}, {"extra": 1}, {"role": None}])
def test_invalid_body_is_422(patch):
    r = post(client_with(FakeUseCase()), json={**VALID, **patch})
    assert r.status_code == 422
    body = r.json()["error"]
    assert body["code"] == "validation_error" and body["details"]


def test_missing_field_is_422():
    r = post(client_with(FakeUseCase()), json={k: v for k, v in VALID.items() if k != "query"})
    assert r.status_code == 422
    assert r.json()["error"]["details"][0]["field"] == "query"


@pytest.mark.parametrize(
    "exc,status,code",
    [
        (ForbiddenError("no"), 403, "forbidden"),
        (ServiceUnavailableError("caído"), 503, "service_unavailable"),
    ],
)
def test_domain_errors_use_common_format(exc, status, code):
    r = post(client_with(FakeUseCase(exc)))
    assert r.status_code == status
    assert r.json() == {"error": {"code": code, "message": exc.message}}


def test_unhandled_error_does_not_leak():
    r = post(client_with(FakeUseCase(RuntimeError("secreto interno"))))
    assert r.status_code == 500
    assert "secreto" not in r.text


def test_unknown_route_uses_common_format():
    r = client_with(FakeUseCase()).get("/nope")
    assert r.status_code == 404 and r.json()["error"]["code"] == "not_found"


def test_correlation_id_is_generated_and_propagated():
    c = client_with(FakeUseCase())
    assert len(post(c).headers["X-Correlation-ID"]) == 32
    assert post(c, headers={**HEADERS, "X-Correlation-ID": "mi-id-1"}).headers["X-Correlation-ID"] == "mi-id-1"
    assert post(c, headers={**HEADERS, "X-Correlation-ID": "mal id!\n"}).headers["X-Correlation-ID"] != "mal id!\n"
