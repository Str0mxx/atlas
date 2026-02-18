"""
Oturum yonetici modulu.

Oturum olusturma, durum yonetimi,
zaman asimi, temizlik, kalicilik.
"""

import logging
import time
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class CoreSessionManager:
    """Cekirdek oturum yoneticisi.

    Attributes:
        _sessions: Aktif oturumlar.
        _expired: Suresi dolen oturumlar.
        _stats: Istatistikler.
    """

    SESSION_STATES: list[str] = [
        "active",
        "idle",
        "suspended",
        "expired",
        "closed",
    ]

    def __init__(
        self,
        default_timeout: int = 3600,
        max_sessions: int = 1000,
        cleanup_interval: int = 300,
    ) -> None:
        """Yoneticiyi baslatir.

        Args:
            default_timeout: Varsayilan zaman asimi (sn).
            max_sessions: Max oturum sayisi.
            cleanup_interval: Temizlik araligi (sn).
        """
        self._default_timeout = (
            default_timeout
        )
        self._max_sessions = max_sessions
        self._cleanup_interval = (
            cleanup_interval
        )
        self._sessions: dict[
            str, dict
        ] = {}
        self._expired: list[dict] = []
        self._persisted: dict[
            str, dict
        ] = {}
        self._stats: dict[str, int] = {
            "sessions_created": 0,
            "sessions_closed": 0,
            "sessions_expired": 0,
            "sessions_restored": 0,
            "cleanups_run": 0,
        }
        logger.info(
            "CoreSessionManager baslatildi"
        )

    @property
    def active_count(self) -> int:
        """Aktif oturum sayisi."""
        return len(self._sessions)

    def create_session(
        self,
        user_id: str = "",
        metadata: dict | None = None,
        timeout: int | None = None,
    ) -> dict[str, Any]:
        """Oturum olusturur.

        Args:
            user_id: Kullanici ID.
            metadata: Ek veri.
            timeout: Zaman asimi (sn).

        Returns:
            Oturum bilgisi.
        """
        try:
            if (
                len(self._sessions)
                >= self._max_sessions
            ):
                return {
                    "created": False,
                    "error": (
                        "Max oturum siniri"
                    ),
                }

            sid = (
                f"sess_{uuid4()!s:.8}"
            )
            now = time.time()
            ttl = (
                timeout
                or self._default_timeout
            )

            session = {
                "session_id": sid,
                "user_id": user_id,
                "state": "active",
                "metadata": (
                    metadata or {}
                ),
                "data": {},
                "timeout": ttl,
                "created_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
                "last_activity": now,
                "expires_at": now + ttl,
            }

            self._sessions[sid] = session
            self._stats[
                "sessions_created"
            ] += 1

            return {
                "session_id": sid,
                "user_id": user_id,
                "expires_in": ttl,
                "created": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "created": False,
                "error": str(e),
            }

    def get_session(
        self, session_id: str = ""
    ) -> dict[str, Any]:
        """Oturum getirir.

        Args:
            session_id: Oturum ID.

        Returns:
            Oturum bilgisi.
        """
        try:
            session = self._sessions.get(
                session_id
            )
            if not session:
                return {
                    "found": False,
                    "error": (
                        "Oturum bulunamadi"
                    ),
                }

            # Zaman asimi kontrolu
            if (
                time.time()
                > session["expires_at"]
            ):
                self._expire_session(
                    session_id
                )
                return {
                    "found": False,
                    "error": (
                        "Oturum suresi doldu"
                    ),
                }

            return {
                "session_id": session_id,
                "user_id": session[
                    "user_id"
                ],
                "state": session["state"],
                "data": dict(
                    session["data"]
                ),
                "found": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "found": False,
                "error": str(e),
            }

    def set_data(
        self,
        session_id: str = "",
        key: str = "",
        value: Any = None,
    ) -> dict[str, Any]:
        """Oturum verisini ayarlar.

        Args:
            session_id: Oturum ID.
            key: Anahtar.
            value: Deger.

        Returns:
            Ayarlama bilgisi.
        """
        try:
            session = self._sessions.get(
                session_id
            )
            if not session:
                return {
                    "set": False,
                    "error": (
                        "Oturum bulunamadi"
                    ),
                }

            session["data"][key] = value
            session["last_activity"] = (
                time.time()
            )

            return {
                "session_id": session_id,
                "key": key,
                "set": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "set": False,
                "error": str(e),
            }

    def get_data(
        self,
        session_id: str = "",
        key: str = "",
    ) -> dict[str, Any]:
        """Oturum verisi getirir.

        Args:
            session_id: Oturum ID.
            key: Anahtar.

        Returns:
            Veri bilgisi.
        """
        try:
            session = self._sessions.get(
                session_id
            )
            if not session:
                return {
                    "found": False,
                    "error": (
                        "Oturum bulunamadi"
                    ),
                }

            value = session["data"].get(
                key
            )
            return {
                "key": key,
                "value": value,
                "found": value is not None,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "found": False,
                "error": str(e),
            }

    def touch(
        self, session_id: str = ""
    ) -> dict[str, Any]:
        """Oturum aktivitesini gunceller.

        Args:
            session_id: Oturum ID.

        Returns:
            Guncelleme bilgisi.
        """
        try:
            session = self._sessions.get(
                session_id
            )
            if not session:
                return {
                    "touched": False,
                    "error": (
                        "Oturum bulunamadi"
                    ),
                }

            now = time.time()
            session["last_activity"] = now
            session["expires_at"] = (
                now + session["timeout"]
            )
            session["state"] = "active"

            return {
                "session_id": session_id,
                "touched": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "touched": False,
                "error": str(e),
            }

    def close_session(
        self, session_id: str = ""
    ) -> dict[str, Any]:
        """Oturumu kapatir.

        Args:
            session_id: Oturum ID.

        Returns:
            Kapatma bilgisi.
        """
        try:
            session = self._sessions.pop(
                session_id, None
            )
            if not session:
                return {
                    "closed": False,
                    "error": (
                        "Oturum bulunamadi"
                    ),
                }

            session["state"] = "closed"
            session["closed_at"] = (
                datetime.now(
                    timezone.utc
                ).isoformat()
            )
            self._expired.append(session)
            self._stats[
                "sessions_closed"
            ] += 1

            return {
                "session_id": session_id,
                "closed": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "closed": False,
                "error": str(e),
            }

    def _expire_session(
        self, session_id: str
    ) -> None:
        """Oturumu suresi dolmus olarak isaretle."""
        session = self._sessions.pop(
            session_id, None
        )
        if session:
            session["state"] = "expired"
            self._expired.append(session)
            self._stats[
                "sessions_expired"
            ] += 1

    def cleanup(
        self,
    ) -> dict[str, Any]:
        """Suresi dolen oturumlari temizler.

        Returns:
            Temizlik bilgisi.
        """
        try:
            now = time.time()
            expired_ids = [
                sid
                for sid, s in
                self._sessions.items()
                if now > s["expires_at"]
            ]

            for sid in expired_ids:
                self._expire_session(sid)

            self._stats[
                "cleanups_run"
            ] += 1

            return {
                "expired_count": len(
                    expired_ids
                ),
                "remaining": len(
                    self._sessions
                ),
                "cleaned": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "cleaned": False,
                "error": str(e),
            }

    def persist_session(
        self, session_id: str = ""
    ) -> dict[str, Any]:
        """Oturumu kalici depoya yazar.

        Args:
            session_id: Oturum ID.

        Returns:
            Kalicilik bilgisi.
        """
        try:
            session = self._sessions.get(
                session_id
            )
            if not session:
                return {
                    "persisted": False,
                    "error": (
                        "Oturum bulunamadi"
                    ),
                }

            self._persisted[
                session_id
            ] = dict(session)

            return {
                "session_id": session_id,
                "persisted": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "persisted": False,
                "error": str(e),
            }

    def restore_session(
        self, session_id: str = ""
    ) -> dict[str, Any]:
        """Oturumu kalici depodan yukler.

        Args:
            session_id: Oturum ID.

        Returns:
            Yukleme bilgisi.
        """
        try:
            persisted = (
                self._persisted.get(
                    session_id
                )
            )
            if not persisted:
                return {
                    "restored": False,
                    "error": (
                        "Kalici oturum yok"
                    ),
                }

            # Zaman asimini yenile
            now = time.time()
            persisted["last_activity"] = (
                now
            )
            persisted["expires_at"] = (
                now
                + persisted["timeout"]
            )
            persisted["state"] = "active"

            self._sessions[
                session_id
            ] = dict(persisted)
            self._stats[
                "sessions_restored"
            ] += 1

            return {
                "session_id": session_id,
                "restored": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "restored": False,
                "error": str(e),
            }

    def get_summary(
        self,
    ) -> dict[str, Any]:
        """Ozet getirir."""
        try:
            return {
                "active_sessions": len(
                    self._sessions
                ),
                "expired_sessions": len(
                    self._expired
                ),
                "persisted_sessions": len(
                    self._persisted
                ),
                "stats": dict(
                    self._stats
                ),
                "retrieved": True,
            }
        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }
