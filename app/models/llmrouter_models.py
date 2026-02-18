"""
Multi-LLM Router & Orchestrator modelleri.

Yonlendirici, model, saglayici,
maliyet, gecikme, performans modelleri.
"""

from enum import Enum

from pydantic import BaseModel, Field


class ModelStatus(str, Enum):
    """Model durumu."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    DEPRECATED = "deprecated"
    MAINTENANCE = "maintenance"


class HealthState(str, Enum):
    """Saglik durumu."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class CircuitState(str, Enum):
    """Devre durumu."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class SelectionStrategy(str, Enum):
    """Secim stratejisi."""

    BEST_QUALITY = "best_quality"
    LOWEST_COST = "lowest_cost"
    BALANCED = "balanced"
    FASTEST = "fastest"
    CAPABILITY_MATCH = "capability_match"


class ComplexityLevel(str, Enum):
    """Karmasiklik seviyesi."""

    TRIVIAL = "trivial"
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    EXPERT = "expert"


class ReasoningDepth(str, Enum):
    """Muhakeme derinligi."""

    SHALLOW = "shallow"
    MODERATE = "moderate"
    DEEP = "deep"


class CacheStrategy(str, Enum):
    """Onbellek stratejisi."""

    EXACT_MATCH = "exact_match"
    SEMANTIC_SIMILARITY = (
        "semantic_similarity"
    )
    PREFIX_MATCH = "prefix_match"
    TEMPLATE_MATCH = "template_match"


class ModelCapability(str, Enum):
    """Model yetenegi."""

    TEXT_GENERATION = "text_generation"
    CODE_GENERATION = "code_generation"
    REASONING = "reasoning"
    SUMMARIZATION = "summarization"
    TRANSLATION = "translation"
    CLASSIFICATION = "classification"
    EMBEDDING = "embedding"
    VISION = "vision"
    FUNCTION_CALLING = "function_calling"
    STRUCTURED_OUTPUT = (
        "structured_output"
    )


class ProviderRecord(BaseModel):
    """Saglayici kaydi."""

    provider_id: str = ""
    name: str = ""
    base_url: str = ""
    api_type: str = "rest"
    auth_type: str = "api_key"
    rate_limit_rpm: int = 60
    rate_limit_tpm: int = 100000
    health_state: str = (
        HealthState.UNKNOWN
    )


class ModelRecord(BaseModel):
    """Model kaydi."""

    model_id: str = ""
    provider: str = ""
    name: str = ""
    capabilities: list[str] = Field(
        default_factory=list
    )
    max_tokens: int = 4096
    input_cost_per_1k: float = 0.0
    output_cost_per_1k: float = 0.0
    context_window: int = 4096
    status: str = ModelStatus.ACTIVE


class ComplexityAnalysis(BaseModel):
    """Karmasiklik analizi."""

    analysis_id: str = ""
    task_text: str = ""
    complexity_score: float = 0.0
    complexity_level: str = (
        ComplexityLevel.MODERATE
    )
    domain: str = "general"
    estimated_tokens: int = 256
    reasoning_depth: str = (
        ReasoningDepth.MODERATE
    )


class ModelSelection(BaseModel):
    """Model secimi."""

    selection_id: str = ""
    model_id: str = ""
    provider: str = ""
    strategy: str = (
        SelectionStrategy.BALANCED
    )
    score: float = 0.0
    candidates: int = 0


class RouteResult(BaseModel):
    """Yonlendirme sonucu."""

    request_id: str = ""
    routed_to: str = ""
    is_fallback: bool = False
    attempt: int = 1
    original: str = ""


class UsageRecord(BaseModel):
    """Kullanim kaydi."""

    record_id: str = ""
    model_id: str = ""
    provider: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    input_cost: float = 0.0
    output_cost: float = 0.0
    total_cost: float = 0.0
    task_id: str = ""


class LatencyRecord(BaseModel):
    """Gecikme kaydi."""

    record_id: str = ""
    model_id: str = ""
    provider: str = ""
    latency_ms: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    success: bool = True


class PerformanceEvaluation(BaseModel):
    """Performans degerlendirmesi."""

    eval_id: str = ""
    model_id: str = ""
    task_domain: str = ""
    scores: dict[str, float] = Field(
        default_factory=dict
    )
    overall_score: float = 0.0
    feedback: str = ""


class ABTestRecord(BaseModel):
    """A/B test kaydi."""

    test_id: str = ""
    name: str = ""
    model_a: str = ""
    model_b: str = ""
    task_domain: str = ""
    sample_size: int = 100
    status: str = "active"


class HealthCheckRecord(BaseModel):
    """Saglik kontrol kaydi."""

    check_id: str = ""
    provider_id: str = ""
    is_available: bool = True
    response_time_ms: float = 0.0
    health_state: str = (
        HealthState.UNKNOWN
    )
    error_message: str = ""


class LLMRouterSummary(BaseModel):
    """LLM Router ozet."""

    total_models: int = 0
    total_providers: int = 0
    total_cost: float = 0.0
    cache_hit_rate: float = 0.0
    healthy_providers: int = 0
    cost_optimization: bool = True
    auto_fallback: bool = True
