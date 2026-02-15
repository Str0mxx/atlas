"""ATLAS Rol Yoneticisi modulu.

Rol hiyerarsisi, miras alma,
varsayilan roller.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class RoleManager:
    """Rol yoneticisi.

    Rolleri ve hiyerarsiyi yonetir.

    Attributes:
        _roles: Rol kayitlari.
        _hierarchy: Rol hiyerarsisi.
    """

    def __init__(self) -> None:
        """Rol yoneticisini baslatir."""
        self._roles: dict[
            str, dict[str, Any]
        ] = {}
        self._hierarchy: dict[
            str, str | None
        ] = {}
        self._defaults: list[str] = []
        self._stats = {
            "created": 0,
            "deleted": 0,
            "assigned": 0,
        }

        logger.info(
            "RoleManager baslatildi",
        )

    def create_role(
        self,
        role_id: str,
        name: str,
        permissions: list[str] | None = None,
        parent_role: str | None = None,
        is_default: bool = False,
        description: str = "",
    ) -> dict[str, Any]:
        """Rol olusturur.

        Args:
            role_id: Rol ID.
            name: Rol adi.
            permissions: Izinler.
            parent_role: Ust rol.
            is_default: Varsayilan mi.
            description: Aciklama.

        Returns:
            Rol bilgisi.
        """
        if role_id in self._roles:
            return {"error": "role_exists"}

        if parent_role and parent_role not in self._roles:
            return {"error": "parent_not_found"}

        self._roles[role_id] = {
            "role_id": role_id,
            "name": name,
            "permissions": list(permissions or []),
            "parent_role": parent_role,
            "is_default": is_default,
            "description": description,
            "created_at": time.time(),
        }

        self._hierarchy[role_id] = parent_role

        if is_default:
            self._defaults.append(role_id)

        self._stats["created"] += 1

        return {
            "role_id": role_id,
            "name": name,
            "status": "created",
        }

    def delete_role(
        self,
        role_id: str,
    ) -> bool:
        """Rol siler.

        Args:
            role_id: Rol ID.

        Returns:
            Basarili mi.
        """
        if role_id not in self._roles:
            return False

        # Cocuk rollerin parent'ini temizle
        for rid, parent in self._hierarchy.items():
            if parent == role_id:
                self._hierarchy[rid] = None
                if rid in self._roles:
                    self._roles[rid][
                        "parent_role"
                    ] = None

        del self._roles[role_id]
        self._hierarchy.pop(role_id, None)

        if role_id in self._defaults:
            self._defaults.remove(role_id)

        self._stats["deleted"] += 1
        return True

    def get_role(
        self,
        role_id: str,
    ) -> dict[str, Any] | None:
        """Rol getirir.

        Args:
            role_id: Rol ID.

        Returns:
            Rol bilgisi veya None.
        """
        return self._roles.get(role_id)

    def update_role(
        self,
        role_id: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Rol gunceller.

        Args:
            role_id: Rol ID.
            **kwargs: Guncellenecek alanlar.

        Returns:
            Guncelleme sonucu.
        """
        role = self._roles.get(role_id)
        if not role:
            return {"error": "role_not_found"}

        allowed = {
            "name", "permissions",
            "description", "is_default",
        }
        for key, value in kwargs.items():
            if key in allowed:
                role[key] = value

        return {
            "role_id": role_id,
            "status": "updated",
        }

    def add_permission(
        self,
        role_id: str,
        permission: str,
    ) -> dict[str, Any]:
        """Role izin ekler.

        Args:
            role_id: Rol ID.
            permission: Izin.

        Returns:
            Ekleme sonucu.
        """
        role = self._roles.get(role_id)
        if not role:
            return {"error": "role_not_found"}

        if permission not in role["permissions"]:
            role["permissions"].append(permission)

        return {
            "role_id": role_id,
            "permission": permission,
            "status": "added",
        }

    def remove_permission(
        self,
        role_id: str,
        permission: str,
    ) -> dict[str, Any]:
        """Rolden izin kaldirir.

        Args:
            role_id: Rol ID.
            permission: Izin.

        Returns:
            Kaldirma sonucu.
        """
        role = self._roles.get(role_id)
        if not role:
            return {"error": "role_not_found"}

        if permission in role["permissions"]:
            role["permissions"].remove(permission)

        return {
            "role_id": role_id,
            "permission": permission,
            "status": "removed",
        }

    def get_effective_permissions(
        self,
        role_id: str,
    ) -> list[str]:
        """Etkin izinleri getirir (miras dahil).

        Args:
            role_id: Rol ID.

        Returns:
            Izin listesi.
        """
        permissions: set[str] = set()
        current = role_id
        visited: set[str] = set()

        while current and current not in visited:
            visited.add(current)
            role = self._roles.get(current)
            if not role:
                break
            permissions.update(role["permissions"])
            current = role.get("parent_role")

        return sorted(permissions)

    def get_children(
        self,
        role_id: str,
    ) -> list[str]:
        """Alt rolleri getirir.

        Args:
            role_id: Rol ID.

        Returns:
            Alt rol ID listesi.
        """
        return [
            rid
            for rid, parent in self._hierarchy.items()
            if parent == role_id
        ]

    def get_ancestors(
        self,
        role_id: str,
    ) -> list[str]:
        """Ust rolleri getirir.

        Args:
            role_id: Rol ID.

        Returns:
            Ust rol ID listesi.
        """
        ancestors: list[str] = []
        current = self._hierarchy.get(role_id)
        visited: set[str] = set()

        while current and current not in visited:
            visited.add(current)
            ancestors.append(current)
            current = self._hierarchy.get(current)

        return ancestors

    def get_defaults(self) -> list[str]:
        """Varsayilan rolleri getirir.

        Returns:
            Varsayilan rol ID listesi.
        """
        return list(self._defaults)

    def list_roles(
        self,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Rolleri listeler.

        Args:
            limit: Limit.

        Returns:
            Rol listesi.
        """
        items = list(self._roles.values())
        return items[-limit:]

    @property
    def role_count(self) -> int:
        """Rol sayisi."""
        return len(self._roles)

    @property
    def default_count(self) -> int:
        """Varsayilan rol sayisi."""
        return len(self._defaults)
