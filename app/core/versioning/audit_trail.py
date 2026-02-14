"""ATLAS Surum Denetim Izi modulu.

Kim ne degistirdi, ne zaman,
neden degistirdi, onay takibi
ve uyumluluk.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class VersionAuditTrail:
    """Surum denetim izi.

    Tum surumleme islemlerinin
    tam denetim izini tutar.

    Attributes:
        _entries: Denetim kayitlari.
        _approvals: Onay kayitlari.
    """

    def __init__(self) -> None:
        """Denetim izi baslatir."""
        self._entries: list[
            dict[str, Any]
        ] = []
        self._approvals: dict[
            str, dict[str, Any]
        ] = {}
        self._compliance_rules: dict[
            str, dict[str, Any]
        ] = {}

        logger.info(
            "VersionAuditTrail baslatildi",
        )

    def log_action(
        self,
        action: str,
        actor: str,
        resource: str,
        details: dict[str, Any] | None = None,
        reason: str = "",
    ) -> dict[str, Any]:
        """Aksiyonu loglar.

        Args:
            action: Aksiyon adi.
            actor: Yapan kisi.
            resource: Kaynak.
            details: Detaylar.
            reason: Sebep.

        Returns:
            Log kaydi.
        """
        entry = {
            "action": action,
            "actor": actor,
            "resource": resource,
            "details": details or {},
            "reason": reason,
            "at": time.time(),
        }
        self._entries.append(entry)
        return entry

    def request_approval(
        self,
        request_id: str,
        action: str,
        requester: str,
        resource: str,
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Onay ister.

        Args:
            request_id: Istek ID.
            action: Aksiyon.
            requester: Talep eden.
            resource: Kaynak.
            details: Detaylar.

        Returns:
            Onay istegi.
        """
        approval = {
            "request_id": request_id,
            "action": action,
            "requester": requester,
            "resource": resource,
            "details": details or {},
            "status": "pending",
            "at": time.time(),
        }
        self._approvals[request_id] = approval
        return approval

    def approve(
        self,
        request_id: str,
        approver: str,
        notes: str = "",
    ) -> dict[str, Any]:
        """Onaylar.

        Args:
            request_id: Istek ID.
            approver: Onaylayan.
            notes: Notlar.

        Returns:
            Onay sonucu.
        """
        approval = self._approvals.get(
            request_id,
        )
        if not approval:
            return {
                "success": False,
                "reason": "request_not_found",
            }

        approval["status"] = "approved"
        approval["approver"] = approver
        approval["notes"] = notes
        approval["approved_at"] = time.time()

        self.log_action(
            "approval_granted",
            approver,
            approval["resource"],
            {"request_id": request_id},
        )

        return {
            "success": True,
            "request_id": request_id,
            "approver": approver,
        }

    def reject(
        self,
        request_id: str,
        rejector: str,
        reason: str = "",
    ) -> dict[str, Any]:
        """Reddeder.

        Args:
            request_id: Istek ID.
            rejector: Reddeden.
            reason: Sebep.

        Returns:
            Ret sonucu.
        """
        approval = self._approvals.get(
            request_id,
        )
        if not approval:
            return {
                "success": False,
                "reason": "request_not_found",
            }

        approval["status"] = "rejected"
        approval["rejector"] = rejector
        approval["reject_reason"] = reason
        approval["rejected_at"] = time.time()

        self.log_action(
            "approval_rejected",
            rejector,
            approval["resource"],
            {
                "request_id": request_id,
                "reason": reason,
            },
        )

        return {
            "success": True,
            "request_id": request_id,
            "rejector": rejector,
        }

    def add_compliance_rule(
        self,
        rule_name: str,
        description: str,
        check_fn_name: str = "",
    ) -> dict[str, Any]:
        """Uyumluluk kurali ekler.

        Args:
            rule_name: Kural adi.
            description: Aciklama.
            check_fn_name: Kontrol fonksiyonu.

        Returns:
            Kural bilgisi.
        """
        rule = {
            "name": rule_name,
            "description": description,
            "check": check_fn_name,
            "active": True,
        }
        self._compliance_rules[rule_name] = rule
        return rule

    def check_compliance(
        self,
        resource: str,
    ) -> dict[str, Any]:
        """Uyumluluk kontrolu yapar.

        Args:
            resource: Kaynak.

        Returns:
            Kontrol sonucu.
        """
        entries = [
            e for e in self._entries
            if e["resource"] == resource
        ]
        rules = list(
            self._compliance_rules.values(),
        )

        # Temel kontroller
        has_author = any(
            e.get("actor") for e in entries
        )
        has_reason = any(
            e.get("reason") for e in entries
        )

        return {
            "resource": resource,
            "total_entries": len(entries),
            "active_rules": len(rules),
            "has_author": has_author,
            "has_reason": has_reason,
            "compliant": has_author,
        }

    def get_entries(
        self,
        actor: str | None = None,
        resource: str | None = None,
        action: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Denetim kayitlari getirir.

        Args:
            actor: Yapan filtresi.
            resource: Kaynak filtresi.
            action: Aksiyon filtresi.
            limit: Limit.

        Returns:
            Denetim kayitlari.
        """
        entries = self._entries
        if actor:
            entries = [
                e for e in entries
                if e["actor"] == actor
            ]
        if resource:
            entries = [
                e for e in entries
                if e["resource"] == resource
            ]
        if action:
            entries = [
                e for e in entries
                if e["action"] == action
            ]
        return entries[-limit:]

    def get_approval(
        self,
        request_id: str,
    ) -> dict[str, Any] | None:
        """Onay getirir.

        Args:
            request_id: Istek ID.

        Returns:
            Onay veya None.
        """
        return self._approvals.get(request_id)

    def get_pending_approvals(
        self,
    ) -> list[dict[str, Any]]:
        """Bekleyen onaylari getirir.

        Returns:
            Bekleyen onaylar.
        """
        return [
            a for a in self._approvals.values()
            if a["status"] == "pending"
        ]

    @property
    def entry_count(self) -> int:
        """Kayit sayisi."""
        return len(self._entries)

    @property
    def approval_count(self) -> int:
        """Onay sayisi."""
        return len(self._approvals)

    @property
    def pending_count(self) -> int:
        """Bekleyen onay sayisi."""
        return sum(
            1 for a in self._approvals.values()
            if a["status"] == "pending"
        )

    @property
    def rule_count(self) -> int:
        """Kural sayisi."""
        return len(self._compliance_rules)
