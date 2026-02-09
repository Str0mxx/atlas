"""Olasiliksal karar verme veri modelleri.

BayesianNetwork, MonteCarloSimulator, UncertaintyManager ve
DecisionTheory modulleri icin Pydantic modelleri.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# === Enum'lar ===


class DistributionType(str, Enum):
    """Olasilik dagilimi tipi."""

    NORMAL = "normal"
    UNIFORM = "uniform"
    BETA = "beta"
    TRIANGULAR = "triangular"
    CUSTOM = "custom"


class DecisionCriterion(str, Enum):
    """Belirsizlik altinda karar kriteri."""

    MAXIMAX = "maximax"
    MAXIMIN = "maximin"
    HURWICZ = "hurwicz"
    MINIMAX_REGRET = "minimax_regret"
    EXPECTED_VALUE = "expected_value"


class RiskAttitude(str, Enum):
    """Risk tutumu."""

    AVERSE = "averse"
    NEUTRAL = "neutral"
    SEEKING = "seeking"


# === Bayesian Modeller ===


class PriorBelief(BaseModel):
    """Bayesci on inanc (prior).

    Attributes:
        variable: Degisken adi.
        probabilities: Durum -> olasilik eslesmesi.
        source: Inanc kaynagi.
    """

    variable: str
    probabilities: dict[str, float]
    source: str = "prior"


class Evidence(BaseModel):
    """Gozlenen kanit.

    Attributes:
        variable: Gozlenen degisken.
        observed_value: Gozlenen deger.
        confidence: Gozlem guvenirliligi (0-1).
        timestamp: Gozlem zamani.
    """

    variable: str
    observed_value: str
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )


class PosteriorResult(BaseModel):
    """Bayesci guncelleme sonucu.

    Attributes:
        variable: Degisken adi.
        prior: On inanc olasiliklari.
        posterior: Guncellenmis olasiliklar.
        evidence_used: Kullanilan kanit listesi.
        log_likelihood: Log-likelihood degeri.
    """

    variable: str
    prior: dict[str, float]
    posterior: dict[str, float]
    evidence_used: list[str] = Field(default_factory=list)
    log_likelihood: float = 0.0


class ConditionalProbability(BaseModel):
    """Kosullu olasilik tablosu girdisi.

    Attributes:
        child: Cocuk degisken.
        parents: Ebeveyn degisken(ler).
        table: (ebeveyn_durum -> cocuk_durum -> olasilik) eslesmesi.
    """

    child: str
    parents: list[str]
    table: dict[str, dict[str, float]]


# === Belirsizlik Modelleri ===


class ConfidenceInterval(BaseModel):
    """Guven araligi.

    Attributes:
        lower: Alt sinir.
        upper: Ust sinir.
        confidence_level: Guven duzeyi (0-1).
        mean: Ortalama deger.
    """

    lower: float
    upper: float
    confidence_level: float = Field(default=0.95, ge=0.0, le=1.0)
    mean: float = 0.0


class RiskQuantification(BaseModel):
    """Risk nicelestirme sonucu.

    Attributes:
        expected_loss: Beklenen kayip.
        var_95: %95 Value at Risk.
        cvar_95: Conditional VaR (%95).
        probability_of_loss: Kayip olasiligi.
        worst_case: En kotu senaryo.
        best_case: En iyi senaryo.
    """

    expected_loss: float = 0.0
    var_95: float = 0.0
    cvar_95: float = 0.0
    probability_of_loss: float = Field(default=0.0, ge=0.0, le=1.0)
    worst_case: float = 0.0
    best_case: float = 0.0


class ScenarioAnalysis(BaseModel):
    """Senaryo analizi sonucu.

    Attributes:
        worst_case: En kotu durum sonucu.
        best_case: En iyi durum sonucu.
        expected_case: Beklenen durum sonucu.
        scenarios: Tum senaryolar.
        probabilities: Senaryo olasiliklari.
    """

    worst_case: float
    best_case: float
    expected_case: float
    scenarios: dict[str, float] = Field(default_factory=dict)
    probabilities: dict[str, float] = Field(default_factory=dict)


# === Karar Teorisi Modelleri ===


class UtilityOutcome(BaseModel):
    """Tek bir alternatifin fayda-sonucu.

    Attributes:
        action: Aksiyon/alternatif adi.
        state: Dogal durum.
        probability: Durum olasiligi.
        payoff: Getiri/kayip degeri.
        utility: Fayda degeri (risk tutumuna gore).
    """

    action: str
    state: str
    probability: float = Field(ge=0.0, le=1.0)
    payoff: float = 0.0
    utility: float = 0.0


class DecisionResult(BaseModel):
    """Karar teorisi analiz sonucu.

    Attributes:
        recommended_action: Onerilen aksiyon.
        criterion_used: Kullanilan kriter.
        expected_utility: Beklenen fayda.
        all_scores: Tum aksiyonlarin skorlari.
        risk_assessment: Risk degerlendirmesi.
        metadata: Ek bilgiler.
    """

    recommended_action: str
    criterion_used: str
    expected_utility: float = 0.0
    all_scores: dict[str, float] = Field(default_factory=dict)
    risk_assessment: RiskQuantification | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


# === Monte Carlo Modelleri ===


class SimulationConfig(BaseModel):
    """Monte Carlo simulasyon yapilandirmasi.

    Attributes:
        n_simulations: Simulasyon sayisi.
        random_seed: Tekrarlanabilirlik icin tohum.
        variables: Degisken tanimlari.
    """

    n_simulations: int = Field(default=10000, ge=100)
    random_seed: int | None = None
    variables: dict[str, dict[str, Any]] = Field(default_factory=dict)


class SimulationResult(BaseModel):
    """Monte Carlo simulasyon sonucu.

    Attributes:
        mean: Ortalama sonuc.
        std: Standart sapma.
        percentiles: Yuzdelik degerleri.
        confidence_interval: Guven araligi.
        n_simulations: Calistirilan simulasyon sayisi.
        convergence_achieved: Yakinsaklik saglandi mi.
        metadata: Ek bilgiler.
    """

    mean: float
    std: float
    percentiles: dict[str, float] = Field(default_factory=dict)
    confidence_interval: ConfidenceInterval | None = None
    n_simulations: int = 0
    convergence_achieved: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class SensitivityResult(BaseModel):
    """Duyarlilik analizi sonucu.

    Attributes:
        variable: Analiz edilen degisken.
        base_value: Temel deger.
        impact_scores: Etki skorlari.
        tornado_data: Tornado grafik verileri.
        correlation_coefficients: Korelasyon katsayilari.
    """

    variable: str
    base_value: float
    impact_scores: dict[str, float] = Field(default_factory=dict)
    tornado_data: list[dict[str, Any]] = Field(default_factory=list)
    correlation_coefficients: dict[str, float] = Field(default_factory=dict)
