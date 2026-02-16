"""ATLAS Email Özeti modülü.

Günlük özet, özet üretimi,
öne çıkanlar, aksiyon öğeleri,
okunmamış özeti.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class EmailDigest:
    """Email özeti.

    Email özetleri üretir.

    Attributes:
        _emails: Email kayıtları.
        _digests: Özet kayıtları.
    """

    def __init__(self) -> None:
        """Özeti başlatır."""
        self._emails: list[
            dict[str, Any]
        ] = []
        self._digests: list[
            dict[str, Any]
        ] = []
        self._counter = 0
        self._stats = {
            "digests_generated": 0,
            "emails_summarized": 0,
        }

        logger.info(
            "EmailDigest baslatildi",
        )

    def add_email(
        self,
        email_id: str = "",
        sender: str = "",
        subject: str = "",
        priority: str = "medium",
        has_action: bool = False,
        read: bool = False,
    ) -> dict[str, Any]:
        """Email ekler.

        Args:
            email_id: Email kimliği.
            sender: Gönderici.
            subject: Konu.
            priority: Öncelik.
            has_action: Aksiyon var mı.
            read: Okundu mu.

        Returns:
            Ekleme bilgisi.
        """
        self._counter += 1
        if not email_id:
            email_id = f"ed_{self._counter}"

        self._emails.append({
            "email_id": email_id,
            "sender": sender,
            "subject": subject,
            "priority": priority,
            "has_action": has_action,
            "read": read,
            "timestamp": time.time(),
        })

        return {
            "email_id": email_id,
            "added": True,
        }

    def generate_daily_digest(
        self,
    ) -> dict[str, Any]:
        """Günlük özet üretir.

        Returns:
            Özet bilgisi.
        """
        total = len(self._emails)
        unread = sum(
            1 for e in self._emails
            if not e["read"]
        )
        high_priority = sum(
            1 for e in self._emails
            if e["priority"] in (
                "critical", "high",
            )
        )
        action_items = sum(
            1 for e in self._emails
            if e["has_action"]
        )

        self._counter += 1
        did = f"dig_{self._counter}"

        digest = {
            "digest_id": did,
            "period": "daily",
            "total_emails": total,
            "unread": unread,
            "high_priority": high_priority,
            "action_items": action_items,
            "timestamp": time.time(),
        }

        self._digests.append(digest)
        self._stats[
            "digests_generated"
        ] += 1
        self._stats[
            "emails_summarized"
        ] += total

        return {
            **digest,
            "generated": True,
        }

    def generate_summary(
        self,
        max_items: int = 10,
    ) -> dict[str, Any]:
        """Özet üretir.

        Args:
            max_items: Maks öğe.

        Returns:
            Özet bilgisi.
        """
        # Önceliğe göre sırala
        sorted_emails = sorted(
            self._emails,
            key=lambda e: {
                "critical": 0,
                "high": 1,
                "medium": 2,
                "low": 3,
            }.get(e["priority"], 2),
        )

        items = [
            {
                "sender": e["sender"],
                "subject": e["subject"],
                "priority": e["priority"],
            }
            for e in sorted_emails[
                :max_items
            ]
        ]

        return {
            "items": items,
            "count": len(items),
            "total_emails": len(
                self._emails,
            ),
            "generated": True,
        }

    def get_highlights(
        self,
        limit: int = 5,
    ) -> dict[str, Any]:
        """Öne çıkanları getirir.

        Args:
            limit: Sınır.

        Returns:
            Öne çıkanlar bilgisi.
        """
        highlights = [
            e for e in self._emails
            if e["priority"] in (
                "critical", "high",
            )
            or e["has_action"]
        ]

        highlights.sort(
            key=lambda e: e["timestamp"],
            reverse=True,
        )

        return {
            "highlights": [
                {
                    "sender": e["sender"],
                    "subject": e["subject"],
                    "priority": e["priority"],
                    "has_action": e[
                        "has_action"
                    ],
                }
                for e in highlights[:limit]
            ],
            "count": min(
                len(highlights), limit,
            ),
            "retrieved": True,
        }

    def get_action_items(
        self,
    ) -> dict[str, Any]:
        """Aksiyon öğelerini getirir.

        Returns:
            Aksiyon bilgisi.
        """
        actions = [
            {
                "email_id": e["email_id"],
                "sender": e["sender"],
                "subject": e["subject"],
                "priority": e["priority"],
            }
            for e in self._emails
            if e["has_action"]
        ]

        return {
            "action_items": actions,
            "count": len(actions),
            "retrieved": True,
        }

    def get_unread_summary(
        self,
    ) -> dict[str, Any]:
        """Okunmamış özeti döndürür.

        Returns:
            Özet bilgisi.
        """
        unread = [
            e for e in self._emails
            if not e["read"]
        ]

        by_priority: dict[str, int] = {}
        for e in unread:
            p = e["priority"]
            by_priority[p] = (
                by_priority.get(p, 0) + 1
            )

        return {
            "total_unread": len(unread),
            "by_priority": by_priority,
            "oldest_unread": (
                unread[0]["subject"]
                if unread
                else None
            ),
            "summarized": True,
        }

    @property
    def digest_count(self) -> int:
        """Özet sayısı."""
        return self._stats[
            "digests_generated"
        ]

    @property
    def email_count(self) -> int:
        """Email sayısı."""
        return len(self._emails)
