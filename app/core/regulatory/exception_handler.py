"""ATLAS İstisna Yöneticisi modulu.

İstisna talepleri, onay iş akışı,
geçici geçersiz kılma, denetim izi, süre dolumu.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class RegulatoryExceptionHandler:
    """İstisna yöneticisi.

    Kural istisnalarını yönetir.

    Attributes:
        _exceptions: İstisna kayıtları.
        _audit_trail: Denetim izi.
    """

    def __init__(
        self,
        approval_required: bool = True,
    ) -> None:
        """Yöneticiyi başlatır.

        Args:
            approval_required: Onay gerekli mi.
        """
        self._exceptions: dict[
            str, dict[str, Any]
        ] = {}
        self._audit_trail: list[
            dict[str, Any]
        ] = []
        self._approval_required = (
            approval_required
        )
        self._counter = 0
        self._stats = {
            "requested": 0,
            "approved": 0,
            "denied": 0,
        }

        logger.info(
            "RegulatoryExceptionHandler "
            "baslatildi",
        )

    def request_exception(
        self,
        rule_id: str,
        reason: str,
        duration_hours: int = 24,
        requester: str = "system",
    ) -> dict[str, Any]:
        """İstisna talep eder.

        Args:
            rule_id: Kural ID.
            reason: Talep nedeni.
            duration_hours: Süre (saat).
            requester: Talep eden.

        Returns:
            Talep bilgisi.
        """
        self._counter += 1
        eid = f"exc_{self._counter}"

        status = "requested"
        if not self._approval_required:
            status = "approved"
            self._stats["approved"] += 1

        exc = {
            "exception_id": eid,
            "rule_id": rule_id,
            "reason": reason,
            "requester": requester,
            "status": status,
            "duration_hours": duration_hours,
            "requested_at": time.time(),
            "expires_at": (
                time.time()
                + duration_hours * 3600
            ),
        }
        self._exceptions[eid] = exc
        self._stats["requested"] += 1

        self._log_audit(
            eid, "requested", requester,
        )

        return {
            "exception_id": eid,
            "rule_id": rule_id,
            "status": status,
            "auto_approved": (
                not self._approval_required
            ),
        }

    def approve_exception(
        self,
        exception_id: str,
        approver: str = "admin",
    ) -> dict[str, Any]:
        """İstisnayı onaylar.

        Args:
            exception_id: İstisna ID.
            approver: Onaylayan.

        Returns:
            Onay bilgisi.
        """
        exc = self._exceptions.get(
            exception_id,
        )
        if not exc:
            return {
                "error": "exception_not_found",
            }

        if exc["status"] != "requested":
            return {
                "error": "invalid_status",
                "current": exc["status"],
            }

        exc["status"] = "approved"
        exc["approved_by"] = approver
        exc["approved_at"] = time.time()
        self._stats["approved"] += 1

        self._log_audit(
            exception_id, "approved", approver,
        )

        return {
            "exception_id": exception_id,
            "approved": True,
            "approver": approver,
        }

    def deny_exception(
        self,
        exception_id: str,
        reason: str = "",
        denier: str = "admin",
    ) -> dict[str, Any]:
        """İstisnayı reddeder.

        Args:
            exception_id: İstisna ID.
            reason: Red nedeni.
            denier: Reddeden.

        Returns:
            Red bilgisi.
        """
        exc = self._exceptions.get(
            exception_id,
        )
        if not exc:
            return {
                "error": "exception_not_found",
            }

        if exc["status"] != "requested":
            return {
                "error": "invalid_status",
                "current": exc["status"],
            }

        exc["status"] = "denied"
        exc["denial_reason"] = reason
        exc["denied_by"] = denier
        self._stats["denied"] += 1

        self._log_audit(
            exception_id, "denied", denier,
        )

        return {
            "exception_id": exception_id,
            "denied": True,
            "reason": reason,
        }

    def revoke_exception(
        self,
        exception_id: str,
        reason: str = "",
    ) -> dict[str, Any]:
        """İstisnayı iptal eder.

        Args:
            exception_id: İstisna ID.
            reason: İptal nedeni.

        Returns:
            İptal bilgisi.
        """
        exc = self._exceptions.get(
            exception_id,
        )
        if not exc:
            return {
                "error": "exception_not_found",
            }

        exc["status"] = "revoked"
        exc["revoke_reason"] = reason

        self._log_audit(
            exception_id, "revoked", "system",
        )

        return {
            "exception_id": exception_id,
            "revoked": True,
        }

    def check_exception(
        self,
        rule_id: str,
    ) -> dict[str, Any]:
        """Aktif istisna kontrolü yapar.

        Args:
            rule_id: Kural ID.

        Returns:
            İstisna bilgisi.
        """
        now = time.time()
        for exc in self._exceptions.values():
            if (
                exc["rule_id"] == rule_id
                and exc["status"] == "approved"
                and exc["expires_at"] > now
            ):
                return {
                    "rule_id": rule_id,
                    "has_exception": True,
                    "exception_id": exc[
                        "exception_id"
                    ],
                    "expires_at": exc[
                        "expires_at"
                    ],
                }

        return {
            "rule_id": rule_id,
            "has_exception": False,
        }

    def cleanup_expired(self) -> dict[str, Any]:
        """Süresi dolmuş istisnaları temizler.

        Returns:
            Temizlik bilgisi.
        """
        now = time.time()
        expired = 0
        for exc in self._exceptions.values():
            if (
                exc["status"] == "approved"
                and exc["expires_at"] <= now
            ):
                exc["status"] = "expired"
                expired += 1

        return {
            "expired_count": expired,
            "cleaned": True,
        }

    def get_audit_trail(
        self,
        exception_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Denetim izi getirir.

        Args:
            exception_id: İstisna ID filtresi.

        Returns:
            Denetim izi.
        """
        if exception_id:
            return [
                a for a in self._audit_trail
                if a["exception_id"]
                == exception_id
            ]
        return list(self._audit_trail)

    def _log_audit(
        self,
        exception_id: str,
        action: str,
        actor: str,
    ) -> None:
        """Denetim kaydı ekler.

        Args:
            exception_id: İstisna ID.
            action: Aksiyon.
            actor: Aktör.
        """
        self._audit_trail.append({
            "exception_id": exception_id,
            "action": action,
            "actor": actor,
            "timestamp": time.time(),
        })

    @property
    def exception_count(self) -> int:
        """İstisna sayısı."""
        return self._stats["requested"]

    @property
    def approved_count(self) -> int:
        """Onaylı sayısı."""
        return self._stats["approved"]

    @property
    def active_exception_count(self) -> int:
        """Aktif istisna sayısı."""
        now = time.time()
        return sum(
            1
            for e in self._exceptions.values()
            if (
                e["status"] == "approved"
                and e["expires_at"] > now
            )
        )
