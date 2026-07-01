import asyncio
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any


@dataclass
class ProviderResult:
    content: str
    prompt_tokens: int
    completion_tokens: int
    model: str
    raw: dict[str, Any] | None = None


class BaseProvider(ABC):
    name: str
    model_id: str

    @abstractmethod
    async def complete(
        self, messages: list[dict[str, str]], temperature: float = 0.2
    ) -> ProviderResult:
        ...

    async def stream(
        self, messages: list[dict[str, str]], temperature: float = 0.2
    ) -> AsyncIterator[str]:
        """Yield content deltas for a completion.

        Providers with native streaming APIs override this; the default runs a
        regular completion and re-chunks it so every provider can serve the
        streaming endpoint.
        """
        result = await self.complete(messages, temperature)
        text = result.content
        step = 24
        for i in range(0, len(text), step):
            yield text[i : i + step]
            await asyncio.sleep(0)

    @abstractmethod
    async def health_check(self) -> bool:
        ...

    @abstractmethod
    def estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        ...

    def input_price_per_1k(self) -> float:
        return 0.0001

    def output_price_per_1k(self) -> float:
        return 0.0002
