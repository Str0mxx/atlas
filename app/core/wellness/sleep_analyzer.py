"""
Uyku analiz modülü.

Uyku takibi, patern analizi, kalite puanlama,
öneriler ve trend tespiti.
"""

import logging
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class SleepAnalyzer:
    """Uyku analiz motoru.

    Attributes:
        _records: Uyku kayıtları.
        _stats: İstatistikler.
    """

    def __init__(self) -> None:
        """Analiz motorunu başlatır."""
        self._records: list[dict] = []
        self._stats: dict[str, int] = {
            "records_logged": 0,
        }
        logger.info(
            "SleepAnalyzer baslatildi"
        )

    @property
    def record_count(self) -> int:
        """Kayıt sayısı."""
        return len(self._records)

    def log_sleep(
        self,
        hours: float = 7.0,
        deep_sleep_pct: float = 20.0,
        interruptions: int = 0,
    ) -> dict[str, Any]:
        """Uyku kaydı ekler.

        Args:
            hours: Uyku süresi (saat).
            deep_sleep_pct: Derin uyku yüzdesi.
            interruptions: Kesinti sayısı.

        Returns:
            Kayıt bilgisi.
        """
        try:
            sid = f"slp_{uuid4()!s:.8}"

            score = self._calculate_score(
                hours, deep_sleep_pct, interruptions
            )

            if score >= 85:
                quality = "excellent"
            elif score >= 70:
                quality = "good"
            elif score >= 50:
                quality = "fair"
            elif score >= 30:
                quality = "poor"
            else:
                quality = "very_poor"

            record = {
                "sleep_id": sid,
                "hours": hours,
                "deep_sleep_pct": deep_sleep_pct,
                "interruptions": interruptions,
                "score": score,
                "quality": quality,
            }
            self._records.append(record)
            self._stats["records_logged"] += 1

            return {
                "sleep_id": sid,
                "hours": hours,
                "deep_sleep_pct": deep_sleep_pct,
                "interruptions": interruptions,
                "score": score,
                "quality": quality,
                "logged": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "logged": False,
                "error": str(e),
            }

    def _calculate_score(
        self,
        hours: float,
        deep_pct: float,
        interruptions: int,
    ) -> float:
        """Uyku puanı hesaplar.

        Args:
            hours: Uyku süresi.
            deep_pct: Derin uyku yüzdesi.
            interruptions: Kesinti sayısı.

        Returns:
            Uyku puanı (0-100).
        """
        duration_score = min(
            hours / 8.0 * 40, 40.0
        )
        deep_score = min(
            deep_pct / 25.0 * 30, 30.0
        )
        interrupt_penalty = min(
            interruptions * 10, 30
        )
        continuity_score = 30.0 - interrupt_penalty

        total = (
            duration_score
            + deep_score
            + continuity_score
        )
        return round(
            max(min(total, 100.0), 0.0), 1
        )

    def analyze_patterns(
        self,
    ) -> dict[str, Any]:
        """Uyku paternlerini analiz eder.

        Returns:
            Patern analizi.
        """
        try:
            if not self._records:
                return {
                    "analyzed": True,
                    "pattern": "no_data",
                    "records": 0,
                }

            avg_hours = sum(
                r["hours"] for r in self._records
            ) / len(self._records)
            avg_score = sum(
                r["score"] for r in self._records
            ) / len(self._records)
            avg_deep = sum(
                r["deep_sleep_pct"]
                for r in self._records
            ) / len(self._records)

            if avg_hours >= 7 and avg_score >= 70:
                pattern = "healthy"
            elif avg_hours >= 6:
                pattern = "adequate"
            elif avg_hours >= 4:
                pattern = "insufficient"
            else:
                pattern = "critical"

            return {
                "avg_hours": round(
                    avg_hours, 1
                ),
                "avg_score": round(
                    avg_score, 1
                ),
                "avg_deep_pct": round(
                    avg_deep, 1
                ),
                "pattern": pattern,
                "records": len(self._records),
                "analyzed": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "analyzed": False,
                "error": str(e),
            }

    def score_quality(
        self,
        hours: float = 7.0,
        deep_sleep_pct: float = 20.0,
        interruptions: int = 0,
    ) -> dict[str, Any]:
        """Uyku kalitesini puanlar.

        Args:
            hours: Uyku süresi.
            deep_sleep_pct: Derin uyku yüzdesi.
            interruptions: Kesinti sayısı.

        Returns:
            Kalite puanı.
        """
        try:
            score = self._calculate_score(
                hours, deep_sleep_pct, interruptions
            )

            factors = []
            if hours < 6:
                factors.append("short_duration")
            if hours > 9:
                factors.append("oversleeping")
            if deep_sleep_pct < 15:
                factors.append("low_deep_sleep")
            if interruptions > 3:
                factors.append(
                    "frequent_interruptions"
                )

            return {
                "score": score,
                "factors": factors,
                "factor_count": len(factors),
                "scored": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "scored": False,
                "error": str(e),
            }

    def get_recommendations(
        self,
        avg_hours: float = 7.0,
        avg_score: float = 70.0,
    ) -> dict[str, Any]:
        """Uyku önerileri verir.

        Args:
            avg_hours: Ortalama uyku süresi.
            avg_score: Ortalama uyku puanı.

        Returns:
            Öneri listesi.
        """
        try:
            recommendations = []

            if avg_hours < 7:
                recommendations.append(
                    "increase_sleep_duration"
                )
            if avg_hours > 9:
                recommendations.append(
                    "reduce_oversleeping"
                )
            if avg_score < 50:
                recommendations.append(
                    "improve_sleep_hygiene"
                )
            if avg_score < 70:
                recommendations.append(
                    "consistent_schedule"
                )

            recommendations.append(
                "limit_screen_before_bed"
            )

            return {
                "avg_hours": avg_hours,
                "avg_score": avg_score,
                "recommendations": recommendations,
                "count": len(recommendations),
                "generated": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "generated": False,
                "error": str(e),
            }

    def detect_trends(
        self,
    ) -> dict[str, Any]:
        """Uyku trendlerini tespit eder.

        Returns:
            Trend bilgisi.
        """
        try:
            if len(self._records) < 2:
                return {
                    "trend": "insufficient_data",
                    "records": len(
                        self._records
                    ),
                    "detected": True,
                }

            mid = len(self._records) // 2
            first_half = self._records[:mid]
            second_half = self._records[mid:]

            avg_first = sum(
                r["score"] for r in first_half
            ) / len(first_half)
            avg_second = sum(
                r["score"] for r in second_half
            ) / len(second_half)

            change = avg_second - avg_first

            if change > 5:
                trend = "improving"
            elif change < -5:
                trend = "declining"
            else:
                trend = "stable"

            return {
                "trend": trend,
                "score_change": round(change, 1),
                "first_avg": round(
                    avg_first, 1
                ),
                "second_avg": round(
                    avg_second, 1
                ),
                "records": len(self._records),
                "detected": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "detected": False,
                "error": str(e),
            }
