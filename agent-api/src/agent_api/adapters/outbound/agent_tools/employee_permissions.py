from dataclasses import asdict

from langchain_core.tools import BaseTool, tool

from agent_api.application.ports.permissions import PermissionsRepository
from agent_api.domain.errors import EmployeeNotFoundError


def build_get_employee_permissions_tool(repo: PermissionsRepository) -> BaseTool:
    """Tool local del agente (no pasa por MCP) respaldada por el puerto de permisos."""

    @tool
    def get_employee_permissions(employee_id: str) -> dict:
        """Devuelve rol, áreas y nivel máximo de clasificación del empleado.

        Si el empleado no existe devuelve {"error": "employee_not_found"} y ningún acceso.
        """
        try:
            return asdict(repo.get(employee_id))
        except EmployeeNotFoundError:
            return {"error": "employee_not_found", "areas": [], "max_classification": None}

    return get_employee_permissions
