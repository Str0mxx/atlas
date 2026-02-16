"""ATLAS Doküman Erişim Kontrolcüsü modülü.

İzin yönetimi, paylaşım kontrolü,
denetim günlüğü, şifreleme,
filigran ekleme.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class DocAccessController:
    """Doküman erişim kontrolcüsü.

    Doküman erişimlerini kontrol eder.

    Attributes:
        _permissions: İzin kayıtları.
        _audit_log: Denetim günlüğü.
    """

    def __init__(self) -> None:
        """Kontrolcüyü başlatır."""
        self._permissions: dict[
            str, dict[str, Any]
        ] = {}
        self._shares: dict[
            str, list[dict[str, Any]]
        ] = {}
        self._audit_log: list[
            dict[str, Any]
        ] = []
        self._encrypted: set[str] = set()
        self._watermarked: set[str] = set()
        self._counter = 0
        self._stats = {
            "permissions_set": 0,
            "access_checks": 0,
        }

        logger.info(
            "DocAccessController "
            "baslatildi",
        )

    def set_permission(
        self,
        doc_id: str,
        user: str = "",
        level: str = "internal",
        can_read: bool = True,
        can_write: bool = False,
        can_share: bool = False,
    ) -> dict[str, Any]:
        """İzin ayarlar.

        Args:
            doc_id: Doküman kimliği.
            user: Kullanıcı.
            level: Erişim seviyesi.
            can_read: Okuma izni.
            can_write: Yazma izni.
            can_share: Paylaşma izni.

        Returns:
            İzin bilgisi.
        """
        key = f"{doc_id}:{user}"

        self._permissions[key] = {
            "doc_id": doc_id,
            "user": user,
            "level": level,
            "can_read": can_read,
            "can_write": can_write,
            "can_share": can_share,
            "timestamp": time.time(),
        }
        self._stats[
            "permissions_set"
        ] += 1

        self._log_audit(
            doc_id, user,
            "permission_set",
        )

        return {
            "doc_id": doc_id,
            "user": user,
            "level": level,
            "set": True,
        }

    def check_access(
        self,
        doc_id: str,
        user: str = "",
        action: str = "read",
    ) -> dict[str, Any]:
        """Erişim kontrol eder.

        Args:
            doc_id: Doküman kimliği.
            user: Kullanıcı.
            action: Eylem.

        Returns:
            Kontrol bilgisi.
        """
        self._stats["access_checks"] += 1
        key = f"{doc_id}:{user}"

        perm = self._permissions.get(key)
        if not perm:
            self._log_audit(
                doc_id, user,
                f"access_denied:{action}",
            )
            return {
                "doc_id": doc_id,
                "user": user,
                "action": action,
                "allowed": False,
                "reason": "no_permission",
            }

        allowed = False
        if action == "read":
            allowed = perm["can_read"]
        elif action == "write":
            allowed = perm["can_write"]
        elif action == "share":
            allowed = perm["can_share"]

        self._log_audit(
            doc_id, user,
            f"access_{'granted' if allowed else 'denied'}:{action}",
        )

        return {
            "doc_id": doc_id,
            "user": user,
            "action": action,
            "allowed": allowed,
        }

    def share_document(
        self,
        doc_id: str,
        owner: str = "",
        recipient: str = "",
        level: str = "internal",
    ) -> dict[str, Any]:
        """Doküman paylaşır.

        Args:
            doc_id: Doküman kimliği.
            owner: Sahip.
            recipient: Alıcı.
            level: Erişim seviyesi.

        Returns:
            Paylaşım bilgisi.
        """
        # Sahip paylaşabilir mi?
        owner_key = f"{doc_id}:{owner}"
        owner_perm = self._permissions.get(
            owner_key,
        )
        if owner_perm and not (
            owner_perm["can_share"]
        ):
            return {
                "doc_id": doc_id,
                "shared": False,
                "reason": (
                    "no_share_permission"
                ),
            }

        # Alıcıya okuma izni ver
        self.set_permission(
            doc_id=doc_id,
            user=recipient,
            level=level,
            can_read=True,
        )

        if doc_id not in self._shares:
            self._shares[doc_id] = []

        self._shares[doc_id].append({
            "owner": owner,
            "recipient": recipient,
            "level": level,
            "timestamp": time.time(),
        })

        self._log_audit(
            doc_id, owner,
            f"shared_with:{recipient}",
        )

        return {
            "doc_id": doc_id,
            "recipient": recipient,
            "shared": True,
        }

    def get_audit_log(
        self,
        doc_id: str = "",
        limit: int = 20,
    ) -> dict[str, Any]:
        """Denetim günlüğü döndürür.

        Args:
            doc_id: Doküman kimliği filtresi.
            limit: Sınır.

        Returns:
            Günlük bilgisi.
        """
        if doc_id:
            entries = [
                e for e in self._audit_log
                if e["doc_id"] == doc_id
            ]
        else:
            entries = self._audit_log

        return {
            "entries": entries[-limit:],
            "total": len(entries),
            "retrieved": True,
        }

    def encrypt_document(
        self,
        doc_id: str,
        algorithm: str = "AES-256",
    ) -> dict[str, Any]:
        """Doküman şifreler.

        Args:
            doc_id: Doküman kimliği.
            algorithm: Algoritma.

        Returns:
            Şifreleme bilgisi.
        """
        self._encrypted.add(doc_id)

        self._log_audit(
            doc_id, "system", "encrypted",
        )

        return {
            "doc_id": doc_id,
            "algorithm": algorithm,
            "encrypted": True,
        }

    def add_watermark(
        self,
        doc_id: str,
        watermark_text: str = "",
        user: str = "",
    ) -> dict[str, Any]:
        """Filigran ekler.

        Args:
            doc_id: Doküman kimliği.
            watermark_text: Filigran metni.
            user: Kullanıcı.

        Returns:
            Filigran bilgisi.
        """
        self._watermarked.add(doc_id)

        self._log_audit(
            doc_id, user, "watermarked",
        )

        return {
            "doc_id": doc_id,
            "watermark_text": watermark_text,
            "watermarked": True,
        }

    def _log_audit(
        self,
        doc_id: str,
        user: str,
        action: str,
    ) -> None:
        """Denetim günlüğüne yazar."""
        self._counter += 1
        self._audit_log.append({
            "audit_id": (
                f"aud_{self._counter}"
            ),
            "doc_id": doc_id,
            "user": user,
            "action": action,
            "timestamp": time.time(),
        })

    @property
    def permission_count(self) -> int:
        """İzin sayısı."""
        return self._stats[
            "permissions_set"
        ]

    @property
    def audit_count(self) -> int:
        """Denetim kaydı sayısı."""
        return len(self._audit_log)
