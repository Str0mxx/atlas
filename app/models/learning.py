"""ATLAS ogrenme veri modelleri.

Reinforcement Learning, deneyim tamponu, odul sistemi,
politika ve adaptasyon icin Pydantic modelleri.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# === Enum'lar ===


class PolicyType(str, Enum):
    """Politika tipi."""

    EPSILON_GREEDY = "epsilon_greedy"
    UCB = "ucb"
    SOFTMAX = "softmax"
    GRADIENT = "gradient"


class DriftType(str, Enum):
    """Konsept drift tipi."""

    SUDDEN = "sudden"
    GRADUAL = "gradual"
    INCREMENTAL = "incremental"
    RECURRING = "recurring"


# === Pydantic Modeller ===


class Experience(BaseModel):
    """Tek bir deneyim kaydi (s, a, r, s', done).

    Attributes:
        state: Baslangic durumu.
        action: Alinan aksiyon.
        reward: Alinan odul.
        next_state: Sonraki durum.
        done: Episode sona erdi mi.
        timestamp: Deneyim zamani.
        metadata: Ek veriler.
    """

    state: dict[str, Any] = Field(default_factory=dict)
    action: str
    reward: float = 0.0
    next_state: dict[str, Any] = Field(default_factory=dict)
    done: bool = False
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
    metadata: dict[str, Any] = Field(default_factory=dict)


class PrioritizedExperience(BaseModel):
    """Oncelikli deneyim kaydi.

    Attributes:
        experience: Deneyim.
        priority: Oncelik degeri (TD-hata tabanli).
        weight: Onem ornekleme agirligi.
    """

    experience: Experience
    priority: float = 1.0
    weight: float = 1.0


class RewardSignal(BaseModel):
    """Odul sinyali.

    Attributes:
        value: Toplam odul degeri.
        components: Odul bilesenleri {hedef: deger}.
        shaped_value: Sekillenmis odul.
        intrinsic_bonus: Icselfif merak bonusu.
    """

    value: float = 0.0
    components: dict[str, float] = Field(default_factory=dict)
    shaped_value: float = 0.0
    intrinsic_bonus: float = 0.0


class RewardConfig(BaseModel):
    """Odul fonksiyonu yapilandirmasi.

    Attributes:
        objectives: Hedef agirliklari {hedef: agirlik}.
        shaping_gamma: Odul sekillendirme iskonto faktoru.
        curiosity_weight: Merak bonusu agirligi.
        success_reward: Basari odulu.
        failure_penalty: Basarisizlik cezasi.
    """

    objectives: dict[str, float] = Field(
        default_factory=lambda: {"success_rate": 0.6, "efficiency": 0.3, "exploration": 0.1},
    )
    shaping_gamma: float = Field(default=0.99, ge=0.0, le=1.0)
    curiosity_weight: float = Field(default=0.1, ge=0.0)
    success_reward: float = 1.0
    failure_penalty: float = -0.5


class PolicyConfig(BaseModel):
    """Politika yapilandirmasi.

    Attributes:
        policy_type: Politika tipi.
        epsilon: Epsilon-greedy kesfif orani.
        epsilon_decay: Epsilon azalma carpani.
        epsilon_min: Minimum epsilon.
        ucb_c: UCB kesfif parametresi.
        temperature: Softmax sicaklik parametresi.
        learning_rate: Gradyan ogrenme orani.
    """

    policy_type: PolicyType = PolicyType.EPSILON_GREEDY
    epsilon: float = Field(default=0.1, ge=0.0, le=1.0)
    epsilon_decay: float = Field(default=0.995, ge=0.0, le=1.0)
    epsilon_min: float = Field(default=0.01, ge=0.0, le=1.0)
    ucb_c: float = Field(default=2.0, ge=0.0)
    temperature: float = Field(default=1.0, gt=0.0)
    learning_rate: float = Field(default=0.01, gt=0.0)


class QTableEntry(BaseModel):
    """Q-tablosu girdisi.

    Attributes:
        state: Durum anahtari.
        action: Aksiyon.
        value: Q-degeri.
        visits: Ziyaret sayisi.
    """

    state: str
    action: str
    value: float = 0.0
    visits: int = 0


class LearningConfig(BaseModel):
    """Q-Learning yapilandirmasi.

    Attributes:
        gamma: Iskonto faktoru.
        alpha: Ogrenme orani.
        alpha_decay: Ogrenme orani azalma carpani.
        batch_size: Mini-batch boyutu.
        buffer_size: Deneyim tamponu kapasitesi.
        double_q: Double Q-Learning kullan.
        use_torch: PyTorch kullan (opsiyonel).
    """

    gamma: float = Field(default=0.99, ge=0.0, le=1.0)
    alpha: float = Field(default=0.1, gt=0.0, le=1.0)
    alpha_decay: float = Field(default=0.999, ge=0.0, le=1.0)
    batch_size: int = Field(default=32, ge=1)
    buffer_size: int = Field(default=10000, ge=100)
    double_q: bool = False
    use_torch: bool = False


class LearningMetrics(BaseModel):
    """Ogrenme metrikleri.

    Attributes:
        total_episodes: Toplam episode sayisi.
        avg_reward: Ortalama odul.
        epsilon_current: Mevcut epsilon degeri.
        q_table_size: Q-tablosu boyutu.
        convergence_rate: Yakinsaklik orani.
        metadata: Ek metrikler.
    """

    total_episodes: int = 0
    avg_reward: float = 0.0
    epsilon_current: float = 0.1
    q_table_size: int = 0
    convergence_rate: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class DriftDetection(BaseModel):
    """Konsept drift algilama sonucu.

    Attributes:
        detected: Drift algilandi mi.
        drift_type: Drift tipi (algilandiysa).
        confidence: Algilama guveni.
        window_mean: Pencere ortalamasi.
        reference_mean: Referans ortalamasi.
        p_value: Istatistiksel anlamlilik.
    """

    detected: bool = False
    drift_type: DriftType | None = None
    confidence: float = 0.0
    window_mean: float = 0.0
    reference_mean: float = 0.0
    p_value: float = 1.0


class AdaptationState(BaseModel):
    """Adaptasyon durumu.

    Attributes:
        current_strategy: Mevcut strateji.
        strategies: Strateji performans skorlari.
        switch_count: Strateji degisim sayisi.
        performance_history: Performans gecmisi.
        drift_detections: Drift algilama gecmisi.
    """

    current_strategy: str = ""
    strategies: dict[str, float] = Field(default_factory=dict)
    switch_count: int = 0
    performance_history: list[float] = Field(default_factory=list)
    drift_detections: list[DriftDetection] = Field(default_factory=list)
