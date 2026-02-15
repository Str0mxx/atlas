"""ATLAS Profil Oluşturucu modulu.

Bilgi toplama, çoklu kaynak birleştirme,
çatışma çözümü, tamlık puanlama, güncelleme takibi.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class ProfileBuilder:
    """Profil oluşturucu.

    Varlık profillerini oluşturur ve zenginleştirir.

    Attributes:
        _profiles: Profil verileri.
        _sources: Kaynak takibi.
    """

    def __init__(self) -> None:
        """Profil oluşturucuyu başlatır."""
        self._profiles: dict[
            str, dict[str, Any]
        ] = {}
        self._sources: dict[
            str, list[dict[str, Any]]
        ] = {}
        self._conflicts: list[
            dict[str, Any]
        ] = []
        self._stats = {
            "profiles_built": 0,
            "merges": 0,
            "conflicts_resolved": 0,
        }

        logger.info(
            "ProfileBuilder baslatildi",
        )

    def build_profile(
        self,
        entity_id: str,
        data: dict[str, Any],
        source: str = "manual",
    ) -> dict[str, Any]:
        """Profil oluşturur veya günceller.

        Args:
            entity_id: Varlık ID.
            data: Profil verileri.
            source: Veri kaynağı.

        Returns:
            Profil bilgisi.
        """
        is_new = entity_id not in self._profiles

        if is_new:
            self._profiles[entity_id] = {
                "entity_id": entity_id,
                "fields": {},
                "completeness": 0.0,
                "created_at": time.time(),
                "updated_at": time.time(),
            }
            self._stats["profiles_built"] += 1

        profile = self._profiles[entity_id]
        for k, v in data.items():
            profile["fields"][k] = v

        profile["updated_at"] = time.time()

        # Kaynak takibi
        if entity_id not in self._sources:
            self._sources[entity_id] = []
        self._sources[entity_id].append({
            "source": source,
            "fields": list(data.keys()),
            "timestamp": time.time(),
        })

        # Tamlık hesapla
        profile["completeness"] = (
            self._calc_completeness(entity_id)
        )

        return {
            "entity_id": entity_id,
            "is_new": is_new,
            "fields_updated": list(data.keys()),
            "completeness": profile[
                "completeness"
            ],
        }

    def merge_sources(
        self,
        entity_id: str,
        sources: list[dict[str, Any]],
        strategy: str = "latest",
    ) -> dict[str, Any]:
        """Çoklu kaynaktan birleştirir.

        Args:
            entity_id: Varlık ID.
            sources: Kaynak verileri.
            strategy: Birleştirme stratejisi.

        Returns:
            Birleştirme bilgisi.
        """
        if entity_id not in self._profiles:
            self._profiles[entity_id] = {
                "entity_id": entity_id,
                "fields": {},
                "completeness": 0.0,
                "created_at": time.time(),
                "updated_at": time.time(),
            }
            self._stats["profiles_built"] += 1

        merged_fields: dict[str, Any] = {}
        conflicts = []

        for src in sources:
            src_name = src.get("source", "unknown")
            src_data = src.get("data", {})

            for k, v in src_data.items():
                if k in merged_fields:
                    if merged_fields[k] != v:
                        conflicts.append({
                            "field": k,
                            "existing": merged_fields[
                                k
                            ],
                            "incoming": v,
                            "source": src_name,
                        })
                        if strategy == "latest":
                            merged_fields[k] = v
                else:
                    merged_fields[k] = v

        self._profiles[entity_id][
            "fields"
        ].update(merged_fields)
        self._profiles[entity_id][
            "updated_at"
        ] = time.time()
        self._stats["merges"] += 1

        if conflicts:
            self._conflicts.extend(conflicts)

        self._profiles[entity_id][
            "completeness"
        ] = self._calc_completeness(entity_id)

        return {
            "entity_id": entity_id,
            "fields_merged": len(merged_fields),
            "conflicts": len(conflicts),
            "strategy": strategy,
        }

    def resolve_conflict(
        self,
        entity_id: str,
        field: str,
        value: Any,
    ) -> dict[str, Any]:
        """Çatışma çözer.

        Args:
            entity_id: Varlık ID.
            field: Alan adı.
            value: Seçilen değer.

        Returns:
            Çözüm bilgisi.
        """
        p = self._profiles.get(entity_id)
        if not p:
            return {"error": "profile_not_found"}

        p["fields"][field] = value
        p["updated_at"] = time.time()
        self._stats["conflicts_resolved"] += 1

        return {
            "entity_id": entity_id,
            "field": field,
            "resolved": True,
        }

    def get_completeness(
        self,
        entity_id: str,
    ) -> dict[str, Any]:
        """Tamlık puanı getirir.

        Args:
            entity_id: Varlık ID.

        Returns:
            Tamlık bilgisi.
        """
        p = self._profiles.get(entity_id)
        if not p:
            return {"error": "profile_not_found"}

        expected = [
            "name", "email", "phone",
            "company", "role",
        ]
        present = [
            f for f in expected
            if f in p["fields"]
        ]
        missing = [
            f for f in expected
            if f not in p["fields"]
        ]

        return {
            "entity_id": entity_id,
            "completeness": p["completeness"],
            "present_fields": present,
            "missing_fields": missing,
            "total_fields": len(p["fields"]),
        }

    def get_profile(
        self,
        entity_id: str,
    ) -> dict[str, Any]:
        """Profil getirir.

        Args:
            entity_id: Varlık ID.

        Returns:
            Profil bilgisi.
        """
        p = self._profiles.get(entity_id)
        if not p:
            return {"error": "profile_not_found"}
        return dict(p)

    def get_update_history(
        self,
        entity_id: str,
    ) -> list[dict[str, Any]]:
        """Güncelleme geçmişi getirir.

        Args:
            entity_id: Varlık ID.

        Returns:
            Güncelleme listesi.
        """
        return list(
            self._sources.get(entity_id, []),
        )

    def _calc_completeness(
        self,
        entity_id: str,
    ) -> float:
        """Tamlık hesaplar.

        Args:
            entity_id: Varlık ID.

        Returns:
            Tamlık puanı (0-1).
        """
        p = self._profiles.get(entity_id)
        if not p:
            return 0.0

        expected = [
            "name", "email", "phone",
            "company", "role",
        ]
        present = sum(
            1 for f in expected
            if f in p["fields"]
        )
        return round(
            present / len(expected), 2,
        )

    @property
    def profile_count(self) -> int:
        """Profil sayısı."""
        return self._stats["profiles_built"]

    @property
    def merge_count(self) -> int:
        """Birleştirme sayısı."""
        return self._stats["merges"]
