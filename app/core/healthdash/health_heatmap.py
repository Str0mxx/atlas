"""
Sağlık ısı haritası modülü.

Görsel ısı haritası, renk kodlama,
zaman bazlı görünüm, örüntü tespiti,
sıcak nokta tanımlama.
"""

import logging
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class HealthHeatmap:
    """Sağlık ısı haritası.

    Attributes:
        _cells: Isı haritası hücreleri.
        _snapshots: Zaman snapshot'ları.
        _stats: İstatistikler.
    """

    def __init__(self) -> None:
        """Isı haritasını başlatır."""
        self._cells: list[dict] = []
        self._snapshots: list[dict] = []
        self._stats: dict[str, int] = {
            "cells_added": 0,
            "hotspots_detected": 0,
        }
        logger.info(
            "HealthHeatmap baslatildi"
        )

    @property
    def cell_count(self) -> int:
        """Hücre sayısı."""
        return len(self._cells)

    def add_cell(
        self,
        system_name: str = "",
        metric_name: str = "",
        value: float = 0.0,
        timestamp: str = "",
    ) -> dict[str, Any]:
        """Hücre ekler.

        Args:
            system_name: Sistem adı.
            metric_name: Metrik adı.
            value: Değer (0-100).
            timestamp: Zaman damgası.

        Returns:
            Ekleme bilgisi.
        """
        try:
            cid = f"hc_{uuid4()!s:.8}"

            if value >= 90:
                color = "green"
            elif value >= 70:
                color = "yellow"
            elif value >= 50:
                color = "orange"
            else:
                color = "red"

            record = {
                "cell_id": cid,
                "system_name": system_name,
                "metric_name": metric_name,
                "value": value,
                "color": color,
                "timestamp": timestamp,
            }
            self._cells.append(record)
            self._stats["cells_added"] += 1

            return {
                "cell_id": cid,
                "system_name": system_name,
                "metric_name": metric_name,
                "value": value,
                "color": color,
                "added": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "added": False,
                "error": str(e),
            }

    def generate_heatmap(
        self,
        granularity: str = "system",
    ) -> dict[str, Any]:
        """Isı haritası oluşturur.

        Args:
            granularity: Ayrıntı düzeyi.

        Returns:
            Isı haritası bilgisi.
        """
        try:
            groups: dict[str, list] = {}
            for c in self._cells:
                key = c["system_name"]
                if key not in groups:
                    groups[key] = []
                groups[key].append(c["value"])

            heatmap = []
            for name, values in groups.items():
                avg = (
                    sum(values) / len(values)
                    if values
                    else 0.0
                )
                if avg >= 90:
                    color = "green"
                elif avg >= 70:
                    color = "yellow"
                elif avg >= 50:
                    color = "orange"
                else:
                    color = "red"

                heatmap.append({
                    "system": name,
                    "avg_health": round(avg, 1),
                    "color": color,
                    "data_points": len(values),
                })

            return {
                "granularity": granularity,
                "systems": len(heatmap),
                "heatmap": heatmap,
                "generated": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "generated": False,
                "error": str(e),
            }

    def get_time_view(
        self,
        system_name: str = "",
        periods: int = 5,
    ) -> dict[str, Any]:
        """Zaman bazlı görünüm.

        Args:
            system_name: Sistem adı.
            periods: Dönem sayısı.

        Returns:
            Zaman görünümü bilgisi.
        """
        try:
            filtered = [
                c for c in self._cells
                if c["system_name"] == system_name
            ]

            recent = filtered[-periods:]
            values = [c["value"] for c in recent]

            avg = (
                sum(values) / len(values)
                if values
                else 0.0
            )

            trend = "stable"
            if len(values) >= 2:
                first_half = values[
                    :len(values) // 2
                ]
                second_half = values[
                    len(values) // 2:
                ]
                avg_first = (
                    sum(first_half)
                    / len(first_half)
                    if first_half
                    else 0.0
                )
                avg_second = (
                    sum(second_half)
                    / len(second_half)
                    if second_half
                    else 0.0
                )
                diff = avg_second - avg_first
                if diff > 5:
                    trend = "improving"
                elif diff < -5:
                    trend = "declining"

            return {
                "system_name": system_name,
                "periods": len(recent),
                "values": values,
                "average": round(avg, 1),
                "trend": trend,
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }

    def detect_patterns(
        self,
    ) -> dict[str, Any]:
        """Örüntü tespiti yapar.

        Returns:
            Örüntü bilgisi.
        """
        try:
            groups: dict[str, list] = {}
            for c in self._cells:
                key = c["system_name"]
                if key not in groups:
                    groups[key] = []
                groups[key].append(c["value"])

            patterns = []
            for name, values in groups.items():
                if len(values) < 2:
                    continue

                avg = sum(values) / len(values)
                low_count = sum(
                    1 for v in values if v < 50
                )
                high_var = max(values) - min(values)

                pattern_type = "stable"
                if low_count > len(values) * 0.3:
                    pattern_type = "frequent_issues"
                elif high_var > 40:
                    pattern_type = "volatile"

                patterns.append({
                    "system": name,
                    "pattern": pattern_type,
                    "avg_health": round(avg, 1),
                    "variance": round(
                        high_var, 1
                    ),
                    "low_count": low_count,
                })

            return {
                "patterns_found": len(patterns),
                "patterns": patterns,
                "detected": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "detected": False,
                "error": str(e),
            }

    def identify_hotspots(
        self,
        threshold: float = 50.0,
    ) -> dict[str, Any]:
        """Sıcak noktaları tanımlar.

        Args:
            threshold: Eşik değer.

        Returns:
            Sıcak nokta bilgisi.
        """
        try:
            groups: dict[str, list] = {}
            for c in self._cells:
                key = c["system_name"]
                if key not in groups:
                    groups[key] = []
                groups[key].append(c["value"])

            hotspots = []
            for name, values in groups.items():
                avg = (
                    sum(values) / len(values)
                    if values
                    else 100.0
                )
                if avg < threshold:
                    if avg < 30:
                        severity = "critical"
                    elif avg < 50:
                        severity = "high"
                    else:
                        severity = "medium"

                    hotspots.append({
                        "system": name,
                        "avg_health": round(
                            avg, 1
                        ),
                        "severity": severity,
                        "data_points": len(
                            values
                        ),
                    })

            self._stats[
                "hotspots_detected"
            ] += len(hotspots)

            hotspots.sort(
                key=lambda h: h["avg_health"]
            )

            return {
                "hotspots": hotspots,
                "hotspot_count": len(hotspots),
                "threshold": threshold,
                "identified": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "identified": False,
                "error": str(e),
            }
