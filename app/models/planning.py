"""Stratejik planlama veri modelleri.

GoalTree, HTN planlama, zamansal kisitlar, acil durum planlari,
kaynak yonetimi ve strateji motoru icin Pydantic modelleri.
"""

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# === Enum'lar ===


class GoalType(str, Enum):
    """Hedef tipi (AND/OR decomposition)."""

    AND = "and"
    OR = "or"
    LEAF = "leaf"


class GoalNodeStatus(str, Enum):
    """Hedef dugum durumu."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


class HTNTaskType(str, Enum):
    """HTN gorev tipi."""

    PRIMITIVE = "primitive"
    COMPOUND = "compound"


class HTNMethodStatus(str, Enum):
    """HTN metot durumu."""

    APPLICABLE = "applicable"
    NOT_APPLICABLE = "not_applicable"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"


class ConstraintType(str, Enum):
    """Zamansal kisit tipi."""

    DEADLINE = "deadline"
    START_AFTER = "start_after"
    FINISH_BEFORE = "finish_before"
    DURATION_MAX = "duration_max"
    DEPENDENCY = "dependency"


class TriggerType(str, Enum):
    """Acil durum tetikleyici tipi."""

    THRESHOLD = "threshold"
    TIMEOUT = "timeout"
    FAILURE_COUNT = "failure_count"
    EXTERNAL_EVENT = "external_event"
    CONDITION = "condition"


class ResourceType(str, Enum):
    """Kaynak tipi."""

    CPU = "cpu"
    MEMORY = "memory"
    BUDGET = "budget"
    AGENT = "agent"
    API_QUOTA = "api_quota"
    TIME = "time"
    CUSTOM = "custom"


class AllocationStatus(str, Enum):
    """Kaynak tahsis durumu."""

    ALLOCATED = "allocated"
    RELEASED = "released"
    PENDING = "pending"
    CONFLICT = "conflict"


class StrategyType(str, Enum):
    """Strateji tipi."""

    LONG_TERM = "long_term"
    SHORT_TERM = "short_term"
    ADAPTIVE = "adaptive"
    DEFENSIVE = "defensive"
    AGGRESSIVE = "aggressive"


class ScenarioLikelihood(str, Enum):
    """Senaryo olasilik seviyesi."""

    VERY_LIKELY = "very_likely"
    LIKELY = "likely"
    POSSIBLE = "possible"
    UNLIKELY = "unlikely"
    RARE = "rare"


# === GoalTree Modelleri ===


class GoalNode(BaseModel):
    """Hedef agacindaki tek bir dugum.

    Attributes:
        id: Benzersiz dugum kimlik numarasi.
        name: Hedef adi.
        description: Hedef aciklamasi.
        goal_type: AND/OR/LEAF tipi.
        status: Mevcut durum.
        progress: Ilerleme yuzdesi (0.0-1.0).
        parent_id: Ust dugum ID.
        children_ids: Alt dugum ID listesi.
        dependencies: Bagimlilik ID listesi.
        priority: Oncelik puani (0.0-1.0).
        metadata: Ek veriler.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str = ""
    goal_type: GoalType = GoalType.LEAF
    status: GoalNodeStatus = GoalNodeStatus.PENDING
    progress: float = Field(default=0.0, ge=0.0, le=1.0)
    parent_id: str | None = None
    children_ids: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    priority: float = Field(default=0.5, ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class GoalTreeSnapshot(BaseModel):
    """Hedef agacinin tam goruntusu.

    Attributes:
        root_id: Kok dugum ID.
        nodes: Tum dugumlerin sozlugu (id -> GoalNode).
        total_progress: Toplam ilerleme (0.0-1.0).
        timestamp: Goruntu zamani.
    """

    root_id: str | None = None
    nodes: dict[str, GoalNode] = Field(default_factory=dict)
    total_progress: float = Field(default=0.0, ge=0.0, le=1.0)
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )


# === HTN Planlama Modelleri ===


class HTNTask(BaseModel):
    """HTN gorev tanimi.

    Attributes:
        id: Benzersiz gorev kimlik numarasi.
        name: Gorev adi.
        task_type: Primitive veya compound.
        preconditions: On kosullar (anahtar -> deger).
        effects: Sonuc etkileri (anahtar -> deger).
        parameters: Gorev parametreleri.
        duration_estimate: Tahmini sure (saniye).
        agent: Hedef agent adi.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    task_type: HTNTaskType = HTNTaskType.PRIMITIVE
    preconditions: dict[str, Any] = Field(default_factory=dict)
    effects: dict[str, Any] = Field(default_factory=dict)
    parameters: dict[str, Any] = Field(default_factory=dict)
    duration_estimate: float = 0.0
    agent: str | None = None


class HTNMethod(BaseModel):
    """HTN decomposition metodu.

    Attributes:
        id: Benzersiz metot kimlik numarasi.
        name: Metot adi.
        task_name: Uygulandigi compound gorev adi.
        preconditions: On kosullar.
        subtasks: Alt gorev adlari (sirali).
        preference: Metot tercih puani (yuksek = daha tercih edilir).
        status: Metot durumu.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    task_name: str
    preconditions: dict[str, Any] = Field(default_factory=dict)
    subtasks: list[str] = Field(default_factory=list)
    preference: float = Field(default=0.5, ge=0.0, le=1.0)
    status: HTNMethodStatus = HTNMethodStatus.APPLICABLE


