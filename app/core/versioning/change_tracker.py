"""ATLAS Degisiklik Takipcisi modulu.

Degisiklik tespiti, diff uretimi,
gecmis, kategorizasyon ve
etki analizi.
"""

import logging
import time
from typing import Any

from app.models.versioning import ChangeType

logger = logging.getLogger(__name__)


class ChangeTracker:
    """Degisiklik takipcisi.

    Degisiklikleri tespit eder,
    kaydeder ve analiz eder.

    Attributes:
        _changes: Degisiklik gecmisi.
        _watchers: Izleyiciler.
    """

    def __init__(self) -> None:
        """Degisiklik takipcisini baslatir."""
        self._changes: list[
            dict[str, Any]
        ] = []
        self._watchers: dict[
            str, list[str]
        ] = {}
        self._baselines: dict[
            str, dict[str, Any]
        ] = {}

        logger.info(
            "ChangeTracker baslatildi",
        )

    def set_baseline(
        self,
        resource: str,
        state: dict[str, Any],
    ) -> None:
        """Temel durumu ayarlar.

        Args:
            resource: Kaynak adi.
            state: Temel durum.
        """
        self._baselines[resource] = dict(state)

    def detect_changes(
        self,
        resource: str,
        current: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Degisiklikleri tespit eder.

        Args:
            resource: Kaynak adi.
            current: Guncel durum.

        Returns:
            Degisiklik listesi.
        """
        baseline = self._baselines.get(
            resource, {},
        )
        changes: list[dict[str, Any]] = []

        # Eklenen ve degisen
        for key, val in current.items():
            if key not in baseline:
                changes.append({
                    "resource": resource,
                    "key": key,
                    "type": ChangeType.ADDED.value,
                    "new_value": val,
                    "at": time.time(),
                })
            elif baseline[key] != val:
                changes.append({
                    "resource": resource,
                    "key": key,
                    "type": ChangeType.MODIFIED.value,
                    "old_value": baseline[key],
                    "new_value": val,
                    "at": time.time(),
                })

        # Silinen
        for key in baseline:
            if key not in current:
                changes.append({
                    "resource": resource,
                    "key": key,
                    "type": ChangeType.DELETED.value,
                    "old_value": baseline[key],
                    "at": time.time(),
                })

        return changes

    def record_change(
        self,
        resource: str,
        change_type: str,
        key: str,
        old_value: Any = None,
        new_value: Any = None,
        author: str = "",
        reason: str = "",
    ) -> dict[str, Any]:
        """Degisiklik kaydeder.

        Args:
            resource: Kaynak adi.
            change_type: Degisiklik turu.
            key: Degisen alan.
            old_value: Eski deger.
            new_value: Yeni deger.
            author: Yapan.
            reason: Sebep.

        Returns:
            Degisiklik kaydi.
        """
        change = {
            "resource": resource,
            "type": change_type,
            "key": key,
            "old_value": old_value,
            "new_value": new_value,
            "author": author,
            "reason": reason,
            "at": time.time(),
        }
        self._changes.append(change)
        return change

    def generate_diff(
        self,
        old_state: dict[str, Any],
        new_state: dict[str, Any],
    ) -> dict[str, Any]:
        """Diff uretir.

        Args:
            old_state: Eski durum.
            new_state: Yeni durum.

        Returns:
            Diff bilgisi.
        """
        added: list[str] = []
        modified: list[str] = []
        deleted: list[str] = []

        for key in new_state:
            if key not in old_state:
                added.append(key)
            elif old_state[key] != new_state[key]:
                modified.append(key)

        for key in old_state:
            if key not in new_state:
                deleted.append(key)

        return {
            "added": added,
            "modified": modified,
            "deleted": deleted,
            "total_changes": (
                len(added)
                + len(modified)
                + len(deleted)
            ),
        }

    def get_history(
        self,
        resource: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Degisiklik gecmisi getirir.

        Args:
            resource: Kaynak filtresi.
            limit: Limit.

        Returns:
            Degisiklik listesi.
        """
        changes = self._changes
        if resource:
            changes = [
                c for c in changes
                if c["resource"] == resource
            ]
        return changes[-limit:]

    def categorize_changes(
        self,
        changes: list[dict[str, Any]],
    ) -> dict[str, list[dict[str, Any]]]:
        """Degisiklikleri kategorize eder.

        Args:
            changes: Degisiklik listesi.

        Returns:
            Kategorize edilmis degisiklikler.
        """
        categories: dict[
            str, list[dict[str, Any]]
        ] = {}

        for change in changes:
            ct = change.get("type", "unknown")
            if ct not in categories:
                categories[ct] = []
            categories[ct].append(change)

        return categories

    def analyze_impact(
        self,
        resource: str,
    ) -> dict[str, Any]:
        """Etki analizi yapar.

        Args:
            resource: Kaynak adi.

        Returns:
            Etki analizi.
        """
        changes = self.get_history(resource)
        watchers = self._watchers.get(
            resource, [],
        )

        type_counts: dict[str, int] = {}
        for c in changes:
            ct = c.get("type", "unknown")
            type_counts[ct] = (
                type_counts.get(ct, 0) + 1
            )

        return {
            "resource": resource,
            "total_changes": len(changes),
            "change_types": type_counts,
            "affected_watchers": len(watchers),
            "watchers": watchers,
        }

    def add_watcher(
        self,
        resource: str,
        watcher: str,
    ) -> None:
        """Izleyici ekler.

        Args:
            resource: Kaynak adi.
            watcher: Izleyici adi.
        """
        if resource not in self._watchers:
            self._watchers[resource] = []
        if watcher not in self._watchers[resource]:
            self._watchers[resource].append(
                watcher,
            )

    def remove_watcher(
        self,
        resource: str,
        watcher: str,
    ) -> bool:
        """Izleyici kaldirir.

        Args:
            resource: Kaynak adi.
            watcher: Izleyici adi.

        Returns:
            Basarili ise True.
        """
        watchers = self._watchers.get(resource)
        if watchers and watcher in watchers:
            watchers.remove(watcher)
            return True
        return False

    @property
    def change_count(self) -> int:
        """Degisiklik sayisi."""
        return len(self._changes)

    @property
    def baseline_count(self) -> int:
        """Temel durum sayisi."""
        return len(self._baselines)

    @property
    def watcher_count(self) -> int:
        """Izleyici sayisi."""
        return sum(
            len(w) for w in self._watchers.values()
        )
