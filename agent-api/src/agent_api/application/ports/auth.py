from typing import Protocol

from agent_api.domain.auth import Principal


class Authenticator(Protocol):
    def authenticate(self, token: str | None) -> Principal:
        """Lanza UnauthorizedError si el token falta o no es válido."""
        ...
