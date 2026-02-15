"""ATLAS Grup Yoneticisi modulu.

Grup uyeligu, ic ice gruplar,
senkronizasyon.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class GroupManager:
    """Grup yoneticisi.

    Grup ve uyelik islemlerini yonetir.

    Attributes:
        _groups: Grup kayitlari.
        _members: Uyelikler.
    """

    def __init__(self) -> None:
        """Grup yoneticisini baslatir."""
        self._groups: dict[
            str, dict[str, Any]
        ] = {}
        self._members: dict[
            str, set[str]
        ] = {}
        self._nested: dict[
            str, set[str]
        ] = {}
        self._stats = {
            "created": 0,
            "deleted": 0,
            "members_added": 0,
            "members_removed": 0,
        }

        logger.info(
            "GroupManager baslatildi",
        )

    def create_group(
        self,
        group_id: str,
        name: str,
        description: str = "",
        parent_group: str | None = None,
        roles: list[str] | None = None,
    ) -> dict[str, Any]:
        """Grup olusturur.

        Args:
            group_id: Grup ID.
            name: Grup adi.
            description: Aciklama.
            parent_group: Ust grup.
            roles: Grup rolleri.

        Returns:
            Grup bilgisi.
        """
        if group_id in self._groups:
            return {"error": "group_exists"}

        if parent_group and parent_group not in self._groups:
            return {"error": "parent_not_found"}

        self._groups[group_id] = {
            "group_id": group_id,
            "name": name,
            "description": description,
            "parent_group": parent_group,
            "roles": roles or [],
            "created_at": time.time(),
        }

        self._members[group_id] = set()
        self._nested[group_id] = set()

        if parent_group:
            self._nested[parent_group].add(
                group_id,
            )

        self._stats["created"] += 1

        return {
            "group_id": group_id,
            "name": name,
            "status": "created",
        }

    def delete_group(
        self,
        group_id: str,
    ) -> bool:
        """Grup siler.

        Args:
            group_id: Grup ID.

        Returns:
            Basarili mi.
        """
        if group_id not in self._groups:
            return False

        group = self._groups[group_id]

        # Ust gruptan cikar
        parent = group.get("parent_group")
        if parent and parent in self._nested:
            self._nested[parent].discard(group_id)

        # Cocuk gruplarin parent'ini temizle
        for child_id in list(
            self._nested.get(group_id, set()),
        ):
            if child_id in self._groups:
                self._groups[child_id][
                    "parent_group"
                ] = None

        del self._groups[group_id]
        self._members.pop(group_id, None)
        self._nested.pop(group_id, None)

        self._stats["deleted"] += 1
        return True

    def add_member(
        self,
        group_id: str,
        member_id: str,
    ) -> dict[str, Any]:
        """Gruba uye ekler.

        Args:
            group_id: Grup ID.
            member_id: Uye ID.

        Returns:
            Ekleme sonucu.
        """
        if group_id not in self._groups:
            return {"error": "group_not_found"}

        self._members[group_id].add(member_id)
        self._stats["members_added"] += 1

        return {
            "group_id": group_id,
            "member_id": member_id,
            "status": "added",
        }

    def remove_member(
        self,
        group_id: str,
        member_id: str,
    ) -> dict[str, Any]:
        """Gruptan uye cikarir.

        Args:
            group_id: Grup ID.
            member_id: Uye ID.

        Returns:
            Cikarma sonucu.
        """
        if group_id not in self._groups:
            return {"error": "group_not_found"}

        self._members[group_id].discard(member_id)
        self._stats["members_removed"] += 1

        return {
            "group_id": group_id,
            "member_id": member_id,
            "status": "removed",
        }

    def get_members(
        self,
        group_id: str,
        include_nested: bool = False,
    ) -> list[str]:
        """Grup uyelerini getirir.

        Args:
            group_id: Grup ID.
            include_nested: Alt gruplari dahil et.

        Returns:
            Uye ID listesi.
        """
        if group_id not in self._members:
            return []

        members = set(self._members[group_id])

        if include_nested:
            for child_id in self._nested.get(
                group_id, set(),
            ):
                members.update(
                    self.get_members(
                        child_id,
                        include_nested=True,
                    ),
                )

        return sorted(members)

    def get_user_groups(
        self,
        member_id: str,
    ) -> list[str]:
        """Kullanicinin gruplarini getirir.

        Args:
            member_id: Uye ID.

        Returns:
            Grup ID listesi.
        """
        groups = []
        for gid, members in self._members.items():
            if member_id in members:
                groups.append(gid)
        return groups

    def is_member(
        self,
        group_id: str,
        member_id: str,
        check_nested: bool = False,
    ) -> bool:
        """Uyelik kontrolu.

        Args:
            group_id: Grup ID.
            member_id: Uye ID.
            check_nested: Alt gruplari kontrol et.

        Returns:
            Uye mi.
        """
        if group_id not in self._members:
            return False

        if member_id in self._members[group_id]:
            return True

        if check_nested:
            for child_id in self._nested.get(
                group_id, set(),
            ):
                if self.is_member(
                    child_id,
                    member_id,
                    check_nested=True,
                ):
                    return True

        return False

    def get_group(
        self,
        group_id: str,
    ) -> dict[str, Any] | None:
        """Grup bilgisi getirir.

        Args:
            group_id: Grup ID.

        Returns:
            Grup bilgisi veya None.
        """
        return self._groups.get(group_id)

    def get_nested_groups(
        self,
        group_id: str,
    ) -> list[str]:
        """Alt gruplari getirir.

        Args:
            group_id: Grup ID.

        Returns:
            Alt grup ID listesi.
        """
        return sorted(
            self._nested.get(group_id, set()),
        )

    def sync_roles(
        self,
        group_id: str,
        roles: list[str],
    ) -> dict[str, Any]:
        """Grup rollerini senkronize eder.

        Args:
            group_id: Grup ID.
            roles: Yeni roller.

        Returns:
            Senkronizasyon sonucu.
        """
        group = self._groups.get(group_id)
        if not group:
            return {"error": "group_not_found"}

        old_roles = group["roles"]
        group["roles"] = list(roles)

        return {
            "group_id": group_id,
            "old_roles": old_roles,
            "new_roles": list(roles),
            "status": "synced",
        }

    def list_groups(
        self,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Gruplari listeler.

        Args:
            limit: Limit.

        Returns:
            Grup listesi.
        """
        result = []
        for gid, group in self._groups.items():
            g = dict(group)
            g["member_count"] = len(
                self._members.get(gid, set()),
            )
            result.append(g)
        return result[-limit:]

    @property
    def group_count(self) -> int:
        """Grup sayisi."""
        return len(self._groups)

    @property
    def total_members(self) -> int:
        """Toplam uye sayisi."""
        all_members: set[str] = set()
        for members in self._members.values():
            all_members.update(members)
        return len(all_members)

    @property
    def nested_count(self) -> int:
        """Ic ice grup sayisi."""
        return sum(
            len(v) for v in self._nested.values()
        )
