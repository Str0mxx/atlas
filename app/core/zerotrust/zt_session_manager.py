"""
ZT oturum yoneticisi modulu.

Oturum olusturma, surekli dogrulama,
zaman asimi, zorla sonlandirma,
oturum analitigi.
"""

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class ZTSessionManager:
    """ZT oturum yoneticisi.

    Attributes:
        _sessions: Oturum kayitlari.
        _policies: Oturum politikalari.
        _events: Oturum olaylari.
        _stats: Istatistikler.
    """

    SESSION_STATES: list[str] = [
        "active",
        "idle",
        "suspended",
        "terminated",
        "expired",
    ]

    def __init__(
        self,
        default_timeout_min: int = 30,
        max_sessions_per_user: int = 5,
    ) -> None:
        """Yoneticiyi baslatir.

        Args:
            default_timeout_min: Varsayilan zaman asimi.
            max_sessions_per_user: Kullanici basina max.
        """
        self._sessions: dict[
            str, dict
        ] = {}
        self._policies: dict[
            str, dict
        ] = {}
        self._events: list[dict] = []
        self._default_timeout = (
            default_timeout_min
        )
        self._max_sessions = (
            max_sessions_per_user
        )
        self._stats: dict[str, int] = {
            "sessions_created": 0,
            "sessions_terminated": 0,
            "sessions_expired": 0,
            "validations": 0,
            "forced_terminations": 0,
        }
        logger.info(
            "ZTSessionManager baslatildi"
        )

    @property
    def session_count(self) -> int:
        """Aktif oturum sayisi."""
        return sum(
            1
            for s in self._sessions.values()
            if s["state"] == "active"
        )

    def create_session(
        self,
        user_id: str = "",
        device_id: str = "",
        ip_address: str = "",
        risk_level: str = "low",
        timeout_min: int = 0,
    ) -> dict[str, Any]:
        """Oturum olusturur.

        Args:
            user_id: Kullanici ID.
            device_id: Cihaz ID.
            ip_address: IP adresi.
            risk_level: Risk seviyesi.
            timeout_min: Zaman asimi.

        Returns:
            Olusturma bilgisi.
        """
        try:
            user_sessions = [
                s
                for s in self._sessions.values()
                if s["user_id"] == user_id
                and s["state"] == "active"
            ]
            if (
                len(user_sessions)
                >= self._max_sessions
            ):
                return {
                    "created": False,
                    "error": (
                        "Max oturum limiti"
                    ),
                }

            sid = f"zs_{uuid4()!s:.8}"
            token = hashlib.sha256(
                f"{sid}{user_id}{uuid4()}"
                .encode()
            ).hexdigest()[:32]
            tout = (
                timeout_min
                or self._default_timeout
            )

            if risk_level in (
                "high",
                "critical",
            ):
                tout = min(tout, 15)

            now = datetime.now(
                timezone.utc
            ).isoformat()
            self._sessions[sid] = {
                "session_id": sid,
                "user_id": user_id,
                "device_id": device_id,
                "ip_address": ip_address,
                "token": token,
                "risk_level": risk_level,
                "timeout_min": tout,
                "state": "active",
                "created_at": now,
                "last_activity": now,
                "validation_count": 0,
            }
            self._stats[
                "sessions_created"
            ] += 1

            self._log_event(
                sid,
                "created",
                {"user_id": user_id},
            )

            return {
                "session_id": sid,
                "token": token,
                "timeout_min": tout,
                "created": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "created": False,
                "error": str(e),
            }

    def validate_session(
        self,
        session_id: str = "",
        token: str = "",
        ip_address: str = "",
    ) -> dict[str, Any]:
        """Oturumu dogrular.

        Args:
            session_id: Oturum ID.
            token: Oturum tokeni.
            ip_address: Mevcut IP.

        Returns:
            Dogrulama bilgisi.
        """
        try:
            self._stats["validations"] += 1
            sess = self._sessions.get(
                session_id
            )
            if not sess:
                return {
                    "valid": False,
                    "error": (
                        "Oturum bulunamadi"
                    ),
                }

            if sess["state"] != "active":
                return {
                    "valid": False,
                    "error": (
                        f"Oturum {sess['state']}"
                    ),
                }

            issues: list[str] = []
            if token and (
                token != sess["token"]
            ):
                issues.append(
                    "token_mismatch"
                )
            if ip_address and (
                ip_address
                != sess["ip_address"]
            ):
                issues.append("ip_changed")

            valid = len(issues) == 0
            if valid:
                sess["last_activity"] = (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                )
                sess[
                    "validation_count"
                ] += 1

            return {
                "session_id": session_id,
                "valid": valid,
                "issues": issues,
                "state": sess["state"],
                "validated": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "valid": False,
                "error": str(e),
            }

    def refresh_session(
        self,
        session_id: str = "",
    ) -> dict[str, Any]:
        """Oturumu yeniler.

        Args:
            session_id: Oturum ID.

        Returns:
            Yenileme bilgisi.
        """
        try:
            sess = self._sessions.get(
                session_id
            )
            if not sess:
                return {
                    "refreshed": False,
                    "error": (
                        "Oturum bulunamadi"
                    ),
                }

            if sess["state"] != "active":
                return {
                    "refreshed": False,
                    "error": (
                        "Oturum aktif degil"
                    ),
                }

            new_token = hashlib.sha256(
                f"{session_id}{uuid4()}"
                .encode()
            ).hexdigest()[:32]
            sess["token"] = new_token
            sess["last_activity"] = (
                datetime.now(
                    timezone.utc
                ).isoformat()
            )

            self._log_event(
                session_id,
                "refreshed",
                {},
            )

            return {
                "session_id": session_id,
                "new_token": new_token,
                "refreshed": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "refreshed": False,
                "error": str(e),
            }

    def terminate_session(
        self,
        session_id: str = "",
        reason: str = "user_logout",
        forced: bool = False,
    ) -> dict[str, Any]:
        """Oturumu sonlandirir.

        Args:
            session_id: Oturum ID.
            reason: Sebep.
            forced: Zorla mi.

        Returns:
            Sonlandirma bilgisi.
        """
        try:
            sess = self._sessions.get(
                session_id
            )
            if not sess:
                return {
                    "terminated": False,
                    "error": (
                        "Oturum bulunamadi"
                    ),
                }

            sess["state"] = "terminated"
            sess["terminated_at"] = (
                datetime.now(
                    timezone.utc
                ).isoformat()
            )
            sess["termination_reason"] = (
                reason
            )
            self._stats[
                "sessions_terminated"
            ] += 1
            if forced:
                self._stats[
                    "forced_terminations"
                ] += 1

            self._log_event(
                session_id,
                "terminated",
                {
                    "reason": reason,
                    "forced": forced,
                },
            )

            return {
                "session_id": session_id,
                "reason": reason,
                "forced": forced,
                "terminated": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "terminated": False,
                "error": str(e),
            }

    def terminate_user_sessions(
        self,
        user_id: str = "",
        reason: str = "security",
    ) -> dict[str, Any]:
        """Kullanici oturumlarini sonlandirir.

        Args:
            user_id: Kullanici ID.
            reason: Sebep.

        Returns:
            Sonlandirma bilgisi.
        """
        try:
            count = 0
            for sess in (
                self._sessions.values()
            ):
                if (
                    sess["user_id"] == user_id
                    and sess["state"]
                    == "active"
                ):
                    sess["state"] = (
                        "terminated"
                    )
                    sess["terminated_at"] = (
                        datetime.now(
                            timezone.utc
                        ).isoformat()
                    )
                    sess[
                        "termination_reason"
                    ] = reason
                    count += 1

            self._stats[
                "sessions_terminated"
            ] += count
            self._stats[
                "forced_terminations"
            ] += count

            return {
                "user_id": user_id,
                "terminated_count": count,
                "reason": reason,
                "terminated": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "terminated": False,
                "error": str(e),
            }

    def check_timeout(
        self,
        session_id: str = "",
    ) -> dict[str, Any]:
        """Zaman asimi kontrol eder.

        Args:
            session_id: Oturum ID.

        Returns:
            Kontrol bilgisi.
        """
        try:
            sess = self._sessions.get(
                session_id
            )
            if not sess:
                return {
                    "checked": False,
                    "error": (
                        "Oturum bulunamadi"
                    ),
                }

            if sess["state"] != "active":
                return {
                    "session_id": session_id,
                    "expired": True,
                    "state": sess["state"],
                    "checked": True,
                }

            last = datetime.fromisoformat(
                sess["last_activity"]
            )
            now = datetime.now(timezone.utc)
            elapsed = (
                now - last
            ).total_seconds() / 60
            timeout = sess["timeout_min"]
            expired = elapsed > timeout

            if expired:
                sess["state"] = "expired"
                self._stats[
                    "sessions_expired"
                ] += 1
                self._log_event(
                    session_id,
                    "expired",
                    {
                        "elapsed_min": round(
                            elapsed, 1
                        )
                    },
                )

            return {
                "session_id": session_id,
                "elapsed_min": round(
                    elapsed, 1
                ),
                "timeout_min": timeout,
                "expired": expired,
                "checked": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "checked": False,
                "error": str(e),
            }

    def get_user_sessions(
        self,
        user_id: str = "",
    ) -> dict[str, Any]:
        """Kullanici oturumlarini getirir.

        Args:
            user_id: Kullanici ID.

        Returns:
            Oturum bilgisi.
        """
        try:
            sessions = [
                {
                    "session_id": s[
                        "session_id"
                    ],
                    "device_id": s[
                        "device_id"
                    ],
                    "state": s["state"],
                    "created_at": s[
                        "created_at"
                    ],
                }
                for s in (
                    self._sessions.values()
                )
                if s["user_id"] == user_id
            ]
            return {
                "user_id": user_id,
                "sessions": sessions,
                "count": len(sessions),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }

    def get_analytics(
        self,
    ) -> dict[str, Any]:
        """Oturum analitigi getirir.

        Returns:
            Analitik bilgisi.
        """
        try:
            active = sum(
                1
                for s in (
                    self._sessions.values()
                )
                if s["state"] == "active"
            )
            terminated = sum(
                1
                for s in (
                    self._sessions.values()
                )
                if s["state"]
                == "terminated"
            )
            expired = sum(
                1
                for s in (
                    self._sessions.values()
                )
                if s["state"] == "expired"
            )
            users = set(
                s["user_id"]
                for s in (
                    self._sessions.values()
                )
            )

            return {
                "total_sessions": len(
                    self._sessions
                ),
                "active": active,
                "terminated": terminated,
                "expired": expired,
                "unique_users": len(users),
                "total_events": len(
                    self._events
                ),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }

    def _log_event(
        self,
        session_id: str,
        event_type: str,
        details: dict,
    ) -> None:
        """Olay kaydeder."""
        self._events.append({
            "session_id": session_id,
            "event_type": event_type,
            "details": details,
            "timestamp": datetime.now(
                timezone.utc
            ).isoformat(),
        })

    def get_summary(
        self,
    ) -> dict[str, Any]:
        """Ozet getirir."""
        try:
            return {
                "total_sessions": len(
                    self._sessions
                ),
                "active_sessions": (
                    self.session_count
                ),
                "total_events": len(
                    self._events
                ),
                "stats": dict(self._stats),
                "retrieved": True,
            }
        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }
