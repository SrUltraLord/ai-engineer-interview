from typing import Protocol

from mcp_server.config import Settings


class Embedder(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...


class AzureOpenAIEmbedder:
    def __init__(self, settings: Settings) -> None:
        from openai import AzureOpenAI

        self._client = AzureOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
        )
        self._deployment = settings.azure_openai_embedding_deployment

    def embed(self, texts: list[str]) -> list[list[float]]:
        response = self._client.embeddings.create(model=self._deployment, input=texts)
        return [item.embedding for item in response.data]
