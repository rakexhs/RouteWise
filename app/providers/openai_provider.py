import httpx

from app.config import get_settings
from app.providers.base import BaseProvider, ProviderResult


class OpenAIProvider(BaseProvider):
    name = "openai"
    model_id = "openai"

    def __init__(self) -> None:
        self.settings = get_settings()
        self.api_key = self.settings.openai_api_key
        self.model = self.settings.openai_model

    async def complete(
        self, messages: list[dict[str, str]], temperature: float = 0.2
    ) -> ProviderResult:
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}
        async with httpx.AsyncClient(timeout=60.0, trust_env=False) as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                json=payload,
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()
        choice = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        return ProviderResult(
            content=choice,
            prompt_tokens=int(usage.get("prompt_tokens", 0)),
            completion_tokens=int(usage.get("completion_tokens", 0)),
            model=self.model_id,
            raw=data,
        )

    async def health_check(self) -> bool:
        return bool(self.api_key)

    def estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        return (prompt_tokens / 1000) * 0.00015 + (completion_tokens / 1000) * 0.0006

    def input_price_per_1k(self) -> float:
        return 0.00015

    def output_price_per_1k(self) -> float:
        return 0.0006
