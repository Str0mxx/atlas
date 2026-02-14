"""ATLAS Kapasite Planlayici modulu.

Talep tahmini, olcekleme onerileri,
kaynak rezervasyonu, buyume planlamasi
ve darbogazlari tahmin.
"""

import logging
from typing import Any

from app.models.resource import ResourceType, ScaleDirection

logger = logging.getLogger(__name__)


class CapacityPlanner:
    """Kapasite planlayici.

    Kaynak kapasitesini planlar, tahmin
    eder ve olcekleme onerir.

    Attributes:
        _capacities: Kapasite kayitlari.
        _usage_trends: Kullanim trendleri.
        _reservations: Rezervasyonlar.
    """

    def __init__(self) -> None:
        """Kapasite planlayiciyi baslatir."""
        self._capacities: dict[str, dict[str, Any]] = {}
        self._usage_trends: dict[str, list[float]] = {}
        self._reservations: dict[str, dict[str, Any]] = {}
        self._recommendations: list[dict[str, Any]] = []

        logger.info("CapacityPlanner baslatildi")

    def register_capacity(
        self,
        resource: str,
        resource_type: ResourceType,
        current: float,
        maximum: float,
    ) -> dict[str, Any]:
        """Kapasite kaydeder.

        Args:
            resource: Kaynak adi.
            resource_type: Kaynak turu.
            current: Mevcut kullanim.
            maximum: Maks kapasite.

        Returns:
            Kapasite bilgisi.
        """
        cap = {
            "resource": resource,
            "type": resource_type.value,
            "current": current,
            "maximum": max(1.0, maximum),
            "ratio": current / max(1.0, maximum),
        }
        self._capacities[resource] = cap
        return cap

    def record_usage(
        self,
        resource: str,
        usage: float,
    ) -> None:
        """Kullanim kaydeder.

        Args:
            resource: Kaynak adi.
            usage: Kullanim degeri.
        """
        if resource not in self._usage_trends:
            self._usage_trends[resource] = []
        self._usage_trends[resource].append(usage)

        # Kapasite guncelle
        if resource in self._capacities:
            cap = self._capacities[resource]
            cap["current"] = usage
            cap["ratio"] = usage / cap["maximum"]

    def forecast_demand(
        self,
        resource: str,
        periods: int = 5,
    ) -> dict[str, Any]:
        """Talep tahmini yapar.

        Args:
            resource: Kaynak adi.
            periods: Tahmin periyodu.

        Returns:
            Tahmin sonucu.
        """
        trend = self._usage_trends.get(resource, [])
        if len(trend) < 3:
            return {
                "resource": resource,
                "forecast": [],
                "sufficient": True,
                "confidence": 0.0,
            }

        # Basit linear tahmin
        n = len(trend)
        avg_change = (trend[-1] - trend[0]) / max(1, n - 1)
        last = trend[-1]

        forecast = [
            last + avg_change * (i + 1)
            for i in range(periods)
        ]

        cap = self._capacities.get(resource)
        maximum = cap["maximum"] if cap else float("inf")
        sufficient = all(f <= maximum for f in forecast)

        return {
            "resource": resource,
            "forecast": forecast,
            "avg_change": avg_change,
            "sufficient": sufficient,
            "confidence": min(1.0, len(trend) / 20),
        }

    def recommend_scaling(
        self,
        resource: str,
    ) -> dict[str, Any]:
        """Olcekleme onerir.

        Args:
            resource: Kaynak adi.

        Returns:
            Oneri.
        """
        cap = self._capacities.get(resource)
        if not cap:
            return {
                "resource": resource,
                "direction": ScaleDirection.NONE.value,
            }

        ratio = cap["ratio"]
        direction = ScaleDirection.NONE

        if ratio >= 0.85:
            direction = ScaleDirection.UP
        elif ratio <= 0.2:
            direction = ScaleDirection.DOWN

        rec = {
            "resource": resource,
            "current_ratio": ratio,
            "direction": direction.value,
            "current": cap["current"],
            "maximum": cap["maximum"],
        }

        if direction != ScaleDirection.NONE:
            self._recommendations.append(rec)

        return rec

    def reserve_capacity(
        self,
        resource: str,
        amount: float,
        requester: str = "",
    ) -> bool:
        """Kapasite rezerve eder.

        Args:
            resource: Kaynak adi.
            amount: Miktar.
            requester: Talep eden.

        Returns:
            Basarili ise True.
        """
        cap = self._capacities.get(resource)
        if not cap:
            return False

        available = cap["maximum"] - cap["current"]
        if amount > available:
            return False

        key = f"{resource}:{requester or 'system'}"
        self._reservations[key] = {
            "resource": resource,
            "amount": amount,
            "requester": requester,
        }
        cap["current"] += amount
        cap["ratio"] = cap["current"] / cap["maximum"]
        return True

    def release_reservation(
        self,
        resource: str,
        requester: str = "",
    ) -> bool:
        """Rezervasyonu serbest birakir.

        Args:
            resource: Kaynak adi.
            requester: Talep eden.

        Returns:
            Basarili ise True.
        """
        key = f"{resource}:{requester or 'system'}"
        res = self._reservations.get(key)
        if not res:
            return False

        cap = self._capacities.get(resource)
        if cap:
            cap["current"] = max(
                0.0, cap["current"] - res["amount"],
            )
            cap["ratio"] = cap["current"] / cap["maximum"]

        del self._reservations[key]
        return True

    def predict_bottleneck(self) -> list[dict[str, Any]]:
        """Darbogazlari tahmin eder.

        Returns:
            Darbogazlar.
        """
        bottlenecks: list[dict[str, Any]] = []
        for resource in self._capacities:
            forecast = self.forecast_demand(resource)
            if not forecast["sufficient"]:
                bottlenecks.append({
                    "resource": resource,
                    "forecast": forecast["forecast"],
                    "maximum": self._capacities[resource]["maximum"],
                })
        return bottlenecks

    @property
    def capacity_count(self) -> int:
        """Kapasite sayisi."""
        return len(self._capacities)

    @property
    def reservation_count(self) -> int:
        """Rezervasyon sayisi."""
        return len(self._reservations)

    @property
    def recommendation_count(self) -> int:
        """Oneri sayisi."""
        return len(self._recommendations)
