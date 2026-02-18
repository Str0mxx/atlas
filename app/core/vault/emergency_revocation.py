"""
Acil iptal modulu.

Aninda iptal, kaskad iptal,
bildirim, kurtarma sureci,
denetim loglama.
"""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class EmergencyRevocation:
    """Acil iptal.

    Attributes:
        _revocations: Iptal kayitlari.
        _cascades: Kaskad kayitlari.
        _notifications: Bildirimler.
        _stats: Istatistikler.
    """

    def __init__(self) -> None:
        """Iptali baslatir."""
        self._revocations: list[dict] = []
        self._cascades: list[dict] = []
        self._notifications: list[dict] = []
        self._stats: dict[str, int] = {
            "revocations_done": 0,
            "cascades_triggered": 0,
            "recoveries_done": 0,
        }
        logger.info(
            "EmergencyRevocation baslatildi"
        )

    @property
    def revocation_count(self) -> int:
        """Iptal sayisi."""
        return len(self._revocations)

    def revoke_immediately(
        self,
        target_type: str = "secret",
        target_id: str = "",
        reason: str = "",
        initiated_by: str = "",
        severity: str = "high",
    ) -> dict[str, Any]:
        """Aninda iptal eder.

        Args:
            target_type: Hedef turu.
            target_id: Hedef ID.
            reason: Neden.
            initiated_by: Baslatan.
            severity: Ciddiyet.

        Returns:
            Iptal bilgisi.
        """
        try:
            rid = f"rv_{uuid4()!s:.8}"
            now = datetime.now(
                timezone.utc
            ).isoformat()

            revocation = {
                "revocation_id": rid,
                "target_type": target_type,
                "target_id": target_id,
                "reason": reason,
                "initiated_by": initiated_by,
                "severity": severity,
                "status": "completed",
                "created_at": now,
                "completed_at": now,
                "recovered": False,
            }
            self._revocations.append(
                revocation
            )
            self._stats[
                "revocations_done"
            ] += 1

            self._add_notification(
                rid,
                f"Acil iptal: {target_type}"
                f"/{target_id}",
                severity,
            )

            return {
                "revocation_id": rid,
                "target_type": target_type,
                "target_id": target_id,
                "status": "completed",
                "revoked": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "revoked": False,
                "error": str(e),
            }

    def cascade_revoke(
        self,
        root_target_id: str = "",
        related_ids: list[str]
        | None = None,
        reason: str = "",
        initiated_by: str = "",
    ) -> dict[str, Any]:
        """Kaskad iptal yapar.

        Args:
            root_target_id: Kok hedef.
            related_ids: Iliskili hedefler.
            reason: Neden.
            initiated_by: Baslatan.

        Returns:
            Kaskad bilgisi.
        """
        try:
            cid = f"cs_{uuid4()!s:.8}"
            now = datetime.now(
                timezone.utc
            ).isoformat()
            targets = related_ids or []

            revoked_items = []
            root_rev = (
                self.revoke_immediately(
                    target_id=root_target_id,
                    reason=reason,
                    initiated_by=initiated_by,
                    severity="critical",
                )
            )
            revoked_items.append(root_rev)

            for tid in targets:
                rev = self.revoke_immediately(
                    target_id=tid,
                    reason=(
                        f"Kaskad: {reason}"
                    ),
                    initiated_by=initiated_by,
                    severity="high",
                )
                revoked_items.append(rev)

            cascade = {
                "cascade_id": cid,
                "root_target": root_target_id,
                "total_revoked": len(
                    revoked_items
                ),
                "created_at": now,
            }
            self._cascades.append(cascade)
            self._stats[
                "cascades_triggered"
            ] += 1

            return {
                "cascade_id": cid,
                "root_target": root_target_id,
                "total_revoked": len(
                    revoked_items
                ),
                "cascaded": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "cascaded": False,
                "error": str(e),
            }

    def _add_notification(
        self,
        revocation_id: str,
        message: str,
        severity: str,
    ) -> None:
        """Bildirim ekler."""
        self._notifications.append({
            "notification_id": (
                f"nt_{uuid4()!s:.8}"
            ),
            "revocation_id": revocation_id,
            "message": message,
            "severity": severity,
            "read": False,
            "timestamp": datetime.now(
                timezone.utc
            ).isoformat(),
        })

    def get_notifications(
        self,
        unread_only: bool = False,
    ) -> dict[str, Any]:
        """Bildirimleri getirir.

        Args:
            unread_only: Sadece okunmamis.

        Returns:
            Bildirim bilgisi.
        """
        try:
            notifs = [
                n
                for n in self._notifications
                if not unread_only
                or not n["read"]
            ]

            return {
                "notifications": notifs,
                "count": len(notifs),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }

    def initiate_recovery(
        self,
        revocation_id: str = "",
        recovery_plan: str = "",
        initiated_by: str = "",
    ) -> dict[str, Any]:
        """Kurtarma baslatir.

        Args:
            revocation_id: Iptal ID.
            recovery_plan: Kurtarma plani.
            initiated_by: Baslatan.

        Returns:
            Kurtarma bilgisi.
        """
        try:
            target_rev = None
            for r in self._revocations:
                if (
                    r["revocation_id"]
                    == revocation_id
                ):
                    target_rev = r
                    break

            if not target_rev:
                return {
                    "recovered": False,
                    "error": "Bulunamadi",
                }

            target_rev["recovered"] = True
            target_rev[
                "recovery_plan"
            ] = recovery_plan
            target_rev[
                "recovered_by"
            ] = initiated_by
            target_rev[
                "recovered_at"
            ] = datetime.now(
                timezone.utc
            ).isoformat()

            self._stats[
                "recoveries_done"
            ] += 1

            return {
                "revocation_id": revocation_id,
                "recovery_plan": recovery_plan,
                "recovered": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "recovered": False,
                "error": str(e),
            }

    def get_revocation_log(
        self,
        severity: str = "",
        limit: int = 20,
    ) -> dict[str, Any]:
        """Iptal logunu getirir.

        Args:
            severity: Ciddiyet filtresi.
            limit: Sonuc limiti.

        Returns:
            Log bilgisi.
        """
        try:
            revs = [
                r
                for r in self._revocations
                if not severity
                or r["severity"] == severity
            ]

            recent = revs[-limit:]
            recent.reverse()

            return {
                "revocations": recent,
                "total": len(revs),
                "showing": len(recent),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }
