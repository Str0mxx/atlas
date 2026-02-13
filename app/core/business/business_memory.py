"""ATLAS Is Hafizasi modulu.

Basari oruntuleri, basarisizlik dersleri, pazar bilgisi,
musteri ic goruleri ve rekabet istihbarati yonetimi.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from app.models.business import (
    BusinessMemoryStats,
    CompetitorInfo,
    CustomerInsight,
    FailureLesson,
    MarketKnowledge,
    SuccessPattern,
)

logger = logging.getLogger(__name__)


class BusinessMemory:
    """Is hafizasi sistemi.

    Basari oruntuleri, basarisizlik dersleri, pazar bilgileri,
    musteri ic goruleri ve rekabet istihbaratini yonetir.
    Gecmis deneyimlerden ogrenme icin merkezi hafiza.

    Attributes:
        _success_patterns: Basari oruntuleri (id -> SuccessPattern).
        _failure_lessons: Basarisizlik dersleri (id -> FailureLesson).
        _market_knowledge: Pazar bilgileri (id -> MarketKnowledge).
        _customer_insights: Musteri ic goruleri (id -> CustomerInsight).
        _competitors: Rekabet istihbarati (id -> CompetitorInfo).
    """

    def __init__(self) -> None:
        """Is hafizasi sistemini baslatir."""
        self._success_patterns: dict[str, SuccessPattern] = {}
        self._failure_lessons: dict[str, FailureLesson] = {}
        self._market_knowledge: dict[str, MarketKnowledge] = {}
        self._customer_insights: dict[str, CustomerInsight] = {}
        self._competitors: dict[str, CompetitorInfo] = {}

        logger.info("BusinessMemory baslatildi")

    # === Basari Oruntuleri ===

    def record_success(
        self,
        pattern_name: str,
        description: str = "",
        conditions: dict[str, Any] | None = None,
        expected_outcome: str = "",
        confidence: float = 0.5,
    ) -> SuccessPattern:
        """Basari oruntusunu kaydeder.

        Args:
            pattern_name: Oruntu adi.
            description: Aciklama.
            conditions: Kosullar.
            expected_outcome: Beklenen sonuc.
            confidence: Guven derecesi (0.0-1.0).

        Returns:
            Olusturulan SuccessPattern nesnesi.
        """
        pattern = SuccessPattern(
            pattern_name=pattern_name,
            description=description,
            conditions=conditions or {},
            expected_outcome=expected_outcome,
            confidence=max(0.0, min(1.0, confidence)),
        )
        self._success_patterns[pattern.id] = pattern
        logger.info("Basari oruntuleri kaydedildi: %s (guven=%.2f)", pattern_name, pattern.confidence)
        return pattern

    def find_success_patterns(self, min_confidence: float = 0.5) -> list[SuccessPattern]:
        """Yuksek guvenli basari oruntuleri getirir.

        Args:
            min_confidence: Minimum guven esigi.

        Returns:
            Guven degerine gore siralanmis oruntler.
        """
        patterns = [
            p for p in self._success_patterns.values()
            if p.confidence >= min_confidence
        ]
        patterns.sort(key=lambda p: p.confidence, reverse=True)
        return patterns

    def use_pattern(self, pattern_id: str) -> bool:
        """Basari oruntusunu kullanir (kullanim sayisini arttirir).

        Args:
            pattern_id: Oruntu ID.

        Returns:
            Basarili mi.
        """
        pattern = self._success_patterns.get(pattern_id)
        if not pattern:
            return False

        pattern.usage_count += 1
        pattern.last_used = datetime.now(timezone.utc)
        return True

    # === Basarisizlik Dersleri ===

    def record_failure(
        self,
        title: str,
        what_happened: str = "",
        root_cause: str = "",
        what_to_avoid: str = "",
        severity: float = 0.5,
    ) -> FailureLesson:
        """Basarisizlik dersini kaydeder.

        Args:
            title: Ders basligi.
            what_happened: Ne oldugu.
            root_cause: Kok neden.
            what_to_avoid: Kacinilmasi gerekenler.
            severity: Ciddiyet (0.0-1.0).

        Returns:
            Olusturulan FailureLesson nesnesi.
        """
        lesson = FailureLesson(
            title=title,
            what_happened=what_happened,
            root_cause=root_cause,
            what_to_avoid=what_to_avoid,
            severity=max(0.0, min(1.0, severity)),
        )
        self._failure_lessons[lesson.id] = lesson
        logger.info("Basarisizlik dersi kaydedildi: %s (ciddiyet=%.2f)", title, lesson.severity)
        return lesson

    def get_failure_lessons(self, min_severity: float = 0.0) -> list[FailureLesson]:
        """Basarisizlik derslerini getirir.

        Args:
            min_severity: Minimum ciddiyet esigi.

        Returns:
            Ciddiyet degerine gore siralanmis dersler.
        """
        lessons = [
            l for l in self._failure_lessons.values()
            if l.severity >= min_severity
        ]
        lessons.sort(key=lambda l: l.severity, reverse=True)
        return lessons

    # === Pazar Bilgisi ===

    def store_market_knowledge(
        self,
        domain: str,
        topic: str,
        content: str = "",
        reliability: float = 0.5,
        source: str = "",
    ) -> MarketKnowledge:
        """Pazar bilgisi depolar.

        Args:
            domain: Alan.
            topic: Konu.
            content: Icerik.
            reliability: Guvenilirlik (0.0-1.0).
            source: Kaynak.

        Returns:
            Olusturulan MarketKnowledge nesnesi.
        """
        knowledge = MarketKnowledge(
            domain=domain,
            topic=topic,
            content=content,
            reliability=max(0.0, min(1.0, reliability)),
            source=source,
        )
        self._market_knowledge[knowledge.id] = knowledge
        logger.info("Pazar bilgisi depolandi: %s / %s", domain, topic)
        return knowledge

    def query_market(self, domain: str = "", min_reliability: float = 0.0) -> list[MarketKnowledge]:
        """Pazar bilgisi sorgular.

        Args:
            domain: Filtrelenecek alan (bos ise hepsi).
            min_reliability: Minimum guvenilirlik.

        Returns:
            Eslesen pazar bilgileri.
        """
        results = []
        for mk in self._market_knowledge.values():
            if domain and mk.domain != domain:
                continue
            if mk.reliability >= min_reliability:
                results.append(mk)
        results.sort(key=lambda m: m.reliability, reverse=True)
        return results

    # === Musteri Ic Goruleri ===

    def record_customer_insight(
        self,
        segment: str,
        insight: str,
        evidence: list[str] | None = None,
        impact_score: float = 0.5,
    ) -> CustomerInsight:
        """Musteri ic gorusu kaydeder.

        Args:
            segment: Musteri segmenti.
            insight: Ic goru.
            evidence: Kanitlar.
            impact_score: Etki puani (0.0-1.0).

        Returns:
            Olusturulan CustomerInsight nesnesi.
        """
        ci = CustomerInsight(
            segment=segment,
            insight=insight,
            evidence=evidence or [],
            impact_score=max(0.0, min(1.0, impact_score)),
        )
        self._customer_insights[ci.id] = ci
        logger.info("Musteri ic gorusu kaydedildi: %s (segment=%s)", insight[:30], segment)
        return ci

    def get_customer_insights(self, segment: str = "") -> list[CustomerInsight]:
        """Musteri ic goruleri getirir.

        Args:
            segment: Filtrelenecek segment (bos ise hepsi).

        Returns:
            Etki puanina gore siralanmis ic goruler.
        """
        results = []
        for ci in self._customer_insights.values():
            if segment and ci.segment != segment:
                continue
            results.append(ci)
        results.sort(key=lambda c: c.impact_score, reverse=True)
        return results

    # === Rekabet Istihbarati ===

    def record_competitor(
        self,
        name: str,
        strengths: list[str] | None = None,
        weaknesses: list[str] | None = None,
        market_share: float = 0.0,
        threat_level: float = 0.3,
    ) -> CompetitorInfo:
        """Rakip bilgisi kaydeder.

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
        logger.info("Rakip kaydedildi: %s (tehdit=%.2f)", name, competitor.threat_level)
        return competitor

    def get_competitors(self, min_threat: float = 0.0) -> list[CompetitorInfo]:
        """Rakip bilgilerini getirir.

        Args:
            min_threat: Minimum tehdit seviyesi.

        Returns:
            Tehdit seviyesine gore siralanmis rakipler.
        """
        comps = [c for c in self._competitors.values() if c.threat_level >= min_threat]
        comps.sort(key=lambda c: c.threat_level, reverse=True)
        return comps

    # === Istatistikler ===

    def get_stats(self) -> BusinessMemoryStats:
        """Is hafizasi istatistiklerini getirir.

        Returns:
            BusinessMemoryStats nesnesi.
        """
        patterns = list(self._success_patterns.values())
        avg_confidence = (
            sum(p.confidence for p in patterns) / len(patterns)
            if patterns else 0.0
        )

        return BusinessMemoryStats(
            total_success_patterns=len(self._success_patterns),
            total_failure_lessons=len(self._failure_lessons),
            total_market_knowledge=len(self._market_knowledge),
            total_customer_insights=len(self._customer_insights),
            total_competitor_records=len(self._competitors),
            avg_pattern_confidence=avg_confidence,
        )

    def search(self, query: str) -> list[dict[str, Any]]:
        """Tum hafiza kategorilerinde arama yapar.

        Basit metin eslestirmesi ile tum kategorilerdeki
        kayitlari arar.

        Args:
            query: Arama metni.

        Returns:
            Eslesen kayitlar (tip, id, baslik bilgisi).
        """
        query_lower = query.lower()
        results: list[dict[str, Any]] = []

        for p in self._success_patterns.values():
            if query_lower in p.pattern_name.lower() or query_lower in p.description.lower():
                results.append({"type": "success_pattern", "id": p.id, "title": p.pattern_name})

        for l in self._failure_lessons.values():
            if query_lower in l.title.lower() or query_lower in l.what_happened.lower():
                results.append({"type": "failure_lesson", "id": l.id, "title": l.title})

        for m in self._market_knowledge.values():
            if query_lower in m.domain.lower() or query_lower in m.topic.lower() or query_lower in m.content.lower():
                results.append({"type": "market_knowledge", "id": m.id, "title": m.topic})

        for c in self._customer_insights.values():
            if query_lower in c.insight.lower() or query_lower in c.segment.lower():
                results.append({"type": "customer_insight", "id": c.id, "title": c.insight[:50]})

        for comp in self._competitors.values():
            if query_lower in comp.name.lower():
                results.append({"type": "competitor", "id": comp.id, "title": comp.name})

        return results
