"""ATLAS LinkedIn Bağlayıcı modülü.

Bağlantı istekleri, mesaj gönderme,
profil görüntüleme, aktivite takibi,
rate uyumluluğu.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class LinkedInConnector:
    """LinkedIn bağlayıcı.

    LinkedIn etkileşimlerini yönetir.

    Attributes:
        _connections: Bağlantılar.
        _messages: Mesajlar.
    """

    DAILY_CONNECTION_LIMIT = 20
    DAILY_MESSAGE_LIMIT = 50

    def __init__(self) -> None:
        """Bağlayıcıyı başlatır."""
        self._connections: list[
            dict[str, Any]
        ] = []
        self._messages: list[
            dict[str, Any]
        ] = []
        self._profile_views: list[
            dict[str, Any]
        ] = []
        self._counter = 0
        self._daily_connections = 0
        self._daily_messages = 0
        self._stats = {
            "connections_sent": 0,
            "connections_accepted": 0,
            "messages_sent": 0,
            "profiles_viewed": 0,
        }

        logger.info(
            "LinkedInConnector baslatildi",
        )

    def send_connection_request(
        self,
        profile_id: str,
        name: str,
        note: str = "",
    ) -> dict[str, Any]:
        """Bağlantı isteği gönderir.

        Args:
            profile_id: Profil ID.
            name: İsim.
            note: Not.

        Returns:
            İstek bilgisi.
        """
        if (
            self._daily_connections
            >= self.DAILY_CONNECTION_LIMIT
        ):
            return {
                "error": "daily_limit_reached",
                "limit": (
                    self.DAILY_CONNECTION_LIMIT
                ),
            }

        # Not karakter limiti (300)
        if len(note) > 300:
            note = note[:297] + "..."

        self._counter += 1
        cid = f"conn_{self._counter}"

        conn = {
            "connection_id": cid,
            "profile_id": profile_id,
            "name": name,
            "note": note,
            "status": "pending",
            "sent_at": time.time(),
        }
        self._connections.append(conn)
        self._daily_connections += 1
        self._stats[
            "connections_sent"
        ] += 1

        return {
            "connection_id": cid,
            "profile_id": profile_id,
            "name": name,
            "status": "pending",
            "sent": True,
        }

    def send_message(
        self,
        profile_id: str,
        message: str,
        subject: str = "",
    ) -> dict[str, Any]:
        """Mesaj gönderir.

        Args:
            profile_id: Profil ID.
            message: Mesaj.
            subject: Konu.

        Returns:
            Gönderim bilgisi.
        """
        if (
            self._daily_messages
            >= self.DAILY_MESSAGE_LIMIT
        ):
            return {
                "error": "daily_limit_reached",
                "limit": (
                    self.DAILY_MESSAGE_LIMIT
                ),
            }

        self._counter += 1
        mid = f"lmsg_{self._counter}"

        msg = {
            "message_id": mid,
            "profile_id": profile_id,
            "subject": subject,
            "message": message,
            "status": "sent",
            "sent_at": time.time(),
        }
        self._messages.append(msg)
        self._daily_messages += 1
        self._stats["messages_sent"] += 1

        return {
            "message_id": mid,
            "profile_id": profile_id,
            "status": "sent",
            "sent": True,
        }

    def view_profile(
        self,
        profile_id: str,
        name: str = "",
    ) -> dict[str, Any]:
        """Profil görüntüler.

        Args:
            profile_id: Profil ID.
            name: İsim.

        Returns:
            Görüntüleme bilgisi.
        """
        self._counter += 1
        vid = f"view_{self._counter}"

        view = {
            "view_id": vid,
            "profile_id": profile_id,
            "name": name,
            "viewed_at": time.time(),
        }
        self._profile_views.append(view)
        self._stats["profiles_viewed"] += 1

        return {
            "view_id": vid,
            "profile_id": profile_id,
            "name": name,
            "viewed": True,
        }

    def accept_connection(
        self,
        connection_id: str,
    ) -> dict[str, Any]:
        """Bağlantıyı kabul eder.

        Args:
            connection_id: Bağlantı ID.

        Returns:
            Kabul bilgisi.
        """
        for conn in self._connections:
            if (
                conn["connection_id"]
                == connection_id
            ):
                conn["status"] = "accepted"
                conn["accepted_at"] = (
                    time.time()
                )
                self._stats[
                    "connections_accepted"
                ] += 1
                return {
                    "connection_id": (
                        connection_id
                    ),
                    "status": "accepted",
                    "accepted": True,
                }

        return {
            "error": "connection_not_found",
        }

    def get_activity(
        self,
        profile_id: str | None = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        """Aktivite getirir.

        Args:
            profile_id: Profil filtresi.
            limit: Maks kayıt.

        Returns:
            Aktivite bilgisi.
        """
        activities = []

        conns = self._connections
        msgs = self._messages
        views = self._profile_views

        if profile_id:
            conns = [
                c for c in conns
                if c["profile_id"]
                == profile_id
            ]
            msgs = [
                m for m in msgs
                if m["profile_id"]
                == profile_id
            ]
            views = [
                v for v in views
                if v["profile_id"]
                == profile_id
            ]

        for c in conns:
            activities.append({
                "type": "connection",
                "id": c["connection_id"],
                "time": c["sent_at"],
            })
        for m in msgs:
            activities.append({
                "type": "message",
                "id": m["message_id"],
                "time": m["sent_at"],
            })
        for v in views:
            activities.append({
                "type": "profile_view",
                "id": v["view_id"],
                "time": v["viewed_at"],
            })

        activities.sort(
            key=lambda x: x["time"],
            reverse=True,
        )

        return {
            "activities": activities[:limit],
            "total": len(activities),
        }

    def reset_daily_counters(self) -> None:
        """Günlük sayaçları sıfırlar."""
        self._daily_connections = 0
        self._daily_messages = 0

    @property
    def connection_count(self) -> int:
        """Bağlantı sayısı."""
        return self._stats[
            "connections_sent"
        ]

    @property
    def message_count(self) -> int:
        """Mesaj sayısı."""
        return self._stats["messages_sent"]
