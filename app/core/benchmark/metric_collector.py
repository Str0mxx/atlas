"""ATLAS Benchmark Metrik Toplayici modulu.

Gercek zamanli toplama, tarihsel veri,
toplulastirma, ornekleme, depolama.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class BenchmarkMetricCollector:
    """Benchmark metrik toplayici.

    Benchmark metriklerini toplar ve depolar.

    Attributes:
        _metrics: Metrik depolama.
        _samples: Ornek kayitlari.
    """

    def __init__(
        self,
        max_samples: int = 10000,
    ) -> None:
        """Metrik toplayiciyi baslatir.

        Args:
            max_samples: Maks ornek sayisi.
        """
        self._metrics: dict[
            str, list[dict[str, Any]]
        ] = {}
        self._latest: dict[
            str, dict[str, Any]
        ] = {}
        self._max_samples = max_samples
        self._stats = {
            "collected": 0,
            "kpis_tracked": 0,
        }

        logger.info(
            "BenchmarkMetricCollector baslatildi",
        )

    def collect(
        self,
        kpi_id: str,
        value: float,
        tags: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Metrik toplar.

        Args:
            kpi_id: KPI ID.
            value: Deger.
            tags: Etiketler.

        Returns:
            Toplama bilgisi.
        """
        now = time.time()
        sample = {
            "kpi_id": kpi_id,
            "value": value,
            "tags": tags or {},
            "timestamp": now,
        }

        if kpi_id not in self._metrics:
            self._metrics[kpi_id] = []
            self._stats["kpis_tracked"] += 1

        self._metrics[kpi_id].append(sample)

        # Max ornek siniri
        if len(self._metrics[kpi_id]) > self._max_samples:
            self._metrics[kpi_id] = (
                self._metrics[kpi_id][
                    -self._max_samples:
                ]
            )

        self._latest[kpi_id] = sample
        self._stats["collected"] += 1

        return {
            "kpi_id": kpi_id,
            "value": value,
            "collected": True,
        }

    def get_latest(
        self,
        kpi_id: str,
    ) -> dict[str, Any] | None:
        """Son metrigi getirir.

        Args:
            kpi_id: KPI ID.

        Returns:
            Son metrik veya None.
        """
        return self._latest.get(kpi_id)

    def get_history(
        self,
        kpi_id: str,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Metrik gecmisini getirir.

        Args:
            kpi_id: KPI ID.
            limit: Limit.

        Returns:
            Gecmis kayitlari.
        """
        samples = self._metrics.get(kpi_id, [])
        return list(samples[-limit:])

    def aggregate(
        self,
        kpi_id: str,
        period_seconds: int = 3600,
    ) -> dict[str, Any]:
        """Metrikleri topluIastirir.

        Args:
            kpi_id: KPI ID.
            period_seconds: Periyot (sn).

        Returns:
            Toplulastirma sonucu.
        """
        cutoff = time.time() - period_seconds
        samples = self._metrics.get(kpi_id, [])
        recent = [
            s for s in samples
            if s["timestamp"] > cutoff
        ]

        if not recent:
            return {
                "kpi_id": kpi_id,
                "count": 0,
                "avg": 0.0,
            }

        values = [s["value"] for s in recent]
        avg = sum(values) / len(values)
        min_v = min(values)
        max_v = max(values)

        return {
            "kpi_id": kpi_id,
            "count": len(values),
            "avg": round(avg, 4),
            "min": min_v,
            "max": max_v,
            "sum": round(sum(values), 4),
            "period_seconds": period_seconds,
        }

    def sample(
        self,
        kpi_id: str,
        count: int = 10,
    ) -> list[float]:
        """Ornekler.

        Args:
            kpi_id: KPI ID.
            count: Ornek sayisi.

        Returns:
            Ornek degerleri.
        """
        samples = self._metrics.get(kpi_id, [])
        recent = samples[-count:]
        return [s["value"] for s in recent]

    def get_all_latest(
        self,
    ) -> dict[str, dict[str, Any]]:
        """Tum son metrikleri getirir.

        Returns:
            Son metrik haritasi.
        """
        return dict(self._latest)

    @property
    def metric_count(self) -> int:
        """Izlenen metrik sayisi."""
        return len(self._metrics)

    @property
    def total_samples(self) -> int:
        """Toplam ornek sayisi."""
        return sum(
            len(v) for v in self._metrics.values()
        )
