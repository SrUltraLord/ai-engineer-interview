from collections.abc import Sequence
from typing import Protocol

from agent_api.domain.chat import ChatMessage, LLMResponse, ToolSpec


class LLMPort(Protocol):
    """Modelo de lenguaje. Cambiar de proveedor = escribir otro adaptador de este puerto."""

    async def generate(
        self, messages: Sequence[ChatMessage], tools: Sequence[ToolSpec] = ()
    ) -> LLMResponse: ...
