from app.providers.base import BaseProvider


def estimate_cost(
    provider: BaseProvider,
    prompt_tokens: int,
    completion_tokens: int,
) -> float:
    return provider.estimate_cost(prompt_tokens, completion_tokens)


PRICE_TABLE = {
    "mock-small": {"input": 0.00005, "output": 0.0001},
    "mock-large": {"input": 0.0002, "output": 0.0004},
    "ollama": {"input": 0.0, "output": 0.0},
    "openai": {"input": 0.00015, "output": 0.0006},
    "anthropic": {"input": 0.00025, "output": 0.00125},
}


def cost_from_table(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    prices = PRICE_TABLE.get(model, PRICE_TABLE["mock-small"])
    return (prompt_tokens / 1000) * prices["input"] + (completion_tokens / 1000) * prices["output"]
