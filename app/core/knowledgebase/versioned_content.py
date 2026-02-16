"""ATLAS Versiyonlu İçerik modülü.

Versiyon kontrolü, değişiklik geçmişi,
fark görüntüleme, geri alma,
işbirliği.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class VersionedContent:
    """Versiyonlu içerik yöneticisi.

    İçerik versiyonlarını yönetir.

    Attributes:
        _versions: Versiyon kayıtları.
        _current: Güncel versiyonlar.
    """

    def __init__(self) -> None:
        """Versiyon yöneticisini başlatır."""
        self._versions: dict[
            str, list[dict[str, Any]]
        ] = {}
        self._current: dict[
            str, int
        ] = {}
        self._locks: dict[
            str, str
        ] = {}
        self._counter = 0
        self._stats = {
            "versions_created": 0,
            "rollbacks": 0,
        }

        logger.info(
            "VersionedContent baslatildi",
        )

    def create_version(
        self,
        page_id: str,
        content: str = "",
        author: str = "",
        message: str = "",
    ) -> dict[str, Any]:
        """Versiyon oluşturur.

        Args:
            page_id: Sayfa kimliği.
            content: İçerik.
            author: Yazar.
            message: Commit mesajı.

        Returns:
            Versiyon bilgisi.
        """
        if page_id not in self._versions:
            self._versions[page_id] = []
            self._current[page_id] = 0

        version_num = len(
            self._versions[page_id],
        ) + 1

        self._versions[page_id].append({
            "version": version_num,
            "content": content,
            "author": author,
            "message": message,
            "timestamp": time.time(),
        })
        self._current[
            page_id
        ] = version_num

        self._stats[
            "versions_created"
        ] += 1

        return {
            "page_id": page_id,
            "version": version_num,
            "created": True,
        }

    def get_history(
        self,
        page_id: str,
        limit: int = 10,
    ) -> dict[str, Any]:
        """Değişiklik geçmişini getirir.

        Args:
            page_id: Sayfa kimliği.
            limit: Maks kayıt.

        Returns:
            Geçmiş bilgisi.
        """
        versions = self._versions.get(
            page_id, [],
        )

        history = [
            {
                "version": v["version"],
                "author": v.get(
                    "author", "",
                ),
                "message": v.get(
                    "message", "",
                ),
                "timestamp": v[
                    "timestamp"
                ],
            }
            for v in reversed(versions)
        ][:limit]

        return {
            "page_id": page_id,
            "history": history,
            "total_versions": len(
                versions,
            ),
            "retrieved": True,
        }

    def view_diff(
        self,
        page_id: str,
        version_a: int = 0,
        version_b: int = 0,
    ) -> dict[str, Any]:
        """Fark görüntüler.

        Args:
            page_id: Sayfa kimliği.
            version_a: Versiyon A.
            version_b: Versiyon B.

        Returns:
            Fark bilgisi.
        """
        versions = self._versions.get(
            page_id, [],
        )
        if not versions:
            return {
                "page_id": page_id,
                "found": False,
            }

        va = version_a or max(
            len(versions) - 1, 1,
        )
        vb = version_b or len(versions)

        content_a = ""
        content_b = ""
        for v in versions:
            if v["version"] == va:
                content_a = v.get(
                    "content", "",
                )
            if v["version"] == vb:
                content_b = v.get(
                    "content", "",
                )

        lines_a = set(
            content_a.split("\n"),
        )
        lines_b = set(
            content_b.split("\n"),
        )
        added = lines_b - lines_a
        removed = lines_a - lines_b

        return {
            "page_id": page_id,
            "version_a": va,
            "version_b": vb,
            "added_lines": len(added),
            "removed_lines": len(removed),
            "changed": len(added) > 0
            or len(removed) > 0,
            "diff_ok": True,
        }

    def rollback(
        self,
        page_id: str,
        target_version: int = 0,
    ) -> dict[str, Any]:
        """Geri alır.

        Args:
            page_id: Sayfa kimliği.
            target_version: Hedef versiyon.

        Returns:
            Geri alma bilgisi.
        """
        versions = self._versions.get(
            page_id, [],
        )
        if not versions:
            return {
                "page_id": page_id,
                "found": False,
            }

        target = target_version or max(
            len(versions) - 1, 1,
        )

        target_content = ""
        for v in versions:
            if v["version"] == target:
                target_content = v.get(
                    "content", "",
                )
                break

        new_version = (
            len(versions) + 1
        )
        self._versions[page_id].append({
            "version": new_version,
            "content": target_content,
            "author": "system",
            "message": (
                f"Rollback to v{target}"
            ),
            "timestamp": time.time(),
        })
        self._current[
            page_id
        ] = new_version

        self._stats["rollbacks"] += 1
        self._stats[
            "versions_created"
        ] += 1

        return {
            "page_id": page_id,
            "rolled_back_to": target,
            "new_version": new_version,
            "rolled_back": True,
        }

    def collaborate(
        self,
        page_id: str,
        action: str = "lock",
        user: str = "",
    ) -> dict[str, Any]:
        """İşbirliği yönetir.

        Args:
            page_id: Sayfa kimliği.
            action: Eylem (lock/unlock/status).
            user: Kullanıcı.

        Returns:
            İşbirliği bilgisi.
        """
        if action == "lock":
            current = self._locks.get(
                page_id,
            )
            if current and current != user:
                return {
                    "page_id": page_id,
                    "locked_by": current,
                    "conflict": True,
                }
            self._locks[page_id] = user
            return {
                "page_id": page_id,
                "locked_by": user,
                "locked": True,
            }

        if action == "unlock":
            self._locks.pop(
                page_id, None,
            )
            return {
                "page_id": page_id,
                "unlocked": True,
            }

        current = self._locks.get(
            page_id, "",
        )
        return {
            "page_id": page_id,
            "locked_by": current,
            "is_locked": bool(current),
            "status_ok": True,
        }

    @property
    def version_count(self) -> int:
        """Versiyon sayısı."""
        return self._stats[
            "versions_created"
        ]

    @property
    def rollback_count(self) -> int:
        """Geri alma sayısı."""
        return self._stats["rollbacks"]
