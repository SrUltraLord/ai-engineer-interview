from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class ToolSpec:
    """Descripción de una tool para el modelo, independiente del proveedor (JSON Schema)."""

    name: str
    description: str
    parameters: dict[str, Any]


@dataclass(frozen=True)
class ChatMessage:
    """Mensaje independiente del proveedor de LLM."""

    role: Literal["system", "user", "assistant", "tool"]
    content: str = ""
    tool_calls: tuple[ToolCall, ...] = field(default_factory=tuple)  # solo role="assistant"
    tool_call_id: str | None = None  # solo role="tool"


@dataclass(frozen=True)
class LLMResponse:
    content: str = ""
    tool_calls: tuple[ToolCall, ...] = field(default_factory=tuple)
