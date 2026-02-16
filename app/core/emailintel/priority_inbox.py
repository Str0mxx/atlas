"""ATLAS Öncelikli Gelen Kutusu modülü.

Öncelik sıralama, önemli önce,
VIP işleme, zamana duyarlı,
özel kurallar.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)

PRIORITY_ORDER = {
    "critical": 0,
    "high": 1,
    "medium": 2,
    "low": 3,
}


class PriorityInbox:
    """Öncelikli gelen kutusu.

    Emailleri önceliklerine göre sıralar.

    Attributes:
        _emails: Email kayıtları.
        _vip_senders: VIP göndericiler.
    """

    def __init__(self) -> None:
        """Gelen kutusunu başlatır."""
        self._emails: list[
            dict[str, Any]
        ] = []
        self._vip_senders: set[str] = set()
        self._rules: list[
            dict[str, Any]
        ] = []
        self._counter = 0
        self._stats = {
            "emails_sorted": 0,
            "vip_processed": 0,
        }

        logger.info(
            "PriorityInbox baslatildi",
        )

    def add_email(
        self,
        email_id: str = "",
        sender: str = "",
        subject: str = "",
        priority: str = "medium",
        timestamp: float | None = None,
    ) -> dict[str, Any]:
        """Email ekler.

        Args:
            email_id: Email kimliği.
            sender: Gönderici.
            subject: Konu.
            priority: Öncelik.
            timestamp: Zaman damgası.

        Returns:
            Ekleme bilgisi.
        """
        self._counter += 1
        if not email_id:
            email_id = f"em_{self._counter}"

        if sender in self._vip_senders:
            priority = "critical"
            self._stats[
                "vip_processed"
            ] += 1

        entry = {
            "email_id": email_id,
            "sender": sender,
            "subject": subject,
            "priority": priority,
            "timestamp": (
                timestamp or time.time()
            ),
            "read": False,
        }

        self._emails.append(entry)

        return {
            "email_id": email_id,
            "priority": priority,
            "added": True,
        }

    def sort_by_priority(
        self,
        limit: int = 20,
    ) -> dict[str, Any]:
        """Öncelik sıralar.

        Args:
            limit: Sınır.

        Returns:
            Sıralama bilgisi.
        """
        sorted_emails = sorted(
            self._emails,
            key=lambda e: (
                PRIORITY_ORDER.get(
                    e["priority"], 2,
                ),
                -e["timestamp"],
            ),
        )

        self._stats[
            "emails_sorted"
        ] += 1

        return {
            "emails": sorted_emails[
                :limit
            ],
            "total": len(sorted_emails),
            "sorted": True,
        }

    def get_important_first(
        self,
        limit: int = 10,
    ) -> dict[str, Any]:
        """Önemli olanları önce getirir.

        Args:
            limit: Sınır.

        Returns:
            Liste bilgisi.
        """
        important = [
            e for e in self._emails
            if e["priority"] in (
                "critical", "high",
            )
        ]

        important.sort(
            key=lambda e: (
                PRIORITY_ORDER.get(
                    e["priority"], 2,
                ),
                -e["timestamp"],
            ),
        )

        return {
            "emails": important[:limit],
            "count": len(important),
            "retrieved": True,
        }

    def add_vip(
        self,
        sender: str,
    ) -> dict[str, Any]:
        """VIP gönderici ekler.

        Args:
            sender: Gönderici.

        Returns:
            Ekleme bilgisi.
        """
        self._vip_senders.add(sender)

        return {
            "sender": sender,
            "added": True,
            "total_vip": len(
                self._vip_senders,
            ),
        }

    def get_time_sensitive(
        self,
        max_age_hours: int = 24,
    ) -> dict[str, Any]:
        """Zamana duyarlı emailleri getirir.

        Args:
            max_age_hours: Maks yaş (saat).

        Returns:
            Liste bilgisi.
        """
        now = time.time()
        cutoff = now - (
            max_age_hours * 3600
        )

        recent = [
            e for e in self._emails
            if e["timestamp"] >= cutoff
            and not e["read"]
        ]

        recent.sort(
            key=lambda e: e["timestamp"],
            reverse=True,
        )

        return {
            "emails": recent,
            "count": len(recent),
            "retrieved": True,
        }

    def add_rule(
        self,
        name: str,
        condition_field: str = "",
        condition_value: str = "",
        set_priority: str = "high",
    ) -> dict[str, Any]:
        """Özel kural ekler.

        Args:
            name: Kural adı.
            condition_field: Koşul alanı.
            condition_value: Koşul değeri.
            set_priority: Atanacak öncelik.

        Returns:
            Ekleme bilgisi.
        """
        rule = {
            "name": name,
            "condition_field": (
                condition_field
            ),
            "condition_value": (
                condition_value
            ),
            "set_priority": set_priority,
            "timestamp": time.time(),
        }
        self._rules.append(rule)

        return {
            "name": name,
            "added": True,
            "total_rules": len(self._rules),
        }

    @property
    def email_count(self) -> int:
        """Email sayısı."""
        return len(self._emails)

    @property
    def vip_count(self) -> int:
        """VIP sayısı."""
        return len(self._vip_senders)
