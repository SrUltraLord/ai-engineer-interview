from dataclasses import dataclass
from typing import Literal

Classification = Literal["publico", "interno", "confidencial"]

# Orden de menor a mayor sensibilidad; mismo catálogo que el servidor MCP.
CLASSIFICATION_LEVELS: dict[str, int] = {"publico": 0, "interno": 1, "confidencial": 2}


@dataclass(frozen=True)
class EmployeePermissions:
    employee_id: str
    role: str
    areas: list[str]
    max_classification: Classification
