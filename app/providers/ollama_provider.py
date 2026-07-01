import json
from collections.abc import AsyncIterator

import httpx

from app.config import get_settings
from app.providers.base import BaseProvider, ProviderResult


class OllamaProvider(BaseProvider):
    name = "ollama"
    model_id = "ollama"

    def __init__(self) -> None:
        self.settings = get_settings()
        if not self.settings.ollama_base_url:
            self.base_url = ""
        else:
            self.base_url = self.settings.ollama_base_url.rstrip("/")
        self.model = self.settings.ollama_model

    async def complete(
        self, messages: list[dict[str, str]], temperature: float = 0.2
    ) -> ProviderResult:
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature},
        }
        async with httpx.AsyncClient(timeout=60.0, trust_env=False) as client:
            resp = await client.post(f"{self.base_url}/api/chat", json=payload)
            resp.raise_for_status()
            data = resp.json()
        content = data.get("message", {}).get("content", "")
        prompt_tokens = data.get("prompt_eval_count", max(1, len(str(messages)) // 4))
        completion_tokens = data.get("eval_count", max(1, len(content.split())))
        return ProviderResult(
            content=content,
            prompt_tokens=int(prompt_tokens),
            completion_tokens=int(completion_tokens),
            model=self.model_id,
            raw=data,
        )

    async def stream(
        self, messages: list[dict[str, str]], temperature: float = 0.2
    ) -> AsyncIterator[str]:
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "options": {"temperature": temperature},
        }
        async with httpx.AsyncClient(timeout=120.0, trust_env=False) as client:
            async with client.stream(
                "POST", f"{self.base_url}/api/chat", json=payload
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.strip():
                        continue
                    data = json.loads(line)
                    if data.get("done"):
                        break
                    delta = data.get("message", {}).get("content", "")
                    if delta:
                        yield delta

    async def health_check(self) -> bool:
        if not self.base_url:
            return False
        try:
            async with httpx.AsyncClient(timeout=3.0, trust_env=False) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                return resp.status_code == 200
        except Exception:
            return False

    def estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        return 0.0
