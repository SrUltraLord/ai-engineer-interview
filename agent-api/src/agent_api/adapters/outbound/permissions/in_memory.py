from agent_api.domain.errors import EmployeeNotFoundError
from agent_api.domain.permissions import EmployeePermissions

_DEFAULT = (
    EmployeePermissions("E001", "comercial", ["creditos"], "interno"),
    EmployeePermissions("E002", "analista_riesgos", ["riesgos"], "confidencial"),
    EmployeePermissions("E003", "tesorero", ["tesoreria"], "interno"),
    EmployeePermissions("E004", "practicante", ["creditos"], "publico"),
)


class InMemoryPermissionsRepository:
    """Almacén simulado. Sustituible por Entra ID / BD sin tocar el resto."""

    def __init__(self, employees: tuple[EmployeePermissions, ...] = _DEFAULT) -> None:
        self._by_id = {e.employee_id: e for e in employees}

    def get(self, employee_id: str) -> EmployeePermissions:
        try:
            return self._by_id[employee_id]
        except KeyError:
            raise EmployeeNotFoundError(employee_id) from None
