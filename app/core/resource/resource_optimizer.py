"""ATLAS Kaynak Optimizasyonu modulu.

Otomatik olcekleme tetikleri, kaynak
yeniden dengeleme, verimlilik iyilestirme,
israf eliminasyonu ve performans ayari.
"""

import logging
from typing import Any

from app.models.resource import (
    OptimizationAction,
    ResourceType,
)

logger = logging.getLogger(__name__)


class ResourceOptimizer:
    """Kaynak optimizasyonu.

    Kaynak kullanimini optimize eder
    ve israfi azaltir.

    Attributes:
        _thresholds: Olcekleme esikleri.
        _actions: Uygulanan aksiyonlar.
        _waste_reports: Israf raporlari.
    """

    def __init__(
        self,
        scale_up_threshold: float = 0.85,
        scale_down_threshold: float = 0.2,
    ) -> None:
        """Kaynak optimizasyonunu baslatir.

        Args:
            scale_up_threshold: Yukari olcekleme esigi.
            scale_down_threshold: Asagi olcekleme esigi.
        """
        self._thresholds = {
            "scale_up": max(0.5, min(1.0, scale_up_threshold)),
            "scale_down": max(0.0, min(0.5, scale_down_threshold)),
        }
        self._actions: list[dict[str, Any]] = []
        self._waste_reports: list[dict[str, Any]] = []
        self._tuning_history: list[dict[str, Any]] = []

        logger.info("ResourceOptimizer baslatildi")

    def check_auto_scale(
        self,
        resource: str,
        resource_type: ResourceType,
        usage_ratio: float,
    ) -> dict[str, Any]:
        """Otomatik olcekleme kontrolu.

        Args:
            resource: Kaynak adi.
            resource_type: Kaynak turu.
            usage_ratio: Kullanim orani.

        Returns:
            Olcekleme karari.
        """
        action = OptimizationAction.REBALANCE
        triggered = False

        if usage_ratio >= self._thresholds["scale_up"]:
            action = OptimizationAction.SCALE_UP
            triggered = True
        elif usage_ratio <= self._thresholds["scale_down"]:
            action = OptimizationAction.SCALE_DOWN
            triggered = True

        result = {
            "resource": resource,
            "type": resource_type.value,
            "usage_ratio": usage_ratio,
            "action": action.value,
            "triggered": triggered,
        }

        if triggered:
            self._actions.append(result)

        return result

    def rebalance(
        self,
        resources: dict[str, float],
    ) -> dict[str, float]:
        """Kaynaklari yeniden dengeler.

        Args:
            resources: Kaynak -> kullanim eslesmesi.

        Returns:
            Dengelenmis tahsis.
        """
        if not resources:
            return {}

        total = sum(resources.values())
        count = len(resources)
        target = total / count if count > 0 else 0.0

        balanced: dict[str, float] = {}
        for name in resources:
            balanced[name] = target

        self._actions.append({
            "action": OptimizationAction.REBALANCE.value,
            "resources": list(resources.keys()),
            "target_each": target,
        })

        return balanced

    def detect_waste(
        self,
        allocations: dict[str, dict[str, float]],
    ) -> list[dict[str, Any]]:
        """Israfi tespit eder.

        Args:
            allocations: Kaynak tahsisleri
                {name: {"allocated": x, "used": y}}.

        Returns:
            Israf raporlari.
        """
        wastes: list[dict[str, Any]] = []

        for name, alloc in allocations.items():
            allocated = alloc.get("allocated", 0.0)
            used = alloc.get("used", 0.0)
            if allocated <= 0:
                continue

            utilization = used / allocated
            if utilization < 0.3:
                waste = {
                    "resource": name,
                    "allocated": allocated,
                    "used": used,
                    "utilization": utilization,
                    "wasted": allocated - used,
                    "suggestion": "reduce_allocation",
                }
                wastes.append(waste)
                self._waste_reports.append(waste)

        return wastes

    def suggest_efficiency(
        self,
        resource: str,
        resource_type: ResourceType,
        metrics: dict[str, float],
    ) -> dict[str, Any]:
        """Verimlilik onerisi uretir.

        Args:
            resource: Kaynak adi.
            resource_type: Kaynak turu.
            metrics: Performans metrikleri.

        Returns:
            Oneri.
        """
        suggestion: dict[str, Any] = {
            "resource": resource,
            "type": resource_type.value,
            "improvements": [],
        }

        usage = metrics.get("usage", 0.0)
        latency = metrics.get("latency", 0.0)
        error_rate = metrics.get("error_rate", 0.0)

        if usage > 0.8:
            suggestion["improvements"].append({
                "action": OptimizationAction.CACHE.value,
                "reason": "Yuksek kullanim, cache oneriliyor",
            })

        if latency > 1.0:
            suggestion["improvements"].append({
                "action": OptimizationAction.SCALE_UP.value,
                "reason": "Yuksek gecikme, olcekleme oneriliyor",
            })

        if error_rate > 0.05:
            suggestion["improvements"].append({
                "action": OptimizationAction.REBALANCE.value,
                "reason": "Yuksek hata orani, yeniden dengeleme",
            })

        return suggestion

    def tune_performance(
        self,
        resource: str,
        param: str,
        old_value: float,
        new_value: float,
    ) -> dict[str, Any]:
        """Performans ayari yapar.

        Args:
            resource: Kaynak adi.
            param: Parametre adi.
            old_value: Eski deger.
            new_value: Yeni deger.

        Returns:
            Ayar bilgisi.
        """
        tuning = {
            "resource": resource,
            "param": param,
            "old_value": old_value,
            "new_value": new_value,
        }
        self._tuning_history.append(tuning)
        return tuning

    @property
    def action_count(self) -> int:
        """Aksiyon sayisi."""
        return len(self._actions)

    @property
    def waste_count(self) -> int:
        """Israf sayisi."""
        return len(self._waste_reports)

    @property
    def tuning_count(self) -> int:
        """Ayar sayisi."""
        return len(self._tuning_history)
