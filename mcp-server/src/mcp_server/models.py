from typing import Literal

from pydantic import BaseModel

Classification = Literal["publico", "interno", "confidencial"]

# Orden de menor a mayor sensibilidad; un filtro de clasificación es el nivel máximo permitido.
CLASSIFICATION_LEVELS: dict[str, int] = {"publico": 0, "interno": 1, "confidencial": 2}


class Document(BaseModel):
    id: str
    title: str
    area: str
    classification: Classification
    source: str
    text: str

# Catálogo de áreas válidas para `area_filter`.
AREAS: tuple[str, ...] = ("creditos", "riesgos", "tesoreria")
