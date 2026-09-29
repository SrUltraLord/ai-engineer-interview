from dataclasses import dataclass


@dataclass(frozen=True)
class Principal:
    """Identidad autenticada. Rol y área efectivos se derivan de los permisos, no del cliente."""

    employee_id: str
