"""ATLAS Trend Takipçisi modülü.

Trend tespiti, momentum analizi,
yaşam döngüsü, tahmin, uyarı üretimi.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class TrendTracker:
    """Trend takipçisi.

    Pazar trendlerini tespit eder ve izler.

    Attributes:
        _trends: Trend kayıtları.
        _alerts: Uyarı geçmişi.
    """

    STAGES = [
        "emerging", "growing",
        "maturing", "declining",
        "stable", "reviving",
    ]

    def __init__(self) -> None:
        """Takipçiyi başlatır."""
        self._trends: dict[
            str, dict[str, Any]
        ] = {}
        self._alerts: list[
            dict[str, Any]
        ] = []
        self._data_points: dict[
            str, list[dict[str, Any]]
        ] = {}
        self._counter = 0
        self._stats = {
            "trends_detected": 0,
            "alerts_generated": 0,
            "predictions_made": 0,
        }

        logger.info(
            "TrendTracker baslatildi",
        )

    def detect_trend(
        self,
        name: str,
        data_points: list[float],
        category: str = "general",
        source: str = "",
    ) -> dict[str, Any]:
        """Trend tespit eder.

        Args:
            name: Trend adı.
            data_points: Veri noktaları.
            category: Kategori.
            source: Kaynak.

        Returns:
            Trend bilgisi.
        """
        self._counter += 1
        tid = f"tr_{self._counter}"

        momentum = self._calc_momentum(
            data_points,
        )
        stage = self._determine_stage(
            momentum, data_points,
        )
        confidence = min(
            1.0,
            len(data_points) / 10.0,
        )

        trend = {
            "trend_id": tid,
            "name": name,
            "category": category,
            "source": source,
            "stage": stage,
            "momentum": round(momentum, 3),
            "confidence": round(
                confidence, 2,
            ),
            "data_points": len(data_points),
            "latest_value": (
                data_points[-1]
                if data_points
                else 0
            ),
            "created_at": time.time(),
        }
        self._trends[tid] = trend
        self._data_points[tid] = [
            {"value": v, "ts": time.time()}
            for v in data_points
        ]
        self._stats["trends_detected"] += 1

        return {
            "trend_id": tid,
            "name": name,
            "stage": stage,
            "momentum": trend["momentum"],
            "confidence": trend["confidence"],
            "detected": True,
        }

    def analyze_momentum(
        self,
        trend_id: str,
    ) -> dict[str, Any]:
        """Momentum analiz eder.

        Args:
            trend_id: Trend ID.

        Returns:
            Analiz bilgisi.
        """
        trend = self._trends.get(trend_id)
        if not trend:
            return {
                "error": "trend_not_found",
            }

        points = self._data_points.get(
            trend_id, [],
        )
        values = [p["value"] for p in points]

        if len(values) < 2:
            return {
                "trend_id": trend_id,
                "momentum": 0.0,
                "acceleration": 0.0,
                "direction": "flat",
            }

        momentum = self._calc_momentum(
            values,
        )
        # Basit ivme hesabı
        if len(values) >= 3:
            recent = values[-3:]
            m1 = recent[1] - recent[0]
            m2 = recent[2] - recent[1]
            acceleration = m2 - m1
        else:
            acceleration = 0.0

        direction = (
            "up" if momentum > 0.05
            else "down" if momentum < -0.05
            else "flat"
        )

        return {
            "trend_id": trend_id,
            "momentum": round(momentum, 3),
            "acceleration": round(
                acceleration, 3,
            ),
            "direction": direction,
        }

    def get_lifecycle_stage(
        self,
        trend_id: str,
    ) -> dict[str, Any]:
        """Yaşam döngüsü aşaması.

        Args:
            trend_id: Trend ID.

        Returns:
            Aşama bilgisi.
        """
        trend = self._trends.get(trend_id)
        if not trend:
            return {
                "error": "trend_not_found",
            }

        return {
            "trend_id": trend_id,
            "name": trend["name"],
            "stage": trend["stage"],
            "momentum": trend["momentum"],
        }

    def predict(
        self,
        trend_id: str,
        periods: int = 3,
    ) -> dict[str, Any]:
        """Trend tahmini yapar.

        Args:
            trend_id: Trend ID.
            periods: Tahmin periyodu.

        Returns:
            Tahmin bilgisi.
        """
        trend = self._trends.get(trend_id)
        if not trend:
            return {
                "error": "trend_not_found",
            }

        points = self._data_points.get(
            trend_id, [],
        )
        values = [p["value"] for p in points]

        if len(values) < 2:
            return {
                "trend_id": trend_id,
                "predictions": [],
                "confidence": 0.0,
            }

        # Basit lineer projeksiyon
        avg_change = (
            (values[-1] - values[0])
            / max(len(values) - 1, 1)
        )
        predictions = []
        last = values[-1]
        for i in range(1, periods + 1):
            pred = last + avg_change * i
            predictions.append(
                round(pred, 2),
            )

        self._stats[
            "predictions_made"
        ] += 1

        return {
            "trend_id": trend_id,
            "predictions": predictions,
            "periods": periods,
            "avg_change": round(
                avg_change, 3,
            ),
            "confidence": trend[
                "confidence"
            ],
        }

    def generate_alert(
        self,
        trend_id: str,
        alert_type: str = "momentum_shift",
        message: str = "",
    ) -> dict[str, Any]:
        """Uyarı üretir.

        Args:
            trend_id: Trend ID.
            alert_type: Uyarı tipi.
            message: Mesaj.

        Returns:
            Uyarı bilgisi.
        """
        trend = self._trends.get(trend_id)
        if not trend:
            return {
                "error": "trend_not_found",
            }

        self._counter += 1
        aid = f"ta_{self._counter}"

        alert = {
            "alert_id": aid,
            "trend_id": trend_id,
            "trend_name": trend["name"],
            "alert_type": alert_type,
            "message": message or (
                f"Trend '{trend['name']}' "
                f"{alert_type}"
            ),
            "created_at": time.time(),
        }
        self._alerts.append(alert)
        self._stats[
            "alerts_generated"
        ] += 1

        return {
            "alert_id": aid,
            "trend_id": trend_id,
            "alert_type": alert_type,
            "generated": True,
        }

    def add_data_point(
        self,
        trend_id: str,
        value: float,
    ) -> dict[str, Any]:
        """Veri noktası ekler.

        Args:
            trend_id: Trend ID.
            value: Değer.

        Returns:
            Ekleme bilgisi.
        """
        trend = self._trends.get(trend_id)
        if not trend:
            return {
                "error": "trend_not_found",
            }

        if trend_id not in self._data_points:
            self._data_points[trend_id] = []

        self._data_points[trend_id].append({
            "value": value,
            "ts": time.time(),
        })

        # Güncelle
        values = [
            p["value"]
            for p in self._data_points[
                trend_id
            ]
        ]
        trend["momentum"] = round(
            self._calc_momentum(values), 3,
        )
        trend["stage"] = (
            self._determine_stage(
                trend["momentum"], values,
            )
        )
        trend["latest_value"] = value
        trend["data_points"] = len(values)

        return {
            "trend_id": trend_id,
            "value": value,
            "total_points": len(values),
            "added": True,
        }

    def get_trends(
        self,
        category: str | None = None,
        stage: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Trendleri getirir.

        Args:
            category: Kategori filtresi.
            stage: Aşama filtresi.
            limit: Maks kayıt.

        Returns:
            Trend listesi.
        """
        results = list(
            self._trends.values(),
        )
        if category:
            results = [
                t for t in results
                if t["category"] == category
            ]
        if stage:
            results = [
                t for t in results
                if t["stage"] == stage
            ]
        return results[:limit]

    def _calc_momentum(
        self,
        values: list[float],
    ) -> float:
        """Momentum hesaplar."""
        if len(values) < 2:
            return 0.0
        total_change = (
            values[-1] - values[0]
        )
        base = abs(values[0]) if values[0] != 0 else 1.0
        return total_change / base

    def _determine_stage(
        self,
        momentum: float,
        values: list[float],
    ) -> str:
        """Aşamayı belirler."""
        if momentum > 0.3:
            return "growing"
        if momentum > 0.1:
            return "emerging"
        if momentum < -0.2:
            return "declining"
        if momentum < -0.05:
            return "maturing"
        # Stabilize olmuş mu kontrol
        if len(values) >= 3:
            recent = values[-3:]
            spread = max(recent) - min(recent)
            avg = sum(recent) / len(recent)
            if avg != 0 and spread / abs(avg) < 0.05:
                return "stable"
        return "emerging"

    @property
    def trend_count(self) -> int:
        """Trend sayısı."""
        return len(self._trends)

    @property
    def alert_count(self) -> int:
        """Uyarı sayısı."""
        return self._stats[
            "alerts_generated"
        ]
