from dataclasses import dataclass, field


@dataclass(frozen=True)
class QueryCommand:
    employee_id: str
    role: str
    area: str
    query: str


@dataclass(frozen=True)
class Answer:
    answer: str
    citations: list[str] = field(default_factory=list)
