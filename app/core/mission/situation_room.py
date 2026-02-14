"""ATLAS Durum Odasi modulu.

Canli dashboard verisi, uyari yonetimi,
karar destegi, ne-olur analizi ve paydas guncellemeleri.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from app.models.mission import AlertSeverity, MissionAlert

logger = logging.getLogger(__name__)


class SituationRoom:
    """Durum odasi.

    Canli gorev durumunu izler, uyarilari yonetir,
    karar destegi saglar.

    Attributes:
        _alerts: Uyarilar.
        _dashboards: Dashboard verileri.
        _decisions: Karar kayitlari.
        _stakeholder_updates: Paydas guncellemeleri.
    """

    def __init__(self) -> None:
        """Durum odasini baslatir."""
        self._alerts: list[MissionAlert] = []
        self._dashboards: dict[str, dict[str, Any]] = {}
        self._decisions: list[dict[str, Any]] = []
        self._stakeholder_updates: list[dict[str, Any]] = []

        logger.info("SituationRoom baslatildi")

    def raise_alert(
        self,
        mission_id: str,
        message: str,
        severity: AlertSeverity = AlertSeverity.INFO,
        source: str = "",
    ) -> MissionAlert:
        """Uyari olusturur.

        Args:
            mission_id: Gorev ID.
            message: Uyari mesaji.
            severity: Siddet seviyesi.
            source: Kaynak.

        Returns:
            MissionAlert nesnesi.
        """
        alert = MissionAlert(
            mission_id=mission_id,
            message=message,
            severity=severity,
            source=source,
        )
        self._alerts.append(alert)

        logger.warning(
            "Uyari [%s]: %s (%s)",
            severity.value, message, mission_id,
        )
        return alert

    def acknowledge_alert(self, alert_id: str) -> bool:
        """Uyariyi onaylar.

        Args:
            alert_id: Uyari ID.

        Returns:
            Basarili ise True.
        """
        for alert in self._alerts:
            if alert.alert_id == alert_id and not alert.acknowledged:
                alert.acknowledged = True
                return True
        return False

    def get_alerts(
        self,
        mission_id: str = "",
        severity: AlertSeverity | None = None,
        active_only: bool = True,
    ) -> list[MissionAlert]:
        """Uyarilari getirir.

        Args:
            mission_id: Gorev filtresi.
            severity: Siddet filtresi.
            active_only: Sadece onaylanmamislar.

        Returns:
            Uyari listesi.
        """
        alerts = list(self._alerts)
        if mission_id:
            alerts = [a for a in alerts if a.mission_id == mission_id]
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        if active_only:
            alerts = [a for a in alerts if not a.acknowledged]
        return alerts

    def update_dashboard(
        self,
        mission_id: str,
        data: dict[str, Any],
    ) -> None:
        """Dashboard verisini gunceller.

        Args:
            mission_id: Gorev ID.
            data: Dashboard verisi.
        """
        existing = self._dashboards.get(mission_id, {})
        existing.update(data)
        existing["last_updated"] = datetime.now(timezone.utc).isoformat()
        self._dashboards[mission_id] = existing

    def get_dashboard(self, mission_id: str) -> dict[str, Any]:
        """Dashboard verisini getirir.

        Args:
            mission_id: Gorev ID.

        Returns:
            Dashboard sozlugu.
        """
        return dict(self._dashboards.get(mission_id, {}))

    def record_decision(
        self,
        mission_id: str,
        decision: str,
        rationale: str = "",
        decided_by: str = "",
    ) -> dict[str, Any]:
        """Karar kaydeder.

        Args:
            mission_id: Gorev ID.
            decision: Karar.
            rationale: Gerekce.
            decided_by: Karar veren.

        Returns:
            Karar kaydi.
        """
        record = {
            "mission_id": mission_id,
            "decision": decision,
            "rationale": rationale,
            "decided_by": decided_by,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._decisions.append(record)
        return record

    def get_decisions(
        self,
        mission_id: str,
    ) -> list[dict[str, Any]]:
        """Kararlari getirir.

        Args:
            mission_id: Gorev ID.

        Returns:
            Karar listesi.
        """
        return [
            d for d in self._decisions
            if d["mission_id"] == mission_id
        ]

    def what_if_analysis(
        self,
        mission_id: str,
        scenario: str,
        impact: dict[str, Any],
    ) -> dict[str, Any]:
        """Ne-olur analizi yapar.

        Args:
            mission_id: Gorev ID.
            scenario: Senaryo aciklamasi.
            impact: Etki degerlendirmesi.

        Returns:
            Analiz sonucu.
        """
        dashboard = self._dashboards.get(mission_id, {})
        current_progress = dashboard.get("progress", 0.0)

        progress_impact = impact.get("progress_change", 0.0)
        risk_level = impact.get("risk_level", "medium")
        delay_hours = impact.get("delay_hours", 0.0)

        result = {
            "mission_id": mission_id,
            "scenario": scenario,
            "current_progress": current_progress,
            "projected_progress": max(
                0.0, min(1.0, current_progress + progress_impact),
            ),
            "risk_level": risk_level,
            "delay_hours": delay_hours,
            "recommendation": "proceed" if risk_level == "low" else "review",
        }
        return result

    def send_stakeholder_update(
        self,
        mission_id: str,
        summary: str,
        recipients: list[str] | None = None,
    ) -> dict[str, Any]:
        """Paydas guncellemesi gonderir.

        Args:
            mission_id: Gorev ID.
            summary: Ozet.
            recipients: Alicilar.

        Returns:
            Guncelleme kaydi.
        """
        update = {
            "mission_id": mission_id,
            "summary": summary,
            "recipients": recipients or [],
            "sent_at": datetime.now(timezone.utc).isoformat(),
        }
        self._stakeholder_updates.append(update)
        return update

    def get_stakeholder_updates(
        self,
        mission_id: str,
    ) -> list[dict[str, Any]]:
        """Paydas guncellemelerini getirir.

        Args:
            mission_id: Gorev ID.

        Returns:
            Guncelleme listesi.
        """
        return [
            u for u in self._stakeholder_updates
            if u["mission_id"] == mission_id
        ]

    @property
    def total_alerts(self) -> int:
        """Toplam uyari sayisi."""
        return len(self._alerts)

    @property
    def active_alert_count(self) -> int:
        """Aktif uyari sayisi."""
        return sum(1 for a in self._alerts if not a.acknowledged)

    @property
    def critical_alert_count(self) -> int:
        """Kritik uyari sayisi."""
        return sum(
            1 for a in self._alerts
            if not a.acknowledged
            and a.severity in (AlertSeverity.CRITICAL, AlertSeverity.EMERGENCY)
        )
