"""ATLAS Kural Deposu modulu.

Kural saklama, kategorileme,
yetki alanı eşleme, versiyon kontrolü, aktivasyon.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class RuleRepository:
    """Kural deposu.

    Kuralları saklar ve yönetir.

    Attributes:
        _rules: Kural kayıtları.
        _versions: Versiyon geçmişi.
    """

    def __init__(self) -> None:
        """Depoyu başlatır."""
        self._rules: dict[
            str, dict[str, Any]
        ] = {}
        self._versions: dict[
            str, list[dict[str, Any]]
        ] = {}
        self._counter = 0
        self._stats = {
            "created": 0,
            "updated": 0,
        }

        logger.info(
            "RuleRepository baslatildi",
        )

    def add_rule(
        self,
        name: str,
        category: str = "operational",
        description: str = "",
        severity: str = "medium",
        conditions: dict[str, Any] | None = None,
        jurisdiction: str = "global",
    ) -> dict[str, Any]:
        """Kural ekler.

        Args:
            name: Kural adı.
            category: Kategori.
            description: Açıklama.
            severity: Şiddet.
            conditions: Koşullar.
            jurisdiction: Yetki alanı.

        Returns:
            Ekleme bilgisi.
        """
        self._counter += 1
        rid = f"rule_{self._counter}"

        rule = {
            "rule_id": rid,
            "name": name,
            "category": category,
            "description": description,
            "severity": severity,
            "conditions": conditions or {},
            "jurisdiction": jurisdiction,
            "active": True,
            "version": 1,
            "created_at": time.time(),
            "updated_at": time.time(),
        }
        self._rules[rid] = rule
        self._versions[rid] = [dict(rule)]
        self._stats["created"] += 1

        return {
            "rule_id": rid,
            "name": name,
            "category": category,
            "created": True,
        }

    def get_rule(
        self,
        rule_id: str,
    ) -> dict[str, Any]:
        """Kural getirir.

        Args:
            rule_id: Kural ID.

        Returns:
            Kural bilgisi.
        """
        r = self._rules.get(rule_id)
        if not r:
            return {"error": "rule_not_found"}
        return dict(r)

    def update_rule(
        self,
        rule_id: str,
        updates: dict[str, Any],
    ) -> dict[str, Any]:
        """Kural günceller.

        Args:
            rule_id: Kural ID.
            updates: Güncellemeler.

        Returns:
            Güncelleme bilgisi.
        """
        r = self._rules.get(rule_id)
        if not r:
            return {"error": "rule_not_found"}

        for k, v in updates.items():
            if k not in (
                "rule_id", "created_at",
            ):
                r[k] = v

        r["version"] += 1
        r["updated_at"] = time.time()
        self._versions[rule_id].append(dict(r))
        self._stats["updated"] += 1

        return {
            "rule_id": rule_id,
            "version": r["version"],
            "updated": True,
        }

    def activate_rule(
        self,
        rule_id: str,
    ) -> dict[str, Any]:
        """Kural aktifleştirir.

        Args:
            rule_id: Kural ID.

        Returns:
            Aktivasyon bilgisi.
        """
        r = self._rules.get(rule_id)
        if not r:
            return {"error": "rule_not_found"}
        r["active"] = True
        r["updated_at"] = time.time()
        return {
            "rule_id": rule_id,
            "active": True,
        }

    def deactivate_rule(
        self,
        rule_id: str,
    ) -> dict[str, Any]:
        """Kural deaktifleştirir.

        Args:
            rule_id: Kural ID.

        Returns:
            Deaktivasyon bilgisi.
        """
        r = self._rules.get(rule_id)
        if not r:
            return {"error": "rule_not_found"}
        r["active"] = False
        r["updated_at"] = time.time()
        return {
            "rule_id": rule_id,
            "active": False,
        }

    def list_rules(
        self,
        category: str | None = None,
        active_only: bool = True,
        jurisdiction: str | None = None,
    ) -> list[dict[str, Any]]:
        """Kuralları listeler.

        Args:
            category: Kategori filtresi.
            active_only: Sadece aktif.
            jurisdiction: Yetki alanı filtresi.

        Returns:
            Kural listesi.
        """
        results = []
        for r in self._rules.values():
            if active_only and not r["active"]:
                continue
            if category and (
                r["category"] != category
            ):
                continue
            if jurisdiction and (
                r["jurisdiction"] != jurisdiction
            ):
                continue
            results.append({
                "rule_id": r["rule_id"],
                "name": r["name"],
                "category": r["category"],
                "severity": r["severity"],
                "active": r["active"],
            })
        return results

    def get_version_history(
        self,
        rule_id: str,
    ) -> list[dict[str, Any]]:
        """Versiyon geçmişi getirir.

        Args:
            rule_id: Kural ID.

        Returns:
            Versiyon listesi.
        """
        return list(
            self._versions.get(rule_id, []),
        )

    def get_by_jurisdiction(
        self,
        jurisdiction: str,
    ) -> list[dict[str, Any]]:
        """Yetki alanına göre getirir.

        Args:
            jurisdiction: Yetki alanı.

        Returns:
            Kural listesi.
        """
        return self.list_rules(
            jurisdiction=jurisdiction,
        )

    @property
    def rule_count(self) -> int:
        """Kural sayısı."""
        return self._stats["created"]

    @property
    def active_rule_count(self) -> int:
        """Aktif kural sayısı."""
        return sum(
            1
            for r in self._rules.values()
            if r["active"]
        )
