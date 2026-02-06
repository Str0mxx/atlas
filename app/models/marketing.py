"""Google Ads marketing agent'i veri modelleri.

Kampanya performans metriklerini, anahtar kelime analizlerini,
reklam reddi bilgilerini ve butce optimizasyon onerilerini modellar.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class AdCheckType(str, Enum):
    """Marketing kontrol tipleri."""

    CAMPAIGN_PERFORMANCE = "campaign_performance"
    KEYWORD_PERFORMANCE = "keyword_performance"
    AD_DISAPPROVALS = "ad_disapprovals"
    BUDGET_ANALYSIS = "budget_analysis"


class PerformanceLevel(str, Enum):
    """Performans seviyesi."""

    EXCELLENT = "excellent"
    GOOD = "good"
    AVERAGE = "average"
    POOR = "poor"
    CRITICAL = "critical"


class MarketingConfig(BaseModel):
    """Google Ads marketing yapilandirmasi.

    Attributes:
        checks: Calistirilacak kontrol tipleri.
        customer_id: Google Ads musteri ID.
        date_range_days: Analiz icin geri bakilacak gun sayisi.
        cpc_threshold: CPC uyari esigi (TRY).
        cpa_threshold: CPA uyari esigi (TRY).
        roas_min_threshold: Minimum kabul edilebilir ROAS.
        ctr_min_threshold: Minimum kabul edilebilir CTR yuzdesi.
        low_quality_score_threshold: Dusuk kalite puani esigi.
        budget_waste_threshold: Butce israf orani esigi (yuzde).
    """

    checks: list[AdCheckType] = Field(
        default_factory=lambda: list(AdCheckType),
    )
    customer_id: str = ""
    date_range_days: int = 7
    cpc_threshold: float = 15.0
    cpa_threshold: float = 200.0
    roas_min_threshold: float = 2.0
    ctr_min_threshold: float = 1.0
    low_quality_score_threshold: int = 4
    budget_waste_threshold: float = 30.0


class CampaignMetrics(BaseModel):
    """Kampanya performans metrikleri.

    Attributes:
        campaign_id: Kampanya ID.
        campaign_name: Kampanya adi.
        status: Kampanya durumu (ENABLED/PAUSED/REMOVED).
        impressions: Gosterim sayisi.
        clicks: Tiklama sayisi.
        cost: Toplam harcama (mikro birim, 1_000_000 = 1 TRY).
        conversions: Donusum sayisi.
        conversion_value: Donusum degeri.
        cpc: Ortalama tiklama maliyeti (TRY).
        cpa: Donusum basina maliyet (TRY).
        ctr: Tiklama orani (yuzde).
        roas: Reklam harcamasi getirisi.
        daily_budget: Gunluk butce (mikro birim).
        performance_level: Hesaplanan performans seviyesi.
    """

    campaign_id: str = ""
    campaign_name: str = ""
    status: str = "ENABLED"
    impressions: int = 0
    clicks: int = 0
    cost: int = 0
    conversions: float = 0.0
    conversion_value: float = 0.0
    cpc: float = 0.0
    cpa: float = 0.0
    ctr: float = 0.0
    roas: float = 0.0
    daily_budget: int = 0
    performance_level: PerformanceLevel = PerformanceLevel.AVERAGE


class KeywordMetrics(BaseModel):
    """Anahtar kelime performans metrikleri.

    Attributes:
        keyword_id: Anahtar kelime ID.
        keyword_text: Anahtar kelime metni.
        match_type: Eslesme tipi (EXACT/PHRASE/BROAD).
        campaign_name: Ait oldugu kampanya adi.
        ad_group_name: Ait oldugu reklam grubu.
        impressions: Gosterim sayisi.
        clicks: Tiklama sayisi.
        cost: Toplam harcama (mikro birim).
        conversions: Donusum sayisi.
        cpc: Ortalama tiklama maliyeti (TRY).
        ctr: Tiklama orani (yuzde).
        quality_score: Kalite puani (1-10).
        performance_level: Hesaplanan performans seviyesi.
    """

    keyword_id: str = ""
    keyword_text: str = ""
    match_type: str = "BROAD"
    campaign_name: str = ""
    ad_group_name: str = ""
    impressions: int = 0
    clicks: int = 0
    cost: int = 0
    conversions: float = 0.0
    cpc: float = 0.0
    ctr: float = 0.0
    quality_score: int = 0
    performance_level: PerformanceLevel = PerformanceLevel.AVERAGE


class AdDisapproval(BaseModel):
    """Reklam reddi bilgisi.

    Attributes:
        ad_id: Reklam ID.
        ad_group_name: Reklam grubu adi.
        campaign_name: Kampanya adi.
        headline: Reklam basligi.
        policy_topic: Ihlal edilen politika konusu.
        policy_type: Politika tipi (DISAPPROVED/LIMITED).
        evidence: Red kanitlari.
    """

    ad_id: str = ""
    ad_group_name: str = ""
    campaign_name: str = ""
    headline: str = ""
    policy_topic: str = ""
    policy_type: str = "DISAPPROVED"
    evidence: list[str] = Field(default_factory=list)


class BudgetRecommendation(BaseModel):
    """Butce optimizasyon onerisi.

    Attributes:
        campaign_name: Kampanya adi.
        current_budget: Mevcut gunluk butce (TRY).
        recommended_budget: Onerilen gunluk butce (TRY).
        reason: Oneri nedeni.
        estimated_impact: Beklenen etki aciklamasi.
        priority: Oneri onceligi (1=en yuksek).
    """

    campaign_name: str = ""
    current_budget: float = 0.0
    recommended_budget: float = 0.0
    reason: str = ""
    estimated_impact: str = ""
    priority: int = 1


class MarketingAnalysisResult(BaseModel):
    """Marketing analiz genel sonucu.

    Attributes:
        performance_level: Genel performans seviyesi.
        campaigns: Kampanya metrikleri.
        total_spend: Toplam harcama (TRY).
        total_conversions: Toplam donusum.
        total_conversion_value: Toplam donusum degeri (TRY).
        overall_roas: Genel ROAS.
        overall_ctr: Genel CTR (yuzde).
        poor_campaigns: Dusuk performansli kampanyalar.
        poor_keywords: Dusuk performansli anahtar kelimeler.
        disapprovals: Reddedilen reklamlar.
        budget_recommendations: Butce optimizasyon onerileri.
        summary: Analiz ozeti.
    """

    performance_level: PerformanceLevel = PerformanceLevel.AVERAGE
    campaigns: list[CampaignMetrics] = Field(default_factory=list)
    total_spend: float = 0.0
    total_conversions: float = 0.0
    total_conversion_value: float = 0.0
    overall_roas: float = 0.0
    overall_ctr: float = 0.0
    poor_campaigns: list[CampaignMetrics] = Field(default_factory=list)
    poor_keywords: list[KeywordMetrics] = Field(default_factory=list)
    disapprovals: list[AdDisapproval] = Field(default_factory=list)
    budget_recommendations: list[BudgetRecommendation] = Field(default_factory=list)
    summary: str = ""
