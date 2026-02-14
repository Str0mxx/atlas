"""ATLAS Saglik Birlestiricisi modulu.

Sistem saglik toplama, bagimlilik sagligi,
birlesik durum, uyari ve kendini iyilestirme.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Callable

from app.models.bridge import HealthReport, HealthStatus

logger = logging.getLogger(__name__)


class HealthAggregator:
    """Saglik birlestiricisi.

    Tum sistemlerin saglik durumunu toplar,
    birlestirir ve uyari uretir.

    Attributes:
        _reports: Sistem saglik raporlari.
        _checkers: Saglik kontrol fonksiyonlari.
        _healers: Kendini iyilestirme fonksiyonlari.
        _alerts: Uyari gecmisi.
    """

    def __init__(self) -> None:
        """Saglik birlestiricisini baslatir."""
        self._reports: dict[str, HealthReport] = {}
        self._checkers: dict[str, Callable] = {}
        self._healers: dict[str, Callable] = {}
        self._alerts: list[dict[str, Any]] = []
        self._thresholds: dict[str, float] = {}

        logger.info("HealthAggregator baslatildi")

    def register_checker(
        self,
        system_id: str,
        checker: Callable,
    ) -> None:
        """Saglik kontrol fonksiyonu kaydeder.

        Args:
            system_id: Sistem ID.
            checker: Kontrol fonksiyonu () -> HealthStatus.
        """
        self._checkers[system_id] = checker

    def register_healer(
        self,
        system_id: str,
        healer: Callable,
    ) -> None:
        """Kendini iyilestirme fonksiyonu kaydeder.

        Args:
            system_id: Sistem ID.
            healer: Iyilestirme fonksiyonu.
        """
        self._healers[system_id] = healer

    def report_health(
        self,
        system_id: str,
        status: HealthStatus,
        details: dict[str, Any] | None = None,
    ) -> HealthReport:
        """Saglik raporu kaydeder.

        Args:
            system_id: Sistem ID.
            status: Saglik durumu.
            details: Detaylar.

        Returns:
            HealthReport nesnesi.
        """
        report = HealthReport(
            system_id=system_id,
            status=status,
            details=details or {},
        )
        self._reports[system_id] = report

        # Kritik durumlarda uyari
        if status in (HealthStatus.CRITICAL, HealthStatus.WARNING):
            self._alerts.append({
                "system_id": system_id,
                "status": status.value,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

        return report

    def check_all(self) -> dict[str, HealthStatus]:
        """Tum sistemleri kontrol eder.

        Returns:
            Sistem -> durum eslesmesi.
        """
        results: dict[str, HealthStatus] = {}

        for system_id, checker in self._checkers.items():
            try:
                status = checker()
                results[system_id] = status
                self.report_health(system_id, status)
            except Exception as e:
                logger.error("Saglik kontrolu hatasi %s: %s", system_id, e)
                results[system_id] = HealthStatus.UNKNOWN
                self.report_health(system_id, HealthStatus.UNKNOWN)

        return results

    def check_system(self, system_id: str) -> HealthStatus:
        """Tek sistemi kontrol eder.

        Args:
            system_id: Sistem ID.

        Returns:
            Saglik durumu.
        """
        checker = self._checkers.get(system_id)
        if not checker:
            return HealthStatus.UNKNOWN

        try:
            status = checker()
            self.report_health(system_id, status)
            return status
        except Exception:
            self.report_health(system_id, HealthStatus.UNKNOWN)
            return HealthStatus.UNKNOWN

    def get_aggregate_status(self) -> dict[str, Any]:
        """Birlesik saglik durumunu getirir.

        Returns:
            Birlesik durum sozlugu.
        """
        if not self._reports:
            return {
                "overall": HealthStatus.UNKNOWN.value,
                "systems": {},
                "healthy": 0,
                "total": 0,
            }

        statuses = {
            sid: r.status.value for sid, r in self._reports.items()
        }

        healthy = sum(
            1 for r in self._reports.values()
            if r.status == HealthStatus.HEALTHY
        )
        total = len(self._reports)

        # Birlesik durum
        if all(r.status == HealthStatus.HEALTHY for r in self._reports.values()):
            overall = HealthStatus.HEALTHY
        elif any(r.status == HealthStatus.CRITICAL for r in self._reports.values()):
            overall = HealthStatus.CRITICAL
        elif any(r.status == HealthStatus.WARNING for r in self._reports.values()):
            overall = HealthStatus.WARNING
        else:
            overall = HealthStatus.UNKNOWN

        return {
            "overall": overall.value,
            "systems": statuses,
            "healthy": healthy,
            "total": total,
            "health_ratio": round(healthy / total, 3) if total > 0 else 0.0,
        }

    def get_unhealthy_systems(self) -> list[str]:
        """Sagliksiz sistemleri getirir.

        Returns:
            Sistem ID listesi.
        """
        return [
            sid for sid, r in self._reports.items()
            if r.status != HealthStatus.HEALTHY
        ]

    def trigger_healing(self, system_id: str) -> bool:
        """Kendini iyilestirmeyi tetikler.

        Args:
            system_id: Sistem ID.

        Returns:
            Basarili ise True.
        """
        healer = self._healers.get(system_id)
        if not healer:
            return False

        try:
            healer()
            logger.info("Iyilestirme tetiklendi: %s", system_id)
            return True
        except Exception as e:
            logger.error("Iyilestirme hatasi %s: %s", system_id, e)
            return False

    def auto_heal(self) -> list[str]:
        """Sagliksiz sistemleri otomatik iyilestirir.

        Returns:
            Iyilestirilen sistem listesi.
        """
        healed = []
        for system_id in self.get_unhealthy_systems():
            if self.trigger_healing(system_id):
                healed.append(system_id)
        return healed

    def get_health(
        self,
        system_id: str,
    ) -> HealthReport | None:
        """Sistem sagligini getirir.

        Args:
            system_id: Sistem ID.

        Returns:
            HealthReport veya None.
        """
        return self._reports.get(system_id)

    def get_alerts(
        self,
        system_id: str = "",
        limit: int = 0,
    ) -> list[dict[str, Any]]:
        """Uyarilari getirir.

        Args:
            system_id: Sistem filtresi.
            limit: Maks kayit.

        Returns:
            Uyari listesi.
        """
        alerts = list(self._alerts)
        if system_id:
            alerts = [a for a in alerts if a["system_id"] == system_id]
        if limit > 0:
            alerts = alerts[-limit:]
        return alerts

    @property
    def total_reports(self) -> int:
        """Toplam rapor sayisi."""
        return len(self._reports)

    @property
    def healthy_count(self) -> int:
        """Saglikli sistem sayisi."""
        return sum(
            1 for r in self._reports.values()
            if r.status == HealthStatus.HEALTHY
        )

    @property
    def alert_count(self) -> int:
        """Toplam uyari sayisi."""
        return len(self._alerts)
