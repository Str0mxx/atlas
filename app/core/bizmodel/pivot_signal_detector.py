"""
Pivot sinyal tespitçisi modülü.

Uyarı sinyallerini tespit eder, metrik
analizi yapar, pazar geri bildirimi değerlendirir,
trend tespiti ve pivot önerileri sunar.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class PivotSignalDetector:
    """Pivot sinyal tespitçisi.

    Pazar sinyallerini analiz eder,
    metrik değişimlerini izler ve
    pivot ihtiyacını tespit eder.

    Attributes:
        _signals: Sinyal kayıtları.
        _stats: İstatistikler.
    """

    def __init__(self) -> None:
        """Tespitçiyi başlatır."""
        self._signals: list[dict] = []
        self._stats: dict[str, int] = {
            "detections_run": 0,
        }
        logger.info(
            "PivotSignalDetector "
            "baslatildi"
        )

    @property
    def detection_count(self) -> int:
        """Tespit sayısı."""
        return self._stats[
            "detections_run"
        ]

    def detect_warnings(
        self,
        metrics: dict[str, float]
        | None = None,
    ) -> dict[str, Any]:
        """Uyarı sinyallerini tespit eder.

        Args:
            metrics: Metrik değerleri.

        Returns:
            Uyarı tespiti sonucu.
        """
        try:
            if metrics is None:
                metrics = {}

            warnings: list[str] = []

            churn = metrics.get(
                "churn_rate", 0
            )
            if churn > 10:
                warnings.append(
                    "high_churn"
                )

            growth = metrics.get(
                "growth_rate", 0
            )
            if growth < -5:
                warnings.append(
                    "negative_growth"
                )

            satisfaction = metrics.get(
                "satisfaction", 100
            )
            if satisfaction < 50:
                warnings.append(
                    "low_satisfaction"
                )

            burn = metrics.get(
                "burn_rate", 0
            )
            if burn > 80:
                warnings.append(
                    "high_burn_rate"
                )

            if len(warnings) >= 3:
                severity = "critical"
            elif len(warnings) >= 1:
                severity = "warning"
            else:
                severity = "healthy"

            self._stats[
                "detections_run"
            ] += 1

            result = {
                "warnings": warnings,
                "warning_count": len(
                    warnings
                ),
                "severity": severity,
                "detected": True,
            }

            logger.info(
                f"Uyari tespiti: "
                f"{len(warnings)} uyari, "
                f"ciddiyet={severity}"
            )

            return result

        except Exception as e:
            logger.error(
                f"Uyari tespiti "
                f"hatasi: {e}"
            )
            return {
                "warnings": [],
                "warning_count": 0,
                "severity": "unknown",
                "detected": False,
                "error": str(e),
            }

    def analyze_metrics(
        self,
        current: dict[str, float]
        | None = None,
        previous: dict[str, float]
        | None = None,
    ) -> dict[str, Any]:
        """Metrik analizi yapar.

        Args:
            current: Mevcut metrikler.
            previous: Önceki metrikler.

        Returns:
            Metrik analizi sonucu.
        """
        try:
            if current is None:
                current = {}
            if previous is None:
                previous = {}

            changes: dict[str, float] = {}
            for key in current:
                cur = current.get(key, 0)
                prev = previous.get(key, 0)
                diff = round(
                    cur - prev, 2
                )
                changes[key] = diff

            declining = sum(
                1
                for v in changes.values()
                if v < 0
            )
            improving = sum(
                1
                for v in changes.values()
                if v > 0
            )

            if declining > improving:
                trend = "declining"
            elif improving > declining:
                trend = "improving"
            else:
                trend = "stable"

            self._stats[
                "detections_run"
            ] += 1

            result = {
                "changes": changes,
                "metric_count": len(
                    changes
                ),
                "declining": declining,
                "improving": improving,
                "trend": trend,
                "analyzed": True,
            }

            logger.info(
                f"Metrik analizi: "
                f"trend={trend}, "
                f"{len(changes)} metrik"
            )

            return result

        except Exception as e:
            logger.error(
                f"Metrik analizi "
                f"hatasi: {e}"
            )
            return {
                "changes": {},
                "metric_count": 0,
                "declining": 0,
                "improving": 0,
                "trend": "unknown",
                "analyzed": False,
                "error": str(e),
            }

    def evaluate_market_feedback(
        self,
        feedback: list[str]
        | None = None,
    ) -> dict[str, Any]:
        """Pazar geri bildirimi değerlendirir.

        Args:
            feedback: Geri bildirim listesi.

        Returns:
            Değerlendirme sonucu.
        """
        try:
            if feedback is None:
                feedback = []

            negative_keywords = [
                "bad",
                "poor",
                "expensive",
                "slow",
                "difficult",
            ]

            negative_count = 0
            for fb in feedback:
                low = fb.lower()
                for kw in negative_keywords:
                    if kw in low:
                        negative_count += 1
                        break

            total = len(feedback)
            neg_pct = round(
                (
                    negative_count
                    / max(total, 1)
                )
                * 100,
                1,
            )

            if neg_pct >= 60:
                sentiment = "negative"
            elif neg_pct >= 30:
                sentiment = "mixed"
            else:
                sentiment = "positive"

            self._stats[
                "detections_run"
            ] += 1

            result = {
                "total_feedback": total,
                "negative_count": (
                    negative_count
                ),
                "negative_pct": neg_pct,
                "sentiment": sentiment,
                "evaluated": True,
            }

            logger.info(
                f"Pazar degerlendirme: "
                f"duygu={sentiment}, "
                f"negatif={neg_pct}%"
            )

            return result

        except Exception as e:
            logger.error(
                f"Pazar degerlendirme "
                f"hatasi: {e}"
            )
            return {
                "total_feedback": 0,
                "negative_count": 0,
                "negative_pct": 0.0,
                "sentiment": "unknown",
                "evaluated": False,
                "error": str(e),
            }

    def detect_trends(
        self,
        data_points: list[float]
        | None = None,
    ) -> dict[str, Any]:
        """Trend tespiti yapar.

        Args:
            data_points: Veri noktaları.

        Returns:
            Trend tespiti sonucu.
        """
        try:
            if data_points is None:
                data_points = []

            if len(data_points) < 2:
                return {
                    "trend": "insufficient_data",
                    "data_points": len(
                        data_points
                    ),
                    "detected": True,
                }

            first_half = data_points[
                : len(data_points) // 2
            ]
            second_half = data_points[
                len(data_points) // 2 :
            ]

            avg_first = sum(first_half) / len(
                first_half
            )
            avg_second = sum(
                second_half
            ) / len(second_half)

            change = round(
                avg_second - avg_first, 2
            )
            change_pct = round(
                (
                    change
                    / max(
                        abs(avg_first), 1
                    )
                )
                * 100,
                1,
            )

            if change_pct > 10:
                trend = "upward"
            elif change_pct < -10:
                trend = "downward"
            else:
                trend = "flat"

            self._stats[
                "detections_run"
            ] += 1

            result = {
                "data_points": len(
                    data_points
                ),
                "change": change,
                "change_pct": change_pct,
                "trend": trend,
                "detected": True,
            }

            logger.info(
                f"Trend tespiti: "
                f"trend={trend}, "
                f"degisim={change_pct}%"
            )

            return result

        except Exception as e:
            logger.error(
                f"Trend tespiti "
                f"hatasi: {e}"
            )
            return {
                "data_points": 0,
                "change": 0.0,
                "change_pct": 0.0,
                "trend": "unknown",
                "detected": False,
                "error": str(e),
            }

    def recommend_pivot(
        self,
        warning_count: int = 0,
        trend: str = "stable",
        satisfaction: float = 50.0,
    ) -> dict[str, Any]:
        """Pivot önerisi yapar.

        Args:
            warning_count: Uyarı sayısı.
            trend: Mevcut trend.
            satisfaction: Memnuniyet skoru.

        Returns:
            Pivot önerisi.
        """
        try:
            reasons: list[str] = []

            if warning_count >= 3:
                reasons.append(
                    "multiple_warnings"
                )
            if trend == "declining":
                reasons.append(
                    "declining_trend"
                )
            if satisfaction < 30:
                reasons.append(
                    "very_low_satisfaction"
                )

            if len(reasons) >= 2:
                recommendation = (
                    "pivot_recommended"
                )
                urgency = "high"
            elif len(reasons) == 1:
                recommendation = (
                    "consider_pivot"
                )
                urgency = "medium"
            else:
                recommendation = (
                    "stay_the_course"
                )
                urgency = "low"

            self._stats[
                "detections_run"
            ] += 1

            result = {
                "reasons": reasons,
                "reason_count": len(
                    reasons
                ),
                "recommendation": (
                    recommendation
                ),
                "urgency": urgency,
                "recommended": True,
            }

            logger.info(
                f"Pivot onerisi: "
                f"{recommendation}, "
                f"aciliyet={urgency}"
            )

            return result

        except Exception as e:
            logger.error(
                f"Pivot onerisi "
                f"hatasi: {e}"
            )
            return {
                "reasons": [],
                "reason_count": 0,
                "recommendation": "unknown",
                "urgency": "unknown",
                "recommended": False,
                "error": str(e),
            }
