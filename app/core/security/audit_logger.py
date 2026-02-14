"""ATLAS Denetim Gunlugu modulu.

Guvenlik olaylari loglama, erisim
kayitlari, degisiklik takibi, uyumluluk
raporlama ve adli analiz.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from app.models.security_hardening import (
    AuditEntry,
    AuditEventType,
    ThreatLevel,
)

logger = logging.getLogger(__name__)


class AuditLogger:
    """Denetim gunlugu.

    Guvenlik olaylarini kaydeder,
    raporlar ve analiz eder.

    Attributes:
        _entries: Denetim girdileri.
        _retention_days: Saklama suresi (gun).
        _alerts: Olusturulan uyarilar.
    """

    def __init__(
        self,
        retention_days: int = 90,
    ) -> None:
        """Denetim gunlugunu baslatir.

        Args:
            retention_days: Saklama suresi (gun).
        """
        self._entries: list[AuditEntry] = []
        self._retention_days = max(1, retention_days)
        self._alerts: list[dict[str, Any]] = []

        logger.info(
            "AuditLogger baslatildi (retention=%d gun)",
            self._retention_days,
        )

    def log_event(
        self,
        event_type: AuditEventType,
        actor: str,
        action: str,
        resource: str = "",
        details: dict[str, Any] | None = None,
        severity: ThreatLevel = ThreatLevel.NONE,
    ) -> AuditEntry:
        """Olay kaydeder.

        Args:
            event_type: Olay turu.
            actor: Aksiyonu yapan.
            action: Aksiyon.
            resource: Kaynak.
            details: Ek detaylar.
            severity: Onem derecesi.

        Returns:
            Denetim girdisi.
        """
        entry = AuditEntry(
            event_type=event_type,
            actor=actor,
            action=action,
            resource=resource,
            details=details or {},
            severity=severity,
        )
        self._entries.append(entry)

        # Yuksek onem uyarisi
        if severity in (ThreatLevel.HIGH, ThreatLevel.CRITICAL):
            self._create_alert(entry)

        logger.info(
            "Denetim kaydi: [%s] %s -> %s (%s)",
            event_type.value, actor, action, resource,
        )
        return entry

    def log_login(
        self,
        user: str,
        success: bool,
        ip_address: str = "",
    ) -> AuditEntry:
        """Giris olayini kaydeder.

        Args:
            user: Kullanici.
            success: Basarili mi.
            ip_address: IP adresi.

        Returns:
            Denetim girdisi.
        """
        severity = ThreatLevel.NONE if success else ThreatLevel.LOW
        return self.log_event(
            event_type=AuditEventType.LOGIN,
            actor=user,
            action="login_success" if success else "login_failure",
            details={"ip_address": ip_address, "success": success},
            severity=severity,
        )

    def log_access(
        self,
        user: str,
        resource: str,
        action: str,
        granted: bool,
    ) -> AuditEntry:
        """Erisim olayini kaydeder.

        Args:
            user: Kullanici.
            resource: Kaynak.
            action: Aksiyon.
            granted: Izin verildi mi.

        Returns:
            Denetim girdisi.
        """
        severity = ThreatLevel.NONE if granted else ThreatLevel.MEDIUM
        return self.log_event(
            event_type=AuditEventType.ACCESS,
            actor=user,
            action=action,
            resource=resource,
            details={"granted": granted},
            severity=severity,
        )

    def log_change(
        self,
        actor: str,
        resource: str,
        old_value: str = "",
        new_value: str = "",
    ) -> AuditEntry:
        """Degisiklik olayini kaydeder.

        Args:
            actor: Degisikligi yapan.
            resource: Degisen kaynak.
            old_value: Eski deger.
            new_value: Yeni deger.

        Returns:
            Denetim girdisi.
        """
        return self.log_event(
            event_type=AuditEventType.CHANGE,
            actor=actor,
            action="change",
            resource=resource,
            details={
                "old_value": old_value,
                "new_value": new_value,
            },
        )

    def log_threat(
        self,
        source: str,
        threat_type: str,
        description: str = "",
        severity: ThreatLevel = ThreatLevel.HIGH,
    ) -> AuditEntry:
        """Tehdit olayini kaydeder.

        Args:
            source: Tehdit kaynagi.
            threat_type: Tehdit turu.
            description: Aciklama.
            severity: Onem derecesi.

        Returns:
            Denetim girdisi.
        """
        return self.log_event(
            event_type=AuditEventType.THREAT,
            actor=source,
            action=threat_type,
            details={"description": description},
            severity=severity,
        )

    def get_entries(
        self,
        event_type: AuditEventType | None = None,
        actor: str = "",
        severity: ThreatLevel | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Denetim girdilerini getirir.

        Args:
            event_type: Olay turu filtresi.
            actor: Aktor filtresi.
            severity: Onem filtresi.
            limit: Maks kayit.

        Returns:
            Girdi listesi.
        """
        entries = self._entries

        if event_type:
            entries = [
                e for e in entries
                if e.event_type == event_type
            ]
        if actor:
            entries = [
                e for e in entries
                if e.actor == actor
            ]
        if severity:
            entries = [
                e for e in entries
                if e.severity == severity
            ]

        return [
            {
                "entry_id": e.entry_id,
                "event_type": e.event_type.value,
                "actor": e.actor,
                "action": e.action,
                "resource": e.resource,
                "severity": e.severity.value,
                "timestamp": e.timestamp.isoformat(),
            }
            for e in entries[-limit:]
        ]

    def get_compliance_report(self) -> dict[str, Any]:
        """Uyumluluk raporu olusturur.

        Returns:
            Rapor verisi.
        """
        total = len(self._entries)
        by_type: dict[str, int] = {}
        by_severity: dict[str, int] = {}
        failed_logins = 0
        access_denials = 0

        for entry in self._entries:
            t = entry.event_type.value
            by_type[t] = by_type.get(t, 0) + 1

            s = entry.severity.value
            by_severity[s] = by_severity.get(s, 0) + 1

            if (entry.event_type == AuditEventType.LOGIN
                    and entry.action == "login_failure"):
                failed_logins += 1

            if (entry.event_type == AuditEventType.ACCESS
                    and not entry.details.get("granted", True)):
                access_denials += 1

        return {
            "total_entries": total,
            "by_type": by_type,
            "by_severity": by_severity,
            "failed_logins": failed_logins,
            "access_denials": access_denials,
            "alerts": len(self._alerts),
            "retention_days": self._retention_days,
            "generated_at": datetime.now(
                timezone.utc,
            ).isoformat(),
        }

    def get_forensic_timeline(
        self,
        actor: str = "",
        resource: str = "",
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Adli analiz zaman cizelgesi olusturur.

        Args:
            actor: Aktor filtresi.
            resource: Kaynak filtresi.
            limit: Maks kayit.

        Returns:
            Zaman cizelgesi.
        """
        entries = self._entries

        if actor:
            entries = [
                e for e in entries
                if e.actor == actor
            ]
        if resource:
            entries = [
                e for e in entries
                if e.resource == resource
            ]

        return [
            {
                "timestamp": e.timestamp.isoformat(),
                "event_type": e.event_type.value,
                "actor": e.actor,
                "action": e.action,
                "resource": e.resource,
                "severity": e.severity.value,
                "details": e.details,
            }
            for e in entries[-limit:]
        ]

    def _create_alert(
        self,
        entry: AuditEntry,
    ) -> None:
        """Uyari olusturur.

        Args:
            entry: Kaynak denetim girdisi.
        """
        alert = {
            "entry_id": entry.entry_id,
            "event_type": entry.event_type.value,
            "actor": entry.actor,
            "severity": entry.severity.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._alerts.append(alert)
        logger.warning(
            "Guvenlik uyarisi: [%s] %s (%s)",
            entry.severity.value,
            entry.action,
            entry.actor,
        )

    @property
    def entry_count(self) -> int:
        """Girdi sayisi."""
        return len(self._entries)

    @property
    def alert_count(self) -> int:
        """Uyari sayisi."""
        return len(self._alerts)

    @property
    def retention_days(self) -> int:
        """Saklama suresi (gun)."""
        return self._retention_days
