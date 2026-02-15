"""ATLAS IAM Oturum Yoneticisi modulu.

Token yonetimi, suresi dolma,
yenileme, esanli oturum limiti.
"""

import hashlib
import logging
import time
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class IAMSessionManager:
    """IAM oturum yoneticisi.

    Oturum ve token islemlerini yonetir.

    Attributes:
        _sessions: Oturum kayitlari.
        _tokens: Token kayitlari.
    """

    def __init__(
        self,
        session_timeout: int = 1800,
        max_concurrent: int = 5,
        refresh_enabled: bool = True,
    ) -> None:
        """Oturum yoneticisini baslatir.

        Args:
            session_timeout: Oturum suresi (sn).
            max_concurrent: Maks esanli oturum.
            refresh_enabled: Yenileme aktif mi.
        """
        self._sessions: dict[
            str, dict[str, Any]
        ] = {}
        self._tokens: dict[
            str, dict[str, Any]
        ] = {}
        self._user_sessions: dict[
            str, list[str]
        ] = {}
        self._session_timeout = session_timeout
        self._max_concurrent = max_concurrent
        self._refresh_enabled = refresh_enabled
        self._stats = {
            "created": 0,
            "expired": 0,
            "refreshed": 0,
            "revoked": 0,
        }

        logger.info(
            "IAMSessionManager baslatildi",
        )

    def create_session(
        self,
        user_id: str,
        ip_address: str = "",
        user_agent: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Oturum olusturur.

        Args:
            user_id: Kullanici ID.
            ip_address: IP adresi.
            user_agent: Kullanici agenti.
            metadata: Ek bilgiler.

        Returns:
            Oturum bilgisi.
        """
        # Esanli oturum kontrolu
        user_sess = self._user_sessions.get(
            user_id, [],
        )
        active = [
            s for s in user_sess
            if s in self._sessions
            and not self._is_expired(s)
        ]

        if len(active) >= self._max_concurrent:
            # En eski oturumu kapat
            oldest = active[0]
            self.revoke_session(oldest)

        session_id = str(uuid4())[:16]
        access_token = self._generate_token()
        refresh_token = (
            self._generate_token()
            if self._refresh_enabled
            else None
        )

        now = time.time()
        self._sessions[session_id] = {
            "session_id": session_id,
            "user_id": user_id,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "created_at": now,
            "expires_at": now + self._session_timeout,
            "last_activity": now,
            "metadata": metadata or {},
            "active": True,
        }

        # Token -> session eslesmesi
        self._tokens[access_token] = {
            "session_id": session_id,
            "type": "access",
            "user_id": user_id,
        }
        if refresh_token:
            self._tokens[refresh_token] = {
                "session_id": session_id,
                "type": "refresh",
                "user_id": user_id,
            }

        # Kullanici oturumlari
        if user_id not in self._user_sessions:
            self._user_sessions[user_id] = []
        self._user_sessions[user_id].append(
            session_id,
        )

        self._stats["created"] += 1

        return {
            "session_id": session_id,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_at": now + self._session_timeout,
        }

    def validate_token(
        self,
        token: str,
    ) -> dict[str, Any]:
        """Token dogrulama yapar.

        Args:
            token: Token degeri.

        Returns:
            Dogrulama sonucu.
        """
        token_info = self._tokens.get(token)
        if not token_info:
            return {
                "valid": False,
                "reason": "token_not_found",
            }

        session_id = token_info["session_id"]
        session = self._sessions.get(session_id)
        if not session:
            return {
                "valid": False,
                "reason": "session_not_found",
            }

        if not session["active"]:
            return {
                "valid": False,
                "reason": "session_revoked",
            }

        if self._is_expired(session_id):
            self._stats["expired"] += 1
            return {
                "valid": False,
                "reason": "session_expired",
            }

        # Aktivite guncelle
        session["last_activity"] = time.time()

        return {
            "valid": True,
            "user_id": session["user_id"],
            "session_id": session_id,
            "token_type": token_info["type"],
        }

    def refresh_session(
        self,
        refresh_token: str,
    ) -> dict[str, Any]:
        """Oturumu yeniler.

        Args:
            refresh_token: Yenileme tokeni.

        Returns:
            Yeni token bilgisi.
        """
        if not self._refresh_enabled:
            return {
                "error": "refresh_disabled",
            }

        token_info = self._tokens.get(
            refresh_token,
        )
        if not token_info:
            return {"error": "token_not_found"}

        if token_info["type"] != "refresh":
            return {"error": "not_refresh_token"}

        session_id = token_info["session_id"]
        session = self._sessions.get(session_id)
        if not session or not session["active"]:
            return {"error": "session_invalid"}

        # Eski access token'i kaldir
        old_token = session["access_token"]
        self._tokens.pop(old_token, None)

        # Yeni token olustur
        new_token = self._generate_token()
        session["access_token"] = new_token
        session["expires_at"] = (
            time.time() + self._session_timeout
        )
        session["last_activity"] = time.time()

        self._tokens[new_token] = {
            "session_id": session_id,
            "type": "access",
            "user_id": session["user_id"],
        }

        self._stats["refreshed"] += 1

        return {
            "access_token": new_token,
            "session_id": session_id,
            "expires_at": session["expires_at"],
        }

    def revoke_session(
        self,
        session_id: str,
    ) -> dict[str, Any]:
        """Oturumu iptal eder.

        Args:
            session_id: Oturum ID.

        Returns:
            Iptal sonucu.
        """
        session = self._sessions.get(session_id)
        if not session:
            return {"error": "session_not_found"}

        session["active"] = False

        # Tokenlari temizle
        if session.get("access_token"):
            self._tokens.pop(
                session["access_token"], None,
            )
        if session.get("refresh_token"):
            self._tokens.pop(
                session["refresh_token"], None,
            )

        self._stats["revoked"] += 1

        return {
            "session_id": session_id,
            "status": "revoked",
        }

    def revoke_user_sessions(
        self,
        user_id: str,
    ) -> dict[str, Any]:
        """Kullanici tum oturumlarini iptal eder.

        Args:
            user_id: Kullanici ID.

        Returns:
            Iptal sonucu.
        """
        sessions = self._user_sessions.get(
            user_id, [],
        )
        revoked = 0

        for sid in sessions:
            session = self._sessions.get(sid)
            if session and session["active"]:
                self.revoke_session(sid)
                revoked += 1

        return {
            "user_id": user_id,
            "revoked": revoked,
        }

    def get_session(
        self,
        session_id: str,
    ) -> dict[str, Any] | None:
        """Oturum getirir.

        Args:
            session_id: Oturum ID.

        Returns:
            Oturum bilgisi veya None.
        """
        return self._sessions.get(session_id)

    def get_user_sessions(
        self,
        user_id: str,
        active_only: bool = False,
    ) -> list[dict[str, Any]]:
        """Kullanici oturumlarini getirir.

        Args:
            user_id: Kullanici ID.
            active_only: Sadece aktifler.

        Returns:
            Oturum listesi.
        """
        session_ids = self._user_sessions.get(
            user_id, [],
        )
        sessions = []

        for sid in session_ids:
            session = self._sessions.get(sid)
            if not session:
                continue
            if active_only:
                if (
                    session["active"]
                    and not self._is_expired(sid)
                ):
                    sessions.append(session)
            else:
                sessions.append(session)

        return sessions

    def cleanup_expired(self) -> int:
        """Suresi dolmus oturumlari temizler.

        Returns:
            Temizlenen oturum sayisi.
        """
        expired = []
        for sid, session in self._sessions.items():
            if (
                session["active"]
                and self._is_expired(sid)
            ):
                expired.append(sid)

        for sid in expired:
            self.revoke_session(sid)
            self._stats["expired"] += 1

        return len(expired)

    def _is_expired(
        self,
        session_id: str,
    ) -> bool:
        """Oturum suresi dolmus mu.

        Args:
            session_id: Oturum ID.

        Returns:
            Suresi dolmus mu.
        """
        session = self._sessions.get(session_id)
        if not session:
            return True
        return time.time() > session["expires_at"]

    def _generate_token(self) -> str:
        """Token olusturur.

        Returns:
            Token degeri.
        """
        raw = f"{uuid4()}{time.time()}"
        return hashlib.sha256(
            raw.encode(),
        ).hexdigest()[:32]

    @property
    def session_count(self) -> int:
        """Toplam oturum sayisi."""
        return len(self._sessions)

    @property
    def active_session_count(self) -> int:
        """Aktif oturum sayisi."""
        return sum(
            1
            for s in self._sessions.values()
            if s["active"]
            and not self._is_expired(
                s["session_id"],
            )
        )

    @property
    def token_count(self) -> int:
        """Token sayisi."""
        return len(self._tokens)
