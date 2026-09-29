from collections.abc import Sequence

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage

from agent_api.domain.chat import ChatMessage, LLMResponse, ToolCall, ToolSpec


def _to_langchain(m: ChatMessage) -> BaseMessage:
    if m.role == "system":
        return SystemMessage(content=m.content)
    if m.role == "user":
        return HumanMessage(content=m.content)
    if m.role == "tool":
        return ToolMessage(content=m.content, tool_call_id=m.tool_call_id or "")
    return AIMessage(
        content=m.content,
        tool_calls=[{"id": c.id, "name": c.name, "args": c.arguments} for c in m.tool_calls],
    )


class LangChainChatLLM:
    """Adapta cualquier BaseChatModel de LangChain (Azure OpenAI, Anthropic, Ollama...) a LLMPort."""

    def __init__(self, model: BaseChatModel) -> None:
        self._model = model

    async def generate(self, messages: Sequence[ChatMessage], tools: Sequence[ToolSpec] = ()) -> LLMResponse:
        model = self._model
        if tools:
            model = model.bind_tools(
                [
                    {"type": "function", "function": {"name": t.name, "description": t.description, "parameters": t.parameters}}
                    for t in tools
                ]
            )
        result = await model.ainvoke([_to_langchain(m) for m in messages])
        calls = tuple(
            ToolCall(id=c.get("id") or f"call_{i}", name=c["name"], arguments=c.get("args") or {})
            for i, c in enumerate(getattr(result, "tool_calls", None) or [])
        )
        return LLMResponse(content=result.text, tool_calls=calls)
