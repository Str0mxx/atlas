"""ATLAS Doküman Sürüm Takipçisi modülü.

Sürüm geçmişi, değişiklik takibi,
fark üretimi, geri alma desteği,
dal yönetimi.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class DocVersionTracker:
    """Doküman sürüm takipçisi.

    Doküman sürümlerini izler ve yönetir.

    Attributes:
        _versions: Sürüm kayıtları.
        _branches: Dal kayıtları.
    """

    def __init__(self) -> None:
        """Takipçiyi başlatır."""
        self._versions: dict[
            str, list[dict[str, Any]]
        ] = {}
        self._branches: dict[
            str, dict[str, Any]
        ] = {}
        self._counter = 0
        self._stats = {
            "versions_created": 0,
            "rollbacks_performed": 0,
        }

        logger.info(
            "DocVersionTracker baslatildi",
        )

    def create_version(
        self,
        doc_id: str,
        content: str = "",
        author: str = "",
        message: str = "",
    ) -> dict[str, Any]:
        """Yeni sürüm oluşturur.

        Args:
            doc_id: Doküman kimliği.
            content: İçerik.
            author: Yazar.
            message: Mesaj.

        Returns:
            Sürüm bilgisi.
        """
        self._counter += 1
        vid = f"ver_{self._counter}"

        if doc_id not in self._versions:
            self._versions[doc_id] = []

        version_num = (
            len(self._versions[doc_id]) + 1
        )

        entry = {
            "version_id": vid,
            "doc_id": doc_id,
            "version": f"{version_num}.0",
            "content": content,
            "author": author,
            "message": message,
            "timestamp": time.time(),
        }

        self._versions[doc_id].append(entry)
        self._stats[
            "versions_created"
        ] += 1

        return {
            "version_id": vid,
            "version": f"{version_num}.0",
            "doc_id": doc_id,
            "created": True,
        }

    def get_history(
        self,
        doc_id: str,
        limit: int = 10,
    ) -> dict[str, Any]:
        """Sürüm geçmişi döndürür.

        Args:
            doc_id: Doküman kimliği.
            limit: Sınır.

        Returns:
            Geçmiş bilgisi.
        """
        versions = self._versions.get(
            doc_id, [],
        )

        history = [
            {
                "version_id": v["version_id"],
                "version": v["version"],
                "author": v.get("author", ""),
                "message": v.get("message", ""),
                "timestamp": v["timestamp"],
            }
            for v in reversed(versions)
        ][:limit]

        return {
            "doc_id": doc_id,
            "history": history,
            "total": len(versions),
            "retrieved": len(versions) > 0,
        }

    def track_changes(
        self,
        doc_id: str,
    ) -> dict[str, Any]:
        """Değişiklik takibi yapar.

        Args:
            doc_id: Doküman kimliği.

        Returns:
            Takip bilgisi.
        """
        versions = self._versions.get(
            doc_id, [],
        )
        if len(versions) < 2:
            return {
                "doc_id": doc_id,
                "changes": [],
                "tracked": False,
            }

        prev = versions[-2]
        curr = versions[-1]

        prev_len = len(
            prev.get("content", ""),
        )
        curr_len = len(
            curr.get("content", ""),
        )
        diff = curr_len - prev_len

        changes = [{
            "from_version": prev["version"],
            "to_version": curr["version"],
            "chars_added": max(diff, 0),
            "chars_removed": abs(
                min(diff, 0),
            ),
            "author": curr.get(
                "author", "",
            ),
        }]

        return {
            "doc_id": doc_id,
            "changes": changes,
            "tracked": True,
        }

    def generate_diff(
        self,
        doc_id: str,
        version_a: str = "",
        version_b: str = "",
    ) -> dict[str, Any]:
        """Fark üretir.

        Args:
            doc_id: Doküman kimliği.
            version_a: Sürüm A.
            version_b: Sürüm B.

        Returns:
            Fark bilgisi.
        """
        versions = self._versions.get(
            doc_id, [],
        )
        if not versions:
            return {
                "doc_id": doc_id,
                "generated": False,
            }

        content_a = ""
        content_b = ""

        for v in versions:
            if v["version"] == version_a:
                content_a = v.get(
                    "content", "",
                )
            if v["version"] == version_b:
                content_b = v.get(
                    "content", "",
                )

        lines_a = content_a.splitlines()
        lines_b = content_b.splitlines()

        added = [
            l for l in lines_b
            if l not in lines_a
        ]
        removed = [
            l for l in lines_a
            if l not in lines_b
        ]

        return {
            "doc_id": doc_id,
            "version_a": version_a,
            "version_b": version_b,
            "lines_added": len(added),
            "lines_removed": len(removed),
            "added": added,
            "removed": removed,
            "generated": True,
        }

    def rollback(
        self,
        doc_id: str,
        target_version: str = "",
    ) -> dict[str, Any]:
        """Geri alma yapar.

        Args:
            doc_id: Doküman kimliği.
            target_version: Hedef sürüm.

        Returns:
            Geri alma bilgisi.
        """
        versions = self._versions.get(
            doc_id, [],
        )
        if not versions:
            return {
                "doc_id": doc_id,
                "rolled_back": False,
            }

        target = None
        for v in versions:
            if v["version"] == target_version:
                target = v
                break

        if not target:
            return {
                "doc_id": doc_id,
                "target_version": (
                    target_version
                ),
                "rolled_back": False,
            }

        # Yeni sürüm olarak geri al
        self._counter += 1
        vid = f"ver_{self._counter}"
        version_num = len(versions) + 1

        entry = {
            "version_id": vid,
            "doc_id": doc_id,
            "version": f"{version_num}.0",
            "content": target.get(
                "content", "",
            ),
            "author": "system",
            "message": (
                f"Rollback to "
                f"{target_version}"
            ),
            "timestamp": time.time(),
        }

        self._versions[doc_id].append(entry)
        self._stats[
            "rollbacks_performed"
        ] += 1

        return {
            "doc_id": doc_id,
            "new_version": f"{version_num}.0",
            "restored_from": target_version,
            "rolled_back": True,
        }

    def create_branch(
        self,
        doc_id: str,
        branch_name: str = "",
        from_version: str = "",
    ) -> dict[str, Any]:
        """Dal oluşturur.

        Args:
            doc_id: Doküman kimliği.
            branch_name: Dal adı.
            from_version: Kaynak sürüm.

        Returns:
            Dal bilgisi.
        """
        bid = f"{doc_id}:{branch_name}"

        self._branches[bid] = {
            "doc_id": doc_id,
            "branch_name": branch_name,
            "from_version": from_version,
            "versions": [],
            "timestamp": time.time(),
        }

        return {
            "doc_id": doc_id,
            "branch_name": branch_name,
            "from_version": from_version,
            "created": True,
        }

    @property
    def version_count(self) -> int:
        """Sürüm sayısı."""
        return self._stats[
            "versions_created"
        ]

    @property
    def rollback_count(self) -> int:
        """Geri alma sayısı."""
        return self._stats[
            "rollbacks_performed"
        ]
