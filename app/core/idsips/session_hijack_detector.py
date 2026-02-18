"""
Oturum kacirma tespitcisi modulu.

Oturum izleme, IP degisiklik tespiti,
cihaz parmak izi, esanli oturum limiti,
zorunlu cikis.
"""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class SessionHijackDetector:
    """Oturum kacirma tespitcisi.

    Attributes:
        _sessions: Oturum kayitlari.
        _alerts: Uyari kayitlari.
        _config: Yapilandirma.
        _stats: Istatistikler.
    """

    def __init__(
        self,
        max_concurrent: int = 3,
    ) -> None:
        """Tespitciyi baslatir.

        Args:
            max_concurrent: Maks esanli oturum.
        """
        self._sessions: dict[
            str, dict
        ] = {}
        self._alerts: list[dict] = []
        self._max_concurrent = max_concurrent
        self._stats: dict[str, int] = {
            "sessions_tracked": 0,
            "hijack_alerts": 0,
            "forced_logouts": 0,
        }
        logger.info(
            "SessionHijackDetector "
            "baslatildi"
        )

    @property
    def session_count(self) -> int:
        """Oturum sayisi."""
        return len(self._sessions)

    def register_session(
        self,
        session_id: str = "",
        user_id: str = "",
        ip: str = "",
        user_agent: str = "",
        fingerprint: str = "",
    ) -> dict[str, Any]:
        """Oturum kaydeder.

        Args:
            session_id: Oturum ID.
            user_id: Kullanici ID.
            ip: IP adresi.
            user_agent: Tarayici bilgisi.
            fingerprint: Cihaz parmak izi.

        Returns:
            Kayit bilgisi.
        """
        try:
            self._sessions[session_id] = {
                "user_id": user_id,
                "ip": ip,
                "user_agent": user_agent,
                "fingerprint": fingerprint,
                "active": True,
                "created_at": datetime.now(
                    timezone.utc
                ).isoformat(),
            }
            self._stats[
                "sessions_tracked"
            ] += 1

            return {
                "session_id": session_id,
                "registered": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "registered": False,
                "error": str(e),
            }

    def check_ip_change(
        self,
        session_id: str = "",
        current_ip: str = "",
    ) -> dict[str, Any]:
        """IP degisiklik kontrol eder.

        Args:
            session_id: Oturum ID.
            current_ip: Mevcut IP.

        Returns:
            Kontrol bilgisi.
        """
        try:
            session = self._sessions.get(
                session_id
            )
            if not session:
                return {
                    "checked": False,
                    "error": (
                        "Oturum bulunamadi"
                    ),
                }

            original_ip = session["ip"]
            changed = (
                current_ip != original_ip
            )

            if changed:
                aid = f"sh_{uuid4()!s:.8}"
                alert = {
                    "alert_id": aid,
                    "type": "ip_change",
                    "session_id": session_id,
                    "original_ip": original_ip,
                    "current_ip": current_ip,
                    "severity": "high",
                    "timestamp": datetime.now(
                        timezone.utc
                    ).isoformat(),
                }
                self._alerts.append(alert)
                self._stats[
                    "hijack_alerts"
                ] += 1

            return {
                "session_id": session_id,
                "ip_changed": changed,
                "original_ip": original_ip,
                "current_ip": current_ip,
                "checked": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "checked": False,
                "error": str(e),
            }

    def check_fingerprint(
        self,
        session_id: str = "",
        current_fingerprint: str = "",
    ) -> dict[str, Any]:
        """Parmak izi kontrol eder.

        Args:
            session_id: Oturum ID.
            current_fingerprint: Mevcut parmak izi.

        Returns:
            Kontrol bilgisi.
        """
        try:
            session = self._sessions.get(
                session_id
            )
            if not session:
                return {
                    "checked": False,
                    "error": (
                        "Oturum bulunamadi"
                    ),
                }

            original = session["fingerprint"]
            changed = (
                current_fingerprint
                != original
            )

            if changed:
                aid = f"sh_{uuid4()!s:.8}"
                alert = {
                    "alert_id": aid,
                    "type": (
                        "fingerprint_change"
                    ),
                    "session_id": session_id,
                    "severity": "critical",
                    "timestamp": datetime.now(
                        timezone.utc
                    ).isoformat(),
                }
                self._alerts.append(alert)
                self._stats[
                    "hijack_alerts"
                ] += 1

            return {
                "session_id": session_id,
                "fingerprint_changed": (
                    changed
                ),
                "checked": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "checked": False,
                "error": str(e),
            }

    def check_concurrent_sessions(
        self,
        user_id: str = "",
    ) -> dict[str, Any]:
        """Esanli oturumlari kontrol eder.

        Args:
            user_id: Kullanici ID.

        Returns:
            Kontrol bilgisi.
        """
        try:
            active = [
                sid
                for sid, s in (
                    self._sessions.items()
                )
                if s["user_id"] == user_id
                and s["active"]
            ]
            exceeded = (
                len(active)
                > self._max_concurrent
            )

            return {
                "user_id": user_id,
                "active_sessions": len(
                    active
                ),
                "max_allowed": (
                    self._max_concurrent
                ),
                "exceeded": exceeded,
                "session_ids": active,
                "checked": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "checked": False,
                "error": str(e),
            }

    def force_logout(
        self,
        session_id: str = "",
        reason: str = "",
    ) -> dict[str, Any]:
        """Zorunlu cikis yapar.

        Args:
            session_id: Oturum ID.
            reason: Sebep.

        Returns:
            Cikis bilgisi.
        """
        try:
            session = self._sessions.get(
                session_id
            )
            if not session:
                return {
                    "logged_out": False,
                    "error": (
                        "Oturum bulunamadi"
                    ),
                }

            session["active"] = False
            session["logout_reason"] = reason
            session[
                "logged_out_at"
            ] = datetime.now(
                timezone.utc
            ).isoformat()
            self._stats[
                "forced_logouts"
            ] += 1

            return {
                "session_id": session_id,
                "reason": reason,
                "logged_out": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "logged_out": False,
                "error": str(e),
            }

    def force_logout_user(
        self,
        user_id: str = "",
        reason: str = "",
    ) -> dict[str, Any]:
        """Kullanicinin tum oturumlarini kapatir.

        Args:
            user_id: Kullanici ID.
            reason: Sebep.

        Returns:
            Cikis bilgisi.
        """
        try:
            count = 0
            for sid, s in (
                self._sessions.items()
            ):
                if (
                    s["user_id"] == user_id
                    and s["active"]
                ):
                    s["active"] = False
                    s[
                        "logout_reason"
                    ] = reason
                    s[
                        "logged_out_at"
                    ] = datetime.now(
                        timezone.utc
                    ).isoformat()
                    count += 1
                    self._stats[
                        "forced_logouts"
                    ] += 1

            return {
                "user_id": user_id,
                "sessions_closed": count,
                "logged_out": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "logged_out": False,
                "error": str(e),
            }

    def get_summary(
        self,
    ) -> dict[str, Any]:
        """Ozet getirir.

        Returns:
            Ozet bilgisi.
        """
        try:
            active = sum(
                1
                for s in (
                    self._sessions.values()
                )
                if s["active"]
            )

            return {
                "total_sessions": len(
                    self._sessions
                ),
                "active_sessions": active,
                "total_alerts": len(
                    self._alerts
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
