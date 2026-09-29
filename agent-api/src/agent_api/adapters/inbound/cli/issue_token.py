"""Emite un JWT de desarrollo: python -m agent_api.adapters.inbound.cli.issue_token E001"""

import sys

from dotenv import find_dotenv, load_dotenv

from agent_api.adapters.outbound.auth.jwt_auth import JwtAuthenticator
from agent_api.config import Settings


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("Uso: python -m agent_api.adapters.inbound.cli.issue_token <employee_id>")
    load_dotenv(find_dotenv(usecwd=True))
    settings = Settings.from_env()
    if not settings.jwt_secret:
        sys.exit("Falta JWT_SECRET (ver .env.example)")
    auth = JwtAuthenticator(settings.jwt_secret, settings.jwt_issuer, settings.jwt_audience)
    print(auth.issue(sys.argv[1]))


if __name__ == "__main__":
    main()
