"""
Cift onay kapisi modulu.

Iki kisi kurali, onay is akisi,
zaman asimi, denetim izi,
gecersiz kilma islemi.
"""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class DualApprovalGate:
    """Cift onay kapisi.

    Attributes:
        _requests: Onay istekleri.
        _approvals: Onay kayitlari.
        _overrides: Gecersiz kilma.
        _audit: Denetim kayitlari.
        _stats: Istatistikler.
    """

    REQUEST_TYPES: list[str] = [
        "payment",
        "refund",
        "transfer",
        "limit_change",
        "config_change",
        "data_export",
        "account_close",
    ]

    STATUSES: list[str] = [
        "pending",
        "approved",
        "rejected",
        "expired",
        "overridden",
    ]

    def __init__(
        self,
        threshold: float = 10000.0,
        timeout_minutes: int = 30,
    ) -> None:
        """Kapiyi baslatir.

        Args:
            threshold: Onay esigi.
            timeout_minutes: Zaman asimi.
        """
        self._threshold = threshold
        self._timeout = timeout_minutes
        self._requests: dict[
            str, dict
        ] = {}
        self._approvals: list[dict] = []
        self._overrides: list[dict] = []
        self._audit: list[dict] = []
        self._stats: dict[str, int] = {
            "requests_created": 0,
            "approvals_given": 0,
            "rejections": 0,
            "expirations": 0,
            "overrides_used": 0,
        }
        logger.info(
            "DualApprovalGate baslatildi"
        )

    @property
    def pending_count(self) -> int:
        """Bekleyen istek sayisi."""
        return sum(
            1
            for r in self._requests.values()
            if r["status"] == "pending"
        )

    def requires_approval(
        self,
        amount: float = 0.0,
        request_type: str = "payment",
    ) -> bool:
        """Onay gerekip gerekmedigi.

        Args:
            amount: Tutar.
            request_type: Istek tipi.

        Returns:
            Onay gerekli mi.
        """
        high_risk = [
            "data_export",
            "account_close",
            "config_change",
        ]
        if request_type in high_risk:
            return True
        return amount >= self._threshold

    def create_request(
        self,
        request_type: str = "payment",
        amount: float = 0.0,
        requester_id: str = "",
        description: str = "",
        metadata: dict | None = None,
    ) -> dict[str, Any]:
        """Onay istegi olusturur.

        Args:
            request_type: Istek tipi.
            amount: Tutar.
            requester_id: Isteyen.
            description: Aciklama.
            metadata: Ek veri.

        Returns:
            Istek bilgisi.
        """
        try:
            if (
                request_type
                not in self.REQUEST_TYPES
            ):
                return {
                    "created": False,
                    "error": (
                        f"Gecersiz tip: "
                        f"{request_type}"
                    ),
                }

            rid = f"req_{uuid4()!s:.8}"
            self._requests[rid] = {
                "request_id": rid,
                "request_type": request_type,
                "amount": amount,
                "requester_id": requester_id,
                "description": description,
                "metadata": metadata or {},
                "status": "pending",
                "approvals": [],
                "rejections": [],
                "required_approvals": 2,
                "created_at": datetime.now(
                    timezone.utc
                ).isoformat(),
            }
            self._stats[
                "requests_created"
            ] += 1

            self._log_audit(
                rid,
                "request_created",
                f"{requester_id} "
                f"tarafindan "
                f"olusturuldu",
            )

            return {
                "request_id": rid,
                "status": "pending",
                "required_approvals": 2,
                "created": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "created": False,
                "error": str(e),
            }

    def approve(
        self,
        request_id: str = "",
        approver_id: str = "",
        comment: str = "",
    ) -> dict[str, Any]:
        """Istegi onaylar.

        Args:
            request_id: Istek ID.
            approver_id: Onaylayan.
            comment: Yorum.

        Returns:
            Onay bilgisi.
        """
        try:
            req = self._requests.get(
                request_id
            )
            if not req:
                return {
                    "approved": False,
                    "error": (
                        "Istek bulunamadi"
                    ),
                }

            if req["status"] != "pending":
                return {
                    "approved": False,
                    "error": (
                        f"Istek durumu: "
                        f"{req['status']}"
                    ),
                }

            # Isteyen onaylayamaz
            if (
                approver_id
                == req["requester_id"]
            ):
                return {
                    "approved": False,
                    "error": (
                        "Isteyen onaylayamaz"
                    ),
                }

            # Ayni kisi tekrar
            existing = [
                a["approver_id"]
                for a in req["approvals"]
            ]
            if approver_id in existing:
                return {
                    "approved": False,
                    "error": (
                        "Zaten onaylamis"
                    ),
                }

            approval = {
                "approver_id": approver_id,
                "comment": comment,
                "approved_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
            }
            req["approvals"].append(approval)
            self._approvals.append({
                "request_id": request_id,
                **approval,
            })
            self._stats[
                "approvals_given"
            ] += 1

            # Yeterli onay
            fully = (
                len(req["approvals"])
                >= req["required_approvals"]
            )
            if fully:
                req["status"] = "approved"

            self._log_audit(
                request_id,
                "approved",
                f"{approver_id} onayladi",
            )

            return {
                "request_id": request_id,
                "approver_id": approver_id,
                "fully_approved": fully,
                "current_approvals": len(
                    req["approvals"]
                ),
                "approved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "approved": False,
                "error": str(e),
            }

    def reject(
        self,
        request_id: str = "",
        rejector_id: str = "",
        reason: str = "",
    ) -> dict[str, Any]:
        """Istegi reddeder.

        Args:
            request_id: Istek ID.
            rejector_id: Reddeden.
            reason: Neden.

        Returns:
            Red bilgisi.
        """
        try:
            req = self._requests.get(
                request_id
            )
            if not req:
                return {
                    "rejected": False,
                    "error": (
                        "Istek bulunamadi"
                    ),
                }

            if req["status"] != "pending":
                return {
                    "rejected": False,
                    "error": (
                        f"Istek durumu: "
                        f"{req['status']}"
                    ),
                }

            req["status"] = "rejected"
            req["rejections"].append({
                "rejector_id": rejector_id,
                "reason": reason,
                "rejected_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
            })
            self._stats["rejections"] += 1

            self._log_audit(
                request_id,
                "rejected",
                f"{rejector_id} reddetti: "
                f"{reason}",
            )

            return {
                "request_id": request_id,
                "rejector_id": rejector_id,
                "rejected": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "rejected": False,
                "error": str(e),
            }

    def override(
        self,
        request_id: str = "",
        overrider_id: str = "",
        reason: str = "",
        authority_level: str = "admin",
    ) -> dict[str, Any]:
        """Istegi gecersiz kilar.

        Args:
            request_id: Istek ID.
            overrider_id: Gecersiz kilan.
            reason: Neden.
            authority_level: Yetki.

        Returns:
            Override bilgisi.
        """
        try:
            req = self._requests.get(
                request_id
            )
            if not req:
                return {
                    "overridden": False,
                    "error": (
                        "Istek bulunamadi"
                    ),
                }

            if authority_level not in (
                "admin", "super_admin",
            ):
                return {
                    "overridden": False,
                    "error": (
                        "Yetersiz yetki"
                    ),
                }

            req["status"] = "overridden"
            oid = f"ov_{uuid4()!s:.8}"
            self._overrides.append({
                "override_id": oid,
                "request_id": request_id,
                "overrider_id": overrider_id,
                "reason": reason,
                "authority": authority_level,
                "created_at": datetime.now(
                    timezone.utc
                ).isoformat(),
            })
            self._stats[
                "overrides_used"
            ] += 1

            self._log_audit(
                request_id,
                "overridden",
                f"{overrider_id} "
                f"gecersiz kildi: {reason}",
            )

            return {
                "override_id": oid,
                "request_id": request_id,
                "overridden": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "overridden": False,
                "error": str(e),
            }

    def expire_pending(
        self,
    ) -> dict[str, Any]:
        """Suresi dolmuslari isaretle."""
        try:
            expired = 0
            for req in (
                self._requests.values()
            ):
                if (
                    req["status"] == "pending"
                ):
                    req["status"] = "expired"
                    expired += 1
                    self._stats[
                        "expirations"
                    ] += 1

            return {
                "expired_count": expired,
                "processed": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "processed": False,
                "error": str(e),
            }

    def _log_audit(
        self,
        request_id: str,
        action: str,
        detail: str,
    ) -> None:
        """Denetim kaydi ekler."""
        self._audit.append({
            "request_id": request_id,
            "action": action,
            "detail": detail,
            "timestamp": datetime.now(
                timezone.utc
            ).isoformat(),
        })

    def get_request(
        self,
        request_id: str = "",
    ) -> dict[str, Any]:
        """Istek bilgisi getirir."""
        try:
            req = self._requests.get(
                request_id
            )
            if not req:
                return {
                    "found": False,
                    "error": (
                        "Istek bulunamadi"
                    ),
                }
            return {
                **req,
                "found": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "found": False,
                "error": str(e),
            }

    def get_summary(
        self,
    ) -> dict[str, Any]:
        """Ozet getirir."""
        try:
            return {
                "total_requests": len(
                    self._requests
                ),
                "pending": self.pending_count,
                "total_approvals": len(
                    self._approvals
                ),
                "total_overrides": len(
                    self._overrides
                ),
                "threshold": (
                    self._threshold
                ),
                "timeout_minutes": (
                    self._timeout
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
