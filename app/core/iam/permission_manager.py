"""ATLAS Izin Yoneticisi modulu.

Kaynak/aksiyon izinleri, wildcard,
negasyon destegi.
"""

import fnmatch
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class PermissionManager:
    """Izin yoneticisi.

    Izinleri ve erisim kontrolunu yonetir.

    Attributes:
        _permissions: Izin kayitlari.
        _assignments: Izin atamalari.
    """

    def __init__(self) -> None:
        """Izin yoneticisini baslatir."""
        self._permissions: dict[
            str, dict[str, Any]
        ] = {}
        self._assignments: dict[
            str, list[str]
        ] = {}
        self._negations: dict[
            str, list[str]
        ] = {}
        self._stats = {
            "created": 0,
            "assigned": 0,
            "checks": 0,
            "allowed": 0,
            "denied": 0,
        }

        logger.info(
            "PermissionManager baslatildi",
        )

    def create_permission(
        self,
        permission_id: str,
        resource: str,
        action: str,
        description: str = "",
    ) -> dict[str, Any]:
        """Izin olusturur.

        Args:
            permission_id: Izin ID.
            resource: Kaynak.
            action: Aksiyon.
            description: Aciklama.

        Returns:
            Izin bilgisi.
        """
        if permission_id in self._permissions:
            return {"error": "permission_exists"}

        self._permissions[permission_id] = {
            "permission_id": permission_id,
            "resource": resource,
            "action": action,
            "description": description,
            "created_at": time.time(),
        }

        self._stats["created"] += 1

        return {
            "permission_id": permission_id,
            "resource": resource,
            "action": action,
            "status": "created",
        }

    def delete_permission(
        self,
        permission_id: str,
    ) -> bool:
        """Izin siler.

        Args:
            permission_id: Izin ID.

        Returns:
            Basarili mi.
        """
        if permission_id not in self._permissions:
            return False

        del self._permissions[permission_id]

        # Atamalardan temizle
        for subject in list(self._assignments):
            if permission_id in self._assignments[subject]:
                self._assignments[subject].remove(
                    permission_id,
                )

        return True

    def assign(
        self,
        subject_id: str,
        permission_id: str,
    ) -> dict[str, Any]:
        """Izin atar.

        Args:
            subject_id: Konu ID (kullanici/rol).
            permission_id: Izin ID.

        Returns:
            Atama sonucu.
        """
        if subject_id not in self._assignments:
            self._assignments[subject_id] = []

        if permission_id not in self._assignments[subject_id]:
            self._assignments[subject_id].append(
                permission_id,
            )

        self._stats["assigned"] += 1

        return {
            "subject_id": subject_id,
            "permission_id": permission_id,
            "status": "assigned",
        }

    def revoke(
        self,
        subject_id: str,
        permission_id: str,
    ) -> dict[str, Any]:
        """Izni geri alir.

        Args:
            subject_id: Konu ID.
            permission_id: Izin ID.

        Returns:
            Geri alma sonucu.
        """
        if subject_id in self._assignments:
            perms = self._assignments[subject_id]
            if permission_id in perms:
                perms.remove(permission_id)

        return {
            "subject_id": subject_id,
            "permission_id": permission_id,
            "status": "revoked",
        }

    def negate(
        self,
        subject_id: str,
        permission_id: str,
    ) -> dict[str, Any]:
        """Izin negasyonu ekler.

        Args:
            subject_id: Konu ID.
            permission_id: Izin ID.

        Returns:
            Negasyon sonucu.
        """
        if subject_id not in self._negations:
            self._negations[subject_id] = []

        if permission_id not in self._negations[subject_id]:
            self._negations[subject_id].append(
                permission_id,
            )

        return {
            "subject_id": subject_id,
            "permission_id": permission_id,
            "status": "negated",
        }

    def check(
        self,
        subject_id: str,
        resource: str,
        action: str,
    ) -> bool:
        """Izin kontrol eder.

        Args:
            subject_id: Konu ID.
            resource: Kaynak.
            action: Aksiyon.

        Returns:
            Izin var mi.
        """
        self._stats["checks"] += 1

        # Negasyon kontrolu
        negated = self._negations.get(
            subject_id, [],
        )
        for neg_perm in negated:
            perm = self._permissions.get(neg_perm)
            if perm and self._matches(
                perm["resource"],
                resource,
            ) and self._matches(
                perm["action"],
                action,
            ):
                self._stats["denied"] += 1
                return False

        # Izin kontrolu
        assigned = self._assignments.get(
            subject_id, [],
        )
        for perm_id in assigned:
            perm = self._permissions.get(perm_id)
            if not perm:
                continue
            if self._matches(
                perm["resource"],
                resource,
            ) and self._matches(
                perm["action"],
                action,
            ):
                self._stats["allowed"] += 1
                return True

        self._stats["denied"] += 1
        return False

    def get_permissions(
        self,
        subject_id: str,
    ) -> list[str]:
        """Konu izinlerini getirir.

        Args:
            subject_id: Konu ID.

        Returns:
            Izin ID listesi.
        """
        return list(
            self._assignments.get(
                subject_id, [],
            ),
        )

    def get_permission(
        self,
        permission_id: str,
    ) -> dict[str, Any] | None:
        """Izin bilgisi getirir.

        Args:
            permission_id: Izin ID.

        Returns:
            Izin bilgisi veya None.
        """
        return self._permissions.get(
            permission_id,
        )

    def find_by_resource(
        self,
        resource: str,
    ) -> list[dict[str, Any]]:
        """Kaynaga gore izin arar.

        Args:
            resource: Kaynak deseni.

        Returns:
            Eslesen izinler.
        """
        results = []
        for perm in self._permissions.values():
            if self._matches(
                perm["resource"], resource,
            ):
                results.append(perm)
        return results

    def list_permissions(
        self,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Izinleri listeler.

        Args:
            limit: Limit.

        Returns:
            Izin listesi.
        """
        items = list(self._permissions.values())
        return items[-limit:]

    def _matches(
        self,
        pattern: str,
        value: str,
    ) -> bool:
        """Desen eslestirir (wildcard destegi).

        Args:
            pattern: Desen.
            value: Deger.

        Returns:
            Eslesiyor mu.
        """
        if pattern == "*":
            return True
        return fnmatch.fnmatch(value, pattern)

    @property
    def permission_count(self) -> int:
        """Izin sayisi."""
        return len(self._permissions)

    @property
    def assignment_count(self) -> int:
        """Atama sayisi."""
        return sum(
            len(v)
            for v in self._assignments.values()
        )

    @property
    def negation_count(self) -> int:
        """Negasyon sayisi."""
        return sum(
            len(v)
            for v in self._negations.values()
        )
