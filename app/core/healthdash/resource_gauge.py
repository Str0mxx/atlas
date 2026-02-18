"""
Kaynak göstergesi modülü.

CPU izleme, bellek kullanımı,
disk alanı, ağ bant genişliği,
eşik uyarıları.
"""

import logging
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class ResourceGauge:
    """Kaynak göstergesi.

    Attributes:
        _gauges: Gösterge kayıtları.
        _readings: Okuma geçmişi.
        _stats: İstatistikler.
    """

    def __init__(self) -> None:
        """Göstergeyi başlatır."""
        self._gauges: list[dict] = []
        self._readings: list[dict] = []
        self._stats: dict[str, int] = {
            "gauges_created": 0,
            "alerts_triggered": 0,
        }
        logger.info(
            "ResourceGauge baslatildi"
        )

    @property
    def gauge_count(self) -> int:
        """Gösterge sayısı."""
        return len(self._gauges)

    def create_gauge(
        self,
        resource_type: str = "cpu",
        label: str = "",
        unit: str = "%",
        threshold_warning: float = 70.0,
        threshold_critical: float = 90.0,
    ) -> dict[str, Any]:
        """Gösterge oluşturur.

        Args:
            resource_type: Kaynak türü.
            label: Etiket.
            unit: Birim.
            threshold_warning: Uyarı eşiği.
            threshold_critical: Kritik eşik.

        Returns:
            Gösterge bilgisi.
        """
        try:
            gid = f"rg_{uuid4()!s:.8}"

            record = {
                "gauge_id": gid,
                "resource_type": resource_type,
                "label": label or resource_type,
                "unit": unit,
                "current_value": 0.0,
                "threshold_warning": (
                    threshold_warning
                ),
                "threshold_critical": (
                    threshold_critical
                ),
                "status": "normal",
            }
            self._gauges.append(record)
            self._stats[
                "gauges_created"
            ] += 1

            return {
                "gauge_id": gid,
                "resource_type": resource_type,
                "label": record["label"],
                "unit": unit,
                "created": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "created": False,
                "error": str(e),
            }

    def update_reading(
        self,
        gauge_id: str = "",
        value: float = 0.0,
    ) -> dict[str, Any]:
        """Okuma günceller.

        Args:
            gauge_id: Gösterge ID.
            value: Değer.

        Returns:
            Güncelleme bilgisi.
        """
        try:
            gauge = None
            for g in self._gauges:
                if g["gauge_id"] == gauge_id:
                    gauge = g
                    break

            if not gauge:
                return {
                    "updated": False,
                    "error": "gauge_not_found",
                }

            prev_value = gauge["current_value"]
            gauge["current_value"] = value

            if value >= gauge[
                "threshold_critical"
            ]:
                status = "critical"
            elif value >= gauge[
                "threshold_warning"
            ]:
                status = "warning"
            else:
                status = "normal"

            prev_status = gauge["status"]
            gauge["status"] = status

            alert = (
                status != "normal"
                and prev_status == "normal"
            )
            if alert:
                self._stats[
                    "alerts_triggered"
                ] += 1

            self._readings.append({
                "gauge_id": gauge_id,
                "value": value,
                "status": status,
            })

            return {
                "gauge_id": gauge_id,
                "value": value,
                "unit": gauge["unit"],
                "status": status,
                "previous_value": prev_value,
                "alert_triggered": alert,
                "updated": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "updated": False,
                "error": str(e),
            }

    def monitor_cpu(
        self,
        usage_percent: float = 0.0,
        cores: int = 4,
    ) -> dict[str, Any]:
        """CPU izler.

        Args:
            usage_percent: Kullanım yüzdesi.
            cores: Çekirdek sayısı.

        Returns:
            CPU bilgisi.
        """
        try:
            if usage_percent >= 90:
                status = "critical"
            elif usage_percent >= 70:
                status = "warning"
            else:
                status = "normal"

            per_core = round(
                usage_percent / cores, 1
            )

            return {
                "resource": "cpu",
                "usage_percent": usage_percent,
                "cores": cores,
                "per_core_avg": per_core,
                "status": status,
                "monitored": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "monitored": False,
                "error": str(e),
            }

    def monitor_memory(
        self,
        used_mb: float = 0.0,
        total_mb: float = 8192.0,
    ) -> dict[str, Any]:
        """Bellek izler.

        Args:
            used_mb: Kullanılan (MB).
            total_mb: Toplam (MB).

        Returns:
            Bellek bilgisi.
        """
        try:
            usage_pct = (
                (used_mb / total_mb * 100.0)
                if total_mb > 0
                else 0.0
            )
            available_mb = total_mb - used_mb

            if usage_pct >= 90:
                status = "critical"
            elif usage_pct >= 70:
                status = "warning"
            else:
                status = "normal"

            return {
                "resource": "memory",
                "used_mb": used_mb,
                "total_mb": total_mb,
                "available_mb": round(
                    available_mb, 1
                ),
                "usage_percent": round(
                    usage_pct, 1
                ),
                "status": status,
                "monitored": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "monitored": False,
                "error": str(e),
            }

    def monitor_disk(
        self,
        used_gb: float = 0.0,
        total_gb: float = 100.0,
    ) -> dict[str, Any]:
        """Disk izler.

        Args:
            used_gb: Kullanılan (GB).
            total_gb: Toplam (GB).

        Returns:
            Disk bilgisi.
        """
        try:
            usage_pct = (
                (used_gb / total_gb * 100.0)
                if total_gb > 0
                else 0.0
            )
            free_gb = total_gb - used_gb

            if usage_pct >= 90:
                status = "critical"
            elif usage_pct >= 80:
                status = "warning"
            else:
                status = "normal"

            return {
                "resource": "disk",
                "used_gb": used_gb,
                "total_gb": total_gb,
                "free_gb": round(free_gb, 1),
                "usage_percent": round(
                    usage_pct, 1
                ),
                "status": status,
                "monitored": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "monitored": False,
                "error": str(e),
            }

    def monitor_network(
        self,
        bandwidth_mbps: float = 0.0,
        max_bandwidth_mbps: float = 1000.0,
    ) -> dict[str, Any]:
        """Ağ bant genişliği izler.

        Args:
            bandwidth_mbps: Kullanım (Mbps).
            max_bandwidth_mbps: Max (Mbps).

        Returns:
            Ağ bilgisi.
        """
        try:
            usage_pct = (
                (
                    bandwidth_mbps
                    / max_bandwidth_mbps
                    * 100.0
                )
                if max_bandwidth_mbps > 0
                else 0.0
            )

            if usage_pct >= 90:
                status = "critical"
            elif usage_pct >= 70:
                status = "warning"
            else:
                status = "normal"

            return {
                "resource": "network",
                "bandwidth_mbps": bandwidth_mbps,
                "max_bandwidth_mbps": (
                    max_bandwidth_mbps
                ),
                "usage_percent": round(
                    usage_pct, 1
                ),
                "status": status,
                "monitored": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "monitored": False,
                "error": str(e),
            }

    def check_thresholds(
        self,
    ) -> dict[str, Any]:
        """Eşik kontrolleri yapar.

        Returns:
            Eşik kontrol bilgisi.
        """
        try:
            alerts = []
            for g in self._gauges:
                if g["status"] == "critical":
                    alerts.append({
                        "gauge_id": g[
                            "gauge_id"
                        ],
                        "resource": g[
                            "resource_type"
                        ],
                        "value": g[
                            "current_value"
                        ],
                        "threshold": g[
                            "threshold_critical"
                        ],
                        "severity": "critical",
                    })
                elif g["status"] == "warning":
                    alerts.append({
                        "gauge_id": g[
                            "gauge_id"
                        ],
                        "resource": g[
                            "resource_type"
                        ],
                        "value": g[
                            "current_value"
                        ],
                        "threshold": g[
                            "threshold_warning"
                        ],
                        "severity": "warning",
                    })

            return {
                "alerts": alerts,
                "alert_count": len(alerts),
                "total_gauges": len(
                    self._gauges
                ),
                "checked": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "checked": False,
                "error": str(e),
            }
