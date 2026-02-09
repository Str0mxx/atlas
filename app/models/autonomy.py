"""BDI otonomi veri modelleri.

Belief, Desire, Intention ve Plan Pydantic modelleri.
BDI agent dongusu icin kullanilan tum veri yapilarini tanimlar.
"""

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# === Enum'lar ===


class BeliefSource(str, Enum):
    """Belief kaynagi."""

    MONITOR = "monitor"
    AGENT = "agent"
    USER = "user"
    INFERENCE = "inference"


class BeliefCategory(str, Enum):
    """Belief kategorisi."""

    SERVER = "server"
    SECURITY = "security"
    MARKETING = "marketing"
    COMMUNICATION = "communication"
    OPPORTUNITY = "opportunity"
    SYSTEM = "system"


class GoalStatus(str, Enum):
    """Hedef durumu."""

    ACTIVE = "active"
    ACHIEVED = "achieved"
    DROPPED = "dropped"
    SUSPENDED = "suspended"
    FAILED = "failed"


class GoalPriority(str, Enum):
    """Hedef oncelik seviyesi."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class PlanStatus(str, Enum):
    """Plan durumu."""

    READY = "ready"
    EXECUTING = "executing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    ABORTED = "aborted"


class CommitmentStrategy(str, Enum):
    """Taahhut stratejisi."""

    BLIND = "blind"
    SINGLE_MINDED = "single_minded"
    OPEN_MINDED = "open_minded"


# === Pydantic Modeller ===


class Belief(BaseModel):
    """Sistemin dunya hakkindaki tek bir inanci.

    Attributes:
        id: Benzersiz belief kimlik numarasi.
        key: Belief tanimlayici anahtari (ornek: "server:cpu_usage").
        value: Belief degeri (herhangi bir tip).
        confidence: Guven skoru (0.0-1.0).
        source: Belief kaynagi.
        category: Belief kategorisi.
        timestamp: Olusturulma/guncelleme zamani.
        decay_rate: Guven azalma orani (saat basina).
        metadata: Ek veriler.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    key: str
    value: Any
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    source: BeliefSource = BeliefSource.MONITOR
    category: BeliefCategory = BeliefCategory.SYSTEM
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
    decay_rate: float = Field(default=0.1, ge=0.0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class BeliefUpdate(BaseModel):
    """Belief guncelleme istegi.

    Attributes:
        key: Guncellenecek belief anahtari.
        value: Yeni deger.
        confidence: Yeni guven skoru.
        source: Guncelleme kaynagi.
    """

    key: str
    value: Any
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    source: BeliefSource = BeliefSource.MONITOR


class Desire(BaseModel):
    """Sistemin bir hedefi/istegi.

    Attributes:
        id: Benzersiz hedef kimlik numarasi.
        name: Hedef adi.
        description: Hedef aciklamasi.
        priority: Oncelik seviyesi.
        priority_score: Dinamik oncelik puani (0.0-1.0).
        status: Mevcut durum.
        parent_id: Ust hedef ID (hiyerarsi icin).
        sub_goal_ids: Alt hedef ID listesi.
        preconditions: On kosullar (belief key -> beklenen deger).
        success_conditions: Basari kosullari (belief key -> beklenen deger).
        deadline: Son teslim zamani (opsiyonel).
        created_at: Olusturulma zamani.
        metadata: Ek veriler.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str = ""
    priority: GoalPriority = GoalPriority.MEDIUM
    priority_score: float = Field(default=0.5, ge=0.0, le=1.0)
    status: GoalStatus = GoalStatus.ACTIVE
    parent_id: str | None = None
    sub_goal_ids: list[str] = Field(default_factory=list)
    preconditions: dict[str, Any] = Field(default_factory=dict)
    success_conditions: dict[str, Any] = Field(default_factory=dict)
    deadline: datetime | None = None
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
    metadata: dict[str, Any] = Field(default_factory=dict)


class PlanStep(BaseModel):
    """Plan icindeki tek bir adim.

    Attributes:
        description: Adim aciklamasi.
        target_agent: Hedef agent adi.
        task_params: Gorev parametreleri.
        order: Siralama (dusuk = once).
        completed: Adim tamamlandi mi.
    """

    description: str
    target_agent: str | None = None
    task_params: dict[str, Any] = Field(default_factory=dict)
    order: int = 0
    completed: bool = False


class Plan(BaseModel):
    """Onceden tanimlanmis veya dinamik plan.

    Attributes:
        id: Benzersiz plan kimlik numarasi.
        name: Plan adi.
        description: Plan aciklamasi.
        goal_name: Bu planin karsiladigi hedef adi.
        preconditions: On kosullar (belief key -> beklenen deger).
        steps: Plan adimlari.
        status: Plan durumu.
        success_rate: Gecmis basari orani (0.0-1.0).
        metadata: Ek veriler.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str = ""
    goal_name: str = ""
    preconditions: dict[str, Any] = Field(default_factory=dict)
    steps: list[PlanStep] = Field(default_factory=list)
    status: PlanStatus = PlanStatus.READY
    success_rate: float = Field(default=0.5, ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class Intention(BaseModel):
    """Taahhut edilmis bir plan-hedef cifti.

    Attributes:
        id: Benzersiz intention kimlik numarasi.
        desire_id: Hedef ID.
        plan_id: Secilen plan ID.
        status: Plan durumu.
        current_step: Mevcut adim indeksi.
        commitment: Taahhut stratejisi.
        started_at: Baslanma zamani.
        retry_count: Yeniden deneme sayisi.
        max_retries: Maksimum yeniden deneme.
        metadata: Ek veriler.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    desire_id: str
    plan_id: str
    status: PlanStatus = PlanStatus.READY
    current_step: int = 0
    commitment: CommitmentStrategy = CommitmentStrategy.SINGLE_MINDED
    started_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
    retry_count: int = 0
    max_retries: int = 3
    metadata: dict[str, Any] = Field(default_factory=dict)
