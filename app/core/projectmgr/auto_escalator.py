"""ATLAS Otomatik Eskalasyon modülü.

Eskalasyon kuralları, tetik algılama,
bildirim yönlendirme, takip izleme,
çözüm doğrulama.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class AutoEscalator:
    """Otomatik eskalasyon yöneticisi.

    Proje eskalasyonlarını otomatik yönetir.

    Attributes:
        _rules: Eskalasyon kuralları.
        _escalations: Eskalasyon kayıtları.
    """

    def __init__(self) -> None:
        """Eskalasyon yöneticisini başlatır."""
        self._rules: list[
            dict[str, Any]
        ] = []
        self._escalations: list[
            dict[str, Any]
        ] = []
        self._followups: dict[
            str, list[dict[str, Any]]
        ] = {}
        self._counter = 0
        self._rule_counter = 0
        self._stats = {
            "rules_created": 0,
            "escalations_triggered": 0,
            "followups_sent": 0,
            "resolutions_verified": 0,
        }

        logger.info(
            "AutoEscalator baslatildi",
        )

    def create_rule(
        self,
        name: str,
        condition: str,
        severity: str = "medium",
        notify: list[str] | None = None,
        auto_trigger: bool = True,
    ) -> dict[str, Any]:
        """Eskalasyon kuralı oluşturur.

        Args:
            name: Kural adı.
            condition: Koşul.
            severity: Ciddiyet.
            notify: Bildirilecekler.
            auto_trigger: Otomatik tetik.

        Returns:
            Kural bilgisi.
        """
        self._rule_counter += 1
        rid = f"rule_{self._rule_counter}"

        rule = {
            "rule_id": rid,
            "name": name,
            "condition": condition,
            "severity": severity,
            "notify": notify or [],
            "auto_trigger": auto_trigger,
            "active": True,
            "created_at": time.time(),
        }
        self._rules.append(rule)
        self._stats["rules_created"] += 1

        return {
            "rule_id": rid,
            "name": name,
            "severity": severity,
            "created": True,
        }

    def detect_trigger(
        self,
        project_id: str,
        event_type: str,
        context: dict[str, Any]
        | None = None,
    ) -> dict[str, Any]:
        """Tetik algılar.

        Args:
            project_id: Proje ID.
            event_type: Olay tipi.
            context: Bağlam bilgisi.

        Returns:
            Tetik bilgisi.
        """
        context = context or {}
        matched_rules = []

        for rule in self._rules:
            if not rule["active"]:
                continue
            if (
                rule["condition"]
                == event_type
                or event_type
                in rule["condition"]
            ):
                matched_rules.append(
                    rule["rule_id"],
                )

        triggered = len(matched_rules) > 0

        if triggered:
            self._counter += 1
            eid = f"esc_{self._counter}"

            escalation = {
                "escalation_id": eid,
                "project_id": project_id,
                "event_type": event_type,
                "matched_rules": (
                    matched_rules
                ),
                "context": context,
                "status": "active",
                "created_at": time.time(),
            }
            self._escalations.append(
                escalation,
            )
            self._stats[
                "escalations_triggered"
            ] += 1

            return {
                "escalation_id": eid,
                "triggered": True,
                "matched_rules": (
                    matched_rules
                ),
                "count": len(matched_rules),
            }

        return {
            "triggered": False,
            "matched_rules": [],
            "count": 0,
        }

    def route_notification(
        self,
        escalation_id: str,
        recipients: list[str]
        | None = None,
        channel: str = "default",
        priority: str = "normal",
    ) -> dict[str, Any]:
        """Bildirim yönlendirir.

        Args:
            escalation_id: Eskalasyon ID.
            recipients: Alıcılar.
            channel: Kanal.
            priority: Öncelik.

        Returns:
            Yönlendirme bilgisi.
        """
        recipients = recipients or []

        # Eşleşen eskalasyonu bul
        esc = None
        for e in self._escalations:
            if (
                e["escalation_id"]
                == escalation_id
            ):
                esc = e
                break

        if not esc:
            return {
                "escalation_id": (
                    escalation_id
                ),
                "routed": False,
                "reason": "not_found",
            }

        return {
            "escalation_id": escalation_id,
            "recipients": recipients,
            "channel": channel,
            "priority": priority,
            "recipients_count": len(
                recipients,
            ),
            "routed": True,
        }

    def track_followup(
        self,
        escalation_id: str,
        action: str,
        assignee: str = "",
        due_hours: float = 24.0,
    ) -> dict[str, Any]:
        """Takip izler.

        Args:
            escalation_id: Eskalasyon ID.
            action: Aksiyon.
            assignee: Atanan kişi.
            due_hours: Son süre (saat).

        Returns:
            Takip bilgisi.
        """
        followup = {
            "escalation_id": (
                escalation_id
            ),
            "action": action,
            "assignee": assignee,
            "due_hours": due_hours,
            "status": "pending",
            "created_at": time.time(),
        }

        if (
            escalation_id
            not in self._followups
        ):
            self._followups[
                escalation_id
            ] = []
        self._followups[
            escalation_id
        ].append(followup)
        self._stats["followups_sent"] += 1

        return {
            "escalation_id": (
                escalation_id
            ),
            "action": action,
            "assignee": assignee,
            "due_hours": due_hours,
            "tracked": True,
        }

    def verify_resolution(
        self,
        escalation_id: str,
        resolution: str = "",
        verified_by: str = "",
    ) -> dict[str, Any]:
        """Çözüm doğrular.

        Args:
            escalation_id: Eskalasyon ID.
            resolution: Çözüm açıklaması.
            verified_by: Doğrulayan.

        Returns:
            Doğrulama bilgisi.
        """
        # Eskalasyonu bul
        esc = None
        for e in self._escalations:
            if (
                e["escalation_id"]
                == escalation_id
            ):
                esc = e
                break

        if not esc:
            return {
                "escalation_id": (
                    escalation_id
                ),
                "verified": False,
                "reason": "not_found",
            }

        esc["status"] = "resolved"
        esc["resolved_at"] = time.time()

        duration = round(
            esc["resolved_at"]
            - esc["created_at"], 1,
        )

        self._stats[
            "resolutions_verified"
        ] += 1

        return {
            "escalation_id": (
                escalation_id
            ),
            "resolution": resolution,
            "verified_by": verified_by,
            "duration_seconds": duration,
            "verified": True,
        }

    def get_active_escalations(
        self,
        project_id: str = "",
    ) -> list[dict[str, Any]]:
        """Aktif eskalasyonları listeler."""
        results = [
            e for e in self._escalations
            if e["status"] == "active"
        ]
        if project_id:
            results = [
                e for e in results
                if e["project_id"]
                == project_id
            ]
        return results

    @property
    def rule_count(self) -> int:
        """Kural sayısı."""
        return self._stats[
            "rules_created"
        ]

    @property
    def escalation_count(self) -> int:
        """Eskalasyon sayısı."""
        return self._stats[
            "escalations_triggered"
        ]
