"""
Aninda iptal edici modulu.

Aninda iptal, basamakli islem,
servis bildirimi, yedek uretim,
denetim gunlugu.
"""

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class InstantRevocator:
    """Aninda iptal edici.

    Attributes:
        _revocations: Iptal kayitlari.
        _cascades: Basamak kayitlari.
        _replacements: Yedek kayitlari.
        _notifications: Bildirimler.
        _audit_log: Denetim gunlugu.
        _stats: Istatistikler.
    """

    REVOCATION_REASONS: list[str] = [
        "leaked",
        "compromised",
        "expired",
        "over_permissioned",
        "unused",
        "policy_violation",
        "manual",
        "rotation",
    ]

    def __init__(self) -> None:
        """Iptal ediciyi baslatir."""
        self._revocations: dict[
            str, dict
        ] = {}
        self._cascades: list[dict] = []
        self._replacements: dict[
            str, dict
        ] = {}
        self._notifications: list[
            dict
        ] = []
        self._audit_log: list[dict] = []
        self._stats: dict[str, int] = {
            "revocations": 0,
            "cascades_handled": 0,
            "replacements_generated": 0,
            "notifications_sent": 0,
            "audit_entries": 0,
        }
        logger.info(
            "InstantRevocator baslatildi"
        )

    @property
    def revocation_count(self) -> int:
        """Iptal sayisi."""
        return len(self._revocations)

    def revoke_key(
        self,
        key_id: str = "",
        reason: str = "manual",
        revoked_by: str = "system",
        cascade: bool = False,
        generate_replacement: bool = False,
        notify_services: (
            list[str] | None
        ) = None,
    ) -> dict[str, Any]:
        """Anahtari iptal eder.

        Args:
            key_id: Anahtar ID.
            reason: Iptal nedeni.
            revoked_by: Iptal eden.
            cascade: Basamakli iptal.
            generate_replacement: Yedek.
            notify_services: Bildirim.

        Returns:
            Iptal bilgisi.
        """
        try:
            if (
                reason
                not in self.REVOCATION_REASONS
            ):
                return {
                    "revoked": False,
                    "error": (
                        f"Gecersiz neden: "
                        f"{reason}"
                    ),
                }

            rid = f"rv_{uuid4()!s:.8}"
            now = datetime.now(
                timezone.utc
            ).isoformat()

            self._revocations[key_id] = {
                "revocation_id": rid,
                "key_id": key_id,
                "reason": reason,
                "revoked_by": revoked_by,
                "status": "revoked",
                "revoked_at": now,
                "cascade": cascade,
                "replacement_id": None,
            }
            self._stats["revocations"] += 1

            # Denetim
            self._log_audit(
                key_id=key_id,
                action="revoke",
                detail=(
                    f"Iptal: {reason} "
                    f"({revoked_by})"
                ),
            )

            # Basamakli iptal
            cascade_result = None
            if cascade:
                cascade_result = (
                    self._handle_cascade(
                        key_id, reason
                    )
                )

            # Yedek uretim
            replacement = None
            if generate_replacement:
                replacement = (
                    self._generate_replacement(
                        key_id
                    )
                )
                self._revocations[key_id][
                    "replacement_id"
                ] = replacement.get(
                    "replacement_id"
                )

            # Bildirim
            notif_results = []
            services = (
                notify_services or []
            )
            for svc in services:
                nr = self._notify_service(
                    key_id, svc, reason
                )
                notif_results.append(nr)

            return {
                "revocation_id": rid,
                "key_id": key_id,
                "reason": reason,
                "cascade_result": (
                    cascade_result
                ),
                "replacement": replacement,
                "notifications": len(
                    notif_results
                ),
                "revoked": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "revoked": False,
                "error": str(e),
            }

    def _handle_cascade(
        self,
        key_id: str,
        reason: str,
    ) -> dict[str, Any]:
        """Basamakli iptali isler."""
        cid = f"cs_{uuid4()!s:.8}"
        cascade = {
            "cascade_id": cid,
            "parent_key_id": key_id,
            "reason": reason,
            "affected_keys": [],
            "processed_at": datetime.now(
                timezone.utc
            ).isoformat(),
        }
        self._cascades.append(cascade)
        self._stats[
            "cascades_handled"
        ] += 1

        self._log_audit(
            key_id=key_id,
            action="cascade",
            detail="Basamakli iptal islendi",
        )

        return {
            "cascade_id": cid,
            "affected": 0,
            "processed": True,
        }

    def _generate_replacement(
        self,
        key_id: str,
    ) -> dict[str, Any]:
        """Yedek anahtar uretir."""
        rpid = f"rp_{uuid4()!s:.8}"
        new_value = hashlib.sha256(
            f"{key_id}{uuid4()}".encode()
        ).hexdigest()[:32]

        self._replacements[key_id] = {
            "replacement_id": rpid,
            "original_key_id": key_id,
            "new_key_prefix": (
                new_value[:8]
            ),
            "status": "generated",
            "generated_at": datetime.now(
                timezone.utc
            ).isoformat(),
        }
        self._stats[
            "replacements_generated"
        ] += 1

        self._log_audit(
            key_id=key_id,
            action="replacement",
            detail=f"Yedek: {rpid}",
        )

        return {
            "replacement_id": rpid,
            "new_key_prefix": (
                new_value[:8]
            ),
            "generated": True,
        }

    def _notify_service(
        self,
        key_id: str,
        service: str,
        reason: str,
    ) -> dict[str, Any]:
        """Servise bildirim gonderir."""
        nid = f"nt_{uuid4()!s:.8}"
        self._notifications.append({
            "notification_id": nid,
            "key_id": key_id,
            "service": service,
            "reason": reason,
            "status": "sent",
            "sent_at": datetime.now(
                timezone.utc
            ).isoformat(),
        })
        self._stats[
            "notifications_sent"
        ] += 1

        return {
            "notification_id": nid,
            "service": service,
            "sent": True,
        }

    def _log_audit(
        self,
        key_id: str = "",
        action: str = "",
        detail: str = "",
    ) -> None:
        """Denetim kaydeder."""
        self._audit_log.append({
            "audit_id": (
                f"au_{uuid4()!s:.8}"
            ),
            "key_id": key_id,
            "action": action,
            "detail": detail,
            "timestamp": datetime.now(
                timezone.utc
            ).isoformat(),
        })
        self._stats[
            "audit_entries"
        ] += 1

    def bulk_revoke(
        self,
        key_ids: list[str] | None = None,
        reason: str = "manual",
        revoked_by: str = "system",
    ) -> dict[str, Any]:
        """Toplu iptal yapar.

        Args:
            key_ids: Anahtar IDleri.
            reason: Neden.
            revoked_by: Iptal eden.

        Returns:
            Toplu iptal bilgisi.
        """
        try:
            kids = key_ids or []
            results: list[dict] = []
            for kid in kids:
                r = self.revoke_key(
                    key_id=kid,
                    reason=reason,
                    revoked_by=revoked_by,
                )
                results.append(r)

            success = sum(
                1
                for r in results
                if r.get("revoked")
            )

            return {
                "total": len(kids),
                "revoked": success,
                "failed": (
                    len(kids) - success
                ),
                "completed": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "completed": False,
                "error": str(e),
            }

    def get_revocation(
        self,
        key_id: str = "",
    ) -> dict[str, Any]:
        """Iptal bilgisi getirir.

        Args:
            key_id: Anahtar ID.

        Returns:
            Iptal bilgisi.
        """
        try:
            rev = self._revocations.get(
                key_id
            )
            if not rev:
                return {
                    "found": False,
                    "error": (
                        "Iptal bulunamadi"
                    ),
                }

            return {
                **rev,
                "found": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "found": False,
                "error": str(e),
            }

    def get_audit_log(
        self,
        key_id: str = "",
    ) -> dict[str, Any]:
        """Denetim gunlugunu getirir.

        Args:
            key_id: Anahtar ID filtre.

        Returns:
            Gunluk listesi.
        """
        try:
            if key_id:
                logs = [
                    l
                    for l in self._audit_log
                    if l["key_id"] == key_id
                ]
            else:
                logs = list(
                    self._audit_log
                )

            return {
                "logs": logs,
                "count": len(logs),
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
            by_reason: dict[
                str, int
            ] = {}
            for rev in (
                self._revocations.values()
            ):
                r = rev["reason"]
                by_reason[r] = (
                    by_reason.get(r, 0) + 1
                )

            return {
                "total_revocations": len(
                    self._revocations
                ),
                "total_cascades": len(
                    self._cascades
                ),
                "total_replacements": len(
                    self._replacements
                ),
                "by_reason": by_reason,
                "stats": dict(self._stats),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }
