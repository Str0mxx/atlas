"""Is analizi agent'i veri modelleri.

Fizibilite, finansal analiz, pazar analizi, rakip analizi
ve performans degerlendirme sonuclarini modellar.
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class AnalysisType(str, Enum):
    """Analiz tipi."""

    FEASIBILITY = "feasibility"
    FINANCIAL = "financial"
    MARKET = "market"
    COMPETITOR = "competitor"
    PERFORMANCE = "performance"


class AnalysisConfig(BaseModel):
    """Analiz yapilandirmasi.

    Attributes:
        model: Kullanilacak LLM modeli.
        max_tokens: Maks yanit token sayisi.
        currency: Para birimi.
        language: Yanit dili.
    """

    model: str = "claude-sonnet-4-5-20250929"
    max_tokens: int = 4096
    currency: str = "TRY"
    language: str = "tr"


class CompetitorInfo(BaseModel):
    """Rakip bilgisi.

    Attributes:
        name: Rakip adi.
        url: Web sitesi (opsiyonel).
        strengths: Guclu yonleri.
        weaknesses: Zayif yonleri.
        market_share_estimate: Tahmini pazar payi (%).
    """

    name: str
    url: str | None = None
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    market_share_estimate: float | None = None


class FeasibilityResult(BaseModel):
    """Fizibilite analizi sonucu.

    Attributes:
        score: Fizibilite skoru (0-100).
        strengths: SWOT - guclu yonler.
        weaknesses: SWOT - zayif yonler.
        opportunities: SWOT - firsatlar.
        threats: SWOT - tehditler.
        recommendation: Genel oneri.
        estimated_timeline: Tahmini sure.
    """

    score: float = Field(ge=0, le=100)
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    opportunities: list[str] = Field(default_factory=list)
    threats: list[str] = Field(default_factory=list)
    recommendation: str = ""
    estimated_timeline: str = ""


class FinancialResult(BaseModel):
    """Finansal analiz sonucu.

    Attributes:
        investment: Toplam yatirim miktari.
        revenue_estimate: Tahmini aylik gelir.
        costs: Maliyet kalemleri.
        roi_estimate: Tahmini ROI (%).
        break_even_months: Basabaş suresi (ay).
        risk_factors: Finansal risk faktorleri.
        currency: Para birimi.
    """

    investment: float = 0.0
    revenue_estimate: float = 0.0
    costs: dict[str, float] = Field(default_factory=dict)
    roi_estimate: float = 0.0
    break_even_months: int = 0
    risk_factors: list[str] = Field(default_factory=list)
    currency: str = "TRY"


class MarketResult(BaseModel):
    """Pazar analizi sonucu.

    Attributes:
        market_size: Pazar buyuklugu (tahmini).
        growth_rate: Buyume orani (%).
        competitors: Rakip listesi.
        target_audience: Hedef kitle tanimi.
        trends: Pazar trendleri.
        entry_barriers: Giris engelleri.
    """

    market_size: str = ""
    growth_rate: float = 0.0
    competitors: list[CompetitorInfo] = Field(default_factory=list)
    target_audience: str = ""
    trends: list[str] = Field(default_factory=list)
    entry_barriers: list[str] = Field(default_factory=list)


class PerformanceResult(BaseModel):
    """Performans analizi sonucu.

    Attributes:
        metric_name: Metrik adi.
        current_value: Mevcut deger.
        target_value: Hedef deger.
        trend: Trend yonu (up/down/stable).
        gap_percentage: Hedefle aradaki fark (%).
        recommendations: Iyilestirme onerileri.
    """

    metric_name: str = ""
    current_value: float = 0.0
    target_value: float = 0.0
    trend: str = "stable"
    gap_percentage: float = 0.0
    recommendations: list[str] = Field(default_factory=list)


class AnalysisReport(BaseModel):
    """Genel analiz raporu.

    Attributes:
        analysis_type: Analiz turu.
        title: Rapor basligi.
        summary: Ozet.
        data: Analiz verisi (tur bazli sonuc).
        recommendations: Oneriler listesi.
        risk_level: Risk seviyesi (low/medium/high).
        confidence: Guven skoru (0.0-1.0).
    """

    analysis_type: str
    title: str = ""
    summary: str = ""
    data: dict[str, Any] = Field(default_factory=dict)
    recommendations: list[str] = Field(default_factory=list)
    risk_level: str = "low"
    confidence: float = Field(default=0.7, ge=0.0, le=1.0)
