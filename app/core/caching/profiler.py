"""ATLAS Performans Profilleyici modulu.

Calistirma zamanlama, bellek profili,
CPU profili, darbogaz tespiti
ve flame graph.
"""

import logging
import time
from typing import Any

from app.models.caching import (
    ProfileMetric,
    ProfileRecord,
)

logger = logging.getLogger(__name__)


class PerformanceProfiler:
    """Performans profilleyici.

    Islemleri zamanlar ve
    darbogazlari tespit eder.

    Attributes:
        _profiles: Profil kayitlari.
        _timers: Aktif zamanlayicilar.
    """

    def __init__(
        self,
        slow_threshold: float = 1.0,
    ) -> None:
        """Profilleyiciyi baslatir.

        Args:
            slow_threshold: Yavas esik (sn).
        """
        self._profiles: list[
            ProfileRecord
        ] = []
        self._timers: dict[str, float] = {}
        self._memory_snapshots: list[
            dict[str, Any]
        ] = []
        self._bottlenecks: list[
            dict[str, Any]
        ] = []
        self._slow_threshold = slow_threshold

        logger.info(
            "PerformanceProfiler baslatildi",
        )

    def start_timer(
        self,
        operation: str,
    ) -> None:
        """Zamanlayici baslatir.

        Args:
            operation: Islem adi.
        """
        self._timers[operation] = time.time()

    def stop_timer(
        self,
        operation: str,
    ) -> dict[str, Any]:
        """Zamanlayici durdurur.

        Args:
            operation: Islem adi.

        Returns:
            Zamanlama sonucu.
        """
        start = self._timers.pop(operation, None)
        if start is None:
            return {
                "operation": operation,
                "duration": 0.0,
                "error": "no_timer",
            }

        duration = round(
            time.time() - start, 6,
        )
        record = ProfileRecord(
            operation=operation,
            metric=ProfileMetric.EXECUTION_TIME,
            value=duration,
        )
        self._profiles.append(record)

        if duration > self._slow_threshold:
            self._bottlenecks.append({
                "operation": operation,
                "duration": duration,
                "type": "slow_execution",
                "at": time.time(),
            })

        return {
            "operation": operation,
            "duration": duration,
            "slow": (
                duration > self._slow_threshold
            ),
        }

    def record_metric(
        self,
        operation: str,
        metric: ProfileMetric,
        value: float,
        metadata: dict[str, Any] | None = None,
    ) -> ProfileRecord:
        """Metrik kaydeder.

        Args:
            operation: Islem adi.
            metric: Metrik turu.
            value: Deger.
            metadata: Ek veri.

        Returns:
            Profil kaydi.
        """
        record = ProfileRecord(
            operation=operation,
            metric=metric,
            value=value,
            metadata=metadata or {},
        )
        self._profiles.append(record)
        return record

    def record_memory(
        self,
        label: str,
        used_mb: float,
        total_mb: float = 0.0,
    ) -> dict[str, Any]:
        """Bellek kullanimi kaydeder.

        Args:
            label: Etiket.
            used_mb: Kullanan (MB).
            total_mb: Toplam (MB).

        Returns:
            Bellek kaydI.
        """
        snapshot = {
            "label": label,
            "used_mb": used_mb,
            "total_mb": total_mb,
            "usage_pct": round(
                used_mb / max(1, total_mb) * 100,
                1,
            ) if total_mb > 0 else 0.0,
            "at": time.time(),
        }
        self._memory_snapshots.append(snapshot)

        self.record_metric(
            label,
            ProfileMetric.MEMORY_USAGE,
            used_mb,
        )

        return snapshot

    def detect_bottlenecks(
        self,
        threshold: float | None = None,
    ) -> list[dict[str, Any]]:
        """Darbogazlari tespit eder.

        Args:
            threshold: Esik degeri.

        Returns:
            Darbogaz listesi.
        """
        th = threshold or self._slow_threshold
        bottlenecks: list[dict[str, Any]] = []

        for profile in self._profiles:
            if (
                profile.metric
                == ProfileMetric.EXECUTION_TIME
                and profile.value > th
            ):
                bottlenecks.append({
                    "operation": profile.operation,
                    "duration": profile.value,
                    "type": "slow_execution",
                })
            elif (
                profile.metric
                == ProfileMetric.MEMORY_USAGE
                and profile.value > 500
            ):
                bottlenecks.append({
                    "operation": profile.operation,
                    "memory_mb": profile.value,
                    "type": "high_memory",
                })

        return bottlenecks

    def get_flame_data(
        self,
    ) -> list[dict[str, Any]]:
        """Flame graph verisi getirir.

        Returns:
            Flame graph verisi.
        """
        flame: list[dict[str, Any]] = []
        for profile in self._profiles:
            if (
                profile.metric
                == ProfileMetric.EXECUTION_TIME
            ):
                flame.append({
                    "name": profile.operation,
                    "value": profile.value,
                    "depth": 0,
                })
        return flame

    def get_summary(
        self,
        operation: str | None = None,
    ) -> dict[str, Any]:
        """Ozet getirir.

        Args:
            operation: Islem filtresi.

        Returns:
            Ozet.
        """
        profiles = self._profiles
        if operation:
            profiles = [
                p for p in profiles
                if p.operation == operation
            ]

        exec_times = [
            p.value for p in profiles
            if p.metric
            == ProfileMetric.EXECUTION_TIME
        ]

        avg_time = (
            round(
                sum(exec_times) / len(exec_times),
                6,
            )
            if exec_times
            else 0.0
        )
        max_time = (
            max(exec_times)
            if exec_times else 0.0
        )
        min_time = (
            min(exec_times)
            if exec_times else 0.0
        )

        return {
            "total_profiles": len(profiles),
            "avg_execution_time": avg_time,
            "max_execution_time": max_time,
            "min_execution_time": min_time,
            "bottlenecks": len(
                self._bottlenecks,
            ),
            "memory_snapshots": len(
                self._memory_snapshots,
            ),
        }

    def clear(self) -> None:
        """Tum verileri temizler."""
        self._profiles.clear()
        self._timers.clear()
        self._memory_snapshots.clear()
        self._bottlenecks.clear()

    @property
    def profile_count(self) -> int:
        """Profil sayisi."""
        return len(self._profiles)

    @property
    def bottleneck_count(self) -> int:
        """Darbogaz sayisi."""
        return len(self._bottlenecks)

    @property
    def active_timers(self) -> int:
        """Aktif zamanlayici sayisi."""
        return len(self._timers)
