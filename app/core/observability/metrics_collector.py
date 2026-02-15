"""ATLAS Metrik Toplayici modulu.

Counter, gauge, histogram metrikleri,
ozel metrikler, toplulaştirma,
etiketleme ve disa aktarma.
"""

import logging
import math
import time
from typing import Any

logger = logging.getLogger(__name__)


class MetricsCollector:
    """Metrik toplayici.

    Cesitli metrikleri toplar ve raporlar.

    Attributes:
        _counters: Sayac metrikleri.
        _gauges: Gosterge metrikleri.
        _histograms: Histogram metrikleri.
    """

    def __init__(self) -> None:
        """Metrik toplayiciyi baslatir."""
        self._counters: dict[
            str, dict[str, Any]
        ] = {}
        self._gauges: dict[
            str, dict[str, Any]
        ] = {}
        self._histograms: dict[
            str, dict[str, Any]
        ] = {}
        self._custom: dict[
            str, dict[str, Any]
        ] = {}
        self._snapshots: list[
            dict[str, Any]
        ] = []

        logger.info("MetricsCollector baslatildi")

    def increment(
        self,
        name: str,
        value: float = 1.0,
        labels: dict[str, str] | None = None,
    ) -> float:
        """Sayaci arttirir.

        Args:
            name: Metrik adi.
            value: Artis miktari.
            labels: Etiketler.

        Returns:
            Yeni deger.
        """
        key = self._make_key(name, labels)
        if key not in self._counters:
            self._counters[key] = {
                "name": name,
                "value": 0.0,
                "labels": labels or {},
                "created_at": time.time(),
            }
        self._counters[key]["value"] += value
        self._counters[key]["updated_at"] = (
            time.time()
        )
        return self._counters[key]["value"]

    def get_counter(
        self,
        name: str,
        labels: dict[str, str] | None = None,
    ) -> float:
        """Sayac degerini getirir.

        Args:
            name: Metrik adi.
            labels: Etiketler.

        Returns:
            Deger.
        """
        key = self._make_key(name, labels)
        counter = self._counters.get(key)
        return counter["value"] if counter else 0.0

    def set_gauge(
        self,
        name: str,
        value: float,
        labels: dict[str, str] | None = None,
    ) -> None:
        """Gosterge ayarlar.

        Args:
            name: Metrik adi.
            value: Deger.
            labels: Etiketler.
        """
        key = self._make_key(name, labels)
        self._gauges[key] = {
            "name": name,
            "value": value,
            "labels": labels or {},
            "updated_at": time.time(),
        }

    def get_gauge(
        self,
        name: str,
        labels: dict[str, str] | None = None,
    ) -> float | None:
        """Gosterge degerini getirir.

        Args:
            name: Metrik adi.
            labels: Etiketler.

        Returns:
            Deger veya None.
        """
        key = self._make_key(name, labels)
        gauge = self._gauges.get(key)
        return gauge["value"] if gauge else None

    def observe(
        self,
        name: str,
        value: float,
        labels: dict[str, str] | None = None,
    ) -> None:
        """Histogram gozlemi ekler.

        Args:
            name: Metrik adi.
            value: Gozlem degeri.
            labels: Etiketler.
        """
        key = self._make_key(name, labels)
        if key not in self._histograms:
            self._histograms[key] = {
                "name": name,
                "values": [],
                "labels": labels or {},
                "created_at": time.time(),
            }
        self._histograms[key]["values"].append(value)
        self._histograms[key]["updated_at"] = (
            time.time()
        )

    def get_histogram(
        self,
        name: str,
        labels: dict[str, str] | None = None,
    ) -> dict[str, Any] | None:
        """Histogram istatistikleri getirir.

        Args:
            name: Metrik adi.
            labels: Etiketler.

        Returns:
            Istatistikler veya None.
        """
        key = self._make_key(name, labels)
        hist = self._histograms.get(key)
        if not hist or not hist["values"]:
            return None

        values = hist["values"]
        sorted_vals = sorted(values)
        n = len(values)

        return {
            "name": name,
            "count": n,
            "sum": sum(values),
            "min": sorted_vals[0],
            "max": sorted_vals[-1],
            "mean": sum(values) / n,
            "p50": self._percentile(
                sorted_vals, 50,
            ),
            "p95": self._percentile(
                sorted_vals, 95,
            ),
            "p99": self._percentile(
                sorted_vals, 99,
            ),
        }

    def set_custom(
        self,
        name: str,
        value: Any,
        metric_type: str = "custom",
        labels: dict[str, str] | None = None,
    ) -> None:
        """Ozel metrik ayarlar.

        Args:
            name: Metrik adi.
            value: Deger.
            metric_type: Tip.
            labels: Etiketler.
        """
        self._custom[name] = {
            "name": name,
            "value": value,
            "type": metric_type,
            "labels": labels or {},
            "updated_at": time.time(),
        }

    def get_custom(
        self,
        name: str,
    ) -> Any | None:
        """Ozel metrik degerini getirir.

        Args:
            name: Metrik adi.

        Returns:
            Deger veya None.
        """
        entry = self._custom.get(name)
        return entry["value"] if entry else None

    def aggregate(self) -> dict[str, Any]:
        """Tum metrikleri toplulastirir.

        Returns:
            Toplu metrik raporu.
        """
        report = {
            "counters": {},
            "gauges": {},
            "histograms": {},
            "custom": {},
            "timestamp": time.time(),
        }

        for key, c in self._counters.items():
            report["counters"][c["name"]] = (
                c["value"]
            )

        for key, g in self._gauges.items():
            report["gauges"][g["name"]] = (
                g["value"]
            )

        for key, h in self._histograms.items():
            if h["values"]:
                report["histograms"][h["name"]] = {
                    "count": len(h["values"]),
                    "mean": (
                        sum(h["values"])
                        / len(h["values"])
                    ),
                }

        for name, c in self._custom.items():
            report["custom"][name] = c["value"]

        self._snapshots.append(report)
        return report

    def export_prometheus(self) -> str:
        """Prometheus formatinda disa aktarir.

        Returns:
            Prometheus metrikleri.
        """
        lines = []

        for key, c in self._counters.items():
            label_str = self._format_labels(
                c["labels"],
            )
            lines.append(
                f'{c["name"]}{label_str} '
                f'{c["value"]}'
            )

        for key, g in self._gauges.items():
            label_str = self._format_labels(
                g["labels"],
            )
            lines.append(
                f'{g["name"]}{label_str} '
                f'{g["value"]}'
            )

        return "\n".join(lines)

    def reset(self) -> dict[str, int]:
        """Tum metrikleri sifirlar.

        Returns:
            Sifirlanan sayilar.
        """
        counts = {
            "counters": len(self._counters),
            "gauges": len(self._gauges),
            "histograms": len(self._histograms),
            "custom": len(self._custom),
        }
        self._counters.clear()
        self._gauges.clear()
        self._histograms.clear()
        self._custom.clear()
        return counts

    def _make_key(
        self,
        name: str,
        labels: dict[str, str] | None,
    ) -> str:
        """Metrik anahtari olusturur.

        Args:
            name: Metrik adi.
            labels: Etiketler.

        Returns:
            Anahtar.
        """
        if not labels:
            return name
        label_parts = sorted(
            f"{k}={v}" for k, v in labels.items()
        )
        return f"{name}{{{','.join(label_parts)}}}"

    def _format_labels(
        self,
        labels: dict[str, str],
    ) -> str:
        """Etiket formatlar.

        Args:
            labels: Etiketler.

        Returns:
            Formatlanmis etiket.
        """
        if not labels:
            return ""
        parts = [
            f'{k}="{v}"'
            for k, v in sorted(labels.items())
        ]
        return "{" + ",".join(parts) + "}"

    def _percentile(
        self,
        sorted_vals: list[float],
        pct: float,
    ) -> float:
        """Yuzdelik deger hesaplar.

        Args:
            sorted_vals: Siralanmis degerler.
            pct: Yuzdelik.

        Returns:
            Yuzdelik degeri.
        """
        n = len(sorted_vals)
        if n == 0:
            return 0.0
        idx = (pct / 100.0) * (n - 1)
        lower = int(math.floor(idx))
        upper = min(lower + 1, n - 1)
        frac = idx - lower
        return (
            sorted_vals[lower] * (1 - frac)
            + sorted_vals[upper] * frac
        )

    @property
    def counter_count(self) -> int:
        """Sayac sayisi."""
        return len(self._counters)

    @property
    def gauge_count(self) -> int:
        """Gosterge sayisi."""
        return len(self._gauges)

    @property
    def histogram_count(self) -> int:
        """Histogram sayisi."""
        return len(self._histograms)

    @property
    def total_metrics(self) -> int:
        """Toplam metrik sayisi."""
        return (
            len(self._counters)
            + len(self._gauges)
            + len(self._histograms)
            + len(self._custom)
        )
