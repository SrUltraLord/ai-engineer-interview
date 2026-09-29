from typing import Protocol

from agent_api.domain.permissions import EmployeePermissions


class PermissionsRepository(Protocol):
    def get(self, employee_id: str) -> EmployeePermissions:
        """Lanza EmployeeNotFoundError si el empleado no existe."""
        ...
