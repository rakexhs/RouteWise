import httpx

from app.config import get_settings
from app.providers.base import BaseProvider, ProviderResult


class AnthropicProvider(BaseProvider):
    name = "anthropic"
    model_id = "anthropic"

    def __init__(self) -> None:
        self.settings = get_settings()
        self.api_key = self.settings.anthropic_api_key
        self.model = self.settings.anthropic_model

    async def complete(
        self, messages: list[dict[str, str]], temperature: float = 0.2
    ) -> ProviderResult:
        system_parts = [m["content"] for m in messages if m["role"] == "system"]
        user_messages = [m for m in messages if m["role"] != "system"]
        payload: dict = {
            "model": self.model,
            "max_tokens": 1024,
            "temperature": temperature,
            "messages": user_messages,
        }
        if system_parts:
            payload["system"] = "\n".join(system_parts)
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        async with httpx.AsyncClient(timeout=60.0, trust_env=False) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                json=payload,
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()
        content = "".join(
            block.get("text", "") for block in data.get("content", []) if block.get("type") == "text"
        )
        usage = data.get("usage", {})
        return ProviderResult(
            content=content,
            prompt_tokens=int(usage.get("input_tokens", 0)),
            completion_tokens=int(usage.get("output_tokens", 0)),
            model=self.model_id,
            raw=data,
        )

    async def health_check(self) -> bool:
        return bool(self.api_key)

    def estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        return (prompt_tokens / 1000) * 0.00025 + (completion_tokens / 1000) * 0.00125

    def input_price_per_1k(self) -> float:
        return 0.00025

    def output_price_per_1k(self) -> float:
        return 0.00125
