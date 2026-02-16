"""
Müşteri segmentasyonu modülü.

Müşterileri davranış, değer ve ihtiyaçlarına
göre segmentlere ayırır. Segment önceliklendirme
ve LTV/CAC analizi yapar.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class BizCustomerSegmenter:
    """
    Müşteri segmentasyon yöneticisi.

    Müşteri verilerini analiz ederek anlamlı
    segmentler oluşturur, değer analizi yapar
    ve segment önceliklendirmesi sağlar.
    """

    def __init__(self) -> None:
        """Segmentasyon yöneticisini başlatır."""
        self._segments: list[dict] = []
        self._stats: dict = {
            "segments_created": 0,
        }

    @property
    def segment_count(self) -> int:
        """Oluşturulan segment sayısı."""
        return self._stats["segments_created"]

    def identify_segments(
        self,
        customers: (
            list[dict[str, Any]] | None
        ) = None,
    ) -> dict[str, Any]:
        """
        Müşterileri segmentlere ayırır.

        Args:
            customers: Müşteri listesi.

        Returns:
            Segment tanımlama sonucu.
        """
        try:
            if customers is None:
                customers = []
            segments: dict[str, int] = {}
            for customer in customers:
                ctype = customer.get(
                    "type", "unknown"
                )
                segments[ctype] = (
                    segments.get(ctype, 0) + 1
                )
            self._stats[
                "segments_created"
            ] += len(segments)
            return {
                "segments": segments,
                "segment_count": len(segments),
                "total_customers": len(
                    customers
                ),
                "identified": True,
            }
        except Exception as e:
            logger.error(
                f"Segment tanımlama hatası: {e}"
            )
            return {
                "segments": {},
                "segment_count": 0,
                "total_customers": 0,
                "identified": False,
            }

    def analyze_value(
        self,
        segment: str = "default",
        revenue: float = 0.0,
        cost: float = 0.0,
    ) -> dict[str, Any]:
        """
        Segment değer analizi yapar.

        Args:
            segment: Segment adı.
            revenue: Aylık gelir.
            cost: Müşteri edinme maliyeti.

        Returns:
            Değer analiz sonucu.
        """
        try:
            ltv = round(revenue * 12, 2)
            cac = round(cost, 2)
            ratio = round(
                ltv / max(cac, 1), 2
            )
            if ratio >= 3:
                grade = "excellent"
            elif ratio >= 2:
                grade = "good"
            else:
                grade = "poor"
            return {
                "segment": segment,
                "ltv": ltv,
                "cac": cac,
                "ltv_cac_ratio": ratio,
                "grade": grade,
                "analyzed": True,
            }
        except Exception as e:
            logger.error(
                f"Değer analiz hatası: {e}"
            )
            return {
                "segment": segment,
                "ltv": 0.0,
                "cac": 0.0,
                "ltv_cac_ratio": 0.0,
                "grade": "poor",
                "analyzed": False,
            }

    def detect_patterns(
        self,
        behaviors: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Davranış kalıplarını tespit eder.

        Args:
            behaviors: Davranış listesi.

        Returns:
            Kalıp tespit sonucu.
        """
        try:
            if behaviors is None:
                behaviors = []
            frequency = len(behaviors)
            if frequency >= 10:
                pattern = "highly_active"
            elif frequency >= 5:
                pattern = "active"
            elif frequency >= 1:
                pattern = "passive"
            else:
                pattern = "inactive"
            return {
                "behavior_count": frequency,
                "pattern": pattern,
                "detected": True,
            }
        except Exception as e:
            logger.error(
                f"Kalıp tespit hatası: {e}"
            )
            return {
                "behavior_count": 0,
                "pattern": "inactive",
                "detected": False,
            }

    def map_needs(
        self,
        segment: str = "default",
        needs: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Segment ihtiyaç haritası çıkarır.

        Args:
            segment: Segment adı.
            needs: İhtiyaç listesi.

        Returns:
            İhtiyaç haritalama sonucu.
        """
        try:
            if needs is None:
                needs = []
            priority_needs = needs[:3]
            coverage = min(
                len(needs) * 20, 100
            )
            return {
                "segment": segment,
                "needs": needs,
                "need_count": len(needs),
                "priority_needs": (
                    priority_needs
                ),
                "coverage_score": coverage,
                "mapped": True,
            }
        except Exception as e:
            logger.error(
                f"İhtiyaç haritalama "
                f"hatası: {e}"
            )
            return {
                "segment": segment,
                "needs": [],
                "need_count": 0,
                "priority_needs": [],
                "coverage_score": 0,
                "mapped": False,
            }

    def prioritize_segments(
        self,
        segments: (
            list[dict[str, Any]] | None
        ) = None,
    ) -> dict[str, Any]:
        """
        Segmentleri önceliklendirir.

        Args:
            segments: Segment listesi.

        Returns:
            Önceliklendirme sonucu.
        """
        try:
            if segments is None:
                segments = []
            sorted_list = sorted(
                segments,
                key=lambda s: s.get(
                    "value", 0
                ),
                reverse=True,
            )
            ranked = [
                {
                    "rank": i + 1,
                    "segment": s.get(
                        "name", "unknown"
                    ),
                    "value": s.get(
                        "value", 0
                    ),
                }
                for i, s in enumerate(
                    sorted_list
                )
            ]
            top = (
                ranked[0]["segment"]
                if ranked
                else "none"
            )
            return {
                "ranked": ranked,
                "top_segment": top,
                "total": len(ranked),
                "prioritized": True,
            }
        except Exception as e:
            logger.error(
                f"Önceliklendirme "
                f"hatası: {e}"
            )
            return {
                "ranked": [],
                "top_segment": "none",
                "total": 0,
                "prioritized": False,
            }
