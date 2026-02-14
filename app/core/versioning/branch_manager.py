"""ATLAS Dal Yoneticisi modulu.

Dal olusturma, birlestirme,
karsilastirma, catisma tespiti
ve temizlik.
"""

import logging
import time
from typing import Any

from app.models.versioning import BranchStatus

logger = logging.getLogger(__name__)


class BranchManager:
    """Dal yoneticisi.

    Surumleme dallari olusturur
    ve yonetir.

    Attributes:
        _branches: Dal kayitlari.
        _active: Aktif dal.
    """

    def __init__(self) -> None:
        """Dal yoneticisini baslatir."""
        self._branches: dict[
            str, dict[str, Any]
        ] = {
            "main": {
                "name": "main",
                "status": BranchStatus.ACTIVE.value,
                "parent": "",
                "state": {},
                "history": [],
                "created_at": time.time(),
            },
        }
        self._active = "main"

        logger.info("BranchManager baslatildi")

    def create_branch(
        self,
        name: str,
        parent: str = "",
        state: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Dal olusturur.

        Args:
            name: Dal adi.
            parent: Ebeveyn dal.
            state: Baslangic durumu.

        Returns:
            Dal bilgisi.
        """
        parent_name = parent or self._active
        parent_branch = self._branches.get(
            parent_name,
        )
        parent_state = (
            parent_branch.get("state", {})
            if parent_branch
            else {}
        )

        branch = {
            "name": name,
            "status": BranchStatus.ACTIVE.value,
            "parent": parent_name,
            "state": state or dict(parent_state),
            "history": [],
            "created_at": time.time(),
        }
        self._branches[name] = branch
        return branch

    def switch_branch(
        self,
        name: str,
    ) -> bool:
        """Aktif dali degistirir.

        Args:
            name: Dal adi.

        Returns:
            Basarili ise True.
        """
        if name not in self._branches:
            return False

        branch = self._branches[name]
        if branch["status"] != BranchStatus.ACTIVE.value:
            return False

        self._active = name
        return True

    def commit_to_branch(
        self,
        branch_name: str,
        changes: dict[str, Any],
        message: str = "",
    ) -> dict[str, Any]:
        """Dala commit yapar.

        Args:
            branch_name: Dal adi.
            changes: Degisiklikler.
            message: Commit mesaji.

        Returns:
            Commit bilgisi.
        """
        branch = self._branches.get(branch_name)
        if not branch:
            return {
                "success": False,
                "reason": "branch_not_found",
            }

        branch["state"].update(changes)
        commit = {
            "message": message,
            "changes": changes,
            "at": time.time(),
        }
        branch["history"].append(commit)

        return {
            "success": True,
            "branch": branch_name,
            "message": message,
        }

    def merge_branch(
        self,
        source: str,
        target: str = "",
    ) -> dict[str, Any]:
        """Dallari birlestirir.

        Args:
            source: Kaynak dal.
            target: Hedef dal.

        Returns:
            Birlestirme sonucu.
        """
        target_name = target or self._active
        src = self._branches.get(source)
        tgt = self._branches.get(target_name)

        if not src or not tgt:
            return {
                "success": False,
                "reason": "branch_not_found",
            }

        # Catisma kontrolu
        conflicts = self.detect_conflicts(
            source, target_name,
        )
        if conflicts:
            return {
                "success": False,
                "reason": "conflicts_detected",
                "conflicts": conflicts,
            }

        # Birlestir
        tgt["state"].update(src["state"])
        src["status"] = BranchStatus.MERGED.value

        return {
            "success": True,
            "source": source,
            "target": target_name,
            "merged_keys": list(
                src["state"].keys(),
            ),
        }

    def compare_branches(
        self,
        branch1: str,
        branch2: str,
    ) -> dict[str, Any]:
        """Iki dali karsilastirir.

        Args:
            branch1: Birinci dal.
            branch2: Ikinci dal.

        Returns:
            Karsilastirma sonucu.
        """
        b1 = self._branches.get(branch1)
        b2 = self._branches.get(branch2)

        if not b1 or not b2:
            return {
                "success": False,
                "reason": "branch_not_found",
            }

        s1 = b1["state"]
        s2 = b2["state"]

        only_in_1 = [
            k for k in s1 if k not in s2
        ]
        only_in_2 = [
            k for k in s2 if k not in s1
        ]
        different = [
            k for k in s1
            if k in s2 and s1[k] != s2[k]
        ]
        same = [
            k for k in s1
            if k in s2 and s1[k] == s2[k]
        ]

        return {
            "only_in_first": only_in_1,
            "only_in_second": only_in_2,
            "different": different,
            "same": same,
        }

    def detect_conflicts(
        self,
        source: str,
        target: str,
    ) -> list[str]:
        """Catismalari tespit eder.

        Args:
            source: Kaynak dal.
            target: Hedef dal.

        Returns:
            Catisma listesi.
        """
        b_src = self._branches.get(source)
        b_tgt = self._branches.get(target)

        if not b_src or not b_tgt:
            return []

        conflicts: list[str] = []
        s_src = b_src["state"]
        s_tgt = b_tgt["state"]

        for key in s_src:
            if key in s_tgt:
                if (
                    s_src[key] != s_tgt[key]
                    and type(s_src[key])
                    != type(s_tgt[key])
                ):
                    conflicts.append(key)

        return conflicts

    def close_branch(
        self,
        name: str,
    ) -> bool:
        """Dali kapatir.

        Args:
            name: Dal adi.

        Returns:
            Basarili ise True.
        """
        if name == "main":
            return False

        branch = self._branches.get(name)
        if not branch:
            return False

        branch["status"] = (
            BranchStatus.CLOSED.value
        )
        if self._active == name:
            self._active = "main"
        return True

    def delete_branch(
        self,
        name: str,
    ) -> bool:
        """Dali siler.

        Args:
            name: Dal adi.

        Returns:
            Basarili ise True.
        """
        if name == "main":
            return False

        if name in self._branches:
            del self._branches[name]
            if self._active == name:
                self._active = "main"
            return True
        return False

    def get_branch(
        self,
        name: str,
    ) -> dict[str, Any] | None:
        """Dal getirir.

        Args:
            name: Dal adi.

        Returns:
            Dal veya None.
        """
        return self._branches.get(name)

    def cleanup_stale(
        self,
        max_age_seconds: float = 86400,
    ) -> int:
        """Eski dallari temizler.

        Args:
            max_age_seconds: Maks yas.

        Returns:
            Temizlenen dal sayisi.
        """
        now = time.time()
        stale: list[str] = []

        for name, branch in self._branches.items():
            if name == "main":
                continue
            age = now - branch.get(
                "created_at", now,
            )
            if (
                age > max_age_seconds
                and branch["status"]
                in (
                    BranchStatus.MERGED.value,
                    BranchStatus.CLOSED.value,
                )
            ):
                stale.append(name)

        for name in stale:
            del self._branches[name]
            if self._active == name:
                self._active = "main"

        return len(stale)

    @property
    def active_branch(self) -> str:
        """Aktif dal adi."""
        return self._active

    @property
    def branch_count(self) -> int:
        """Dal sayisi."""
        return len(self._branches)

    @property
    def active_count(self) -> int:
        """Aktif dal sayisi."""
        return sum(
            1 for b in self._branches.values()
            if b["status"]
            == BranchStatus.ACTIVE.value
        )
