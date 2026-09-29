import pytest

from agent_api.permissions import EmployeeNotFoundError, get_employee_permissions, get_permissions


def test_known_employee():
    assert get_employee_permissions.invoke({"employee_id": "E001"}) == {
        "employee_id": "E001",
        "role": "comercial",
        "areas": ["creditos"],
        "max_classification": "interno",
    }


def test_unknown_employee_is_controlled_error_without_access():
    result = get_employee_permissions.invoke({"employee_id": "E999"})
    assert result == {"error": "employee_not_found", "areas": [], "max_classification": None}


def test_get_permissions_raises_for_unknown():
    with pytest.raises(EmployeeNotFoundError):
        get_permissions("E999")


def test_is_local_langchain_tool():
    assert get_employee_permissions.name == "get_employee_permissions"
    assert set(get_employee_permissions.args) == {"employee_id"}
