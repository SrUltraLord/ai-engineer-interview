from agent_api.adapters.outbound.llm.langchain_chat import LangChainChatLLM
from agent_api.config import Settings


def build_azure_openai_llm(settings: Settings) -> LangChainChatLLM:
    # Import diferido: langchain-openai solo se exige si se usa este proveedor.
    from langchain_openai import AzureChatOpenAI

    missing = [
        name
        for name, value in (
            ("AZURE_OPENAI_ENDPOINT", settings.azure_openai_endpoint),
            ("AZURE_OPENAI_DEPLOYMENT", settings.azure_openai_deployment),
            ("AZURE_OPENAI_API_KEY", settings.azure_openai_api_key),
        )
        if not value
    ]
    if missing:
        raise ValueError(f"Faltan variables de entorno: {', '.join(missing)}")

    return LangChainChatLLM(
        AzureChatOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            azure_deployment=settings.azure_openai_deployment,
            api_version=settings.azure_openai_api_version,
            api_key=settings.azure_openai_api_key,
            temperature=0,
        )
    )
