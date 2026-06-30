import asyncio
import random

from app.config import get_settings
from app.providers.base import BaseProvider, ProviderResult


class MockSmallProvider(BaseProvider):
    name = "mock-small"
    model_id = "mock-small"

    def __init__(self) -> None:
        self.settings = get_settings()

    async def complete(
        self, messages: list[dict[str, str]], temperature: float = 0.2
    ) -> ProviderResult:
        if random.random() < self.settings.mock_failure_rate:
            raise RuntimeError("Simulated mock-small failure")
        await asyncio.sleep(0.05)
        user_text = messages[-1]["content"] if messages else ""
        content = f"[mock-small] Quick answer: {user_text[:120]}"
        prompt_tokens = max(1, len(user_text.split()) // 2)
        completion_tokens = max(5, len(content.split()))
        return ProviderResult(
            content=content,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            model=self.model_id,
        )

    async def health_check(self) -> bool:
        return True

    def estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        return (prompt_tokens / 1000) * 0.00005 + (completion_tokens / 1000) * 0.0001

    def input_price_per_1k(self) -> float:
        return 0.00005

    def output_price_per_1k(self) -> float:
        return 0.0001


class MockLargeProvider(BaseProvider):
    name = "mock-large"
    model_id = "mock-large"

    def __init__(self) -> None:
        self.settings = get_settings()

    async def complete(
        self, messages: list[dict[str, str]], temperature: float = 0.2
    ) -> ProviderResult:
        if random.random() < self.settings.mock_failure_rate:
            raise RuntimeError("Simulated mock-large failure")
        await asyncio.sleep(0.2)
        user_text = messages[-1]["content"] if messages else ""
        content = (
            f"[mock-large] Detailed response:\n"
            f"1. Context: {user_text[:200]}\n"
            f"2. Analysis: This prompt requires deeper reasoning.\n"
            f"3. Conclusion: Structured answer with higher fidelity."
        )
        prompt_tokens = max(1, len(user_text.split()))
        completion_tokens = max(20, len(content.split()))
        return ProviderResult(
            content=content,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            model=self.model_id,
        )

    async def health_check(self) -> bool:
        return True

    def estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        return (prompt_tokens / 1000) * 0.0002 + (completion_tokens / 1000) * 0.0004

    def input_price_per_1k(self) -> float:
        return 0.0002

    def output_price_per_1k(self) -> float:
        return 0.0004
