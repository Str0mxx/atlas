"""ATLAS Uyari Motoru modulu.

Esik-tabanli uyarilar, kalip-tabanli
uyarilar, anomali uyarilari, eskalasyon
kurallari ve uyari bastirma.
"""

import logging
import time
from typing import Any

from app.models.notification_system import (
    AlertRecord,
    AlertType,
    NotificationPriority,
)

logger = logging.getLogger(__name__)


class AlertEngine:
    """Uyari motoru.

    Esik, kalip ve anomali tabanli
    uyarilar uretir ve yonetir.

    Attributes:
        _alerts: Aktif uyarilar.
        _thresholds: Esik kurallari.
        _patterns: Kalip kurallari.
        _suppression: Bastirma kurallari.
    """

    def __init__(self) -> None:
        """Uyari motorunu baslatir."""
        self._alerts: dict[str, AlertRecord] = {}
        self._thresholds: dict[str, dict[str, Any]] = {}
        self._patterns: dict[str, dict[str, Any]] = {}
        self._suppression: dict[str, dict[str, Any]] = {}

        logger.info("AlertEngine baslatildi")

    def add_threshold(
        self,
        name: str,
        metric: str,
        operator: str,
        value: float,
        severity: NotificationPriority = NotificationPriority.MEDIUM,
    ) -> dict[str, Any]:
        """Esik kurali ekler.

        Args:
            name: Kural adi.
            metric: Metrik adi.
            operator: Operator (gt, lt, eq, gte, lte).
            value: Esik degeri.
            severity: Onem derecesi.

        Returns:
            Kural bilgisi.
        """
        rule = {
            "name": name,
            "metric": metric,
            "operator": operator,
            "value": value,
            "severity": severity.value,
            "enabled": True,
        }
        self._thresholds[name] = rule
        return rule

    def check_threshold(
        self,
        metric: str,
        value: float,
    ) -> list[AlertRecord]:
        """Esik kontrolu yapar.

        Args:
            metric: Metrik adi.
            value: Mevcut deger.

        Returns:
            Tetiklenen uyarilar.
        """
        triggered: list[AlertRecord] = []

        for rule in self._thresholds.values():
            if not rule["enabled"]:
                continue
            if rule["metric"] != metric:
                continue

            fired = False
            op = rule["operator"]
            threshold = rule["value"]

            if op == "gt" and value > threshold:
                fired = True
            elif op == "lt" and value < threshold:
                fired = True
            elif op == "gte" and value >= threshold:
                fired = True
            elif op == "lte" and value <= threshold:
                fired = True
            elif op == "eq" and value == threshold:
                fired = True

            if fired and not self._is_suppressed(
                rule["name"],
            ):
                alert = AlertRecord(
                    alert_type=AlertType.THRESHOLD,
                    source=metric,
                    message=(
                        f"{metric} {op} {threshold}: "
                        f"actual={value}"
                    ),
                    severity=NotificationPriority(
                        rule["severity"],
                    ),
                )
                self._alerts[alert.alert_id] = alert
                triggered.append(alert)

        return triggered

    def add_pattern(
        self,
        name: str,
        pattern: str,
        severity: NotificationPriority = NotificationPriority.MEDIUM,
    ) -> dict[str, Any]:
        """Kalip kurali ekler.

        Args:
            name: Kural adi.
            pattern: Kalip (basit string icerme).
            severity: Onem derecesi.

        Returns:
            Kural bilgisi.
        """
        rule = {
            "name": name,
            "pattern": pattern,
            "severity": severity.value,
            "enabled": True,
        }
        self._patterns[name] = rule
        return rule

    def check_pattern(
        self,
        text: str,
    ) -> list[AlertRecord]:
        """Kalip kontrolu yapar.

        Args:
            text: Kontrol edilecek metin.

        Returns:
            Tetiklenen uyarilar.
        """
        triggered: list[AlertRecord] = []

        for rule in self._patterns.values():
            if not rule["enabled"]:
                continue
            if rule["pattern"].lower() in text.lower():
                if self._is_suppressed(rule["name"]):
                    continue
                alert = AlertRecord(
                    alert_type=AlertType.PATTERN,
                    source="pattern_check",
                    message=(
                        f"Pattern '{rule['pattern']}' "
                        f"detected in: {text[:50]}"
                    ),
                    severity=NotificationPriority(
                        rule["severity"],
                    ),
                )
                self._alerts[alert.alert_id] = alert
                triggered.append(alert)

        return triggered

    def create_anomaly_alert(
        self,
        source: str,
        message: str,
        severity: NotificationPriority = NotificationPriority.HIGH,
    ) -> AlertRecord:
        """Anomali uyarisi olusturur.

        Args:
            source: Kaynak.
            message: Mesaj.
            severity: Onem derecesi.

        Returns:
            Uyari kaydi.
        """
        alert = AlertRecord(
            alert_type=AlertType.ANOMALY,
            source=source,
            message=message,
            severity=severity,
        )
        self._alerts[alert.alert_id] = alert
        return alert

    def acknowledge(self, alert_id: str) -> bool:
        """Uyariyi onaylar.

        Args:
            alert_id: Uyari ID.

        Returns:
            Basarili ise True.
        """
        alert = self._alerts.get(alert_id)
        if not alert:
            return False
        alert.acknowledged = True
        return True

    def suppress(
        self,
        rule_name: str,
        duration_seconds: int = 3600,
    ) -> None:
        """Uyari bastirma ayarlar.

        Args:
            rule_name: Kural adi.
            duration_seconds: Sure (saniye).
        """
        self._suppression[rule_name] = {
            "until": time.time() + duration_seconds,
        }

    def get_active(self) -> list[AlertRecord]:
        """Aktif uyarilari getirir.

        Returns:
            Aktif uyarilar.
        """
        return [
            a for a in self._alerts.values()
            if not a.acknowledged and not a.suppressed
        ]

    def _is_suppressed(self, rule_name: str) -> bool:
        """Bastirma kontrolu.

        Args:
            rule_name: Kural adi.

        Returns:
            Bastirilmis ise True.
        """
        sup = self._suppression.get(rule_name)
        if not sup:
            return False
        return time.time() < sup["until"]

    @property
    def alert_count(self) -> int:
        """Uyari sayisi."""
        return len(self._alerts)

    @property
    def active_count(self) -> int:
        """Aktif uyari sayisi."""
        return sum(
            1 for a in self._alerts.values()
            if not a.acknowledged
        )

    @property
    def threshold_count(self) -> int:
        """Esik kurali sayisi."""
        return len(self._thresholds)

    @property
    def pattern_count(self) -> int:
        """Kalip kurali sayisi."""
        return len(self._patterns)
