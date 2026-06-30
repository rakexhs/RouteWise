from abc import ABC, abstractmethod
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