class HTNPlan(BaseModel):
    """HTN planlama sonucu.

    Attributes:
        id: Benzersiz plan kimlik numarasi.
        task_name: Planlanan gorev adi.
        ordered_tasks: Sirali primitive gorevler.
        total_duration: Toplam tahmini sure.
        method_chain: Kullanilan metot zincirleri.
        feasible: Plan uygulanabilir mi.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    task_name: str
    ordered_tasks: list[HTNTask] = Field(default_factory=list)
    total_duration: float = 0.0
    method_chain: list[str] = Field(default_factory=list)
    feasible: bool = True


# === Zamansal Planlama Modelleri ===


class TemporalConstraint(BaseModel):
    """Zamansal kisit tanimi.

    Attributes:
        id: Benzersiz kisit kimlik numarasi.
        constraint_type: Kisit tipi.
        task_id: Ilgili gorev ID.
        reference_task_id: Referans gorev ID (bagimlilik icin).
        value: Kisit degeri (datetime veya saniye).
        hard: Zorunlu kisit mi (True) yoksa yumusak mi (False).
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    constraint_type: ConstraintType
    task_id: str
    reference_task_id: str | None = None
    value: float | str | None = None
    hard: bool = True


class ScheduleEntry(BaseModel):
    """Zamanlama giris kaydi.

    Attributes:
        task_id: Gorev ID.
        task_name: Gorev adi.
        start_time: Baslangic zamani (goreceli, saniye).
        end_time: Bitis zamani (goreceli, saniye).
        duration: Sure (saniye).
        slack: Bolluk suresi (saniye).
        on_critical_path: Kritik yol uzerinde mi.
    """

    task_id: str
    task_name: str
    start_time: float = 0.0
    end_time: float = 0.0
    duration: float = 0.0
    slack: float = 0.0
    on_critical_path: bool = False


class ScheduleResult(BaseModel):
    """Zamanlama sonucu.

    Attributes:
        entries: Zamanlanmis gorevler.
        total_duration: Toplam proje suresi.
        critical_path: Kritik yol gorev ID listesi.
        feasible: Cozum bulundu mu.
        constraint_violations: Ihlal edilen kisitlar.
    """

    entries: list[ScheduleEntry] = Field(default_factory=list)
    total_duration: float = 0.0
    critical_path: list[str] = Field(default_factory=list)
    feasible: bool = True
    constraint_violations: list[str] = Field(default_factory=list)


# === Acil Durum Planlama Modelleri ===


class TriggerCondition(BaseModel):
    """Acil durum tetikleyici kosulu.

    Attributes:
        id: Benzersiz tetikleyici kimlik numarasi.
        trigger_type: Tetikleyici tipi.
        metric_key: Izlenen metrik anahtari.
        threshold: Esik degeri.
        operator: Karsilastirma operatoru (gt, lt, eq, gte, lte).
        description: Tetikleyici aciklamasi.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    trigger_type: TriggerType = TriggerType.THRESHOLD
    metric_key: str = ""
    threshold: float = 0.0
    operator: str = "gt"
    description: str = ""


class ContingencyPlanDef(BaseModel):
    """Acil durum plan tanimi.

    Attributes:
        id: Benzersiz plan kimlik numarasi.
        name: Plan adi (orn: Plan B).
        description: Plan aciklamasi.
        trigger: Tetikleyici kosul.
        priority: Oncelik (yuksek = daha once denenecek).
        actions: Aksiyonlar listesi (sirali).
        estimated_recovery_time: Tahmini kurtarma suresi (saniye).
        success_probability: Tahmini basari olasiligi (0.0-1.0).
        active: Plan aktif mi.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str = ""
    trigger: TriggerCondition = Field(default_factory=TriggerCondition)
    priority: int = Field(default=0, ge=0)
    actions: list[dict[str, Any]] = Field(default_factory=list)
    estimated_recovery_time: float = 0.0
    success_probability: float = Field(default=0.5, ge=0.0, le=1.0)
    active: bool = True


class ContingencyActivation(BaseModel):
    """Acil durum plan aktivasyonu.

    Attributes:
        plan_id: Aktive edilen plan ID.
        plan_name: Plan adi.
        trigger_reason: Tetiklenme sebebi.
        activated_at: Aktivasyon zamani.
        resolved: Cozuldu mu.
        resolution_time: Cozum suresi (saniye).
    """

    plan_id: str
    plan_name: str
    trigger_reason: str = ""
    activated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
    resolved: bool = False
    resolution_time: float | None = None


