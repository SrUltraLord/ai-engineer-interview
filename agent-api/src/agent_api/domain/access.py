from dataclasses import dataclass

from agent_api.domain.auth import Principal
from agent_api.domain.documents import Document
from agent_api.domain.errors import ForbiddenError
from agent_api.domain.permissions import CLASSIFICATION_LEVELS, Classification, EmployeePermissions
from agent_api.domain.query import QueryCommand


@dataclass(frozen=True)
class SearchFilters:
    area: str
    classification: Classification  # nivel máximo permitido (inclusive)


def check_identity(principal: Principal, permissions: EmployeePermissions, command: QueryCommand) -> None:
    """El body no puede declarar una identidad distinta de la autenticada. Lanza ForbiddenError."""
    if (
        command.employee_id != principal.employee_id
        or command.role != permissions.role
        or command.area not in permissions.areas
    ):
        raise ForbiddenError("Los datos declarados no coinciden con el usuario autenticado")


def build_search_filters(permissions: EmployeePermissions, area: str) -> SearchFilters:
    """Los filtros salen de los permisos, nunca del LLM."""
    if area not in permissions.areas:
        raise ForbiddenError("Área no permitida para el empleado")
    return SearchFilters(area=area, classification=permissions.max_classification)


def is_within_scope(document: Document, filters: SearchFilters) -> bool:
    return (
        document.area == filters.area
        and CLASSIFICATION_LEVELS[document.classification] <= CLASSIFICATION_LEVELS[filters.classification]
    )
