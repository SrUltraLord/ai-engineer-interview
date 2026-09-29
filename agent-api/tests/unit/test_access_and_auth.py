import time

import jwt
import pytest

from agent_api.adapters.outbound.auth.jwt_auth import JwtAuthenticator
from agent_api.domain.access import SearchFilters, build_search_filters, check_identity, is_within_scope
from agent_api.domain.auth import Principal
from agent_api.domain.documents import Document
from agent_api.domain.errors import ForbiddenError, UnauthorizedError
from agent_api.domain.permissions import EmployeePermissions
from agent_api.domain.query import QueryCommand
from agent_api.domain.tools import ToolAllowlist

SECRET = "s" * 40
auth = JwtAuthenticator(SECRET, issuer="banco", audience="agente")
perms = EmployeePermissions("E001", "comercial", ["creditos"], "interno")


def test_valid_token():
    assert auth.authenticate(auth.issue("E001")) == Principal("E001")


@pytest.mark.parametrize("token", [None, "", "basura", "a.b.c"])
def test_invalid_tokens(token):
    with pytest.raises(UnauthorizedError):
        auth.authenticate(token)


def _encode(**claims):
    base = {"sub": "E001", "exp": int(time.time()) + 60, "iss": "banco", "aud": "agente"}
    return jwt.encode({**base, **claims}, SECRET, algorithm="HS256")


def test_rejects_expired_wrong_issuer_audience_secret_and_missing_claims():
    with pytest.raises(UnauthorizedError):
        auth.authenticate(_encode(exp=int(time.time()) - 10))
    with pytest.raises(UnauthorizedError):
        auth.authenticate(_encode(iss="otro"))
    with pytest.raises(UnauthorizedError):
        auth.authenticate(_encode(aud="otro"))
    with pytest.raises(UnauthorizedError):
        auth.authenticate(jwt.encode({"sub": "E001", "exp": int(time.time()) + 60, "iss": "banco", "aud": "agente"}, "x" * 40, algorithm="HS256"))
    with pytest.raises(UnauthorizedError):
        auth.authenticate(jwt.encode({"exp": int(time.time()) + 60, "iss": "banco", "aud": "agente"}, SECRET, algorithm="HS256"))


def test_rejects_alg_none():
    token = jwt.encode({"sub": "E001", "exp": int(time.time()) + 60}, None, algorithm="none")
    with pytest.raises(UnauthorizedError):
        JwtAuthenticator(SECRET).authenticate(token)


@pytest.mark.parametrize(
    "cmd",
    [
        QueryCommand("E002", "comercial", "creditos", "q"),
        QueryCommand("E001", "analista_riesgos", "creditos", "q"),
        QueryCommand("E001", "comercial", "riesgos", "q"),
    ],
)
def test_identity_mismatch_is_forbidden(cmd):
    with pytest.raises(ForbiddenError):
        check_identity(Principal("E001"), perms, cmd)


def test_identity_ok():
    check_identity(Principal("E001"), perms, QueryCommand("E001", "comercial", "creditos", "q"))


def test_filters_come_from_permissions():
    assert build_search_filters(perms, "creditos") == SearchFilters("creditos", "interno")
    with pytest.raises(ForbiddenError):
        build_search_filters(perms, "riesgos")


def test_scope_check():
    f = SearchFilters("creditos", "interno")
    make = lambda area, cls: Document("d", "t", area, cls, "s", "x")
    assert is_within_scope(make("creditos", "publico"), f)
    assert is_within_scope(make("creditos", "interno"), f)
    assert not is_within_scope(make("creditos", "confidencial"), f)
    assert not is_within_scope(make("riesgos", "publico"), f)


def test_allowlist():
    al = ToolAllowlist()
    assert al.allows("comercial", "mcp_search_documents")
    assert not al.allows("comercial", "get_employee_permissions")
    assert not al.allows("rol_desconocido", "mcp_search_documents")
