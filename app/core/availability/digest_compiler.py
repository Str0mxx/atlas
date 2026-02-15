"""ATLAS Özet Derleyici modülü.

Mesaj derleme, öncelik sıralama,
özet üretme, aksiyon çıkarma,
teslimat zamanlama.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class DigestCompiler:
    """Özet derleyici.

    Tamponlanmış mesajları özetler halinde
    derler ve teslim eder.

    Attributes:
        _digests: Oluşturulan özetler.
        _schedule: Teslimat zamanlaması.
    """

    def __init__(
        self,
        max_items_per_digest: int = 20,
        default_frequency: str = "daily",
    ) -> None:
        """Derleyiciyi başlatır.

        Args:
            max_items_per_digest: Maks öğe/özet.
            default_frequency: Varsayılan sıklık.
        """
        self._digests: list[
            dict[str, Any]
        ] = []
        self._schedule: dict[
            str, dict[str, Any]
        ] = {}
        self._templates: dict[str, str] = {
            "summary": (
                "{count} mesaj, "
                "{high_priority} yüksek öncelikli"
            ),
        }
        self._max_items = max_items_per_digest
        self._default_frequency = (
            default_frequency
        )
        self._counter = 0
        self._stats = {
            "digests_created": 0,
            "messages_compiled": 0,
            "actions_extracted": 0,
            "deliveries_scheduled": 0,
        }

        logger.info(
            "DigestCompiler baslatildi",
        )

    def compile(
        self,
        messages: list[dict[str, Any]],
        title: str = "Özet",
    ) -> dict[str, Any]:
        """Mesajları derler.

        Args:
            messages: Mesaj listesi.
            title: Özet başlığı.

        Returns:
            Derleme bilgisi.
        """
        self._counter += 1
        did = f"digest_{self._counter}"

        # Öncelik sıralaması
        sorted_msgs = self._sort_by_priority(
            messages,
        )

        # Limitli al
        compiled = sorted_msgs[
            :self._max_items
        ]

        # Özet üret
        summary = self._generate_summary(
            compiled,
        )

        # Aksiyonları çıkar
        actions = self._extract_actions(
            compiled,
        )

        digest = {
            "digest_id": did,
            "title": title,
            "message_count": len(compiled),
            "total_available": len(messages),
            "summary": summary,
            "actions": actions,
            "messages": compiled,
            "created_at": time.time(),
        }
        self._digests.append(digest)
        self._stats["digests_created"] += 1
        self._stats["messages_compiled"] += len(
            compiled,
        )

        return digest

    def _sort_by_priority(
        self,
        messages: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Önceliğe göre sıralar."""
        priority_order = {
            "critical": 5,
            "high": 4,
            "medium": 3,
            "low": 2,
            "informational": 1,
        }
        return sorted(
            messages,
            key=lambda m: priority_order.get(
                m.get("priority", "medium"), 0,
            ),
            reverse=True,
        )

    def _generate_summary(
        self,
        messages: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Özet üretir."""
        priority_counts: dict[str, int] = {}
        source_counts: dict[str, int] = {}

        for msg in messages:
            p = msg.get("priority", "medium")
            s = msg.get("source", "unknown")
            priority_counts[p] = (
                priority_counts.get(p, 0) + 1
            )
            source_counts[s] = (
                source_counts.get(s, 0) + 1
            )

        high_priority = (
            priority_counts.get("critical", 0)
            + priority_counts.get("high", 0)
        )

        return {
            "total_messages": len(messages),
            "high_priority_count": high_priority,
            "priority_breakdown": (
                priority_counts
            ),
            "source_breakdown": source_counts,
            "text": self._templates[
                "summary"
            ].format(
                count=len(messages),
                high_priority=high_priority,
            ),
        }

    def _extract_actions(
        self,
        messages: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Aksiyonları çıkarır."""
        actions = []
        for msg in messages:
            msg_actions = msg.get("actions", [])
            if msg_actions:
                for action in msg_actions:
                    actions.append({
                        "action": action,
                        "from_message": msg.get(
                            "message_id", "",
                        ),
                        "priority": msg.get(
                            "priority", "medium",
                        ),
                    })
                    self._stats[
                        "actions_extracted"
                    ] += 1

            # İçerikten aksiyon çıkar
            content = msg.get("content", "")
            if any(
                kw in content.lower()
                for kw in [
                    "approve", "confirm",
                    "review", "action",
                    "onayla", "incele",
                ]
            ):
                actions.append({
                    "action": "review_required",
                    "from_message": msg.get(
                        "message_id", "",
                    ),
                    "priority": msg.get(
                        "priority", "medium",
                    ),
                    "content_hint": content[:50],
                })
                self._stats[
                    "actions_extracted"
                ] += 1

        return actions

    def schedule_delivery(
        self,
        user_id: str = "default",
        frequency: str | None = None,
        preferred_hour: int = 9,
    ) -> dict[str, Any]:
        """Teslimat zamanlar.

        Args:
            user_id: Kullanıcı ID.
            frequency: Sıklık.
            preferred_hour: Tercih edilen saat.

        Returns:
            Zamanlama bilgisi.
        """
        freq = (
            frequency or self._default_frequency
        )
        schedule = {
            "user_id": user_id,
            "frequency": freq,
            "preferred_hour": preferred_hour,
            "active": True,
            "created_at": time.time(),
        }
        self._schedule[user_id] = schedule
        self._stats[
            "deliveries_scheduled"
        ] += 1

        return {
            "user_id": user_id,
            "frequency": freq,
            "preferred_hour": preferred_hour,
            "scheduled": True,
        }

    def should_deliver(
        self,
        user_id: str = "default",
        current_hour: int = 12,
    ) -> dict[str, Any]:
        """Teslimat yapılmalı mı kontrol eder.

        Args:
            user_id: Kullanıcı ID.
            current_hour: Mevcut saat.

        Returns:
            Kontrol bilgisi.
        """
        schedule = self._schedule.get(user_id)
        if not schedule:
            return {
                "should_deliver": False,
                "reason": "no_schedule",
            }

        if not schedule["active"]:
            return {
                "should_deliver": False,
                "reason": "schedule_inactive",
            }

        preferred = schedule["preferred_hour"]
        should = current_hour == preferred

        return {
            "should_deliver": should,
            "frequency": schedule["frequency"],
            "preferred_hour": preferred,
            "current_hour": current_hour,
        }

    def get_digest(
        self,
        digest_id: str,
    ) -> dict[str, Any]:
        """Özet getirir.

        Args:
            digest_id: Özet ID.

        Returns:
            Özet bilgisi.
        """
        for digest in self._digests:
            if digest["digest_id"] == digest_id:
                return dict(digest)
        return {"error": "digest_not_found"}

    def get_digests(
        self,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Özetleri getirir.

        Args:
            limit: Maks kayıt.

        Returns:
            Özet listesi.
        """
        return list(self._digests[-limit:])

    @property
    def digest_count(self) -> int:
        """Özet sayısı."""
        return self._stats["digests_created"]

    @property
    def compiled_count(self) -> int:
        """Derlenen mesaj sayısı."""
        return self._stats["messages_compiled"]

    @property
    def actions_count(self) -> int:
        """Çıkarılan aksiyon sayısı."""
        return self._stats["actions_extracted"]
