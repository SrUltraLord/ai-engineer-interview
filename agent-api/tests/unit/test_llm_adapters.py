import pytest
from langchain_core.language_models.fake_chat_models import FakeListChatModel, GenericFakeChatModel
from langchain_core.messages import AIMessage, ToolMessage

from agent_api.adapters.outbound.llm.langchain_chat import LangChainChatLLM
from agent_api.bootstrap import build_llm
from agent_api.config import Settings
from agent_api.domain.chat import ChatMessage, ToolCall, ToolSpec


async def test_langchain_adapter_generates_text():
    llm = LangChainChatLLM(FakeListChatModel(responses=["hola"]))
    response = await llm.generate([ChatMessage("system", "s"), ChatMessage("user", "u")])
    assert response.content == "hola" and response.tool_calls == ()


class ToolCallingFake(GenericFakeChatModel):
    seen: list = []

    def bind_tools(self, tools, **kwargs):
        self.seen.append(tools)
        return self


async def test_langchain_adapter_maps_tool_calls_and_tool_messages():
    ai = AIMessage(content="", tool_calls=[{"id": "c1", "name": "mcp_search_documents", "args": {"query": "q"}}])
    model = ToolCallingFake(messages=iter([ai]))
    llm = LangChainChatLLM(model)
    spec = ToolSpec("mcp_search_documents", "busca", {"type": "object", "properties": {}})
    response = await llm.generate([ChatMessage("user", "u")], [spec])
    assert response.tool_calls == (ToolCall("c1", "mcp_search_documents", {"query": "q"}),)
    assert model.seen[0][0]["function"]["name"] == "mcp_search_documents"


def test_message_conversion_of_tool_roundtrip():
    from agent_api.adapters.outbound.llm.langchain_chat import _to_langchain

    m = _to_langchain(ChatMessage("tool", "datos", tool_call_id="c1"))
    assert isinstance(m, ToolMessage) and m.tool_call_id == "c1"
    a = _to_langchain(ChatMessage("assistant", "", (ToolCall("c1", "t", {"a": 1}),)))
    assert a.tool_calls[0]["args"] == {"a": 1}


def test_default_provider_is_fake():
    assert build_llm(Settings()).__class__.__name__ == "FakeLLM"


def test_azure_requires_configuration():
    with pytest.raises(ValueError, match="AZURE_OPENAI_ENDPOINT"):
        build_llm(Settings(llm_provider="azure_openai"))


def test_azure_builds_with_configuration():
    llm = build_llm(
        Settings(
            llm_provider="azure_openai",
            azure_openai_endpoint="https://x.openai.azure.com",
            azure_openai_deployment="gpt",
            azure_openai_api_key="k",
        )
    )
    assert isinstance(llm, LangChainChatLLM)


def test_invalid_settings(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "otro")
    with pytest.raises(ValueError, match="LLM_PROVIDER"):
        Settings.from_env()
    monkeypatch.setenv("LLM_PROVIDER", "fake")
    monkeypatch.setenv("MCP_CLIENT_TRANSPORT", "carrier-pigeon")
    with pytest.raises(ValueError, match="MCP_CLIENT_TRANSPORT"):
        Settings.from_env()


def test_allowlist_env_parsing(monkeypatch):
    monkeypatch.setenv("TOOL_ALLOWLIST", '{"comercial": ["mcp_search_documents"]}')
    assert Settings.from_env().tool_allowlist == {"comercial": frozenset({"mcp_search_documents"})}
    monkeypatch.setenv("TOOL_ALLOWLIST", "no-json")
    with pytest.raises(ValueError, match="TOOL_ALLOWLIST"):
        Settings.from_env()
