from app.config import get_settings
from app.providers.anthropic_provider import AnthropicProvider
from app.providers.base import BaseProvider
from app.providers.mock_provider import MockLargeProvider, MockSmallProvider
from app.providers.ollama_provider import OllamaProvider
from app.providers.openai_provider import OpenAIProvider


class ProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, BaseProvider] = {}
        self.settings = get_settings()
        self._register_defaults()

    def _register_defaults(self) -> None:
        for provider in [MockSmallProvider(), MockLargeProvider()]:
            self._providers[provider.model_id] = provider

    async def initialize_optional(self) -> None:
        optional = []
        if self.settings.ollama_base_url:
            optional.append(OllamaProvider())
        optional.extend([OpenAIProvider(), AnthropicProvider()])
        for provider in optional:
            if await provider.health_check():
                self._providers[provider.model_id] = provider

    def get(self, model_id: str) -> BaseProvider | None:
        return self._providers.get(model_id)

    def list_models(self) -> list[str]:
        return sorted(self._providers.keys())

    async def health_status(self) -> dict[str, bool]:
        status = {}
        for model_id, provider in self._providers.items():
            status[model_id] = await provider.health_check()
        return status

    def all_providers(self) -> dict[str, BaseProvider]:
        return dict(self._providers)

    def fallback_chain(self, primary: str) -> list[str]:
        chain = [primary]
        if primary != "mock-large":
            chain.append("mock-large")
        if primary != "mock-small":
            chain.append("mock-small")
        return chain
