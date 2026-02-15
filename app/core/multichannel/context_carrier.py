"""ATLAS Bağlam Taşıyıcı modülü.

Kanallar arası bağlam, oturum sürekliliği,
durum senkronizasyonu, geçmiş birleştirme,
bağlam geri yükleme.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class ContextCarrier:
    """Bağlam taşıyıcı.

    Kanallar arası bağlam taşır.

    Attributes:
        _sessions: Oturum kayıtları.
        _contexts: Bağlam kayıtları.
    """

    def __init__(
        self,
        timeout_minutes: int = 30,
    ) -> None:
        """Taşıyıcıyı başlatır.

        Args:
            timeout_minutes: Oturum zaman aşımı.
        """
        self._sessions: dict[
            str, dict[str, Any]
        ] = {}
        self._contexts: dict[
            str, dict[str, Any]
        ] = {}
        self._history: list[dict[str, Any]] = []
        self._timeout = timeout_minutes * 60
        self._counter = 0
        self._stats = {
            "sessions_created": 0,
            "context_transfers": 0,
            "restorations": 0,
        }

        logger.info("ContextCarrier baslatildi")

    def create_session(
        self,
        user_id: str,
        channel: str,
        initial_context: dict[str, Any]
        | None = None,
    ) -> dict[str, Any]:
        """Oturum oluşturur.

        Args:
            user_id: Kullanıcı ID.
            channel: Kanal.
            initial_context: Başlangıç bağlamı.

        Returns:
            Oturum bilgisi.
        """
        self._counter += 1
        sid = f"sess_{self._counter}"

        session = {
            "session_id": sid,
            "user_id": user_id,
            "channel": channel,
            "context": initial_context or {},
            "active": True,
            "created_at": time.time(),
            "last_activity": time.time(),
        }
        self._sessions[sid] = session

        # Kullanıcı bağlamını güncelle
        if user_id not in self._contexts:
            self._contexts[user_id] = {}
        self._contexts[user_id].update(
            initial_context or {},
        )

        self._stats["sessions_created"] += 1
        return session

    def transfer_context(
        self,
        user_id: str,
        from_channel: str,
        to_channel: str,
    ) -> dict[str, Any]:
        """Bağlam transfer eder.

        Args:
            user_id: Kullanıcı ID.
            from_channel: Kaynak kanal.
            to_channel: Hedef kanal.

        Returns:
            Transfer bilgisi.
        """
        # Kaynak oturum bul
        source_session = None
        for s in self._sessions.values():
            if (
                s["user_id"] == user_id
                and s["channel"] == from_channel
                and s["active"]
            ):
                source_session = s
                break

        context = {}
        if source_session:
            context = dict(
                source_session["context"],
            )

        # Kullanıcı bağlamını da ekle
        user_ctx = self._contexts.get(
            user_id, {},
        )
        context.update(user_ctx)

        # Yeni oturum oluştur
        new_session = self.create_session(
            user_id, to_channel, context,
        )

        self._stats["context_transfers"] += 1
        self._history.append({
            "type": "transfer",
            "user_id": user_id,
            "from": from_channel,
            "to": to_channel,
            "timestamp": time.time(),
        })

        return {
            "transferred": True,
            "from_channel": from_channel,
            "to_channel": to_channel,
            "context_keys": list(context.keys()),
            "new_session_id": new_session[
                "session_id"
            ],
        }

    def sync_state(
        self,
        user_id: str,
        updates: dict[str, Any],
    ) -> dict[str, Any]:
        """Durum senkronize eder.

        Args:
            user_id: Kullanıcı ID.
            updates: Güncellemeler.

        Returns:
            Senkronizasyon bilgisi.
        """
        if user_id not in self._contexts:
            self._contexts[user_id] = {}

        self._contexts[user_id].update(updates)

        # Tüm aktif oturumları güncelle
        synced = 0
        for s in self._sessions.values():
            if (
                s["user_id"] == user_id
                and s["active"]
            ):
                s["context"].update(updates)
                s["last_activity"] = time.time()
                synced += 1

        return {
            "user_id": user_id,
            "synced_sessions": synced,
            "keys_updated": list(updates.keys()),
        }

    def merge_history(
        self,
        user_id: str,
        channel: str,
        messages: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Geçmiş birleştirir.

        Args:
            user_id: Kullanıcı ID.
            channel: Kanal.
            messages: Mesajlar.

        Returns:
            Birleştirme bilgisi.
        """
        for msg in messages:
            self._history.append({
                "type": "message",
                "user_id": user_id,
                "channel": channel,
                "content": msg.get("content", ""),
                "timestamp": msg.get(
                    "timestamp", time.time(),
                ),
            })

        return {
            "user_id": user_id,
            "channel": channel,
            "messages_merged": len(messages),
        }

    def restore_context(
        self,
        user_id: str,
        channel: str | None = None,
    ) -> dict[str, Any]:
        """Bağlam geri yükler.

        Args:
            user_id: Kullanıcı ID.
            channel: Kanal filtresi.

        Returns:
            Geri yükleme bilgisi.
        """
        context = dict(
            self._contexts.get(user_id, {}),
        )

        # Kanal bazlı oturum bağlamı
        if channel:
            for s in self._sessions.values():
                if (
                    s["user_id"] == user_id
                    and s["channel"] == channel
                    and s["active"]
                ):
                    context.update(s["context"])
                    break

        self._stats["restorations"] += 1

        return {
            "user_id": user_id,
            "context": context,
            "restored": len(context) > 0,
        }

    def get_session(
        self,
        session_id: str,
    ) -> dict[str, Any]:
        """Oturum getirir.

        Args:
            session_id: Oturum ID.

        Returns:
            Oturum bilgisi.
        """
        session = self._sessions.get(session_id)
        if not session:
            return {"error": "session_not_found"}
        return dict(session)

    def close_session(
        self,
        session_id: str,
    ) -> dict[str, Any]:
        """Oturumu kapatır.

        Args:
            session_id: Oturum ID.

        Returns:
            Kapatma bilgisi.
        """
        session = self._sessions.get(session_id)
        if not session:
            return {"error": "session_not_found"}

        session["active"] = False
        return {
            "session_id": session_id,
            "closed": True,
        }

    def cleanup_expired(self) -> dict[str, Any]:
        """Süresi dolmuş oturumları temizler.

        Returns:
            Temizleme bilgisi.
        """
        now = time.time()
        expired = 0
        for s in self._sessions.values():
            if (
                s["active"]
                and now - s["last_activity"]
                > self._timeout
            ):
                s["active"] = False
                expired += 1

        return {
            "expired": expired,
            "active_sessions": self.active_session_count,
        }

    def get_user_sessions(
        self,
        user_id: str,
    ) -> list[dict[str, Any]]:
        """Kullanıcı oturumlarını getirir.

        Args:
            user_id: Kullanıcı ID.

        Returns:
            Oturum listesi.
        """
        return [
            dict(s) for s in self._sessions.values()
            if s["user_id"] == user_id
        ]

    @property
    def session_count(self) -> int:
        """Oturum sayısı."""
        return self._stats["sessions_created"]

    @property
    def active_session_count(self) -> int:
        """Aktif oturum sayısı."""
        return sum(
            1 for s in self._sessions.values()
            if s["active"]
        )

    @property
    def transfer_count(self) -> int:
        """Transfer sayısı."""
        return self._stats["context_transfers"]
