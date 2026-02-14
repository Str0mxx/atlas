"""ATLAS Oturum Koruyucu modulu.

Oturum yonetimi, token dogrulama,
zaman asimi, esanli oturum kontrolu
ve oturum kacirma onleme.
"""

import hashlib
import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Any

from app.models.security_hardening import (
    SessionRecord,
    SessionStatus,
)

logger = logging.getLogger(__name__)


class SessionGuardian:
    """Oturum koruyucu.

    Kullanici oturumlarini guvenli
    sekilde yonetir ve korur.

    Attributes:
        _sessions: Aktif oturumlar.
        _token_map: Token -> oturum esleme.
        _session_timeout: Oturum zaman asimi (dk).
        _max_concurrent: Maks esanli oturum.
    """

    def __init__(
        self,
        session_timeout: int = 30,
        max_concurrent: int = 3,
    ) -> None:
        """Oturum koruyucuyu baslatir.

        Args:
            session_timeout: Zaman asimi (dk).
            max_concurrent: Maks esanli oturum.
        """
        self._sessions: dict[str, SessionRecord] = {}
        self._token_map: dict[str, str] = {}
        self._session_timeout = max(1, session_timeout)
        self._max_concurrent = max(1, max_concurrent)
        self._revoked_count = 0

        logger.info(
            "SessionGuardian baslatildi "
            "(timeout=%d dk, max=%d)",
            self._session_timeout,
            self._max_concurrent,
        )

    def create_session(
        self,
        user: str,
        ip_address: str = "",
        user_agent: str = "",
    ) -> dict[str, Any]:
        """Oturum olusturur.

        Args:
            user: Kullanici.
            ip_address: IP adresi.
            user_agent: Tarayici bilgisi.

        Returns:
            Oturum bilgisi.
        """
        # Esanli oturum kontrolu
        self._enforce_concurrent_limit(user)

        now = datetime.now(timezone.utc)
        expires = now + timedelta(minutes=self._session_timeout)

        token = hashlib.sha256(
            f"{user}:{os.urandom(32).hex()}".encode(),
        ).hexdigest()

        session = SessionRecord(
            user=user,
            status=SessionStatus.ACTIVE,
            ip_address=ip_address,
            user_agent=user_agent,
            created_at=now,
            expires_at=expires,
        )

        self._sessions[session.session_id] = session
        self._token_map[token] = session.session_id

        logger.info("Oturum olusturuldu: %s (%s)", user, session.session_id)
        return {
            "session_id": session.session_id,
            "token": token,
            "expires_at": expires.isoformat(),
        }

    def validate_token(
        self,
        token: str,
        ip_address: str = "",
    ) -> dict[str, Any]:
        """Token dogrular.

        Args:
            token: Oturum tokeni.
            ip_address: Istekte bulunan IP.

        Returns:
            Dogrulama sonucu.
        """
        session_id = self._token_map.get(token)
        if not session_id:
            return {"valid": False, "reason": "Token bulunamadi"}

        session = self._sessions.get(session_id)
        if not session:
            return {"valid": False, "reason": "Oturum bulunamadi"}

        if session.status != SessionStatus.ACTIVE:
            return {
                "valid": False,
                "reason": f"Oturum durumu: {session.status.value}",
            }

        # Zaman asimi kontrolu
        now = datetime.now(timezone.utc)
        if now > session.expires_at:
            session.status = SessionStatus.EXPIRED
            return {"valid": False, "reason": "Oturum suresi doldu"}

        # IP degisiklik kontrolu (session hijacking)
        if (ip_address and session.ip_address
                and ip_address != session.ip_address):
            logger.warning(
                "IP degisikligi tespiti: %s -> %s (%s)",
                session.ip_address, ip_address,
                session.session_id,
            )
            return {
                "valid": False,
                "reason": "IP degisikligi tespiti",
                "hijacking_suspected": True,
            }

        return {
            "valid": True,
            "session_id": session_id,
            "user": session.user,
        }

    def revoke_session(
        self,
        session_id: str,
    ) -> bool:
        """Oturumu iptal eder.

        Args:
            session_id: Oturum ID.

        Returns:
            Basarili ise True.
        """
        session = self._sessions.get(session_id)
        if not session:
            return False

        session.status = SessionStatus.REVOKED
        self._revoked_count += 1

        # Token'i kaldir
        tokens_to_remove = [
            t for t, sid in self._token_map.items()
            if sid == session_id
        ]
        for token in tokens_to_remove:
            del self._token_map[token]

        logger.info("Oturum iptal edildi: %s", session_id)
        return True

    def revoke_user_sessions(
        self,
        user: str,
    ) -> int:
        """Kullanicinin tum oturumlarini iptal eder.

        Args:
            user: Kullanici.

        Returns:
            Iptal edilen sayisi.
        """
        revoked = 0
        for sid, session in self._sessions.items():
            if session.user == user and session.status == SessionStatus.ACTIVE:
                self.revoke_session(sid)
                revoked += 1
        return revoked

    def extend_session(
        self,
        session_id: str,
        minutes: int = 0,
    ) -> bool:
        """Oturumu uzatir.

        Args:
            session_id: Oturum ID.
            minutes: Uzatma suresi (dk, 0=varsayilan).

        Returns:
            Basarili ise True.
        """
        session = self._sessions.get(session_id)
        if not session or session.status != SessionStatus.ACTIVE:
            return False

        ext = minutes or self._session_timeout
        session.expires_at = (
            datetime.now(timezone.utc)
            + timedelta(minutes=ext)
        )
        return True

    def get_user_sessions(
        self,
        user: str,
    ) -> list[dict[str, Any]]:
        """Kullanici oturumlarini getirir.

        Args:
            user: Kullanici.

        Returns:
            Oturum listesi.
        """
        return [
            {
                "session_id": s.session_id,
                "status": s.status.value,
                "ip_address": s.ip_address,
                "created_at": s.created_at.isoformat(),
                "expires_at": s.expires_at.isoformat(),
            }
            for s in self._sessions.values()
            if s.user == user
        ]

    def cleanup_expired(self) -> int:
        """Suresi dolan oturumlari temizler.

        Returns:
            Temizlenen sayisi.
        """
        now = datetime.now(timezone.utc)
        expired = []

        for sid, session in self._sessions.items():
            if (session.status == SessionStatus.ACTIVE
                    and now > session.expires_at):
                session.status = SessionStatus.EXPIRED
                expired.append(sid)

        return len(expired)

    def _enforce_concurrent_limit(
        self,
        user: str,
    ) -> None:
        """Esanli oturum limitini uygular.

        Args:
            user: Kullanici.
        """
        active = [
            (sid, s) for sid, s in self._sessions.items()
            if s.user == user
            and s.status == SessionStatus.ACTIVE
        ]

        while len(active) >= self._max_concurrent:
            # En eski oturumu iptal et
            oldest_sid = active[0][0]
            self.revoke_session(oldest_sid)
            active.pop(0)

    @property
    def active_count(self) -> int:
        """Aktif oturum sayisi."""
        return sum(
            1 for s in self._sessions.values()
            if s.status == SessionStatus.ACTIVE
        )

    @property
    def total_count(self) -> int:
        """Toplam oturum sayisi."""
        return len(self._sessions)

    @property
    def revoked_count(self) -> int:
        """Iptal edilen sayisi."""
        return self._revoked_count
