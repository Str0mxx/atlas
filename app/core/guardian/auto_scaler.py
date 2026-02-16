"""ATLAS Otomatik Ölçekleyici modülü.

Yük izleme, ölçekleme tetikleyicileri,
kaynak ayarlama, soğuma yönetimi,
maliyet optimizasyonu.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class GuardianAutoScaler:
    """Otomatik ölçekleyici.

    Yüke göre kaynakları otomatik ölçekler.

    Attributes:
        _services: Servis kayıtları.
        _scale_events: Ölçekleme olayları.
    """

    def __init__(self) -> None:
        """Ölçekleyiciyi başlatır."""
        self._services: dict[
            str, dict[str, Any]
        ] = {}
        self._scale_events: list[
            dict[str, Any]
        ] = []
        self._counter = 0
        self._stats = {
            "scale_ups": 0,
            "scale_downs": 0,
        }

        logger.info(
            "GuardianAutoScaler baslatildi",
        )

    def register_service(
        self,
        service: str,
        min_instances: int = 1,
        max_instances: int = 10,
        current_instances: int = 1,
        cooldown_sec: float = 300.0,
    ) -> dict[str, Any]:
        """Servis kaydeder.

        Args:
            service: Servis adı.
            min_instances: Min örnek.
            max_instances: Maks örnek.
            current_instances: Mevcut örnek.
            cooldown_sec: Soğuma süresi.

        Returns:
            Kayıt bilgisi.
        """
        self._counter += 1
        sid = f"as_{self._counter}"

        self._services[service] = {
            "service_id": sid,
            "service": service,
            "min_instances": min_instances,
            "max_instances": max_instances,
            "current_instances": (
                current_instances
            ),
            "cooldown_sec": cooldown_sec,
            "last_scale_time": 0.0,
            "load_pct": 0.0,
        }

        return {
            "service_id": sid,
            "service": service,
            "current_instances": (
                current_instances
            ),
            "registered": True,
        }

    def monitor_load(
        self,
        service: str,
        cpu_pct: float = 0.0,
        memory_pct: float = 0.0,
        request_rate: float = 0.0,
    ) -> dict[str, Any]:
        """Yük izler.

        Args:
            service: Servis adı.
            cpu_pct: CPU yüzdesi.
            memory_pct: Bellek yüzdesi.
            request_rate: İstek hızı.

        Returns:
            Yük bilgisi.
        """
        svc = self._services.get(service)
        if not svc:
            return {
                "service": service,
                "monitored": False,
            }

        load = round(
            cpu_pct * 0.4
            + memory_pct * 0.4
            + min(request_rate, 100) * 0.2,
            1,
        )
        svc["load_pct"] = load

        level = (
            "critical"
            if load >= 90
            else "high"
            if load >= 75
            else "normal"
            if load >= 30
            else "low"
        )

        return {
            "service": service,
            "load_pct": load,
            "level": level,
            "cpu_pct": cpu_pct,
            "memory_pct": memory_pct,
            "monitored": True,
        }

    def check_scale_trigger(
        self,
        service: str,
        scale_up_threshold: float = 80.0,
        scale_down_threshold: float = 30.0,
    ) -> dict[str, Any]:
        """Ölçekleme tetikleyici kontrol eder.

        Args:
            service: Servis adı.
            scale_up_threshold: Yukarı eşik.
            scale_down_threshold: Aşağı eşik.

        Returns:
            Tetik bilgisi.
        """
        svc = self._services.get(service)
        if not svc:
            return {
                "service": service,
                "checked": False,
            }

        load = svc["load_pct"]
        current = svc["current_instances"]

        # Soğuma kontrolü
        elapsed = (
            time.time()
            - svc["last_scale_time"]
        )
        in_cooldown = (
            elapsed < svc["cooldown_sec"]
            and svc["last_scale_time"] > 0
        )

        if in_cooldown:
            direction = "none"
        elif (
            load >= scale_up_threshold
            and current < svc["max_instances"]
        ):
            direction = "up"
        elif (
            load <= scale_down_threshold
            and current > svc["min_instances"]
        ):
            direction = "down"
        else:
            direction = "none"

        return {
            "service": service,
            "load_pct": load,
            "direction": direction,
            "current_instances": current,
            "in_cooldown": in_cooldown,
            "checked": True,
        }

    def adjust_resources(
        self,
        service: str,
        direction: str = "up",
        count: int = 1,
    ) -> dict[str, Any]:
        """Kaynak ayarlar.

        Args:
            service: Servis adı.
            direction: Yön (up/down).
            count: Sayı.

        Returns:
            Ayarlama bilgisi.
        """
        svc = self._services.get(service)
        if not svc:
            return {
                "service": service,
                "adjusted": False,
            }

        current = svc["current_instances"]
        if direction == "up":
            new = min(
                current + count,
                svc["max_instances"],
            )
            self._stats["scale_ups"] += 1
        else:
            new = max(
                current - count,
                svc["min_instances"],
            )
            self._stats["scale_downs"] += 1

        svc["current_instances"] = new
        svc["last_scale_time"] = time.time()

        event = {
            "service": service,
            "direction": direction,
            "from": current,
            "to": new,
            "timestamp": time.time(),
        }
        self._scale_events.append(event)

        return {
            "service": service,
            "direction": direction,
            "previous": current,
            "current": new,
            "adjusted": True,
        }

    def handle_cooldown(
        self,
        service: str,
    ) -> dict[str, Any]:
        """Soğuma durumu kontrol eder.

        Args:
            service: Servis adı.

        Returns:
            Soğuma bilgisi.
        """
        svc = self._services.get(service)
        if not svc:
            return {
                "service": service,
                "checked": False,
            }

        elapsed = (
            time.time()
            - svc["last_scale_time"]
        )
        remaining = max(
            svc["cooldown_sec"] - elapsed,
            0,
        )
        in_cooldown = (
            remaining > 0
            and svc["last_scale_time"] > 0
        )

        return {
            "service": service,
            "in_cooldown": in_cooldown,
            "remaining_sec": round(
                remaining, 1,
            ),
            "cooldown_sec": svc[
                "cooldown_sec"
            ],
            "checked": True,
        }

    def optimize_cost(
        self,
        service: str,
        cost_per_instance: float = 10.0,
    ) -> dict[str, Any]:
        """Maliyet optimizasyonu yapar.

        Args:
            service: Servis adı.
            cost_per_instance: Birim maliyet.

        Returns:
            Optimizasyon bilgisi.
        """
        svc = self._services.get(service)
        if not svc:
            return {
                "service": service,
                "optimized": False,
            }

        current = svc["current_instances"]
        load = svc["load_pct"]
        current_cost = round(
            current * cost_per_instance, 2,
        )

        # Optimal sayı hesaplama
        optimal = max(
            svc["min_instances"],
            round(
                current * load / 70,
            ),
        )
        optimal = min(
            optimal, svc["max_instances"],
        )
        optimal_cost = round(
            optimal * cost_per_instance, 2,
        )
        savings = round(
            current_cost - optimal_cost, 2,
        )

        return {
            "service": service,
            "current_instances": current,
            "optimal_instances": optimal,
            "current_cost": current_cost,
            "optimal_cost": optimal_cost,
            "savings": max(savings, 0),
            "optimized": True,
        }

    @property
    def scale_up_count(self) -> int:
        """Yukarı ölçekleme sayısı."""
        return self._stats["scale_ups"]

    @property
    def scale_down_count(self) -> int:
        """Aşağı ölçekleme sayısı."""
        return self._stats["scale_downs"]
