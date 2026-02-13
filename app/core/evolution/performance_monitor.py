"""ATLAS Performans Izleme modulu.

Agent/gorev bazli basari orani, yanit suresi analizi,
hata kalip tespiti, kaynak kullanimi ve trend analizi.
"""

import logging
import time
from typing import Any

from app.models.evolution import PerformanceMetric, TrendDirection

logger = logging.getLogger(__name__)


class PerformanceMonitor:
    """Performans izleme sistemi.

    Agent ve gorev bazinda basari orani, yanit suresi,
    hata kaliplari ve kaynak kullanimi izler.

    Attributes:
        _metrics: Agent bazli metrikler.
        _response_times: Yanit sureleri gecmisi.
        _errors: Hata kayitlari.
        _resource_usage: Kaynak kullanim gecmisi.
    """

    def __init__(self) -> None:
        """Performans izleyiciyi baslatir."""
        self._metrics: dict[str, PerformanceMetric] = {}
        self._response_times: dict[str, list[float]] = {}
        self._errors: dict[str, list[dict[str, Any]]] = {}
        self._resource_usage: list[dict[str, float]] = []
        self._history: list[PerformanceMetric] = []

        logger.info("PerformanceMonitor baslatildi")

    def record_success(self, agent_name: str, task_type: str, response_ms: float) -> None:
        """Basarili islemi kaydeder.

        Args:
            agent_name: Agent adi.
            task_type: Gorev tipi.
            response_ms: Yanit suresi (ms).
        """
        key = f"{agent_name}:{task_type}"
        metric = self._get_or_create(key, agent_name, task_type)
        metric.success_count += 1
        metric.total_count += 1
        self._update_response_time(key, response_ms)
        self._recalculate(key, metric)

    def record_failure(self, agent_name: str, task_type: str, error: str, response_ms: float = 0.0) -> None:
        """Basarisiz islemi kaydeder.

        Args:
            agent_name: Agent adi.
            task_type: Gorev tipi.
            error: Hata mesaji.
            response_ms: Yanit suresi (ms).
        """
        key = f"{agent_name}:{task_type}"
        metric = self._get_or_create(key, agent_name, task_type)
        metric.failure_count += 1
        metric.total_count += 1

        if response_ms > 0:
            self._update_response_time(key, response_ms)

        errors = self._errors.setdefault(key, [])
        errors.append({"error": error, "timestamp": time.time()})

        self._recalculate(key, metric)

    def get_metric(self, agent_name: str, task_type: str) -> PerformanceMetric | None:
        """Belirli bir metrik getirir.

        Args:
            agent_name: Agent adi.
            task_type: Gorev tipi.

        Returns:
            PerformanceMetric veya None.
        """
        key = f"{agent_name}:{task_type}"
        return self._metrics.get(key)

    def get_success_rate(self, agent_name: str, task_type: str = "") -> float:
        """Basari oranini hesaplar.

        Args:
            agent_name: Agent adi.
            task_type: Gorev tipi (bos ise agent geneli).

        Returns:
            Basari orani (0.0-1.0).
        """
        if task_type:
            key = f"{agent_name}:{task_type}"
            metric = self._metrics.get(key)
            if not metric or metric.total_count == 0:
                return 0.0
            return metric.success_count / metric.total_count

        # Agent geneli
        total = 0
        success = 0
        for key, metric in self._metrics.items():
            if key.startswith(f"{agent_name}:"):
                total += metric.total_count
                success += metric.success_count
        return success / total if total > 0 else 0.0

    def get_avg_response_time(self, agent_name: str, task_type: str = "") -> float:
        """Ortalama yanit suresini getirir.

        Args:
            agent_name: Agent adi.
            task_type: Gorev tipi.

        Returns:
            Ortalama yanit suresi (ms).
        """
        if task_type:
            key = f"{agent_name}:{task_type}"
            times = self._response_times.get(key, [])
            return sum(times) / len(times) if times else 0.0

        all_times: list[float] = []
        for key, times in self._response_times.items():
            if key.startswith(f"{agent_name}:"):
                all_times.extend(times)
        return sum(all_times) / len(all_times) if all_times else 0.0

    def detect_error_patterns(self, agent_name: str = "", min_count: int = 3) -> list[dict[str, Any]]:
        """Hata kaliplarini tespit eder.

        Args:
            agent_name: Agent adi (bos ise tum agentler).
            min_count: Minimum tekrar sayisi.

        Returns:
            Hata kaliplari listesi.
        """
        patterns: dict[str, int] = {}

        for key, errors in self._errors.items():
            if agent_name and not key.startswith(f"{agent_name}:"):
                continue
            for err in errors:
                msg = err["error"]
                # Basit gruplama: ilk 50 karakter
                pattern_key = msg[:50]
                patterns[pattern_key] = patterns.get(pattern_key, 0) + 1

        result = []
        for pattern, count in patterns.items():
            if count >= min_count:
                result.append({"pattern": pattern, "count": count})

        result.sort(key=lambda x: x["count"], reverse=True)
        return result

    def record_resource_usage(self, cpu_pct: float, memory_mb: float, disk_io: float = 0.0) -> None:
        """Kaynak kullanimini kaydeder.

        Args:
            cpu_pct: CPU kullanim yuzdesi.
            memory_mb: Bellek kullanimi (MB).
            disk_io: Disk I/O (MB/s).
        """
        self._resource_usage.append({
            "cpu_pct": cpu_pct,
            "memory_mb": memory_mb,
            "disk_io": disk_io,
            "timestamp": time.time(),
        })

    def get_resource_trend(self) -> dict[str, float]:
        """Kaynak kullanim trendini getirir.

        Returns:
            Ortalama kaynak kullanimi.
        """
        if not self._resource_usage:
            return {"cpu_pct": 0.0, "memory_mb": 0.0, "disk_io": 0.0}

        count = len(self._resource_usage)
        return {
            "cpu_pct": sum(r["cpu_pct"] for r in self._resource_usage) / count,
            "memory_mb": sum(r["memory_mb"] for r in self._resource_usage) / count,
            "disk_io": sum(r["disk_io"] for r in self._resource_usage) / count,
        }

    def analyze_trend(self, agent_name: str, task_type: str) -> TrendDirection:
        """Performans trendini analiz eder.

        Args:
            agent_name: Agent adi.
            task_type: Gorev tipi.

        Returns:
            TrendDirection degeri.
        """
        key = f"{agent_name}:{task_type}"
        times = self._response_times.get(key, [])

        if len(times) < 4:
            return TrendDirection.STABLE

        mid = len(times) // 2
        first_half = sum(times[:mid]) / mid
        second_half = sum(times[mid:]) / (len(times) - mid)

        ratio = second_half / first_half if first_half > 0 else 1.0

        if ratio < 0.85:
            return TrendDirection.IMPROVING
        if ratio > 1.15:
            return TrendDirection.DECLINING

        # Volatilite kontrolu
        avg = sum(times) / len(times)
        variance = sum((t - avg) ** 2 for t in times) / len(times)
        std_dev = variance ** 0.5
        cv = std_dev / avg if avg > 0 else 0

        if cv > 0.5:
            return TrendDirection.VOLATILE

        return TrendDirection.STABLE

    def get_all_metrics(self) -> list[PerformanceMetric]:
        """Tum metrikleri getirir.

        Returns:
            PerformanceMetric listesi.
        """
        return list(self._metrics.values())

    def get_worst_performers(self, top_k: int = 5) -> list[PerformanceMetric]:
        """En kotu performansli metrikleri getirir.

        Args:
            top_k: Kac tane getirilecek.

        Returns:
            PerformanceMetric listesi.
        """
        metrics = [m for m in self._metrics.values() if m.total_count > 0]
        metrics.sort(key=lambda m: m.error_rate, reverse=True)
        return metrics[:top_k]

    def snapshot(self) -> None:
        """Mevcut metriklerin snapshot'ini alir."""
        for metric in self._metrics.values():
            self._history.append(metric.model_copy())

    def _get_or_create(self, key: str, agent_name: str, task_type: str) -> PerformanceMetric:
        """Metrigi getirir veya olusturur."""
        if key not in self._metrics:
            self._metrics[key] = PerformanceMetric(
                agent_name=agent_name,
                task_type=task_type,
            )
        return self._metrics[key]

    def _update_response_time(self, key: str, response_ms: float) -> None:
        """Yanit suresini gunceller."""
        times = self._response_times.setdefault(key, [])
        times.append(response_ms)
        # Son 100 kayit
        if len(times) > 100:
            self._response_times[key] = times[-100:]

    def _recalculate(self, key: str, metric: PerformanceMetric) -> None:
        """Metrikleri yeniden hesaplar."""
        if metric.total_count > 0:
            metric.error_rate = metric.failure_count / metric.total_count

        times = self._response_times.get(key, [])
        if times:
            metric.avg_response_ms = sum(times) / len(times)
            sorted_times = sorted(times)
            idx = int(len(sorted_times) * 0.95)
            metric.p95_response_ms = sorted_times[min(idx, len(sorted_times) - 1)]

    @property
    def metric_count(self) -> int:
        """Metrik sayisi."""
        return len(self._metrics)

    @property
    def total_errors(self) -> int:
        """Toplam hata sayisi."""
        return sum(len(errs) for errs in self._errors.values())

    @property
    def history(self) -> list[PerformanceMetric]:
        """Metrik gecmisi."""
        return list(self._history)
