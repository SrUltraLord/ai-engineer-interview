import time

import jwt

from agent_api.domain.auth import Principal
from agent_api.domain.errors import UnauthorizedError

_INVALID = "Credenciales inválidas o ausentes"


class JwtAuthenticator:
    """JWT HS256 simulado para local. En Azure se sustituye por un adaptador de Entra ID (JWKS/RS256)."""

    def __init__(self, secret: str, issuer: str | None = None, audience: str | None = None) -> None:
        self._secret = secret
        self._issuer = issuer
        self._audience = audience

    def authenticate(self, token: str | None) -> Principal:
        if not token:
            raise UnauthorizedError(_INVALID)
        try:
            claims = jwt.decode(
                token,
                self._secret,
                algorithms=["HS256"],  # lista fija: evita `alg: none` y confusión de algoritmos
                issuer=self._issuer,
                audience=self._audience,
                options={"require": ["exp", "sub"]},
            )
        except jwt.PyJWTError:
            raise UnauthorizedError(_INVALID) from None
        subject = claims["sub"]
        if not isinstance(subject, str) or not subject:
            raise UnauthorizedError(_INVALID)
        return Principal(employee_id=subject)

    def issue(self, employee_id: str, ttl_seconds: int = 3600) -> str:
        """Solo para desarrollo y tests."""
        claims: dict = {"sub": employee_id, "exp": int(time.time()) + ttl_seconds}
        if self._issuer:
            claims["iss"] = self._issuer
        if self._audience:
            claims["aud"] = self._audience
        return jwt.encode(claims, self._secret, algorithm="HS256")
