from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: str = "auto"
    messages: list[ChatMessage]
    temperature: float = 0.2
    stream: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class UsageInfo(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ChatChoice(BaseModel):
    index: int = 0
    message: ChatMessage
    finish_reason: str = "stop"


class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    model: str
    choices: list[ChatChoice]
    usage: UsageInfo
    route_reason: str
    cache_status: Literal["miss", "exact_hit", "semantic_hit"]
    estimated_cost: float
    latency_ms: float
    trace_id: str
    cache_confidence: Optional[float] = None


class ModelInfo(BaseModel):
    id: str
    object: str = "model"
    owned_by: str


class ModelsResponse(BaseModel):
    object: str = "list"
    data: list[ModelInfo]


class HealthResponse(BaseModel):
    status: str
    providers: dict[str, bool]


class RequestLogItem(BaseModel):
    id: int
    trace_id: str
    timestamp: str
    model_requested: str
    model_used: str
    route_reason: str
    cache_status: str
    prompt_tokens: int
    completion_tokens: int
    estimated_cost: float
    latency_ms: float
    feature: Optional[str]
    provider: str
    error: Optional[str]


class CostBreakdown(BaseModel):
    model: str
    feature: Optional[str]
    request_count: int
    total_cost: float
    total_tokens: int


class CostsResponse(BaseModel):
    daily_spend: float
    monthly_spend: float
    daily_budget: float
    monthly_budget: float
    breakdown: list[CostBreakdown]


class EvaluateRequest(BaseModel):
    limit: Optional[int] = None


class EvaluateResponse(BaseModel):
    status: str
    summary: dict[str, Any]
    report_path: str
