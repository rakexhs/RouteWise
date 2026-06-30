from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "RouteWise"
    demo_api_key: str = "demo-key-change-me"
    database_url: str = "sqlite:///./data/routewise.db"

    rate_limit_per_minute: int = 60
    daily_budget_usd: float = 10.0
    monthly_budget_usd: float = 100.0
    budget_exceeded_action: Literal["downgrade", "reject"] = "downgrade"

    semantic_cache_enabled: bool = True
    semantic_similarity_threshold: float = 0.92
    exact_cache_ttl_seconds: int = 3600

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-3-5-haiku-20241022"
    mock_failure_rate: float = 0.0

    redis_url: str = ""

    host: str = "0.0.0.0"
    port: int = 8000

    circuit_failure_threshold: int = 3
    circuit_cooldown_seconds: float = 30.0
    retry_max_attempts: int = 3
    retry_base_delay: float = 0.5


@lru_cache
def get_settings() -> Settings:
    return Settings()
