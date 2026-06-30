from prometheus_client import Counter, Gauge, Histogram

REQUESTS_TOTAL = Counter(
    "routewise_requests_total",
    "Total chat completion requests",
    ["model", "provider", "cache_status"],
)

REQUEST_LATENCY = Histogram(
    "routewise_request_latency_seconds",
    "Request latency in seconds",
    ["model", "provider"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

TOKENS_TOTAL = Counter(
    "routewise_tokens_total",
    "Total tokens processed",
    ["direction", "model"],
)

ESTIMATED_COST = Counter(
    "routewise_estimated_cost_usd_total",
    "Estimated cost in USD",
    ["model", "provider"],
)

CACHE_HITS = Counter(
    "routewise_cache_hits_total",
    "Cache hits by type",
    ["type"],
)

FALLBACKS = Counter(
    "routewise_fallbacks_total",
    "Provider fallback events",
    ["from_provider", "to_provider"],
)

CIRCUIT_BREAKER_STATE = Gauge(
    "routewise_circuit_breaker_state",
    "Circuit breaker state (0=closed, 1=half_open, 2=open)",
    ["provider"],
)

BUDGET_REMAINING = Gauge(
    "routewise_budget_remaining_usd",
    "Remaining daily budget in USD",
)


def record_request(
    *,
    model: str,
    provider: str,
    cache_status: str,
    latency_seconds: float,
    prompt_tokens: int,
    completion_tokens: int,
    estimated_cost: float,
) -> None:
    REQUESTS_TOTAL.labels(model=model, provider=provider, cache_status=cache_status).inc()
    REQUEST_LATENCY.labels(model=model, provider=provider).observe(latency_seconds)
    TOKENS_TOTAL.labels(direction="prompt", model=model).inc(prompt_tokens)
    TOKENS_TOTAL.labels(direction="completion", model=model).inc(completion_tokens)
    ESTIMATED_COST.labels(model=model, provider=provider).inc(estimated_cost)
    if cache_status in ("exact_hit", "semantic_hit"):
        CACHE_HITS.labels(type=cache_status.replace("_hit", "")).inc()


def record_fallback(from_provider: str, to_provider: str) -> None:
    FALLBACKS.labels(from_provider=from_provider, to_provider=to_provider).inc()


def set_circuit_state(provider: str, state: str) -> None:
    mapping = {"closed": 0, "half_open": 1, "open": 2}
    CIRCUIT_BREAKER_STATE.labels(provider=provider).set(mapping.get(state, 0))


def set_budget_remaining(amount: float) -> None:
    BUDGET_REMAINING.set(amount)
