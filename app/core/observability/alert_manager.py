"""ATLAS Uyari Yoneticisi modulu.

Uyari kurallari, esik izleme,
uyari yonlendirme, susturma
ve eskalasyon.
"""

import logging
import time
from typing import Any, Callable

logger = logging.getLogger(__name__)


class AlertManager:
    """Uyari yoneticisi.

    Uyarilari yonetir ve yonlendirir.

    Attributes:
        _rules: Uyari kurallari.
        _alerts: Aktif uyarilar.
    """

    def __init__(self) -> None:
        """Uyari yoneticisini baslatir."""
        self._rules: dict[
            str, dict[str, Any]
        ] = {}
        self._alerts: list[
            dict[str, Any]
        ] = []
        self._silences: dict[
            str, dict[str, Any]
        ] = {}
        self._routes: dict[
            str, list[Callable[..., None]]
        ] = {}
        self._escalation_rules: list[
            dict[str, Any]
        ] = []
        self._acknowledged: set[str] = set()

        logger.info("AlertManager baslatildi")

    def add_rule(
        self,
        name: str,
        metric_name: str,
        condition: str,
        threshold: float,
        severity: str = "warning",
        duration: int = 0,
    ) -> dict[str, Any]:
        """Uyari kurali ekler.

        Args:
            name: Kural adi.
            metric_name: Metrik adi.
            condition: Kosul (gt/lt/eq/gte/lte).
            threshold: Esik degeri.
            severity: Ciddiyet.
            duration: Suren sure (sn).

        Returns:
            Kural bilgisi.
        """
        rule = {
            "name": name,
            "metric_name": metric_name,
            "condition": condition,
            "threshold": threshold,
            "severity": severity,
            "duration": duration,
            "enabled": True,
            "created_at": time.time(),
        }
        self._rules[name] = rule
        return {"name": name, "severity": severity}

    def remove_rule(
        self,
        name: str,
    ) -> bool:
        """Kural kaldirir.

        Args:
            name: Kural adi.

        Returns:
            Basarili mi.
        """
        if name in self._rules:
            del self._rules[name]
            return True
        return False

    def evaluate(
        self,
        metric_name: str,
        value: float,
    ) -> list[dict[str, Any]]:
        """Metrigi kurallara karsi degerlendirir.

        Args:
            metric_name: Metrik adi.
            value: Metrik degeri.

        Returns:
            Tetiklenen uyarilar.
        """
        triggered = []

        for name, rule in self._rules.items():
            if not rule["enabled"]:
                continue
            if rule["metric_name"] != metric_name:
                continue

            # Susturma kontrolu
            if name in self._silences:
                silence = self._silences[name]
                if time.time() < silence.get(
                    "until", 0,
                ):
                    continue

            fired = self._check_condition(
                value, rule["condition"],
                rule["threshold"],
            )

            if fired:
                alert = {
                    "rule": name,
                    "metric": metric_name,
                    "value": value,
                    "threshold": rule["threshold"],
                    "severity": rule["severity"],
                    "timestamp": time.time(),
                }
                self._alerts.append(alert)
                triggered.append(alert)

                # Yonlendirme
                self._route_alert(alert)

        return triggered

    def _check_condition(
        self,
        value: float,
        condition: str,
        threshold: float,
    ) -> bool:
        """Kosul kontrol eder.

        Args:
            value: Deger.
            condition: Kosul.
            threshold: Esik.

        Returns:
            Tetiklendi mi.
        """
        if condition == "gt":
            return value > threshold
        elif condition == "lt":
            return value < threshold
        elif condition == "eq":
            return value == threshold
        elif condition == "gte":
            return value >= threshold
        elif condition == "lte":
            return value <= threshold
        return False

    def silence(
        self,
        rule_name: str,
        duration_seconds: int,
        reason: str = "",
    ) -> dict[str, Any]:
        """Uyariyi susturur.

        Args:
            rule_name: Kural adi.
            duration_seconds: Sure (sn).
            reason: Sebep.

        Returns:
            Susturma bilgisi.
        """
        self._silences[rule_name] = {
            "until": time.time() + duration_seconds,
            "reason": reason,
            "created_at": time.time(),
        }
        return {
            "rule": rule_name,
            "silenced_for": duration_seconds,
        }

    def unsilence(
        self,
        rule_name: str,
    ) -> bool:
        """Susturmayi kaldirir.

        Args:
            rule_name: Kural adi.

        Returns:
            Basarili mi.
        """
        if rule_name in self._silences:
            del self._silences[rule_name]
            return True
        return False

    def add_route(
        self,
        severity: str,
        handler: Callable[..., None],
    ) -> None:
        """Yonlendirme ekler.

        Args:
            severity: Ciddiyet.
            handler: Isleyici.
        """
        if severity not in self._routes:
            self._routes[severity] = []
        self._routes[severity].append(handler)

    def _route_alert(
        self,
        alert: dict[str, Any],
    ) -> int:
        """Uyariyi yonlendirir.

        Args:
            alert: Uyari.

        Returns:
            Yonlendirilen sayisi.
        """
        severity = alert.get("severity", "")
        handlers = self._routes.get(severity, [])
        routed = 0
        for handler in handlers:
            try:
                handler(alert)
                routed += 1
            except Exception as e:
                logger.error(
                    "Route hatasi: %s", e,
                )
        return routed

    def acknowledge(
        self,
        alert_index: int,
    ) -> bool:
        """Uyariyi onaylar.

        Args:
            alert_index: Uyari indeksi.

        Returns:
            Basarili mi.
        """
        if 0 <= alert_index < len(self._alerts):
            self._acknowledged.add(
                str(alert_index),
            )
            return True
        return False

    def add_escalation(
        self,
        severity: str,
        escalate_after: int,
        escalate_to: str,
    ) -> None:
        """Eskalasyon kurali ekler.

        Args:
            severity: Ciddiyet.
            escalate_after: Eskalasyon suresi (sn).
            escalate_to: Eskalasyon hedefi.
        """
        self._escalation_rules.append({
            "severity": severity,
            "escalate_after": escalate_after,
            "escalate_to": escalate_to,
        })

    def get_active_alerts(
        self,
        severity: str | None = None,
    ) -> list[dict[str, Any]]:
        """Aktif uyarilari getirir.

        Args:
            severity: Filtre.

        Returns:
            Uyari listesi.
        """
        alerts = [
            a for i, a in enumerate(self._alerts)
            if str(i) not in self._acknowledged
        ]
        if severity:
            alerts = [
                a for a in alerts
                if a["severity"] == severity
            ]
        return alerts

    def get_alert_summary(self) -> dict[str, Any]:
        """Uyari ozeti getirir.

        Returns:
            Ozet bilgisi.
        """
        by_severity: dict[str, int] = {}
        for alert in self._alerts:
            sev = alert["severity"]
            by_severity[sev] = (
                by_severity.get(sev, 0) + 1
            )

        return {
            "total": len(self._alerts),
            "acknowledged": len(self._acknowledged),
            "active": len(self._alerts) - len(
                self._acknowledged,
            ),
            "by_severity": by_severity,
            "silenced": len(self._silences),
        }

    @property
    def rule_count(self) -> int:
        """Kural sayisi."""
        return len(self._rules)

    @property
    def alert_count(self) -> int:
        """Uyari sayisi."""
        return len(self._alerts)

    @property
    def silence_count(self) -> int:
        """Susturma sayisi."""
        return len(self._silences)

    @property
    def route_count(self) -> int:
        """Yonlendirme sayisi."""
        return sum(
            len(h) for h in self._routes.values()
        )
