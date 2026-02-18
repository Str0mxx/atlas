"""
Kaba kuvvet tespitcisi modulu.

Giris denemesi takibi, esik tespiti,
IP engelleme, hesap kilitleme,
uyari uretimi.
"""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class BruteForceDetector:
    """Kaba kuvvet tespitcisi.

    Attributes:
        _attempts: Deneme kayitlari.
        _blocked_ips: Engelli IP'ler.
        _locked_accounts: Kilitli hesaplar.
        _alerts: Uyari kayitlari.
        _stats: Istatistikler.
    """

    DEFAULT_THRESHOLDS: dict[str, int] = {
        "max_attempts": 5,
        "window_seconds": 300,
        "lockout_minutes": 30,
        "block_minutes": 60,
    }

    def __init__(
        self,
        max_attempts: int = 5,
        lockout_minutes: int = 30,
    ) -> None:
        """Tespitciyi baslatir.

        Args:
            max_attempts: Maks deneme.
            lockout_minutes: Kilit suresi.
        """
        self._attempts: dict[
            str, list[dict]
        ] = {}
        self._blocked_ips: dict[
            str, dict
        ] = {}
        self._locked_accounts: dict[
            str, dict
        ] = {}
        self._alerts: list[dict] = []
        self._max_attempts = max_attempts
        self._lockout_minutes = lockout_minutes
        self._stats: dict[str, int] = {
            "attempts_tracked": 0,
            "ips_blocked": 0,
            "accounts_locked": 0,
            "alerts_generated": 0,
        }
        logger.info(
            "BruteForceDetector baslatildi"
        )

    @property
    def alert_count(self) -> int:
        """Uyari sayisi."""
        return len(self._alerts)

    def record_attempt(
        self,
        ip: str = "",
        username: str = "",
        success: bool = False,
        service: str = "login",
    ) -> dict[str, Any]:
        """Deneme kaydeder.

        Args:
            ip: IP adresi.
            username: Kullanici adi.
            success: Basarili mi.
            service: Servis adi.

        Returns:
            Kayit bilgisi.
        """
        try:
            key = f"{ip}:{username}"
            if key not in self._attempts:
                self._attempts[key] = []

            attempt = {
                "ip": ip,
                "username": username,
                "success": success,
                "service": service,
                "timestamp": datetime.now(
                    timezone.utc
                ).isoformat(),
            }
            self._attempts[key].append(
                attempt
            )
            self._stats[
                "attempts_tracked"
            ] += 1

            failed = [
                a
                for a in self._attempts[key]
                if not a["success"]
            ]
            threshold_exceeded = (
                len(failed)
                >= self._max_attempts
            )

            alert_id = None
            if (
                threshold_exceeded
                and not success
            ):
                alert_id = self._generate_alert(
                    ip=ip,
                    username=username,
                    attempt_count=len(failed),
                    service=service,
                )

            return {
                "ip": ip,
                "username": username,
                "failed_count": len(failed),
                "threshold_exceeded": (
                    threshold_exceeded
                ),
                "alert_id": alert_id,
                "recorded": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "recorded": False,
                "error": str(e),
            }

    def _generate_alert(
        self,
        ip: str,
        username: str,
        attempt_count: int,
        service: str,
    ) -> str:
        """Uyari uretir."""
        aid = f"ba_{uuid4()!s:.8}"
        alert = {
            "alert_id": aid,
            "type": "brute_force",
            "ip": ip,
            "username": username,
            "attempt_count": attempt_count,
            "service": service,
            "severity": (
                "critical"
                if attempt_count >= 10
                else "high"
            ),
            "timestamp": datetime.now(
                timezone.utc
            ).isoformat(),
        }
        self._alerts.append(alert)
        self._stats[
            "alerts_generated"
        ] += 1
        return aid

    def check_threshold(
        self,
        ip: str = "",
        username: str = "",
    ) -> dict[str, Any]:
        """Esik kontrol eder.

        Args:
            ip: IP adresi.
            username: Kullanici adi.

        Returns:
            Kontrol bilgisi.
        """
        try:
            key = f"{ip}:{username}"
            attempts = self._attempts.get(
                key, []
            )
            failed = [
                a
                for a in attempts
                if not a["success"]
            ]
            exceeded = (
                len(failed)
                >= self._max_attempts
            )

            return {
                "ip": ip,
                "username": username,
                "failed_attempts": len(
                    failed
                ),
                "max_attempts": (
                    self._max_attempts
                ),
                "exceeded": exceeded,
                "checked": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "checked": False,
                "error": str(e),
            }

    def block_ip(
        self,
        ip: str = "",
        reason: str = "",
        duration_minutes: int = 60,
    ) -> dict[str, Any]:
        """IP engeller.

        Args:
            ip: IP adresi.
            reason: Sebep.
            duration_minutes: Sure (dakika).

        Returns:
            Engelleme bilgisi.
        """
        try:
            self._blocked_ips[ip] = {
                "reason": reason,
                "duration": duration_minutes,
                "blocked_at": datetime.now(
                    timezone.utc
                ).isoformat(),
            }
            self._stats["ips_blocked"] += 1

            return {
                "ip": ip,
                "duration": duration_minutes,
                "blocked": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "blocked": False,
                "error": str(e),
            }

    def unblock_ip(
        self,
        ip: str = "",
    ) -> dict[str, Any]:
        """IP engelini kaldirir.

        Args:
            ip: IP adresi.

        Returns:
            Kaldirma bilgisi.
        """
        try:
            if ip in self._blocked_ips:
                del self._blocked_ips[ip]
                return {
                    "ip": ip,
                    "unblocked": True,
                }
            return {
                "unblocked": False,
                "error": "IP engelli degil",
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "unblocked": False,
                "error": str(e),
            }

    def is_blocked(
        self,
        ip: str = "",
    ) -> bool:
        """IP engelli mi kontrol eder."""
        return ip in self._blocked_ips

    def lock_account(
        self,
        username: str = "",
        reason: str = "",
    ) -> dict[str, Any]:
        """Hesap kilitler.

        Args:
            username: Kullanici adi.
            reason: Sebep.

        Returns:
            Kilitleme bilgisi.
        """
        try:
            self._locked_accounts[username] = {
                "reason": reason,
                "locked_at": datetime.now(
                    timezone.utc
                ).isoformat(),
            }
            self._stats[
                "accounts_locked"
            ] += 1

            return {
                "username": username,
                "locked": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "locked": False,
                "error": str(e),
            }

    def unlock_account(
        self,
        username: str = "",
    ) -> dict[str, Any]:
        """Hesap kilidini acar.

        Args:
            username: Kullanici adi.

        Returns:
            Acma bilgisi.
        """
        try:
            if (
                username
                in self._locked_accounts
            ):
                del self._locked_accounts[
                    username
                ]
                return {
                    "username": username,
                    "unlocked": True,
                }
            return {
                "unlocked": False,
                "error": "Hesap kilitli degil",
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "unlocked": False,
                "error": str(e),
            }

    def is_locked(
        self,
        username: str = "",
    ) -> bool:
        """Hesap kilitli mi kontrol eder."""
        return (
            username in self._locked_accounts
        )

    def get_summary(
        self,
    ) -> dict[str, Any]:
        """Ozet getirir.

        Returns:
            Ozet bilgisi.
        """
        try:
            return {
                "blocked_ips": len(
                    self._blocked_ips
                ),
                "locked_accounts": len(
                    self._locked_accounts
                ),
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