# === Kaynak Planlama Modelleri ===


class Resource(BaseModel):
    """Sistem kaynagi tanimi.

    Attributes:
        id: Benzersiz kaynak kimlik numarasi.
        name: Kaynak adi.
        resource_type: Kaynak tipi.
        capacity: Toplam kapasite.
        available: Mevcut kapasite.
        unit: Birim (orn: %, MB, USD).
        cost_per_unit: Birim basi maliyet.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    resource_type: ResourceType = ResourceType.CUSTOM
    capacity: float = Field(default=100.0, ge=0.0)
    available: float = Field(default=100.0, ge=0.0)
    unit: str = ""
    cost_per_unit: float = Field(default=0.0, ge=0.0)


class ResourceAllocation(BaseModel):
    """Kaynak tahsis kaydi.

    Attributes:
        id: Benzersiz tahsis kimlik numarasi.
        resource_id: Kaynak ID.
        task_id: Gorev ID.
        amount: Tahsis miktari.
        status: Tahsis durumu.
        allocated_at: Tahsis zamani.
        released_at: Serbest birakma zamani.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    resource_id: str
    task_id: str
    amount: float = Field(default=0.0, ge=0.0)
    status: AllocationStatus = AllocationStatus.PENDING
    allocated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
    released_at: datetime | None = None


class ResourceConflict(BaseModel):
    """Kaynak catismasi.

    Attributes:
        resource_id: Catisan kaynak ID.
        resource_name: Kaynak adi.
        requested: Istenen miktar.
        available: Mevcut miktar.
        competing_tasks: Catisan gorev ID listesi.
        resolution: Cozum onerisi.
    """

    resource_id: str
    resource_name: str = ""
    requested: float = 0.0
    available: float = 0.0
    competing_tasks: list[str] = Field(default_factory=list)
    resolution: str = ""


class OptimizationResult(BaseModel):
    """Kaynak optimizasyon sonucu.

    Attributes:
        allocations: Optimal tahsisler.
        total_cost: Toplam maliyet.
        utilization: Kaynak kullanim oranlari (kaynak_id -> oran).
        conflicts: Cozulmemis catismalar.
        feasible: Cozum bulundu mu.
    """

    allocations: list[ResourceAllocation] = Field(default_factory=list)
    total_cost: float = 0.0
    utilization: dict[str, float] = Field(default_factory=dict)
    conflicts: list[ResourceConflict] = Field(default_factory=list)
    feasible: bool = True


# === Strateji Modelleri ===


class Scenario(BaseModel):
    """Senaryo tanimi.

    Attributes:
        id: Benzersiz senaryo kimlik numarasi.
        name: Senaryo adi.
        description: Senaryo aciklamasi.
        likelihood: Olasilik seviyesi.
        probability: Sayisal olasilik (0.0-1.0).
        conditions: Senaryo kosullari.
        impact: Etki metrikleri.
        recommended_actions: Onerilen aksiyonlar.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str = ""
    likelihood: ScenarioLikelihood = ScenarioLikelihood.POSSIBLE
    probability: float = Field(default=0.5, ge=0.0, le=1.0)
    conditions: dict[str, Any] = Field(default_factory=dict)
    impact: dict[str, float] = Field(default_factory=dict)
    recommended_actions: list[str] = Field(default_factory=list)


class Strategy(BaseModel):
    """Strateji tanimi.

    Attributes:
        id: Benzersiz strateji kimlik numarasi.
        name: Strateji adi.
        description: Strateji aciklamasi.
        strategy_type: Strateji tipi.
        goals: Hedef listesi.
        scenarios: Senaryo listesi.
        kpis: Anahtar performans gostergeleri.
        time_horizon: Zaman ufku (gun).
        confidence: Guven skoru (0.0-1.0).
        active: Strateji aktif mi.
        created_at: Olusturulma zamani.
        metadata: Ek veriler.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str = ""
    strategy_type: StrategyType = StrategyType.ADAPTIVE
    goals: list[str] = Field(default_factory=list)
    scenarios: list[Scenario] = Field(default_factory=list)
    kpis: dict[str, float] = Field(default_factory=dict)
    time_horizon: int = Field(default=30, ge=1)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    active: bool = True
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
    metadata: dict[str, Any] = Field(default_factory=dict)


class StrategyEvaluation(BaseModel):
    """Strateji degerlendirme sonucu.

    Attributes:
        strategy_id: Degerlendirilen strateji ID.
        score: Genel puan (0.0-1.0).
        kpi_scores: KPI bazli puanlar.
        strengths: Guclu yonler.
        weaknesses: Zayif yonler.
        recommendation: Oneri.
        evaluated_at: Degerlendirme zamani.
    """

    strategy_id: str
    score: float = Field(default=0.0, ge=0.0, le=1.0)
    kpi_scores: dict[str, float] = Field(default_factory=dict)
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    recommendation: str = ""
    evaluated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
