"""ATLAS Konfigurasyon Farklayici modulu.

Konfigurasyon karsilastirma, fark uretimi,
degisiklik tespiti, migrasyon yollari
ve etki analizi.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class ConfigDiffer:
    """Konfigurasyon farklayici.

    Konfigurasyonlari karsilastirir.

    Attributes:
        _diffs: Fark gecmisi.
        _migrations: Migrasyon planlari.
    """

    def __init__(self) -> None:
        """Konfigurasyon farklayici baslatir."""
        self._diffs: list[
            dict[str, Any]
        ] = []
        self._migrations: list[
            dict[str, Any]
        ] = []
        self._impact_rules: dict[
            str, dict[str, Any]
        ] = {}

        logger.info("ConfigDiffer baslatildi")

    def diff(
        self,
        source: dict[str, Any],
        target: dict[str, Any],
        label: str = "",
    ) -> dict[str, Any]:
        """Iki konfigurasyon arasindaki farki bulur.

        Args:
            source: Kaynak konfigurasyon.
            target: Hedef konfigurasyon.
            label: Etiket.

        Returns:
            Fark sonucu.
        """
        all_keys = set(source) | set(target)
        added = []
        removed = []
        modified = []
        unchanged = []

        for key in all_keys:
            in_source = key in source
            in_target = key in target
            if in_source and not in_target:
                removed.append({
                    "key": key,
                    "value": source[key],
                })
            elif in_target and not in_source:
                added.append({
                    "key": key,
                    "value": target[key],
                })
            elif source[key] != target[key]:
                modified.append({
                    "key": key,
                    "old_value": source[key],
                    "new_value": target[key],
                })
            else:
                unchanged.append(key)

        result = {
            "label": label,
            "added": added,
            "removed": removed,
            "modified": modified,
            "unchanged": unchanged,
            "total_changes": (
                len(added) + len(removed)
                + len(modified)
            ),
            "has_changes": bool(
                added or removed or modified
            ),
            "timestamp": time.time(),
        }
        self._diffs.append(result)
        return result

    def deep_diff(
        self,
        source: dict[str, Any],
        target: dict[str, Any],
        path: str = "",
    ) -> list[dict[str, Any]]:
        """Derin fark bulur (ic ice sozlukler).

        Args:
            source: Kaynak.
            target: Hedef.
            path: Mevcut yol.

        Returns:
            Degisiklik listesi.
        """
        changes: list[dict[str, Any]] = []
        all_keys = set(source) | set(target)

        for key in all_keys:
            current = (
                f"{path}.{key}" if path else key
            )
            in_s = key in source
            in_t = key in target

            if in_s and not in_t:
                changes.append({
                    "path": current,
                    "type": "removed",
                    "old_value": source[key],
                })
            elif in_t and not in_s:
                changes.append({
                    "path": current,
                    "type": "added",
                    "new_value": target[key],
                })
            elif (
                isinstance(source[key], dict)
                and isinstance(target[key], dict)
            ):
                nested = self.deep_diff(
                    source[key], target[key],
                    current,
                )
                changes.extend(nested)
            elif source[key] != target[key]:
                changes.append({
                    "path": current,
                    "type": "modified",
                    "old_value": source[key],
                    "new_value": target[key],
                })

        return changes

    def create_migration(
        self,
        source: dict[str, Any],
        target: dict[str, Any],
        name: str = "",
    ) -> dict[str, Any]:
        """Migrasyon plani olusturur.

        Args:
            source: Kaynak konfigurasyon.
            target: Hedef konfigurasyon.
            name: Migrasyon adi.

        Returns:
            Migrasyon plani.
        """
        diff_result = self.diff(source, target)
        steps = []

        # Eklenmis anahtarlar
        for item in diff_result["added"]:
            steps.append({
                "action": "add",
                "key": item["key"],
                "value": item["value"],
            })

        # Degismis anahtarlar
        for item in diff_result["modified"]:
            steps.append({
                "action": "update",
                "key": item["key"],
                "old_value": item["old_value"],
                "new_value": item["new_value"],
            })

        # Silinmis anahtarlar
        for item in diff_result["removed"]:
            steps.append({
                "action": "remove",
                "key": item["key"],
                "old_value": item["value"],
            })

        migration = {
            "name": name,
            "steps": steps,
            "total_steps": len(steps),
            "created_at": time.time(),
        }
        self._migrations.append(migration)
        return migration

    def apply_migration(
        self,
        config: dict[str, Any],
        migration: dict[str, Any],
    ) -> dict[str, Any]:
        """Migrasyonu uygular.

        Args:
            config: Mevcut konfigurasyon.
            migration: Migrasyon plani.

        Returns:
            Guncellenmis konfigurasyon.
        """
        result = dict(config)
        applied = 0

        for step in migration.get("steps", []):
            action = step["action"]
            key = step["key"]
            if action == "add":
                result[key] = step["value"]
                applied += 1
            elif action == "update":
                result[key] = step["new_value"]
                applied += 1
            elif action == "remove":
                if key in result:
                    del result[key]
                    applied += 1

        return {
            "config": result,
            "applied_steps": applied,
            "total_steps": migration.get(
                "total_steps", 0,
            ),
        }

    def add_impact_rule(
        self,
        key_pattern: str,
        severity: str = "medium",
        description: str = "",
    ) -> None:
        """Etki kurali ekler.

        Args:
            key_pattern: Anahtar deseni.
            severity: Ciddiyet.
            description: Aciklama.
        """
        self._impact_rules[key_pattern] = {
            "severity": severity,
            "description": description,
        }

    def analyze_impact(
        self,
        diff_result: dict[str, Any],
    ) -> dict[str, Any]:
        """Degisiklik etkisini analiz eder.

        Args:
            diff_result: Fark sonucu.

        Returns:
            Etki analizi.
        """
        impacts = []
        max_severity = "low"
        severity_order = {
            "low": 0,
            "medium": 1,
            "high": 2,
            "critical": 3,
        }

        changed_keys = set()
        for item in diff_result.get("added", []):
            changed_keys.add(item["key"])
        for item in diff_result.get("removed", []):
            changed_keys.add(item["key"])
        for item in diff_result.get("modified", []):
            changed_keys.add(item["key"])

        for key in changed_keys:
            for pattern, rule in (
                self._impact_rules.items()
            ):
                if (
                    pattern in key
                    or pattern == key
                    or key.startswith(pattern)
                ):
                    sev = rule["severity"]
                    impacts.append({
                        "key": key,
                        "severity": sev,
                        "description": rule[
                            "description"
                        ],
                    })
                    if severity_order.get(
                        sev, 0,
                    ) > severity_order.get(
                        max_severity, 0,
                    ):
                        max_severity = sev

        return {
            "impacts": impacts,
            "max_severity": max_severity,
            "impact_count": len(impacts),
            "safe": len(impacts) == 0,
        }

    def detect_breaking(
        self,
        source: dict[str, Any],
        target: dict[str, Any],
        required_keys: list[str] | None = None,
    ) -> dict[str, Any]:
        """Kirilma degisiklikleri tespit eder.

        Args:
            source: Kaynak.
            target: Hedef.
            required_keys: Zorunlu anahtarlar.

        Returns:
            Kirilma analizi.
        """
        breaking = []
        diff_result = self.diff(source, target)

        # Silinen anahtarlar kirilma olabilir
        for item in diff_result["removed"]:
            breaking.append({
                "key": item["key"],
                "reason": "key_removed",
            })

        # Zorunlu anahtarlar
        if required_keys:
            for rk in required_keys:
                if rk in source and rk not in target:
                    if not any(
                        b["key"] == rk
                        for b in breaking
                    ):
                        breaking.append({
                            "key": rk,
                            "reason": "required_missing",
                        })

        # Tip degisiklikleri
        for item in diff_result["modified"]:
            old_type = type(
                item["old_value"],
            ).__name__
            new_type = type(
                item["new_value"],
            ).__name__
            if old_type != new_type:
                breaking.append({
                    "key": item["key"],
                    "reason": "type_changed",
                    "from_type": old_type,
                    "to_type": new_type,
                })

        return {
            "breaking_changes": breaking,
            "is_breaking": len(breaking) > 0,
            "count": len(breaking),
        }

    def get_diff_history(
        self,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Fark gecmisi getirir.

        Args:
            limit: Limit.

        Returns:
            Gecmis listesi.
        """
        return self._diffs[-limit:]

    @property
    def diff_count(self) -> int:
        """Fark sayisi."""
        return len(self._diffs)

    @property
    def migration_count(self) -> int:
        """Migrasyon sayisi."""
        return len(self._migrations)

    @property
    def impact_rule_count(self) -> int:
        """Etki kurali sayisi."""
        return len(self._impact_rules)
