"""
Erisim denetcisi modulu.

Erisim loglama, kim neye eristi,
yetkisiz girisimler, ayricalik
kullanimi, raporlama.
"""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class ComplianceAccessAuditor:
    """Erisim denetcisi.

    Attributes:
        _access_logs: Erisim kayitlari.
        _unauthorized: Yetkisiz kayitlar.
        _privilege_usage: Ayricalik kayit.
        _stats: Istatistikler.
    """

    ACCESS_TYPES: list[str] = [
        "read",
        "write",
        "delete",
        "export",
        "share",
        "admin",
    ]

    RESOURCE_TYPES: list[str] = [
        "personal_data",
        "financial_data",
        "health_data",
        "system_config",
        "audit_log",
        "user_account",
    ]

    def __init__(self) -> None:
        """Denetciyi baslatir."""
        self._access_logs: list[
            dict
        ] = []
        self._unauthorized: list[
            dict
        ] = []
        self._privilege_usage: list[
            dict
        ] = []
        self._stats: dict[str, int] = {
            "accesses_logged": 0,
            "unauthorized_attempts": 0,
            "privilege_uses": 0,
            "reports_generated": 0,
        }
        logger.info(
            "ComplianceAccessAuditor "
            "baslatildi"
        )

    @property
    def log_count(self) -> int:
        """Log sayisi."""
        return len(self._access_logs)

    def log_access(
        self,
        user_id: str = "",
        resource_type: str = (
            "personal_data"
        ),
        resource_id: str = "",
        access_type: str = "read",
        is_authorized: bool = True,
        ip_address: str = "",
        reason: str = "",
    ) -> dict[str, Any]:
        """Erisim loglar.

        Args:
            user_id: Kullanici ID.
            resource_type: Kaynak tipi.
            resource_id: Kaynak ID.
            access_type: Erisim tipi.
            is_authorized: Yetkili mi.
            ip_address: IP adresi.
            reason: Sebep.

        Returns:
            Log bilgisi.
        """
        try:
            lid = f"al_{uuid4()!s:.8}"
            log = {
                "log_id": lid,
                "user_id": user_id,
                "resource_type": (
                    resource_type
                ),
                "resource_id": resource_id,
                "access_type": access_type,
                "is_authorized": (
                    is_authorized
                ),
                "ip_address": ip_address,
                "reason": reason,
                "logged_at": datetime.now(
                    timezone.utc
                ).isoformat(),
            }
            self._access_logs.append(log)
            self._stats[
                "accesses_logged"
            ] += 1

            if not is_authorized:
                self._unauthorized.append(
                    log
                )
                self._stats[
                    "unauthorized_attempts"
                ] += 1

            if access_type in (
                "admin",
                "delete",
                "export",
            ):
                self._privilege_usage\
                    .append(log)
                self._stats[
                    "privilege_uses"
                ] += 1

            return {
                "log_id": lid,
                "is_authorized": (
                    is_authorized
                ),
                "logged": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "logged": False,
                "error": str(e),
            }

    def get_user_access(
        self,
        user_id: str = "",
        limit: int = 50,
    ) -> dict[str, Any]:
        """Kullanici erisimlerini getirir.

        Args:
            user_id: Kullanici ID.
            limit: Limit.

        Returns:
            Erisim listesi.
        """
        try:
            logs = [
                l
                for l in self._access_logs
                if l["user_id"] == user_id
            ]
            recent = logs[-limit:]

            return {
                "user_id": user_id,
                "accesses": recent,
                "count": len(recent),
                "total": len(logs),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }

    def get_resource_access(
        self,
        resource_id: str = "",
    ) -> dict[str, Any]:
        """Kaynak erisimlerini getirir.

        Args:
            resource_id: Kaynak ID.

        Returns:
            Erisim listesi.
        """
        try:
            logs = [
                l
                for l in self._access_logs
                if l["resource_id"]
                == resource_id
            ]
            users = list(
                set(
                    l["user_id"]
                    for l in logs
                )
            )

            return {
                "resource_id": resource_id,
                "accesses": logs,
                "unique_users": users,
                "count": len(logs),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }

    def get_unauthorized_attempts(
        self,
    ) -> dict[str, Any]:
        """Yetkisiz girisimleri getirir.

        Returns:
            Yetkisiz girisim listesi.
        """
        try:
            return {
                "attempts": list(
                    self._unauthorized
                ),
                "count": len(
                    self._unauthorized
                ),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }

    def get_privilege_report(
        self,
    ) -> dict[str, Any]:
        """Ayricalik raporu getirir.

        Returns:
            Ayricalik raporu.
        """
        try:
            by_type: dict[str, int] = {}
            for p in self._privilege_usage:
                at = p["access_type"]
                by_type[at] = (
                    by_type.get(at, 0) + 1
                )

            by_user: dict[str, int] = {}
            for p in self._privilege_usage:
                uid = p["user_id"]
                by_user[uid] = (
                    by_user.get(uid, 0) + 1
                )

            self._stats[
                "reports_generated"
            ] += 1

            return {
                "total_privilege_uses": len(
                    self._privilege_usage
                ),
                "by_type": by_type,
                "by_user": by_user,
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }

    def get_summary(
        self,
    ) -> dict[str, Any]:
        """Ozet getirir."""
        try:
            return {
                "total_logs": len(
                    self._access_logs
                ),
                "unauthorized": len(
                    self._unauthorized
                ),
                "privilege_uses": len(
                    self._privilege_usage
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
