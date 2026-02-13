"""ATLAS Firsat Tespit modulu.

Pazar taramasi, trend analizi, rakip izleme, bosluk tespiti
ve lead puanlama islemleri.
"""

import logging
import math
from datetime import datetime, timezone
from typing import Any

from app.models.business import (
    CompetitorInfo,
    MarketSignal,
    Opportunity,
    OpportunityStatus,
    OpportunityType,
    TrendData,
)

logger = logging.getLogger(__name__)

# Firsat tipi agirlik haritasi
_OPPORTUNITY_TYPE_WEIGHTS: dict[OpportunityType, float] = {
    OpportunityType.MARKET_GAP: 0.9,
    OpportunityType.TREND: 0.7,
    OpportunityType.COMPETITOR_WEAKNESS: 0.8,
    OpportunityType.CUSTOMER_NEED: 0.85,
    OpportunityType.COST_REDUCTION: 0.6,
    OpportunityType.PARTNERSHIP: 0.5,
}


class OpportunityDetector:
    """Firsat tespit sistemi.

    Pazar sinyallerini toplar, trendleri analiz eder,
    rakipleri izler, pazar bosluklarini tespit eder
    ve firsatlari lead puanina gore siralar.

    Attributes:
        _opportunities: Tespit edilen firsatlar (id -> Opportunity).
        _signals: Toplanan pazar sinyalleri.
        _trends: Trend verileri (keyword -> TrendData).
        _competitors: Rakip bilgileri (id -> CompetitorInfo).
        _min_confidence: Minimum guven esigi.
    """

    def __init__(self, min_confidence: float = 0.3) -> None:
        """Firsat tespit sistemini baslatir.

        Args:
            min_confidence: Minimum guven esigi (0.0-1.0).
        """
        self._opportunities: dict[str, Opportunity] = {}
        self._signals: list[MarketSignal] = []
        self._trends: dict[str, TrendData] = {}
        self._competitors: dict[str, CompetitorInfo] = {}
        self._min_confidence = min_confidence

        logger.info(
            "OpportunityDetector baslatildi (min_confidence=%.2f)",
            min_confidence,
        )

    def add_signal(self, source: str, content: str, strength: float = 0.5, signal_type: str = "") -> MarketSignal:
        """Pazar sinyali ekler.

        Args:
            source: Sinyal kaynagi.
            content: Sinyal icerigi.
            strength: Sinyal gucu (0.0-1.0).
            signal_type: Sinyal tipi.

        Returns:
            Olusturulan MarketSignal nesnesi.
        """
        signal = MarketSignal(
            source=source,
            content=content,
            strength=max(0.0, min(1.0, strength)),
            signal_type=signal_type,
        )
        self._signals.append(signal)
        logger.info("Pazar sinyali eklendi: %s (guc=%.2f)", source, signal.strength)
        return signal

    def scan_market(self, domain: str, signals: list[MarketSignal] | None = None) -> list[Opportunity]:
        """Pazar taramasi yapar ve firsatlari tespit eder.

        Verilen sinyalleri analiz ederek potansiyel firsatlari cikarir.
        Guclu sinyaller (>0.7) dogrudan firsat olarak isaretlenir.

        Args:
            domain: Taranacak alan (ornek: 'kozmetik', 'medikal turizm').
            signals: Analiz edilecek sinyaller (None ise mevcut sinyalleri kullanir).

        Returns:
            Tespit edilen firsatlarin listesi.
        """
        source_signals = signals if signals is not None else self._signals
        found: list[Opportunity] = []

        for signal in source_signals:
            if signal.strength >= self._min_confidence:
                opp = Opportunity(
                    title=f"{domain} firsati: {signal.content[:50]}",
                    description=signal.content,
                    opportunity_type=OpportunityType.MARKET_GAP,
                    confidence=signal.strength,
                    potential_value=signal.strength * 10000,
                    signals=[signal],
                    tags=[domain, signal.signal_type] if signal.signal_type else [domain],
                )
                self._opportunities[opp.id] = opp
                found.append(opp)

        logger.info("Pazar taramasi tamamlandi: %s, %d firsat bulundu", domain, len(found))
        return found

    def analyze_trends(self, data_points: list[float], keyword: str, period_days: int = 30) -> TrendData:
        """Trend analizi yapar.

        Veri noktalarindan trend yonu ve momentumunu hesaplar.
        Pozitif momentum yukselis, negatif momentum dusus gosterir.

        Args:
            data_points: Zaman serisindeki veri noktalari.
            keyword: Anahtar kelime.
            period_days: Analiz suresi (gun).

        Returns:
            Trend analiz sonucu.
        """
        if len(data_points) < 2:
            trend = TrendData(
                keyword=keyword,
                direction="stable",
                momentum=0.0,
                data_points=len(data_points),
                period_days=period_days,
            )
            self._trends[keyword] = trend
            return trend

        # Basit dogrusal trend hesaplama
        n = len(data_points)
        x_mean = (n - 1) / 2.0
        y_mean = sum(data_points) / n

        numerator = sum((i - x_mean) * (y - y_mean) for i, y in enumerate(data_points))
        denominator = sum((i - x_mean) ** 2 for i in range(n))

        slope = numerator / denominator if denominator != 0 else 0.0

        # Momentumu normalize et (sigmoid)
        raw_momentum = slope / (abs(y_mean) + 1e-9)
        momentum = 2.0 / (1.0 + math.exp(-5.0 * raw_momentum)) - 1.0
        normalized_momentum = max(0.0, min(1.0, abs(momentum)))

        if slope > 0.01:
            direction = "positive"
        elif slope < -0.01:
            direction = "negative"
        else:
            direction = "stable"

        trend = TrendData(
            keyword=keyword,
            direction=direction,
            momentum=normalized_momentum,
            data_points=n,
            period_days=period_days,
        )
        self._trends[keyword] = trend
        logger.info("Trend analizi: %s -> %s (momentum=%.2f)", keyword, direction, normalized_momentum)
        return trend

    def add_competitor(self, name: str, strengths: list[str] | None = None, weaknesses: list[str] | None = None, market_share: float = 0.0, threat_level: float = 0.3) -> CompetitorInfo:
        """Rakip bilgisi ekler.

        Args:
            name: Rakip adi.
            strengths: Guclu yonleri.
            weaknesses: Zayif yonleri.
            market_share: Pazar payi (0.0-1.0).
            threat_level: Tehdit seviyesi (0.0-1.0).

        Returns:
            Olusturulan CompetitorInfo nesnesi.
        """
        competitor = CompetitorInfo(
            name=name,
            strengths=strengths or [],
            weaknesses=weaknesses or [],
            market_share=max(0.0, min(1.0, market_share)),
            threat_level=max(0.0, min(1.0, threat_level)),
        )
        self._competitors[competitor.id] = competitor
        logger.info("Rakip eklendi: %s (tehdit=%.2f)", name, competitor.threat_level)
        return competitor

    def monitor_competitors(self) -> list[Opportunity]:
        """Rakip zayifliklarindan firsat cikarir.

        Rakiplerin zayif yonlerini analiz ederek
        potansiyel firsatlara donusturur.

        Returns:
            Rakip zayifliklarindan cikan firsatlar.
        """
        found: list[Opportunity] = []

        for competitor in self._competitors.values():
            for weakness in competitor.weaknesses:
                confidence = competitor.threat_level * 0.8
                if confidence >= self._min_confidence:
                    opp = Opportunity(
                        title=f"Rakip zayifligi: {competitor.name} - {weakness[:40]}",
                        description=f"{competitor.name} zayif yonu: {weakness}",
                        opportunity_type=OpportunityType.COMPETITOR_WEAKNESS,
                        confidence=confidence,
                        potential_value=competitor.market_share * 50000,
                        risk_level=competitor.threat_level,
                        tags=["competitor", competitor.name],
                    )
                    self._opportunities[opp.id] = opp
                    found.append(opp)

        logger.info("Rakip izleme tamamlandi: %d firsat bulundu", len(found))
        return found

    def identify_gaps(self, market_needs: list[str], current_offerings: list[str]) -> list[Opportunity]:
        """Pazar bosluglarini tespit eder.

        Pazar ihtiyaclari ile mevcut teklifler arasindaki
        bosluklari bulur ve firsat olarak kaydeder.

        Args:
            market_needs: Pazar ihtiyaclari listesi.
            current_offerings: Mevcut teklifler listesi.

        Returns:
            Bosluk firsatlari listesi.
        """
        offerings_lower = {o.lower() for o in current_offerings}
        found: list[Opportunity] = []

        for need in market_needs:
            if need.lower() not in offerings_lower:
                opp = Opportunity(
                    title=f"Pazar boslugu: {need}",
                    description=f"Karsilanmamis ihtiyac: {need}",
                    opportunity_type=OpportunityType.MARKET_GAP,
                    confidence=0.7,
                    potential_value=5000.0,
                    tags=["gap", "unmet_need"],
                )
                self._opportunities[opp.id] = opp
                found.append(opp)

        logger.info("Bosluk tespiti: %d ihtiyac, %d mevcut, %d bosluk", len(market_needs), len(current_offerings), len(found))
        return found

    def score_lead(self, opportunity_id: str) -> float:
        """Firsat icin lead puani hesaplar.

        Firsat tipine, guven derecesine, potansiyel degere
        ve risk seviyesine gore 0-1 arasi puan hesaplar.

        Args:
            opportunity_id: Puanlanacak firsat ID.

        Returns:
            Lead puani (0.0-1.0). Firsat bulunamazsa 0.0.
        """
        opp = self._opportunities.get(opportunity_id)
        if not opp:
            return 0.0

        type_weight = _OPPORTUNITY_TYPE_WEIGHTS.get(opp.opportunity_type, 0.5)
        value_factor = min(1.0, opp.potential_value / 50000)
        risk_penalty = 1.0 - (opp.risk_level * 0.5)

        score = (opp.confidence * 0.3 + type_weight * 0.2 + value_factor * 0.3 + risk_penalty * 0.2)
        score = max(0.0, min(1.0, score))

        opp.lead_score = score
        logger.info("Lead puanlama: %s -> %.2f", opp.title[:30], score)
        return score

    def get_opportunity(self, opportunity_id: str) -> Opportunity | None:
        """Firsat getirir.

        Args:
            opportunity_id: Firsat ID.

        Returns:
            Opportunity nesnesi veya None.
        """
        return self._opportunities.get(opportunity_id)

    def get_top_opportunities(self, limit: int = 5) -> list[Opportunity]:
        """En yuksek puanli firsatlari getirir.

        Args:
            limit: Maksimum sonuc sayisi.

        Returns:
            Lead puanina gore siralanmis firsatlar.
        """
        scored = sorted(
            self._opportunities.values(),
            key=lambda o: o.lead_score,
            reverse=True,
        )
        return scored[:limit]

    def expire_old_opportunities(self, now: datetime | None = None) -> int:
        """Suresi dolmus firsatlari isaretler.

        Args:
            now: Referans zaman (None ise utcnow).

        Returns:
            Suresi dolmus firsat sayisi.
        """
        now = now or datetime.now(timezone.utc)
        expired_count = 0

        for opp in self._opportunities.values():
            if opp.expires_at and opp.expires_at <= now and opp.status == OpportunityStatus.DETECTED:
                opp.status = OpportunityStatus.EXPIRED
                expired_count += 1

        if expired_count:
            logger.info("%d firsat suresi doldu", expired_count)
        return expired_count

    @property
    def opportunity_count(self) -> int:
        """Toplam firsat sayisi."""
        return len(self._opportunities)

    @property
    def signal_count(self) -> int:
        """Toplam sinyal sayisi."""
        return len(self._signals)

    @property
    def competitor_count(self) -> int:
        """Toplam rakip sayisi."""
        return len(self._competitors)
