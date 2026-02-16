"""ATLAS Finansal Uyarı Motoru modülü.

Eşik uyarıları, anomali uyarıları,
son tarih uyarıları, fırsat uyarıları,
risk uyarıları.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class FinancialAlertEngine:
    """Finansal uyarı motoru.

    Finansal duruma göre uyarı üretir.

    Attributes:
        _alerts: Uyarı kayıtları.
        _rules: Uyarı kuralları.
    """

    def __init__(self) -> None:
        """Motoru başlatır."""
        self._alerts: list[
            dict[str, Any]
        ] = []
        self._rules: list[
            dict[str, Any]
        ] = []
        self._acknowledged: set[str] = set()
        self._counter = 0
        self._stats = {
            "alerts_generated": 0,
            "alerts_acknowledged": 0,
            "rules_active": 0,
        }

        logger.info(
            "FinancialAlertEngine "
            "baslatildi",
        )

    def add_rule(
        self,
        name: str,
        alert_type: str,
        condition: str,
        threshold: float,
        severity: str = "medium",
    ) -> dict[str, Any]:
        """Uyarı kuralı ekler.

        Args:
            name: Kural adı.
            alert_type: Uyarı tipi.
            condition: Koşul.
            threshold: Eşik.
            severity: Şiddet.

        Returns:
            Kural bilgisi.
        """
        self._counter += 1
        rid = f"rule_{self._counter}"

        rule = {
            "rule_id": rid,
            "name": name,
            "alert_type": alert_type,
            "condition": condition,
            "threshold": threshold,
            "severity": severity,
            "active": True,
        }
        self._rules.append(rule)
        self._stats["rules_active"] += 1

        return {
            "rule_id": rid,
            "name": name,
            "created": True,
        }

    def check_threshold(
        self,
        metric: str,
        value: float,
        threshold: float,
        direction: str = "above",
    ) -> dict[str, Any]:
        """Eşik kontrolü yapar.

        Args:
            metric: Metrik adı.
            value: Mevcut değer.
            threshold: Eşik değeri.
            direction: Yön (above/below).

        Returns:
            Kontrol bilgisi.
        """
        triggered = (
            value > threshold
            if direction == "above"
            else value < threshold
        )

        if triggered:
            self._counter += 1
            aid = f"alert_{self._counter}"

            alert = {
                "alert_id": aid,
                "type": "threshold",
                "metric": metric,
                "value": value,
                "threshold": threshold,
                "direction": direction,
                "severity": (
                    "high"
                    if abs(value - threshold)
                    > threshold * 0.5
                    else "medium"
                ),
                "message": (
                    f"{metric} is {value} "
                    f"({direction} threshold "
                    f"{threshold})"
                ),
                "timestamp": time.time(),
            }
            self._alerts.append(alert)
            self._stats[
                "alerts_generated"
            ] += 1

            return {
                "alert_id": aid,
                "triggered": True,
                "metric": metric,
                "value": value,
                "severity": alert["severity"],
            }

        return {
            "triggered": False,
            "metric": metric,
            "value": value,
        }

    def check_anomaly(
        self,
        metric: str,
        value: float,
        historical: list[float],
        threshold_multiplier: float = 2.0,
    ) -> dict[str, Any]:
        """Anomali kontrolü yapar.

        Args:
            metric: Metrik adı.
            value: Mevcut değer.
            historical: Geçmiş değerler.
            threshold_multiplier: Eşik çarpanı.

        Returns:
            Anomali bilgisi.
        """
        if not historical:
            return {
                "anomaly": False,
                "reason": "no_history",
            }

        avg = sum(historical) / len(
            historical,
        )
        deviation = abs(value - avg)
        is_anomaly = (
            deviation > avg * threshold_multiplier
            if avg > 0 else False
        )

        if is_anomaly:
            self._counter += 1
            aid = f"alert_{self._counter}"

            alert = {
                "alert_id": aid,
                "type": "anomaly",
                "metric": metric,
                "value": value,
                "average": round(avg, 2),
                "deviation": round(
                    deviation, 2,
                ),
                "severity": "high",
                "message": (
                    f"Anomaly in {metric}: "
                    f"{value} vs avg {avg:.2f}"
                ),
                "timestamp": time.time(),
            }
            self._alerts.append(alert)
            self._stats[
                "alerts_generated"
            ] += 1

            return {
                "alert_id": aid,
                "anomaly": True,
                "metric": metric,
                "deviation_ratio": round(
                    deviation / max(avg, 0.01),
                    2,
                ),
            }

        return {
            "anomaly": False,
            "metric": metric,
            "value": value,
        }

    def check_deadline(
        self,
        item_id: str,
        item_type: str,
        due_timestamp: float,
        warning_days: int = 7,
    ) -> dict[str, Any]:
        """Son tarih kontrolü yapar.

        Args:
            item_id: Öğe ID.
            item_type: Öğe tipi.
            due_timestamp: Son tarih.
            warning_days: Uyarı günü.

        Returns:
            Kontrol bilgisi.
        """
        now = time.time()
        remaining = due_timestamp - now
        remaining_days = remaining / 86400

        if remaining_days < 0:
            severity = "critical"
            status = "overdue"
        elif remaining_days < warning_days:
            severity = "warning"
            status = "approaching"
        else:
            return {
                "alert_needed": False,
                "remaining_days": round(
                    remaining_days, 1,
                ),
            }

        self._counter += 1
        aid = f"alert_{self._counter}"

        alert = {
            "alert_id": aid,
            "type": "deadline",
            "item_id": item_id,
            "item_type": item_type,
            "remaining_days": round(
                remaining_days, 1,
            ),
            "severity": severity,
            "status": status,
            "message": (
                f"{item_type} {item_id} "
                f"is {status} "
                f"({remaining_days:.0f} days)"
            ),
            "timestamp": time.time(),
        }
        self._alerts.append(alert)
        self._stats["alerts_generated"] += 1

        return {
            "alert_id": aid,
            "alert_needed": True,
            "status": status,
            "severity": severity,
            "remaining_days": round(
                remaining_days, 1,
            ),
        }

    def alert_opportunity(
        self,
        opportunity: str,
        potential_value: float,
        confidence: float = 0.5,
    ) -> dict[str, Any]:
        """Fırsat uyarısı oluşturur.

        Args:
            opportunity: Fırsat açıklaması.
            potential_value: Potansiyel değer.
            confidence: Güven.

        Returns:
            Uyarı bilgisi.
        """
        self._counter += 1
        aid = f"alert_{self._counter}"

        alert = {
            "alert_id": aid,
            "type": "opportunity",
            "opportunity": opportunity,
            "potential_value": potential_value,
            "confidence": confidence,
            "severity": "info",
            "message": (
                f"Opportunity: {opportunity} "
                f"(value: {potential_value})"
            ),
            "timestamp": time.time(),
        }
        self._alerts.append(alert)
        self._stats["alerts_generated"] += 1

        return {
            "alert_id": aid,
            "opportunity": opportunity,
            "potential_value": potential_value,
            "created": True,
        }

    def alert_risk(
        self,
        risk: str,
        impact: float,
        probability: float = 0.5,
    ) -> dict[str, Any]:
        """Risk uyarısı oluşturur.

        Args:
            risk: Risk açıklaması.
            impact: Etki.
            probability: Olasılık.

        Returns:
            Uyarı bilgisi.
        """
        self._counter += 1
        aid = f"alert_{self._counter}"

        risk_score = impact * probability
        severity = (
            "critical" if risk_score > 0.7
            else "high" if risk_score > 0.4
            else "medium"
        )

        alert = {
            "alert_id": aid,
            "type": "risk",
            "risk": risk,
            "impact": impact,
            "probability": probability,
            "risk_score": round(
                risk_score, 2,
            ),
            "severity": severity,
            "message": (
                f"Risk: {risk} "
                f"(score: {risk_score:.2f})"
            ),
            "timestamp": time.time(),
        }
        self._alerts.append(alert)
        self._stats["alerts_generated"] += 1

        return {
            "alert_id": aid,
            "risk": risk,
            "risk_score": round(
                risk_score, 2,
            ),
            "severity": severity,
            "created": True,
        }

    def acknowledge(
        self,
        alert_id: str,
    ) -> dict[str, Any]:
        """Uyarıyı onaylar.

        Args:
            alert_id: Uyarı ID.

        Returns:
            Onay bilgisi.
        """
        self._acknowledged.add(alert_id)
        self._stats[
            "alerts_acknowledged"
        ] += 1
        return {
            "alert_id": alert_id,
            "acknowledged": True,
        }

    def get_active_alerts(
        self,
        alert_type: str | None = None,
        severity: str | None = None,
    ) -> list[dict[str, Any]]:
        """Aktif uyarıları getirir."""
        results = [
            a for a in self._alerts
            if a["alert_id"]
            not in self._acknowledged
        ]
        if alert_type:
            results = [
                a for a in results
                if a["type"] == alert_type
            ]
        if severity:
            results = [
                a for a in results
                if a["severity"] == severity
            ]
        return results

    @property
    def alert_count(self) -> int:
        """Uyarı sayısı."""
        return self._stats[
            "alerts_generated"
        ]

    @property
    def active_count(self) -> int:
        """Aktif uyarı sayısı."""
        return len(self._alerts) - len(
            self._acknowledged,
        )

    @property
    def rule_count(self) -> int:
        """Kural sayısı."""
        return self._stats["rules_active"]
