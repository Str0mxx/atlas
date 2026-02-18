"""
Prompt Engineering & Optimization modelleri.

Enum ve Pydantic modeller.
"""

from enum import Enum

from pydantic import BaseModel, Field


class OptimizationType(str, Enum):
    """Optimizasyon tipleri."""

    LENGTH_REDUCTION = "length_reduction"
    CLARITY_IMPROVEMENT = (
        "clarity_improvement"
    )
    TOKEN_OPTIMIZATION = (
        "token_optimization"
    )
    STRUCTURE_ENHANCEMENT = (
        "structure_enhancement"
    )
    SPECIFICITY_BOOST = "specificity_boost"
    REDUNDANCY_REMOVAL = (
        "redundancy_removal"
    )


class CotType(str, Enum):
    """Chain of Thought tipleri."""

    STANDARD = "standard"
    ZERO_SHOT = "zero_shot"
    FEW_SHOT = "few_shot"
    SELF_CONSISTENCY = "self_consistency"
    TREE_OF_THOUGHT = "tree_of_thought"
    REFLECTION = "reflection"
    STEP_BY_STEP = "step_by_step"


class ChunkStrategy(str, Enum):
    """Chunking stratejileri."""

    FIXED_SIZE = "fixed_size"
    SENTENCE_BOUNDARY = (
        "sentence_boundary"
    )
    PARAGRAPH_BOUNDARY = (
        "paragraph_boundary"
    )
    SEMANTIC_BOUNDARY = (
        "semantic_boundary"
    )
    OVERLAP_SLIDING = "overlap_sliding"


class PriorityLevel(str, Enum):
    """Oncelik seviyeleri."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    OPTIONAL = "optional"


class SelectionStrategy(str, Enum):
    """Ornek secim stratejileri."""

    SIMILARITY = "similarity"
    DIVERSITY = "diversity"
    PERFORMANCE = "performance"
    RANDOM = "random"
    BALANCED = "balanced"


class TestStatus(str, Enum):
    """A/B test durumlari."""

    RUNNING = "running"
    COMPLETED = "completed"
    PROMOTED = "promoted"
    CANCELLED = "cancelled"


class QualityTrend(str, Enum):
    """Kalite trendleri."""

    IMPROVING = "improving"
    STABLE = "stable"
    DECLINING = "declining"
    INSUFFICIENT = "insufficient"


class PromptTemplate(BaseModel):
    """Prompt sablonu."""

    template_id: str = ""
    name: str = ""
    content: str = ""
    category: str = ""
    variables: list[str] = Field(
        default_factory=list
    )
    tags: list[str] = Field(
        default_factory=list
    )
    description: str = ""
    version: int = 1
    usage_count: int = 0


class OptimizationResult(BaseModel):
    """Optimizasyon sonucu."""

    optimization_id: str = ""
    original_words: int = 0
    optimized_words: int = 0
    tokens_saved: int = 0
    applied: list[str] = Field(
        default_factory=list
    )
    optimized: bool = False


class VersionRecord(BaseModel):
    """Versiyon kaydi."""

    prompt_id: str = ""
    version: int = 1
    content: str = ""
    author: str = ""
    message: str = ""
    branch: str = "main"


class ABTestRecord(BaseModel):
    """A/B test kaydi."""

    test_id: str = ""
    name: str = ""
    prompt_a: str = ""
    prompt_b: str = ""
    metric: str = "quality"
    sample_size: int = 100
    status: TestStatus = TestStatus.RUNNING
    winner: str | None = None


class ABTestResult(BaseModel):
    """A/B test sonucu."""

    variant: str = "a"
    score: float = 0.0
    latency_ms: float = 0.0
    success: bool = True


class ContextWindow(BaseModel):
    """Context penceresi."""

    window_id: str = ""
    name: str = ""
    max_tokens: int = 4096
    available_tokens: int = 0
    used_tokens: int = 0
    segment_count: int = 0


class ChunkResult(BaseModel):
    """Chunk sonucu."""

    chunk_id: str = ""
    strategy: str = "fixed_size"
    total_chunks: int = 0
    chunk_sizes: list[int] = Field(
        default_factory=list
    )


class CotChain(BaseModel):
    """CoT zinciri."""

    chain_id: str = ""
    task: str = ""
    cot_type: str = "standard"
    prompt: str = ""


class FewShotExample(BaseModel):
    """Few-shot ornegi."""

    example_id: str = ""
    input_text: str = Field(
        "", alias="input"
    )
    output_text: str = Field(
        "", alias="output"
    )
    domain: str = ""
    task_type: str = ""
    quality_score: float = 1.0
    success_rate: float = 0.0

    model_config = {
        "populate_by_name": True,
    }


class PerformanceMetrics(BaseModel):
    """Performans metrikleri."""

    prompt_id: str = ""
    name: str = ""
    total_calls: int = 0
    success_rate: float = 0.0
    avg_quality: float = 0.0
    avg_latency_ms: float = 0.0
    avg_cost: float = 0.0
    token_efficiency: float = 0.0


class PromptEngSummary(BaseModel):
    """Genel ozet."""

    templates: int = 0
    optimizations: int = 0
    versions: int = 0
    ab_tests: int = 0
    chains: int = 0
    examples: int = 0
    perf_records: int = 0
