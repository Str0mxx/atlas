"""ATLAS Kaynak Saglayici modulu.

Kaynak olusturma, guncelleme,
silme, paralel yurutme
ve geri alma.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class ResourceProvisioner:
    """Kaynak saglayici.

    IaC kaynaklarini saglar.

    Attributes:
        _resources: Saglanan kaynaklar.
        _rollback_stack: Geri alma yigini.
    """

    def __init__(self) -> None:
        """Saglayiciyi baslatir."""
        self._resources: dict[
            str, dict[str, Any]
        ] = {}
        self._rollback_stack: list[
            dict[str, Any]
        ] = []
        self._hooks: dict[
            str, list[Any]
        ] = {}
        self._stats = {
            "created": 0,
            "updated": 0,
            "deleted": 0,
            "failed": 0,
            "rolled_back": 0,
        }

        logger.info(
            "ResourceProvisioner baslatildi",
        )

    def create(
        self,
        resource_key: str,
        resource_type: str,
        properties: dict[str, Any]
            | None = None,
    ) -> dict[str, Any]:
        """Kaynak olusturur.

        Args:
            resource_key: Kaynak anahtari.
            resource_type: Kaynak tipi.
            properties: Ozellikler.

        Returns:
            Saglama bilgisi.
        """
        self._resources[resource_key] = {
            "key": resource_key,
            "type": resource_type,
            "properties": properties or {},
            "status": "created",
            "created_at": time.time(),
            "updated_at": time.time(),
        }

        self._rollback_stack.append({
            "action": "delete",
            "key": resource_key,
        })

        self._stats["created"] += 1
        self._run_hooks("create", resource_key)

        return {
            "key": resource_key,
            "status": "created",
        }

    def update(
        self,
        resource_key: str,
        properties: dict[str, Any],
    ) -> dict[str, Any]:
        """Kaynak gunceller.

        Args:
            resource_key: Kaynak anahtari.
            properties: Yeni ozellikler.

        Returns:
            Guncelleme bilgisi.
        """
        res = self._resources.get(resource_key)
        if not res:
            return {"error": "not_found"}

        old_props = dict(res["properties"])
        self._rollback_stack.append({
            "action": "update",
            "key": resource_key,
            "old_properties": old_props,
        })

        res["properties"].update(properties)
        res["status"] = "updated"
        res["updated_at"] = time.time()

        self._stats["updated"] += 1
        self._run_hooks("update", resource_key)

        return {
            "key": resource_key,
            "status": "updated",
        }

    def delete(
        self,
        resource_key: str,
    ) -> dict[str, Any]:
        """Kaynak siler.

        Args:
            resource_key: Kaynak anahtari.

        Returns:
            Silme bilgisi.
        """
        res = self._resources.get(resource_key)
        if not res:
            return {"error": "not_found"}

        self._rollback_stack.append({
            "action": "create",
            "key": resource_key,
            "resource": dict(res),
        })

        del self._resources[resource_key]
        self._stats["deleted"] += 1
        self._run_hooks("delete", resource_key)

        return {
            "key": resource_key,
            "status": "deleted",
        }

    def apply_plan(
        self,
        changes: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Plan uygular.

        Args:
            changes: Degisiklik listesi.

        Returns:
            Uygulama sonucu.
        """
        results: list[dict[str, Any]] = []
        errors: list[dict[str, Any]] = []

        for change in changes:
            action = change["action"]
            key = change["resource"]

            try:
                if action == "create":
                    res_type = key.split(".")[0] if "." in key else "unknown"
                    result = self.create(
                        key, res_type,
                        change.get("properties"),
                    )
                elif action == "update":
                    result = self.update(
                        key,
                        change.get("new", {}),
                    )
                elif action == "delete":
                    result = self.delete(key)
                else:
                    result = {
                        "error": f"unknown_action: {action}",
                    }

                results.append(result)

                if "error" in result:
                    errors.append(result)

            except Exception as e:
                self._stats["failed"] += 1
                errors.append({
                    "resource": key,
                    "error": str(e),
                })

        return {
            "applied": len(results) - len(errors),
            "errors": len(errors),
            "total": len(changes),
            "details": results,
        }

    def rollback(
        self,
        steps: int = 1,
    ) -> dict[str, Any]:
        """Geri alma yapar.

        Args:
            steps: Geri alinacak adim sayisi.

        Returns:
            Geri alma bilgisi.
        """
        rolled = 0

        for _ in range(steps):
            if not self._rollback_stack:
                break

            entry = self._rollback_stack.pop()
            action = entry["action"]
            key = entry["key"]

            if action == "delete":
                # Olusturmayi geri al
                self._resources.pop(key, None)
            elif action == "update":
                # Guncellemeyi geri al
                res = self._resources.get(key)
                if res:
                    res["properties"] = entry[
                        "old_properties"
                    ]
            elif action == "create":
                # Silmeyi geri al
                self._resources[key] = entry[
                    "resource"
                ]

            rolled += 1

        self._stats["rolled_back"] += rolled

        return {
            "rolled_back": rolled,
            "remaining_stack": len(
                self._rollback_stack,
            ),
        }

    def get_resource(
        self,
        resource_key: str,
    ) -> dict[str, Any] | None:
        """Kaynak bilgisini getirir.

        Args:
            resource_key: Kaynak anahtari.

        Returns:
            Kaynak bilgisi veya None.
        """
        return self._resources.get(
            resource_key,
        )

    def register_hook(
        self,
        event: str,
        hook: Any,
    ) -> None:
        """Hook kaydeder.

        Args:
            event: Olay (create/update/delete).
            hook: Hook fonksiyonu.
        """
        self._hooks.setdefault(event, [])
        self._hooks[event].append(hook)

    def _run_hooks(
        self,
        event: str,
        resource_key: str,
    ) -> None:
        """Hook'lari calistirir.

        Args:
            event: Olay.
            resource_key: Kaynak anahtari.
        """
        for hook in self._hooks.get(event, []):
            try:
                hook(resource_key)
            except Exception:
                pass

    def list_resources(
        self,
        resource_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """Kaynaklari listeler.

        Args:
            resource_type: Tip filtresi.

        Returns:
            Kaynak listesi.
        """
        resources = list(
            self._resources.values(),
        )
        if resource_type:
            resources = [
                r for r in resources
                if r["type"] == resource_type
            ]
        return resources

    def get_stats(self) -> dict[str, int]:
        """Istatistikleri getirir.

        Returns:
            Istatistikler.
        """
        return dict(self._stats)

    @property
    def resource_count(self) -> int:
        """Kaynak sayisi."""
        return len(self._resources)

    @property
    def created_count(self) -> int:
        """Olusturulan sayisi."""
        return self._stats["created"]

    @property
    def rollback_stack_size(self) -> int:
        """Geri alma yigini boyutu."""
        return len(self._rollback_stack)
