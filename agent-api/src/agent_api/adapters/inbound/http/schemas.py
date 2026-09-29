from pydantic import BaseModel, ConfigDict, Field

from agent_api.domain.query import Answer, QueryCommand

_ID = r"^[A-Za-z0-9_-]+$"


class QueryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    employee_id: str = Field(min_length=1, max_length=32, pattern=_ID, examples=["E001"])
    role: str = Field(min_length=1, max_length=64, pattern=_ID, examples=["comercial"])
    area: str = Field(min_length=1, max_length=64, pattern=_ID, examples=["creditos"])
    query: str = Field(min_length=1, max_length=1000, examples=["¿Cuál es la política de crédito?"])

    def to_command(self) -> QueryCommand:
        return QueryCommand(**self.model_dump())


class QueryResponse(BaseModel):
    answer: str
    citations: list[str] = Field(description="Ids de los documentos usados en la respuesta")

    @classmethod
    def from_answer(cls, answer: Answer) -> "QueryResponse":
        return cls(answer=answer.answer, citations=answer.citations)
