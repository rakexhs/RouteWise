import hashlib
import re
from dataclasses import dataclass

from app.config import get_settings
from app.gateway.pii_redactor import detect_pii, redact_messages
from app.gateway.token_counter import count_messages_tokens
from app.providers import ProviderRegistry
from app.providers.base import BaseProvider, ProviderResult
from app.storage.db import get_daily_spend, get_monthly_spend
from sqlalchemy.orm import Session


@dataclass
class ComplexityScore:
    score: float
    token_count: int
    has_code: bool


@dataclass
class RouteDecision:
    model_id: str
    route_reason: str
    budget_downgrade: bool = False


def normalize_prompt(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"\s+", " ", text)
    return text


def prompt_hash(messages: list[dict[str, str]], model_scope: str = "auto") -> str:
    combined = model_scope + "|" + "|".join(
        f"{m['role']}:{normalize_prompt(m['content'])}" for m in messages
    )
    return hashlib.sha256(combined.encode()).hexdigest()


def estimate_complexity(messages: list[dict[str, str]]) -> ComplexityScore:
    text = " ".join(m["content"] for m in messages)
    tokens = count_messages_tokens(messages)
    has_code = "```" in text or "def " in text or "class " in text or "function" in text.lower()
    length_score = min(1.0, tokens / 500)
    code_score = 0.3 if has_code else 0.0
    question_score = 0.1 if "?" in text else 0.0
    score = min(1.0, length_score * 0.6 + code_score + question_score)
    return ComplexityScore(score=score, token_count=tokens, has_code=has_code)


def check_budget(session: Session) -> tuple[bool, str]:
    settings = get_settings()
    daily = get_daily_spend(session)
    monthly = get_monthly_spend(session)
    if daily >= settings.daily_budget_usd or monthly >= settings.monthly_budget_usd:
        return False, "budget_exceeded"
    return True, "ok"


def select_premium(registry: ProviderRegistry) -> str | None:
    for model in ("openai", "anthropic", "ollama", "mock-large"):
        if registry.get(model):
            return model
    return None


def decide_route(
    *,
    model: str,
    messages: list[dict[str, str]],
    registry: ProviderRegistry,
    session: Session,
) -> RouteDecision:
    settings = get_settings()
    within_budget, budget_status = check_budget(session)

    if not within_budget:
        if settings.budget_exceeded_action == "reject":
            from fastapi import HTTPException

            raise HTTPException(status_code=429, detail="Budget exceeded")
        return RouteDecision("mock-small", "budget_downgrade", budget_downgrade=True)

    if model != "auto":
        if registry.get(model):
            return RouteDecision(model, "explicit_model")
        return RouteDecision("mock-small", "unknown_model_fallback")

    redacted = redact_messages(messages)
    complexity = estimate_complexity(redacted)

    if complexity.score < 0.4:
        return RouteDecision("mock-small", "simple_prompt")

    premium = select_premium(registry)
    if complexity.score > 0.7 and premium:
        return RouteDecision(premium, "complex_prompt")

    return RouteDecision("mock-large", "moderate_prompt")


async def execute_with_fallback(
    registry: ProviderRegistry,
    primary_model: str,
    messages: list[dict[str, str]],
    temperature: float,
    circuit_breaker,
) -> tuple[ProviderResult, str, str, bool]:
    from app.gateway.circuit_breaker import CircuitBreaker
    from app.gateway.retry import with_retry
    from app.telemetry.metrics import record_fallback

    breaker: CircuitBreaker = circuit_breaker
    chain = registry.fallback_chain(primary_model)
    last_error: Exception | None = None
    used_fallback = False

    for i, model_id in enumerate(chain):
        provider = registry.get(model_id)
        if not provider:
            continue
        if not breaker.can_execute(model_id):
            continue

        async def _call(p: BaseProvider = provider) -> ProviderResult:
            return await p.complete(messages, temperature)

        try:
            result = await with_retry(_call)
            breaker.record_success(model_id)
            reason = primary_model if model_id == primary_model else f"fallback_from_{primary_model}"
            if i > 0:
                used_fallback = True
                record_fallback(primary_model, model_id)
            return result, model_id, reason, used_fallback
        except Exception as exc:
            last_error = exc
            breaker.record_failure(model_id)

    raise RuntimeError(str(last_error) if last_error else "All providers failed")
