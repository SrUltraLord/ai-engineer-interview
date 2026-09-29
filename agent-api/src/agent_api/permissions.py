from typing import Literal

from langchain_core.tools import tool
from pydantic import BaseModel

Classification = Literal["publico", "interno", "confidencial"]

# Orden de menor a mayor sensibilidad; mismo catálogo que el servidor MCP.
CLASSIFICATION_LEVELS: dict[str, int] = {"publico": 0, "interno": 1, "confidencial": 2}


class EmployeePermissions(BaseModel):
    employee_id: str
    role: str
    areas: list[str]
    max_classification: Classification


class EmployeeNotFoundError(Exception):
    """El empleado no existe en el almacén de permisos."""


# Almacén simulado. Sustituible por un directorio real (Entra ID / BD) sin cambiar la interfaz.
_EMPLOYEES: dict[str, EmployeePermissions] = {
    p.employee_id: p
    for p in (
        EmployeePermissions(
            employee_id="E001", role="comercial", areas=["creditos"], max_classification="interno"
        ),
        EmployeePermissions(
            employee_id="E002", role="analista_riesgos", areas=["riesgos"], max_classification="confidencial"
        ),
        EmployeePermissions(
            employee_id="E003", role="tesorero", areas=["tesoreria"], max_classification="interno"
        ),
        EmployeePermissions(
            employee_id="E004", role="practicante", areas=["creditos"], max_classification="publico"
        ),
    )
}


def get_permissions(employee_id: str) -> EmployeePermissions:
    """Uso interno del código (RBAC, auth). Lanza EmployeeNotFoundError si no existe."""
    try:
        return _EMPLOYEES[employee_id]
    except KeyError:
        raise EmployeeNotFoundError(employee_id) from None


@tool
def get_employee_permissions(employee_id: str) -> dict:
    """Devuelve rol, áreas y nivel máximo de clasificación del empleado.

    Si el empleado no existe devuelve {"error": "employee_not_found"} y ningún acceso.
    """
    try:
        return get_permissions(employee_id).model_dump()
    except EmployeeNotFoundError:
        return {"error": "employee_not_found", "areas": [], "max_classification": None}
