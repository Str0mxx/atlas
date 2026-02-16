"""ATLAS Otomatik Ayarlayıcı modülü.

Parametre optimizasyonu, eşik ayarlama,
konfigürasyon ayarı, kademeli değişiklik,
gerileme geri alma.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class AutoTuner:
    """Otomatik ayarlayıcı.

    Sistem parametrelerini otomatik optimize eder.

    Attributes:
        _params: Parametre kayıtları.
        _history: Ayarlama geçmişi.
    """

    def __init__(self) -> None:
        """Ayarlayıcıyı başlatır."""
        self._params: dict[
            str, dict[str, Any]
        ] = {}
        self._history: list[
            dict[str, Any]
        ] = []
        self._snapshots: dict[
            str, Any
        ] = {}
        self._counter = 0
        self._stats = {
            "optimizations": 0,
            "rollbacks": 0,
        }

        logger.info(
            "AutoTuner baslatildi",
        )

    def register_parameter(
        self,
        name: str,
        current_value: float,
        min_value: float = 0.0,
        max_value: float = 100.0,
        step: float = 1.0,
    ) -> dict[str, Any]:
        """Parametre kaydeder.

        Args:
            name: Parametre adı.
            current_value: Mevcut değer.
            min_value: Min değer.
            max_value: Maks değer.
            step: Adım büyüklüğü.

        Returns:
            Kayıt bilgisi.
        """
        self._params[name] = {
            "name": name,
            "value": current_value,
            "min": min_value,
            "max": max_value,
            "step": step,
            "original": current_value,
        }

        return {
            "name": name,
            "value": current_value,
            "registered": True,
        }

    def optimize_parameter(
        self,
        name: str,
        target_metric: float = 0.0,
        current_metric: float = 0.0,
    ) -> dict[str, Any]:
        """Parametre optimize eder.

        Args:
            name: Parametre adı.
            target_metric: Hedef metrik.
            current_metric: Mevcut metrik.

        Returns:
            Optimizasyon bilgisi.
        """
        param = self._params.get(name)
        if not param:
            return {
                "name": name,
                "optimized": False,
            }

        old_value = param["value"]

        # Hedeften sapma
        gap = target_metric - current_metric
        if gap > 0:
            action = "increase"
            new_value = min(
                old_value + param["step"],
                param["max"],
            )
        elif gap < 0:
            action = "decrease"
            new_value = max(
                old_value - param["step"],
                param["min"],
            )
        else:
            action = "keep"
            new_value = old_value

        # Snapshot kaydet
        self._snapshots[name] = old_value
        param["value"] = new_value

        self._history.append({
            "name": name,
            "old": old_value,
            "new": new_value,
            "action": action,
            "timestamp": time.time(),
        })
        self._stats["optimizations"] += 1

        return {
            "name": name,
            "old_value": old_value,
            "new_value": new_value,
            "action": action,
            "optimized": True,
        }

    def adjust_threshold(
        self,
        name: str,
        performance: float,
        target: float = 80.0,
    ) -> dict[str, Any]:
        """Eşik ayarlar.

        Args:
            name: Parametre adı.
            performance: Performans.
            target: Hedef.

        Returns:
            Ayarlama bilgisi.
        """
        param = self._params.get(name)
        if not param:
            return {
                "name": name,
                "adjusted": False,
            }

        old = param["value"]
        ratio = performance / target if (
            target > 0
        ) else 1.0

        if ratio < 0.9:
            new = max(
                old - param["step"],
                param["min"],
            )
            direction = "lowered"
        elif ratio > 1.1:
            new = min(
                old + param["step"],
                param["max"],
            )
            direction = "raised"
        else:
            new = old
            direction = "kept"

        self._snapshots[name] = old
        param["value"] = new

        return {
            "name": name,
            "old_value": old,
            "new_value": new,
            "direction": direction,
            "adjusted": True,
        }

    def tune_config(
        self,
        config_name: str,
        metrics: dict[str, float]
        | None = None,
    ) -> dict[str, Any]:
        """Konfigürasyon ayarlar.

        Args:
            config_name: Konfigürasyon adı.
            metrics: Metrikler.

        Returns:
            Ayarlama bilgisi.
        """
        metrics = metrics or {}
        changes = []

        for metric, value in metrics.items():
            param = self._params.get(metric)
            if param:
                old = param["value"]
                if value > 80:
                    param["value"] = min(
                        old + param["step"],
                        param["max"],
                    )
                elif value < 50:
                    param["value"] = max(
                        old - param["step"],
                        param["min"],
                    )
                if param["value"] != old:
                    changes.append({
                        "param": metric,
                        "old": old,
                        "new": param["value"],
                    })

        return {
            "config": config_name,
            "changes": len(changes),
            "details": changes,
            "tuned": len(changes) > 0,
        }

    def apply_gradual_change(
        self,
        name: str,
        target_value: float,
        steps: int = 5,
    ) -> dict[str, Any]:
        """Kademeli değişiklik uygular.

        Args:
            name: Parametre adı.
            target_value: Hedef değer.
            steps: Adım sayısı.

        Returns:
            Değişiklik bilgisi.
        """
        param = self._params.get(name)
        if not param:
            return {
                "name": name,
                "applied": False,
            }

        current = param["value"]
        step_size = round(
            (target_value - current) / steps,
            2,
        )

        # İlk adımı uygula
        self._snapshots[name] = current
        next_value = round(
            current + step_size, 2,
        )
        next_value = max(
            param["min"],
            min(next_value, param["max"]),
        )
        param["value"] = next_value

        return {
            "name": name,
            "current": current,
            "next_value": next_value,
            "target": target_value,
            "step_size": step_size,
            "remaining_steps": steps - 1,
            "applied": True,
        }

    def rollback_on_regression(
        self,
        name: str,
        current_metric: float,
        previous_metric: float,
    ) -> dict[str, Any]:
        """Gerileme durumunda geri alır.

        Args:
            name: Parametre adı.
            current_metric: Mevcut metrik.
            previous_metric: Önceki metrik.

        Returns:
            Geri alma bilgisi.
        """
        param = self._params.get(name)
        if not param:
            return {
                "name": name,
                "rolled_back": False,
            }

        regression = (
            current_metric < previous_metric
        )

        if regression and name in (
            self._snapshots
        ):
            old = param["value"]
            param["value"] = self._snapshots[
                name
            ]
            self._stats["rollbacks"] += 1

            return {
                "name": name,
                "rolled_back": True,
                "from": old,
                "to": param["value"],
                "regression_detected": True,
            }

        return {
            "name": name,
            "rolled_back": False,
            "regression_detected": False,
        }

    @property
    def optimization_count(self) -> int:
        """Optimizasyon sayısı."""
        return self._stats[
            "optimizations"
        ]

    @property
    def rollback_count(self) -> int:
        """Geri alma sayısı."""
        return self._stats["rollbacks"]
