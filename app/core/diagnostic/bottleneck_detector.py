"""ATLAS Darbogaz Tespit modulu.

Performans profilleme, yavas islem tespiti,
bellek sizintilari, CPU noktasi tespiti
ve I/O darbogaz analizi.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from app.models.diagnostic import BottleneckRecord, BottleneckType

logger = logging.getLogger(__name__)


class BottleneckDetector:
    """Darbogaz tespit edici.

    Performans darbogazlarini tespit eder
    ve etkilerini degerlendirir.

    Attributes:
        _bottlenecks: Tespit edilen darbogazar.
        _profiles: Performans profilleri.
        _thresholds: Esik degerleri.
        _history: Metrik gecmisi.
    """

    def __init__(self) -> None:
        """Darbogaz tespit ediciyi baslatir."""
        self._bottlenecks: list[BottleneckRecord] = []
        self._profiles: dict[str, list[dict[str, Any]]] = {}
        self._thresholds: dict[str, float] = {
            "cpu_percent": 80.0,
            "memory_percent": 85.0,
            "io_wait_ms": 100.0,
            "network_latency_ms": 200.0,
            "response_time_ms": 1000.0,
        }
        self._history: dict[str, list[float]] = {}

        logger.info("BottleneckDetector baslatildi")

    def profile_operation(
        self,
        operation: str,
        duration_ms: float,
        resource_usage: dict[str, float] | None = None,
    ) -> dict[str, Any]:
        """Islem profili olusturur.

        Args:
            operation: Islem adi.
            duration_ms: Sure (ms).
            resource_usage: Kaynak kullanimi.

        Returns:
            Profil bilgisi.
        """
        profile = {
            "operation": operation,
            "duration_ms": duration_ms,
            "resource_usage": resource_usage or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._profiles.setdefault(operation, []).append(profile)

        # Gecmisi guncelle
        self._history.setdefault(operation, []).append(duration_ms)

        return profile

    def detect_slow_operations(
        self,
        threshold_ms: float = 1000.0,
    ) -> list[dict[str, Any]]:
        """Yavas islemleri tespit eder.

        Args:
            threshold_ms: Sure esigi (ms).

        Returns:
            Yavas islem listesi.
        """
        slow: list[dict[str, Any]] = []

        for operation, durations in self._history.items():
            if not durations:
                continue

            avg = sum(durations) / len(durations)
            max_val = max(durations)

            if avg > threshold_ms or max_val > threshold_ms * 2:
                bottleneck = BottleneckRecord(
                    bottleneck_type=BottleneckType.LATENCY,
                    component=operation,
                    metric_value=avg,
                    threshold=threshold_ms,
                    impact=min(1.0, avg / (threshold_ms * 3)),
                )
                self._bottlenecks.append(bottleneck)

                slow.append({
                    "operation": operation,
                    "avg_ms": round(avg, 2),
                    "max_ms": round(max_val, 2),
                    "sample_count": len(durations),
                    "bottleneck_id": bottleneck.bottleneck_id,
                })

        return slow

    def check_memory(
        self,
        component: str,
        memory_percent: float,
        memory_growth_rate: float = 0.0,
    ) -> BottleneckRecord | None:
        """Bellek kontrolu yapar.

        Args:
            component: Bilesen.
            memory_percent: Bellek kullanim %.
            memory_growth_rate: Buyume orani.

        Returns:
            BottleneckRecord veya None.
        """
        threshold = self._thresholds.get("memory_percent", 85.0)

        if memory_percent > threshold or memory_growth_rate > 5.0:
            impact = min(1.0, memory_percent / 100.0)
            if memory_growth_rate > 5.0:
                impact = min(1.0, impact + 0.2)

            record = BottleneckRecord(
                bottleneck_type=BottleneckType.MEMORY,
                component=component,
                metric_value=memory_percent,
                threshold=threshold,
                impact=round(impact, 3),
            )
            self._bottlenecks.append(record)

            logger.warning(
                "Bellek darbogazi: %s (%.1f%%, buyume=%.1f%%)",
                component, memory_percent, memory_growth_rate,
            )
            return record

        return None

    def check_cpu(
        self,
        component: str,
        cpu_percent: float,
    ) -> BottleneckRecord | None:
        """CPU kontrolu yapar.

        Args:
            component: Bilesen.
            cpu_percent: CPU kullanim %.

        Returns:
            BottleneckRecord veya None.
        """
        threshold = self._thresholds.get("cpu_percent", 80.0)

        if cpu_percent > threshold:
            record = BottleneckRecord(
                bottleneck_type=BottleneckType.CPU,
                component=component,
                metric_value=cpu_percent,
                threshold=threshold,
                impact=round(min(1.0, cpu_percent / 100.0), 3),
            )
            self._bottlenecks.append(record)
            return record

        return None

    def check_io(
        self,
        component: str,
        io_wait_ms: float,
    ) -> BottleneckRecord | None:
        """I/O kontrolu yapar.

        Args:
            component: Bilesen.
            io_wait_ms: I/O bekleme suresi (ms).

        Returns:
            BottleneckRecord veya None.
        """
        threshold = self._thresholds.get("io_wait_ms", 100.0)

        if io_wait_ms > threshold:
            record = BottleneckRecord(
                bottleneck_type=BottleneckType.IO,
                component=component,
                metric_value=io_wait_ms,
                threshold=threshold,
                impact=round(min(1.0, io_wait_ms / 500.0), 3),
            )
            self._bottlenecks.append(record)
            return record

        return None

    def check_network(
        self,
        component: str,
        latency_ms: float,
    ) -> BottleneckRecord | None:
        """Ag kontrolu yapar.

        Args:
            component: Bilesen.
            latency_ms: Gecikme (ms).

        Returns:
            BottleneckRecord veya None.
        """
        threshold = self._thresholds.get("network_latency_ms", 200.0)

        if latency_ms > threshold:
            record = BottleneckRecord(
                bottleneck_type=BottleneckType.NETWORK,
                component=component,
                metric_value=latency_ms,
                threshold=threshold,
                impact=round(min(1.0, latency_ms / 1000.0), 3),
            )
            self._bottlenecks.append(record)
            return record

        return None

    def set_threshold(self, metric: str, value: float) -> None:
        """Esik degeri ayarlar.

        Args:
            metric: Metrik adi.
            value: Esik degeri.
        """
        self._thresholds[metric] = value

    def get_bottlenecks_by_type(
        self,
        bottleneck_type: BottleneckType,
    ) -> list[BottleneckRecord]:
        """Ture gore darbogaz getirir.

        Args:
            bottleneck_type: Darbogaz turu.

        Returns:
            Darbogaz listesi.
        """
        return [
            b for b in self._bottlenecks
            if b.bottleneck_type == bottleneck_type
        ]

    def get_top_bottlenecks(
        self,
        limit: int = 5,
    ) -> list[BottleneckRecord]:
        """En ciddi darbogazlari getirir.

        Args:
            limit: Maks sonuc.

        Returns:
            Darbogaz listesi.
        """
        sorted_bns = sorted(
            self._bottlenecks,
            key=lambda b: b.impact,
            reverse=True,
        )
        return sorted_bns[:limit]

    def get_operation_stats(
        self,
        operation: str,
    ) -> dict[str, Any] | None:
        """Islem istatistiklerini getirir.

        Args:
            operation: Islem adi.

        Returns:
            Istatistik sozlugu veya None.
        """
        durations = self._history.get(operation)
        if not durations:
            return None

        return {
            "operation": operation,
            "count": len(durations),
            "avg_ms": round(sum(durations) / len(durations), 2),
            "min_ms": round(min(durations), 2),
            "max_ms": round(max(durations), 2),
        }

    @property
    def bottleneck_count(self) -> int:
        """Darbogaz sayisi."""
        return len(self._bottlenecks)

    @property
    def profile_count(self) -> int:
        """Profil sayisi."""
        return sum(len(v) for v in self._profiles.values())

    @property
    def operation_count(self) -> int:
        """Islem sayisi."""
        return len(self._history)
