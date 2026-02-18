"""
Denetim izi gorsellestiricisi modulu.

Gorsel denetim izi, aktor aksiyonlari,
degisiklik vurgulama, izin takibi,
dis aktarma secenekleri.
"""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class AuditTrailVisualizer:
    """Denetim izi gorsellestiricisi.

    Attributes:
        _audit_entries: Denetim kayitlari.
        _views: Gorunum kayitlari.
        _stats: Istatistikler.
    """

    def __init__(self) -> None:
        """Gorsellestiricyi baslatir."""
        self._audit_entries: list[dict] = []
        self._views: list[dict] = []
        self._stats: dict[str, int] = {
            "entries_added": 0,
            "views_generated": 0,
        }
        logger.info(
            "AuditTrailVisualizer baslatildi"
        )

    @property
    def entry_count(self) -> int:
        """Kayit sayisi."""
        return len(self._audit_entries)

    def add_entry(
        self,
        actor: str = "",
        action: str = "",
        resource: str = "",
        changes: dict | None = None,
        permission: str = "",
        result: str = "success",
    ) -> dict[str, Any]:
        """Denetim kaydi ekler.

        Args:
            actor: Aktor.
            action: Aksiyon.
            resource: Kaynak.
            changes: Degisiklikler.
            permission: Izin.
            result: Sonuc.

        Returns:
            Ekleme bilgisi.
        """
        try:
            aid = f"au_{uuid4()!s:.8}"
            entry = {
                "audit_id": aid,
                "actor": actor,
                "action": action,
                "resource": resource,
                "changes": changes or {},
                "permission": permission,
                "result": result,
                "timestamp": datetime.now(
                    timezone.utc
                ).isoformat(),
            }
            self._audit_entries.append(entry)
            self._stats[
                "entries_added"
            ] += 1

            return {
                "audit_id": aid,
                "actor": actor,
                "action": action,
                "resource": resource,
                "added": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "added": False,
                "error": str(e),
            }

    def visualize_trail(
        self,
        actor: str = "",
        resource: str = "",
        limit: int = 50,
    ) -> dict[str, Any]:
        """Denetim izini gorsellestirir.

        Args:
            actor: Aktor filtresi.
            resource: Kaynak filtresi.
            limit: Sonuc limiti.

        Returns:
            Gorsel denetim izi.
        """
        try:
            entries = list(
                self._audit_entries
            )

            if actor:
                entries = [
                    e
                    for e in entries
                    if e["actor"] == actor
                ]

            if resource:
                entries = [
                    e
                    for e in entries
                    if e["resource"]
                    == resource
                ]

            entries.sort(
                key=lambda x: x.get(
                    "timestamp", ""
                ),
                reverse=True,
            )
            entries = entries[:limit]

            nodes = []
            for entry in entries:
                node = {
                    "audit_id": entry[
                        "audit_id"
                    ],
                    "actor": entry["actor"],
                    "action": entry["action"],
                    "resource": entry[
                        "resource"
                    ],
                    "result": entry["result"],
                    "timestamp": entry[
                        "timestamp"
                    ],
                    "has_changes": bool(
                        entry.get("changes")
                    ),
                }
                nodes.append(node)

            vid = f"vw_{uuid4()!s:.8}"
            self._views.append({
                "view_id": vid,
                "type": "trail",
                "created_at": datetime.now(
                    timezone.utc
                ).isoformat(),
            })
            self._stats[
                "views_generated"
            ] += 1

            return {
                "view_id": vid,
                "nodes": nodes,
                "node_count": len(nodes),
                "filters": {
                    "actor": actor,
                    "resource": resource,
                },
                "visualized": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "visualized": False,
                "error": str(e),
            }

    def get_actor_actions(
        self,
        actor: str = "",
    ) -> dict[str, Any]:
        """Aktor aksiyonlarini getirir.

        Args:
            actor: Aktor adi.

        Returns:
            Aksiyon listesi.
        """
        try:
            entries = [
                e
                for e in self._audit_entries
                if e["actor"] == actor
            ]

            actions: dict[str, int] = {}
            resources: dict[str, int] = {}
            results: dict[str, int] = {}

            for entry in entries:
                act = entry.get(
                    "action", "unknown"
                )
                actions[act] = (
                    actions.get(act, 0) + 1
                )

                res = entry.get(
                    "resource", "unknown"
                )
                resources[res] = (
                    resources.get(res, 0) + 1
                )

                result = entry.get(
                    "result", "unknown"
                )
                results[result] = (
                    results.get(result, 0) + 1
                )

            return {
                "actor": actor,
                "total_actions": len(entries),
                "action_types": actions,
                "resources_accessed": resources,
                "results": results,
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }

    def highlight_changes(
        self,
        audit_id: str = "",
    ) -> dict[str, Any]:
        """Degisiklikleri vurgular.

        Args:
            audit_id: Denetim ID.

        Returns:
            Degisiklik bilgisi.
        """
        try:
            for entry in self._audit_entries:
                if (
                    entry["audit_id"]
                    == audit_id
                ):
                    changes = entry.get(
                        "changes", {}
                    )
                    highlights = []

                    for (
                        field,
                        change,
                    ) in changes.items():
                        if isinstance(
                            change, dict
                        ):
                            highlights.append({
                                "field": field,
                                "old_value": (
                                    change.get(
                                        "old"
                                    )
                                ),
                                "new_value": (
                                    change.get(
                                        "new"
                                    )
                                ),
                                "changed": (
                                    change.get(
                                        "old"
                                    )
                                    != change.get(
                                        "new"
                                    )
                                ),
                            })
                        else:
                            highlights.append({
                                "field": field,
                                "value": change,
                                "changed": True,
                            })

                    return {
                        "audit_id": audit_id,
                        "highlights": (
                            highlights
                        ),
                        "change_count": len(
                            highlights
                        ),
                        "highlighted": True,
                    }

            return {
                "audit_id": audit_id,
                "highlighted": False,
                "reason": "not_found",
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "highlighted": False,
                "error": str(e),
            }

    def track_permissions(
        self,
        actor: str = "",
    ) -> dict[str, Any]:
        """Izin kullanimini takip eder.

        Args:
            actor: Aktor.

        Returns:
            Izin bilgisi.
        """
        try:
            entries = [
                e
                for e in self._audit_entries
                if e["actor"] == actor
                and e.get("permission")
            ]

            permissions: dict[str, dict] = {}
            for entry in entries:
                perm = entry["permission"]
                if perm not in permissions:
                    permissions[perm] = {
                        "count": 0,
                        "success": 0,
                        "denied": 0,
                    }
                permissions[perm]["count"] += 1
                if (
                    entry.get("result")
                    == "success"
                ):
                    permissions[perm][
                        "success"
                    ] += 1
                elif (
                    entry.get("result")
                    == "denied"
                ):
                    permissions[perm][
                        "denied"
                    ] += 1

            return {
                "actor": actor,
                "permissions": permissions,
                "permission_count": len(
                    permissions
                ),
                "total_entries": len(entries),
                "tracked": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "tracked": False,
                "error": str(e),
            }

    def export_visualization(
        self,
        view_id: str = "",
        format_type: str = "json",
    ) -> dict[str, Any]:
        """Gorsellestirmeyi dis aktarir.

        Args:
            view_id: Gorunum ID.
            format_type: Format.

        Returns:
            Dis aktarma bilgisi.
        """
        try:
            view = None
            for v in self._views:
                if v["view_id"] == view_id:
                    view = v
                    break

            if not view:
                return {
                    "view_id": view_id,
                    "exported": False,
                    "reason": "not_found",
                }

            eid = f"ve_{uuid4()!s:.8}"

            return {
                "export_id": eid,
                "view_id": view_id,
                "format": format_type,
                "entries": len(
                    self._audit_entries
                ),
                "exported": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "exported": False,
                "error": str(e),
            }
