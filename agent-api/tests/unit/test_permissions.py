import pytest

from agent_api.adapters.outbound.agent_tools.employee_permissions import build_get_employee_permissions_tool
from agent_api.adapters.outbound.permissions.in_memory import InMemoryPermissionsRepository
from agent_api.domain.errors import EmployeeNotFoundError

repo = InMemoryPermissionsRepository()
tool = build_get_employee_permissions_tool(repo)


def test_known_employee():
    assert tool.invoke({"employee_id": "E001"}) == {
        "employee_id": "E001",
        "role": "comercial",
        "areas": ["creditos"],
        "max_classification": "interno",
    }


def test_unknown_employee_is_controlled_error_without_access():
    assert tool.invoke({"employee_id": "E999"}) == {
        "error": "employee_not_found",
        "areas": [],
        "max_classification": None,
    }


def test_repository_raises_for_unknown():
    with pytest.raises(EmployeeNotFoundError):
        repo.get("E999")


def test_is_local_langchain_tool():
    assert tool.name == "get_employee_permissions"
    assert set(tool.args) == {"employee_id"}
