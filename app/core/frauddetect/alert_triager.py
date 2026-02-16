"""ATLAS Uyarı Önceliklendirici modülü.

Uyarı puanlama, öncelik atama,
gruplama, yineleme kaldırma,
yönlendirme.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class AlertTriager:
    """Uyarı önceliklendirici.

    Uyarıları puanlar ve önceliklendirir.

    Attributes:
        _alerts: Uyarı kayıtları.
        _groups: Grup kayıtları.
    """

    def __init__(self) -> None:
        """Önceliklendiriciyi başlatır."""
        self._alerts: dict[
            str, dict[str, Any]
        ] = {}
        self._groups: dict[
            str, list[str]
        ] = {}
        self._counter = 0
        self._stats = {
            "alerts_triaged": 0,
            "duplicates_removed": 0,
        }

        logger.info(
            "AlertTriager baslatildi",
        )

    def score_alert(
        self,
        alert_id: str,
        severity: float = 0.0,
        confidence: float = 0.0,
        impact: float = 0.0,
    ) -> dict[str, Any]:
        """Uyarı puanlar.

        Args:
            alert_id: Uyarı ID.
            severity: Ciddiyet (0-100).
            confidence: Güven (0-100).
            impact: Etki (0-100).

        Returns:
            Puanlama bilgisi.
        """
        self._counter += 1
        score = round(
            severity * 0.4
            + confidence * 0.3
            + impact * 0.3,
            1,
        )

        self._alerts[alert_id] = {
            "alert_id": alert_id,
            "score": score,
            "severity": severity,
            "confidence": confidence,
            "impact": impact,
            "priority": None,
            "group": None,
            "timestamp": time.time(),
        }

        return {
            "alert_id": alert_id,
            "score": score,
            "scored": True,
        }

    def assign_priority(
        self,
        alert_id: str,
    ) -> dict[str, Any]:
        """Öncelik atar.

        Args:
            alert_id: Uyarı ID.

        Returns:
            Öncelik bilgisi.
        """
        alert = self._alerts.get(alert_id)
        if not alert:
            return {
                "alert_id": alert_id,
                "assigned": False,
            }

        score = alert["score"]
        priority = (
            "p1" if score >= 80
            else "p2" if score >= 60
            else "p3" if score >= 40
            else "p4"
        )
        alert["priority"] = priority
        self._stats[
            "alerts_triaged"
        ] += 1

        return {
            "alert_id": alert_id,
            "score": score,
            "priority": priority,
            "assigned": True,
        }

    def group_alerts(
        self,
        group_name: str,
        alert_ids: list[str]
        | None = None,
    ) -> dict[str, Any]:
        """Uyarıları gruplar.

        Args:
            group_name: Grup adı.
            alert_ids: Uyarı ID'leri.

        Returns:
            Gruplama bilgisi.
        """
        alert_ids = alert_ids or []
        valid = [
            aid for aid in alert_ids
            if aid in self._alerts
        ]

        self._groups[group_name] = valid
        for aid in valid:
            self._alerts[aid][
                "group"
            ] = group_name

        return {
            "group": group_name,
            "alert_count": len(valid),
            "grouped": len(valid) > 0,
        }

    def deduplicate(
        self,
        alert_ids: list[str]
        | None = None,
    ) -> dict[str, Any]:
        """Yinelemeleri kaldırır.

        Args:
            alert_ids: Uyarı ID'leri.

        Returns:
            Kaldırma bilgisi.
        """
        alert_ids = alert_ids or list(
            self._alerts.keys(),
        )

        seen_scores: dict[float, str] = {}
        duplicates = []

        for aid in alert_ids:
            alert = self._alerts.get(aid)
            if not alert:
                continue
            score = alert["score"]
            sev = alert["severity"]
            key = (score, sev)

            if key in seen_scores:
                duplicates.append(aid)
            else:
                seen_scores[key] = aid

        for aid in duplicates:
            del self._alerts[aid]

        self._stats[
            "duplicates_removed"
        ] += len(duplicates)

        return {
            "removed": len(duplicates),
            "remaining": len(self._alerts),
            "deduplicated": True,
        }

    def route_alert(
        self,
        alert_id: str,
        routing_rules: dict[str, str]
        | None = None,
    ) -> dict[str, Any]:
        """Uyarı yönlendirir.

        Args:
            alert_id: Uyarı ID.
            routing_rules: Yönlendirme kuralları.

        Returns:
            Yönlendirme bilgisi.
        """
        alert = self._alerts.get(alert_id)
        if not alert:
            return {
                "alert_id": alert_id,
                "routed": False,
            }

        routing_rules = routing_rules or {
            "p1": "security_team",
            "p2": "ops_team",
            "p3": "analyst",
            "p4": "queue",
        }

        priority = alert.get(
            "priority", "p4",
        )
        destination = routing_rules.get(
            priority, "queue",
        )

        return {
            "alert_id": alert_id,
            "priority": priority,
            "destination": destination,
            "routed": True,
        }

    @property
    def triage_count(self) -> int:
        """Triyaj sayısı."""
        return self._stats[
            "alerts_triaged"
        ]

    @property
    def dedup_count(self) -> int:
        """Yineleme kaldırma sayısı."""
        return self._stats[
            "duplicates_removed"
        ]
