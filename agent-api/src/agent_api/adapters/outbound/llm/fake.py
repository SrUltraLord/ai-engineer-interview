import re
from collections.abc import Sequence

from agent_api.domain.chat import ChatMessage, LLMResponse, ToolCall, ToolSpec
from agent_api.domain.tools import MCP_SEARCH_TOOL


class FakeLLM:
    """LLM determinista para desarrollo local y tests. No obedece contenido de documentos.

    Con tools disponibles: primero busca con la consulta del usuario; luego responde citando
    los documentos recibidos. Con `script` responde en orden con las respuestas dadas.
    """

    def __init__(self, script: Sequence[LLMResponse] | None = None) -> None:
        self._script = list(script) if script is not None else None
        self.calls: list[tuple[Sequence[ChatMessage], Sequence[ToolSpec]]] = []

    async def generate(self, messages: Sequence[ChatMessage], tools: Sequence[ToolSpec] = ()) -> LLMResponse:
        self.calls.append((messages, tools))
        if self._script is not None:
            return self._script.pop(0) if self._script else LLMResponse("fin")
        tool_messages = [m for m in messages if m.role == "tool"]
        if not tool_messages and any(t.name == MCP_SEARCH_TOOL for t in tools):
            query = next(m.content for m in reversed(messages) if m.role == "user")
            return LLMResponse(tool_calls=(ToolCall("call_1", MCP_SEARCH_TOOL, {"query": query}),))
        ids = re.findall(r'<documento id="([^"]+)"', tool_messages[-1].content) if tool_messages else []
        if not ids:
            return LLMResponse("No encontré documentos relevantes para tu consulta.")
        return LLMResponse("Respuesta simulada basada en: " + " ".join(f"[{i}]" for i in ids))
