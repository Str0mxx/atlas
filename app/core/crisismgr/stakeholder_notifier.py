"""ATLAS Paydaş Bilgilendiricisi modülü.

Bildirim yönlendirme, öncelik işleme,
onay takibi, yanıtsızlık eskalasyonu,
denetim günlüğü.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class StakeholderNotifier:
    """Paydaş bilgilendiricisi.

    Paydaşlara bildirim gönderir.

    Attributes:
        _notifications: Bildirim kayıtları.
        _audit_log: Denetim günlüğü.
    """

    def __init__(self) -> None:
        """Bildirimciyi başlatır."""
        self._notifications: list[
            dict[str, Any]
        ] = []
        self._confirmations: dict[
            str, bool
        ] = {}
        self._audit_log: list[
            dict[str, Any]
        ] = []
        self._counter = 0
        self._stats = {
            "notifications_sent": 0,
            "escalations_triggered": 0,
        }

        logger.info(
            "StakeholderNotifier "
            "baslatildi",
        )

    def route_notification(
        self,
        crisis_id: str,
        stakeholder: str,
        channel: str = "telegram",
        message: str = "",
        priority: str = "high",
    ) -> dict[str, Any]:
        """Bildirim yönlendirir.

        Args:
            crisis_id: Kriz kimliği.
            stakeholder: Paydaş.
            channel: Kanal.
            message: Mesaj.
            priority: Öncelik.

        Returns:
            Yönlendirme bilgisi.
        """
        self._counter += 1
        nid = f"ntf_{self._counter}"

        self._notifications.append({
            "notification_id": nid,
            "crisis_id": crisis_id,
            "stakeholder": stakeholder,
            "channel": channel,
            "message": message,
            "priority": priority,
            "status": "sent",
            "timestamp": time.time(),
        })

        self._audit_log.append({
            "action": "notification_sent",
            "notification_id": nid,
            "stakeholder": stakeholder,
            "timestamp": time.time(),
        })

        self._stats[
            "notifications_sent"
        ] += 1

        return {
            "notification_id": nid,
            "stakeholder": stakeholder,
            "channel": channel,
            "sent": True,
        }

    def handle_priority(
        self,
        crisis_id: str,
        priority: str = "high",
    ) -> dict[str, Any]:
        """Öncelik işler.

        Args:
            crisis_id: Kriz kimliği.
            priority: Öncelik.

        Returns:
            İşleme bilgisi.
        """
        channels = {
            "critical": [
                "phone", "sms",
                "telegram", "email",
            ],
            "high": [
                "telegram", "email",
            ],
            "medium": ["email"],
            "low": ["email"],
        }

        selected = channels.get(
            priority, ["email"],
        )

        return {
            "crisis_id": crisis_id,
            "priority": priority,
            "channels": selected,
            "handled": True,
        }

    def track_confirmation(
        self,
        notification_id: str,
        confirmed: bool = False,
    ) -> dict[str, Any]:
        """Onay takibi yapar.

        Args:
            notification_id: Bildirim kimliği.
            confirmed: Onaylandı mı.

        Returns:
            Takip bilgisi.
        """
        self._confirmations[
            notification_id
        ] = confirmed

        self._audit_log.append({
            "action": (
                "confirmed"
                if confirmed
                else "unconfirmed"
            ),
            "notification_id": (
                notification_id
            ),
            "timestamp": time.time(),
        })

        return {
            "notification_id": (
                notification_id
            ),
            "confirmed": confirmed,
            "tracked": True,
        }

    def escalate_no_response(
        self,
        notification_id: str,
        timeout_seconds: float = 300,
        elapsed_seconds: float = 0,
    ) -> dict[str, Any]:
        """Yanıtsızlık eskalasyonu yapar.

        Args:
            notification_id: Bildirim kimliği.
            timeout_seconds: Zaman aşımı.
            elapsed_seconds: Geçen süre.

        Returns:
            Eskalasyon bilgisi.
        """
        confirmed = (
            self._confirmations.get(
                notification_id, False,
            )
        )

        should_escalate = (
            not confirmed
            and elapsed_seconds
            > timeout_seconds
        )

        if should_escalate:
            self._stats[
                "escalations_triggered"
            ] += 1
            self._audit_log.append({
                "action": (
                    "no_response_escalation"
                ),
                "notification_id": (
                    notification_id
                ),
                "timestamp": time.time(),
            })

        return {
            "notification_id": (
                notification_id
            ),
            "should_escalate": (
                should_escalate
            ),
            "confirmed": confirmed,
            "checked": True,
        }

    def get_audit_log(
        self,
        crisis_id: str = "",
    ) -> dict[str, Any]:
        """Denetim günlüğü döndürür.

        Args:
            crisis_id: Kriz kimliği.

        Returns:
            Günlük bilgisi.
        """
        if crisis_id:
            filtered = [
                e for e in self._audit_log
                if e.get("crisis_id")
                == crisis_id
            ]
        else:
            filtered = list(
                self._audit_log,
            )

        return {
            "entries": filtered,
            "count": len(filtered),
            "retrieved": True,
        }

    @property
    def notification_count(self) -> int:
        """Bildirim sayısı."""
        return self._stats[
            "notifications_sent"
        ]

    @property
    def escalation_count(self) -> int:
        """Eskalasyon sayısı."""
        return self._stats[
            "escalations_triggered"
        ]
