"""ATLAS Erisim Kontrolu modulu.

Rol tabanli erisim (RBAC), izin yonetimi,
kaynak koruma, aksiyon yetkilendirme
ve denetim kaydi.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from app.models.security_hardening import (
    AccessAction,
    AccessRecord,
)

logger = logging.getLogger(__name__)


class AccessController:
    """Erisim kontrolcusu.

    Rol tabanli erisim kontrolu ve
    izin yonetimi saglar.

    Attributes:
        _roles: Tanimli roller.
        _user_roles: Kullanici-rol eslemesi.
        _permissions: Rol izinleri.
        _access_log: Erisim kayitlari.
    """

    def __init__(self) -> None:
        """Erisim kontrolcusunu baslatir."""
        self._roles: dict[str, dict[str, Any]] = {}
        self._user_roles: dict[str, list[str]] = {}
        self._permissions: dict[str, list[dict[str, Any]]] = {}
        self._access_log: list[AccessRecord] = []
        self._denial_count = 0

        logger.info("AccessController baslatildi")

    def create_role(
        self,
        name: str,
        description: str = "",
        parent: str = "",
    ) -> dict[str, Any]:
        """Rol olusturur.

        Args:
            name: Rol adi.
            description: Aciklama.
            parent: Ust rol.

        Returns:
            Rol bilgisi.
        """
        role = {
            "name": name,
            "description": description,
            "parent": parent,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._roles[name] = role

        if name not in self._permissions:
            self._permissions[name] = []

        # Ust rolden izinleri miras al
        if parent and parent in self._permissions:
            self._permissions[name].extend(
                self._permissions[parent],
            )

        logger.info("Rol olusturuldu: %s", name)
        return role

    def assign_role(
        self,
        user: str,
        role: str,
    ) -> bool:
        """Kullaniciya rol atar.

        Args:
            user: Kullanici.
            role: Rol adi.

        Returns:
            Basarili ise True.
        """
        if role not in self._roles:
            return False

        if user not in self._user_roles:
            self._user_roles[user] = []

        if role not in self._user_roles[user]:
            self._user_roles[user].append(role)

        return True

    def revoke_role(
        self,
        user: str,
        role: str,
    ) -> bool:
        """Kullanicidan rol kaldirir.

        Args:
            user: Kullanici.
            role: Rol adi.

        Returns:
            Basarili ise True.
        """
        if user not in self._user_roles:
            return False

        if role in self._user_roles[user]:
            self._user_roles[user].remove(role)
            return True
        return False

    def grant_permission(
        self,
        role: str,
        resource: str,
        actions: list[AccessAction],
    ) -> bool:
        """Role izin verir.

        Args:
            role: Rol adi.
            resource: Kaynak.
            actions: Izin verilen aksiyonlar.

        Returns:
            Basarili ise True.
        """
        if role not in self._roles:
            return False

        perm = {
            "resource": resource,
            "actions": [a.value for a in actions],
        }
        self._permissions[role].append(perm)
        return True

    def check_access(
        self,
        user: str,
        resource: str,
        action: AccessAction,
    ) -> bool:
        """Erisim kontrolu yapar.

        Args:
            user: Kullanici.
            resource: Kaynak.
            action: Aksiyon.

        Returns:
            Izin varsa True.
        """
        roles = self._user_roles.get(user, [])
        granted = False

        for role in roles:
            perms = self._permissions.get(role, [])
            for perm in perms:
                if (perm["resource"] == resource
                        and action.value in perm["actions"]):
                    granted = True
                    break
            if granted:
                break

        # Kayit olustur
        record = AccessRecord(
            user=user,
            role=",".join(roles),
            resource=resource,
            action=action,
            granted=granted,
        )
        self._access_log.append(record)

        if not granted:
            self._denial_count += 1
            logger.warning(
                "Erisim reddedildi: %s -> %s (%s)",
                user, resource, action.value,
            )

        return granted

    def get_user_roles(
        self,
        user: str,
    ) -> list[str]:
        """Kullanici rollerini getirir.

        Args:
            user: Kullanici.

        Returns:
            Rol listesi.
        """
        return list(self._user_roles.get(user, []))

    def get_user_permissions(
        self,
        user: str,
    ) -> list[dict[str, Any]]:
        """Kullanici izinlerini getirir.

        Args:
            user: Kullanici.

        Returns:
            Izin listesi.
        """
        roles = self._user_roles.get(user, [])
        perms: list[dict[str, Any]] = []
        for role in roles:
            perms.extend(self._permissions.get(role, []))
        return perms

    def get_access_log(
        self,
        user: str = "",
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Erisim kaydini getirir.

        Args:
            user: Kullanici filtresi.
            limit: Maks kayit.

        Returns:
            Erisim listesi.
        """
        logs = self._access_log
        if user:
            logs = [l for l in logs if l.user == user]
        return [
            {
                "access_id": l.access_id,
                "user": l.user,
                "resource": l.resource,
                "action": l.action.value,
                "granted": l.granted,
            }
            for l in logs[-limit:]
        ]

    @property
    def role_count(self) -> int:
        """Rol sayisi."""
        return len(self._roles)

    @property
    def user_count(self) -> int:
        """Kullanici sayisi."""
        return len(self._user_roles)

    @property
    def denial_count(self) -> int:
        """Reddedilen erisim sayisi."""
        return self._denial_count

    @property
    def access_log_count(self) -> int:
        """Erisim kaydi sayisi."""
        return len(self._access_log)
