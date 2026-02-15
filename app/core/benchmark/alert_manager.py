"""ATLAS Benchmark Uyari Yoneticisi modulu.

Esik uyarilari, trend uyarilari,
anomali uyarilari, iyilestirme uyarilari, bozulma uyarilari.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class BenchmarkAlertManager:
    """Benchmark uyari yoneticisi.

    Benchmark uyarilarini yonetir.

    Attributes:
        _alerts: Uyari kayitlari.
        _rules: Uyari kurallari.
    """

    def __init__(self) -> None:
        """Uyari yoneticisini baslatir."""
        self._alerts: list[
            dict[str, Any]
        ] = []
        self._rules: dict[
            str, dict[str, Any]
        ] = {}
        self._active: dict[
            str, dict[str, Any]
        ] = {}
        self._stats = {
            "triggered": 0,
            "acknowledged": 0,
            "resolved": 0,
        }

        logger.info(
            "BenchmarkAlertManager baslatildi",
        )

    def add_rule(
        self,
        rule_id: str,
        kpi_id: str,
        condition: str,
        threshold: float,
        severity: str = "warning",
    ) -> dict[str, Any]:
        """Uyari kurali ekler.

        Args:
            rule_id: Kural ID.
            kpi_id: KPI ID.
            condition: Kosul (below/above/equals).
            threshold: Esik.
            severity: Ciddiyet.

        Returns:
            Kural bilgisi.
        """
        self._rules[rule_id] = {
            "rule_id": rule_id,
            "kpi_id": kpi_id,
            "condition": condition,
            "threshold": threshold,
            "severity": severity,
            "enabled": True,
        }

        return {
            "rule_id": rule_id,
            "added": True,
        }

    def check_value(
        self,
        kpi_id: str,
        value: float,
    ) -> list[dict[str, Any]]:
        """Deger kontrolu yapar.

        Args:
            kpi_id: KPI ID.
            value: Deger.

        Returns:
            Tetiklenen uyarilar.
        """
        triggered = []

        for rule in self._rules.values():
            if (
                rule["kpi_id"] != kpi_id
                or not rule["enabled"]
            ):
                continue

            fired = False
            condition = rule["condition"]
            threshold = rule["threshold"]

            if condition == "below" and value < threshold:
                fired = True
            elif condition == "above" and value > threshold:
                fired = True
            elif condition == "equals" and value == threshold:
                fired = True

            if fired:
                alert = self._create_alert(
                    rule, value,
                )
                triggered.append(alert)

        return triggered

    def alert_threshold(
        self,
        kpi_id: str,
        value: float,
        target: float,
    ) -> dict[str, Any] | None:
        """Esik uyarisi kontrol eder.

        Args:
            kpi_id: KPI ID.
            value: Deger.
            target: Hedef.

        Returns:
            Uyari veya None.
        """
        if value < target * 0.8:
            return self._create_alert(
                {
                    "rule_id": f"threshold_{kpi_id}",
                    "kpi_id": kpi_id,
                    "severity": "warning",
                    "condition": "below_threshold",
                    "threshold": target * 0.8,
                },
                value,
            )
        return None

    def alert_degradation(
        self,
        kpi_id: str,
        change_pct: float,
    ) -> dict[str, Any] | None:
        """Bozulma uyarisi olusturur.

        Args:
            kpi_id: KPI ID.
            change_pct: Degisim yuzdesi.

        Returns:
            Uyari veya None.
        """
        if change_pct < -10:
            severity = (
                "critical" if change_pct < -25
                else "warning"
            )
            return self._create_alert(
                {
                    "rule_id": f"degrade_{kpi_id}",
                    "kpi_id": kpi_id,
                    "severity": severity,
                    "condition": "degradation",
                    "threshold": change_pct,
                },
                change_pct,
            )
        return None

    def alert_improvement(
        self,
        kpi_id: str,
        change_pct: float,
    ) -> dict[str, Any] | None:
        """Iyilestirme uyarisi olusturur.

        Args:
            kpi_id: KPI ID.
            change_pct: Degisim yuzdesi.

        Returns:
            Uyari veya None.
        """
        if change_pct > 20:
            return self._create_alert(
                {
                    "rule_id": f"improve_{kpi_id}",
                    "kpi_id": kpi_id,
                    "severity": "improvement",
                    "condition": "improvement",
                    "threshold": change_pct,
                },
                change_pct,
            )
        return None

    def alert_anomaly(
        self,
        kpi_id: str,
        value: float,
        mean: float,
        std: float,
    ) -> dict[str, Any]:
        """Anomali uyarisi olusturur.

        Args:
            kpi_id: KPI ID.
            value: Deger.
            mean: Ortalama.
            std: Standart sapma.

        Returns:
            Uyari bilgisi.
        """
        return self._create_alert(
            {
                "rule_id": f"anomaly_{kpi_id}",
                "kpi_id": kpi_id,
                "severity": "warning",
                "condition": "anomaly",
                "threshold": 0,
            },
            value,
            extra={
                "mean": mean,
                "std": std,
            },
        )

    def acknowledge(
        self,
        alert_id: str,
    ) -> dict[str, Any]:
        """Uyariyi onaylar.

        Args:
            alert_id: Uyari ID.

        Returns:
            Onay bilgisi.
        """
        alert = self._active.get(alert_id)
        if not alert:
            return {"error": "alert_not_found"}

        alert["acknowledged"] = True
        alert["acknowledged_at"] = time.time()
        self._stats["acknowledged"] += 1

        return {
            "alert_id": alert_id,
            "acknowledged": True,
        }

    def resolve(
        self,
        alert_id: str,
    ) -> dict[str, Any]:
        """Uyariyi cozumler.

        Args:
            alert_id: Uyari ID.

        Returns:
            Cozum bilgisi.
        """
        alert = self._active.get(alert_id)
        if not alert:
            return {"error": "alert_not_found"}

        alert["status"] = "resolved"
        alert["resolved_at"] = time.time()
        del self._active[alert_id]
        self._stats["resolved"] += 1

        return {
            "alert_id": alert_id,
            "resolved": True,
        }

    def get_active_alerts(
        self,
        severity: str | None = None,
    ) -> list[dict[str, Any]]:
        """Aktif uyarilari getirir.

        Args:
            severity: Ciddiyet filtresi.

        Returns:
            Uyari listesi.
        """
        alerts = list(self._active.values())
        if severity:
            alerts = [
                a for a in alerts
                if a.get("severity") == severity
            ]
        return alerts

    def _create_alert(
        self,
        rule: dict[str, Any],
        value: float,
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Uyari olusturur (dahili).

        Args:
            rule: Kural.
            value: Deger.
            extra: Ek bilgi.

        Returns:
            Uyari bilgisi.
        """
        alert_id = (
            f"alert_{rule['kpi_id']}"
            f"_{int(time.time())}"
        )

        alert = {
            "alert_id": alert_id,
            "kpi_id": rule["kpi_id"],
            "rule_id": rule["rule_id"],
            "severity": rule["severity"],
            "condition": rule["condition"],
            "threshold": rule["threshold"],
            "value": value,
            "acknowledged": False,
            "status": "active",
            "created_at": time.time(),
            **(extra or {}),
        }

        self._alerts.append(alert)
        self._active[alert_id] = alert
        self._stats["triggered"] += 1

        return alert

    @property
    def alert_count(self) -> int:
        """Toplam uyari sayisi."""
        return len(self._alerts)

    @property
    def active_count(self) -> int:
        """Aktif uyari sayisi."""
        return len(self._active)

    @property
    def rule_count(self) -> int:
        """Kural sayisi."""
        return len(self._rules)
