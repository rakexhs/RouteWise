import time
import uuid
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import PlainTextResponse
from prometheus_client import generate_latest
from sqlalchemy.orm import Session

from app.cache import CacheManager, combined_prompt_text
from app.config import get_settings
from app.evaluation.evaluator import run_evaluation
from app.gateway.auth import verify_api_key
from app.gateway.circuit_breaker import circuit_breaker
from app.gateway.cost import estimate_cost
from app.gateway.pii_redactor import redact_messages
from app.gateway.rate_limiter import rate_limiter
from app.gateway.router import (
    decide_route,
    execute_with_fallback,
    prompt_hash,
)
from app.providers import ProviderRegistry
from app.schemas import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatChoice,
    ChatMessage,
    CostsResponse,
    EvaluateRequest,
    EvaluateResponse,
    HealthResponse,
    ModelsResponse,
    ModelInfo,
    UsageInfo,
)
from app.storage.db import (
    get_cost_breakdown,
    get_daily_spend,
    get_db,
    get_monthly_spend,
    get_recent_requests,
    init_db,
    log_request,
)
from app.telemetry.logger import log_with_trace
from app.telemetry.metrics import record_request, set_budget_remaining
from app.telemetry.traces import new_trace_id

registry = ProviderRegistry()
cache_manager = CacheManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    await registry.initialize_optional()
    yield
    circuit_breaker.save_snapshot()


app = FastAPI(title="RouteWise Gateway", version="1.0.0", lifespan=lifespan)


@app.get("/health", response_model=HealthResponse)
async def health():
    providers = await registry.health_status()
    return HealthResponse(status="ok", providers=providers)


@app.get("/v1/models", response_model=ModelsResponse)
async def list_models(api_key: str = Depends(verify_api_key)):
    models = [
        ModelInfo(id=m, owned_by="routewise") for m in registry.list_models()
    ]
    models.append(ModelInfo(id="auto", owned_by="routewise"))
    return ModelsResponse(data=models)


@app.post("/v1/chat/completions", response_model=ChatCompletionResponse)
async def chat_completions(
    request: ChatCompletionRequest,
    api_key: str = Depends(verify_api_key),
    session: Session = Depends(get_db),
):
    if request.stream:
        raise HTTPException(status_code=400, detail="Streaming not supported in v1")

    rate_limiter.check(api_key)
    trace_id = new_trace_id()
    start = time.perf_counter()
    settings = get_settings()

    raw_messages = [{"role": m.role, "content": m.content} for m in request.messages]
    redacted_messages = redact_messages(raw_messages)
    prompt_text = combined_prompt_text(redacted_messages)
    cache_key = prompt_hash(redacted_messages, request.model)

    cache_result = cache_manager.lookup(prompt_text, cache_key)
    route_decision = decide_route(
        model=request.model,
        messages=redacted_messages,
        registry=registry,
        session=session,
    )

    feature = request.metadata.get("feature") if request.metadata else None
    error_msg = None
    cache_confidence = cache_result.confidence
    used_fallback = False

    if cache_result.hit and cache_result.value:
        result_data = cache_result.value
        model_used = result_data.get("model", route_decision.model_id)
        content = result_data["content"]
        prompt_tokens = int(result_data.get("prompt_tokens", 0))
        completion_tokens = int(result_data.get("completion_tokens", 0))
        route_reason = result_data.get("route_reason", route_decision.route_reason)
        cache_status = cache_result.cache_status
    else:
        cache_status = "miss"
        try:
            provider_result, model_used, route_reason, used_fallback = await execute_with_fallback(
                registry,
                route_decision.model_id,
                redacted_messages,
                request.temperature,
                circuit_breaker,
            )
            content = provider_result.content
            prompt_tokens = provider_result.prompt_tokens
            completion_tokens = provider_result.completion_tokens

            provider = registry.get(model_used)
            cache_manager.store(
                prompt_text,
                cache_key,
                {
                    "content": content,
                    "model": model_used,
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "route_reason": route_reason,
                },
                metadata={"model": model_used, "route_reason": route_reason},
            )
        except Exception as exc:
            error_msg = str(exc)
            log_with_trace(trace_id, "error", f"Request failed: {error_msg}")
            raise HTTPException(status_code=502, detail="All providers failed") from exc

    provider = registry.get(model_used)
    if not provider:
        provider = registry.get("mock-small")
    assert provider is not None

    cost = estimate_cost(provider, prompt_tokens, completion_tokens)
    latency_ms = (time.perf_counter() - start) * 1000

    response = ChatCompletionResponse(
        id=f"chatcmpl-{uuid.uuid4().hex[:12]}",
        model=model_used,
        choices=[
            ChatChoice(
                message=ChatMessage(role="assistant", content=content),
            )
        ],
        usage=UsageInfo(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
        ),
        route_reason=route_reason if not used_fallback else f"fallback:{route_reason}",
        cache_status=cache_status,
        estimated_cost=round(cost, 6),
        latency_ms=round(latency_ms, 2),
        trace_id=trace_id,
        cache_confidence=cache_confidence,
    )

    log_request(
        session,
        trace_id=trace_id,
        model_requested=request.model,
        model_used=model_used,
        route_reason=response.route_reason,
        cache_status=cache_status,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        estimated_cost=cost,
        latency_ms=latency_ms,
        feature=feature,
        provider=provider.name,
        redacted_prompt_hash=prompt_hash(redacted_messages),
        error=error_msg,
    )

    record_request(
        model=model_used,
        provider=provider.name,
        cache_status=cache_status,
        latency_seconds=latency_ms / 1000,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        estimated_cost=cost,
    )

    daily_remaining = settings.daily_budget_usd - get_daily_spend(session)
    set_budget_remaining(max(0.0, daily_remaining))

    log_with_trace(
        trace_id,
        "info",
        f"model={model_used} cache={cache_status} cost={cost:.6f} latency={latency_ms:.1f}ms",
    )

    return response


@app.get("/metrics")
async def metrics():
    return PlainTextResponse(
        generate_latest().decode("utf-8"),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )


@app.get("/admin/requests")
async def admin_requests(
    api_key: str = Depends(verify_api_key),
    session: Session = Depends(get_db),
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
):
    return get_recent_requests(session, limit=limit, offset=offset)


@app.get("/admin/costs", response_model=CostsResponse)
async def admin_costs(
    api_key: str = Depends(verify_api_key),
    session: Session = Depends(get_db),
):
    settings = get_settings()
    from datetime import datetime, timedelta

    breakdown = get_cost_breakdown(session, datetime.utcnow() - timedelta(days=30))
    return CostsResponse(
        daily_spend=round(get_daily_spend(session), 6),
        monthly_spend=round(get_monthly_spend(session), 6),
        daily_budget=settings.daily_budget_usd,
        monthly_budget=settings.monthly_budget_usd,
        breakdown=breakdown,
    )


@app.post("/admin/evaluate", response_model=EvaluateResponse)
async def admin_evaluate(
    body: EvaluateRequest = EvaluateRequest(),
    api_key: str = Depends(verify_api_key),
):
    summary, report_path = await run_evaluation(limit=body.limit)
    return EvaluateResponse(status="completed", summary=summary, report_path=report_path)
