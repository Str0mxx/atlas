"""
Bozulma tahmincisi modülü.

Tahminsel analiz, erken uyarı,
trend projeksiyonu, risk puanlama,
öneri.
"""

import logging
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class HealthDegradationPredictor:
    """Sağlık bozulma tahmincisi.

    Attributes:
        _data_points: Veri noktaları.
        _predictions: Tahminler.
        _stats: İstatistikler.
    """

    def __init__(self) -> None:
        """Tahminci başlatır."""
        self._data_points: list[dict] = []
        self._predictions: list[dict] = []
        self._stats: dict[str, int] = {
            "predictions_made": 0,
            "warnings_issued": 0,
        }
        logger.info(
            "HealthDegradationPredictor "
            "baslatildi"
        )

    @property
    def prediction_count(self) -> int:
        """Tahmin sayısı."""
        return len(self._predictions)

    def add_data_point(
        self,
        system_name: str = "",
        metric: str = "health",
        value: float = 100.0,
        timestamp: str = "",
    ) -> dict[str, Any]:
        """Veri noktası ekler.

        Args:
            system_name: Sistem adı.
            metric: Metrik.
            value: Değer.
            timestamp: Zaman damgası.

        Returns:
            Ekleme bilgisi.
        """
        try:
            self._data_points.append({
                "system_name": system_name,
                "metric": metric,
                "value": value,
                "timestamp": timestamp,
            })

            return {
                "system_name": system_name,
                "metric": metric,
                "value": value,
                "total_points": len(
                    self._data_points
                ),
                "added": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "added": False,
                "error": str(e),
            }

    def predict_degradation(
        self,
        system_name: str = "",
        horizon_periods: int = 5,
    ) -> dict[str, Any]:
        """Bozulma tahmini yapar.

        Args:
            system_name: Sistem adı.
            horizon_periods: Tahmin dönemi.

        Returns:
            Tahmin bilgisi.
        """
        try:
            points = [
                p for p in self._data_points
                if p["system_name"]
                == system_name
            ]

            if len(points) < 3:
                return {
                    "system_name": system_name,
                    "prediction": "insufficient_data",
                    "predicted": True,
                }

            values = [
                p["value"] for p in points
            ]
            n = len(values)

            diffs = [
                values[i] - values[i - 1]
                for i in range(1, n)
            ]
            avg_change = (
                sum(diffs) / len(diffs)
            )

            projected = values[-1]
            projections = []
            for i in range(horizon_periods):
                projected += avg_change
                projections.append(
                    round(projected, 1)
                )

            will_degrade = any(
                p < 50 for p in projections
            )
            will_fail = any(
                p < 20 for p in projections
            )

            if will_fail:
                risk_level = "critical"
            elif will_degrade:
                risk_level = "high"
            elif avg_change < -2:
                risk_level = "medium"
            else:
                risk_level = "low"

            pid = f"pd_{uuid4()!s:.8}"
            prediction = {
                "prediction_id": pid,
                "system_name": system_name,
                "current_value": values[-1],
                "avg_change": round(
                    avg_change, 2
                ),
                "projections": projections,
                "risk_level": risk_level,
            }
            self._predictions.append(
                prediction
            )
            self._stats[
                "predictions_made"
            ] += 1

            return {
                "prediction_id": pid,
                "system_name": system_name,
                "current_value": values[-1],
                "avg_change_per_period": round(
                    avg_change, 2
                ),
                "projections": projections,
                "will_degrade": will_degrade,
                "will_fail": will_fail,
                "risk_level": risk_level,
                "predicted": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "predicted": False,
                "error": str(e),
            }

    def get_early_warnings(
        self,
        threshold: float = 70.0,
    ) -> dict[str, Any]:
        """Erken uyarı getirir.

        Args:
            threshold: Eşik.

        Returns:
            Uyarı bilgisi.
        """
        try:
            groups: dict[str, list] = {}
            for p in self._data_points:
                name = p["system_name"]
                if name not in groups:
                    groups[name] = []
                groups[name].append(
                    p["value"]
                )

            warnings = []
            for name, values in groups.items():
                if len(values) < 2:
                    continue

                current = values[-1]
                recent_avg = (
                    sum(values[-3:])
                    / len(values[-3:])
                )

                declining = all(
                    values[i] >= values[i + 1]
                    for i in range(
                        max(0, len(values) - 3),
                        len(values) - 1,
                    )
                ) if len(values) >= 2 else False

                if (
                    current < threshold
                    or (
                        declining
                        and recent_avg
                        < threshold + 10
                    )
                ):
                    urgency = (
                        "immediate"
                        if current < 30
                        else "soon"
                        if current < 50
                        else "monitor"
                    )

                    warnings.append({
                        "system": name,
                        "current_value": current,
                        "recent_avg": round(
                            recent_avg, 1
                        ),
                        "declining": declining,
                        "urgency": urgency,
                    })

            self._stats[
                "warnings_issued"
            ] += len(warnings)

            return {
                "warnings": warnings,
                "warning_count": len(warnings),
                "threshold": threshold,
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }

    def project_trend(
        self,
        system_name: str = "",
        periods: int = 10,
    ) -> dict[str, Any]:
        """Trend projeksiyonu yapar.

        Args:
            system_name: Sistem adı.
            periods: Dönem sayısı.

        Returns:
            Projeksiyon bilgisi.
        """
        try:
            points = [
                p["value"]
                for p in self._data_points
                if p["system_name"]
                == system_name
            ]

            if len(points) < 2:
                return {
                    "system_name": system_name,
                    "trend": "insufficient_data",
                    "projected": True,
                }

            n = len(points)
            x_mean = (n - 1) / 2.0
            y_mean = sum(points) / n

            num = sum(
                (i - x_mean)
                * (points[i] - y_mean)
                for i in range(n)
            )
            den = sum(
                (i - x_mean) ** 2
                for i in range(n)
            )
            slope = num / den if den != 0 else 0
            intercept = y_mean - slope * x_mean

            projected = [
                round(
                    slope * (n + i) + intercept,
                    1,
                )
                for i in range(periods)
            ]

            if slope > 1:
                direction = "improving"
            elif slope < -1:
                direction = "declining"
            else:
                direction = "stable"

            return {
                "system_name": system_name,
                "current": points[-1],
                "slope": round(slope, 2),
                "direction": direction,
                "projected_values": projected,
                "periods": periods,
                "projected": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "projected": False,
                "error": str(e),
            }

    def score_risk(
        self,
        system_name: str = "",
    ) -> dict[str, Any]:
        """Risk puanlaması yapar.

        Args:
            system_name: Sistem adı.

        Returns:
            Risk puan bilgisi.
        """
        try:
            points = [
                p["value"]
                for p in self._data_points
                if p["system_name"]
                == system_name
            ]

            if not points:
                return {
                    "system_name": system_name,
                    "risk_score": 0.0,
                    "scored": True,
                }

            current = points[-1]
            avg = sum(points) / len(points)

            current_risk = max(
                0, (100 - current) / 100
            )

            decline_risk = 0.0
            if len(points) >= 3:
                recent = points[-3:]
                if all(
                    recent[i] >= recent[i + 1]
                    for i in range(
                        len(recent) - 1
                    )
                ):
                    drop = recent[0] - recent[-1]
                    decline_risk = min(
                        1.0, drop / 50.0
                    )

            volatility_risk = 0.0
            if len(points) >= 3:
                diffs = [
                    abs(
                        points[i]
                        - points[i - 1]
                    )
                    for i in range(
                        1, len(points)
                    )
                ]
                avg_diff = (
                    sum(diffs) / len(diffs)
                )
                volatility_risk = min(
                    1.0, avg_diff / 20.0
                )

            risk_score = round(
                (
                    current_risk * 0.5
                    + decline_risk * 0.3
                    + volatility_risk * 0.2
                )
                * 100,
                1,
            )

            if risk_score >= 70:
                level = "critical"
            elif risk_score >= 40:
                level = "high"
            elif risk_score >= 20:
                level = "medium"
            else:
                level = "low"

            return {
                "system_name": system_name,
                "risk_score": risk_score,
                "risk_level": level,
                "current_value": current,
                "average_value": round(avg, 1),
                "factors": {
                    "current_risk": round(
                        current_risk * 100, 1
                    ),
                    "decline_risk": round(
                        decline_risk * 100, 1
                    ),
                    "volatility_risk": round(
                        volatility_risk * 100,
                        1,
                    ),
                },
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
        system_name: str = "",
    ) -> dict[str, Any]:
        """Öneri getirir.

        Args:
            system_name: Sistem adı.

        Returns:
            Öneri bilgisi.
        """
        try:
            points = [
                p["value"]
                for p in self._data_points
                if p["system_name"]
                == system_name
            ]

            if not points:
                return {
                    "system_name": system_name,
                    "recommendations": [],
                    "retrieved": True,
                }

            current = points[-1]
            recommendations = []

            if current < 30:
                recommendations.append({
                    "priority": "critical",
                    "action": (
                        "immediate_intervention"
                    ),
                    "description": (
                        "Sistem kritik durumda, "
                        "acil müdahale gerekli"
                    ),
                })
            elif current < 50:
                recommendations.append({
                    "priority": "high",
                    "action": (
                        "investigate_root_cause"
                    ),
                    "description": (
                        "Kök neden analizi yapın "
                        "ve düzeltici aksiyon alın"
                    ),
                })
            elif current < 70:
                recommendations.append({
                    "priority": "medium",
                    "action": "monitor_closely",
                    "description": (
                        "Yakın izleme altına alın"
                    ),
                })

            if len(points) >= 3:
                declining = all(
                    points[i] >= points[i + 1]
                    for i in range(
                        max(0, len(points) - 3),
                        len(points) - 1,
                    )
                )
                if declining:
                    recommendations.append({
                        "priority": "high",
                        "action": (
                            "investigate_decline"
                        ),
                        "description": (
                            "Sürekli düşüş trendi "
                            "tespit edildi"
                        ),
                    })

            if not recommendations:
                recommendations.append({
                    "priority": "low",
                    "action": "continue_monitoring",
                    "description": (
                        "Sistem sağlıklı, "
                        "izlemeye devam edin"
                    ),
                })

            return {
                "system_name": system_name,
                "current_health": current,
                "recommendations": (
                    recommendations
                ),
                "recommendation_count": len(
                    recommendations
                ),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }
