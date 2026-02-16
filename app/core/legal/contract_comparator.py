"""ATLAS Sözleşme Karşılaştırıcı modülü.

Yan yana karşılaştırma, fark tespiti,
versiyon takibi, değişiklik işaretleme,
etki analizi.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class ContractComparator:
    """Sözleşme karşılaştırıcı.

    Sözleşmeleri karşılaştırır.

    Attributes:
        _comparisons: Karşılaştırma kayıtları.
        _versions: Versiyon kayıtları.
    """

    def __init__(self) -> None:
        """Karşılaştırıcıyı başlatır."""
        self._comparisons: list[
            dict[str, Any]
        ] = []
        self._versions: dict[
            str, list[dict[str, Any]]
        ] = {}
        self._counter = 0
        self._stats = {
            "comparisons_done": 0,
            "differences_found": 0,
            "versions_tracked": 0,
        }

        logger.info(
            "ContractComparator "
            "baslatildi",
        )

    def compare_side_by_side(
        self,
        contract_a_id: str,
        contract_b_id: str,
        clauses_a: list[dict[str, Any]]
        | None = None,
        clauses_b: list[dict[str, Any]]
        | None = None,
    ) -> dict[str, Any]:
        """Yan yana karşılaştırır.

        Args:
            contract_a_id: Sözleşme A ID.
            contract_b_id: Sözleşme B ID.
            clauses_a: A maddeleri.
            clauses_b: B maddeleri.

        Returns:
            Karşılaştırma bilgisi.
        """
        self._counter += 1
        cmp_id = f"cmp_{self._counter}"

        clauses_a = clauses_a or []
        clauses_b = clauses_b or []

        types_a = {
            c.get("type", "")
            for c in clauses_a
        }
        types_b = {
            c.get("type", "")
            for c in clauses_b
        }

        common = types_a & types_b
        only_a = types_a - types_b
        only_b = types_b - types_a

        comparison = {
            "comparison_id": cmp_id,
            "contract_a": contract_a_id,
            "contract_b": contract_b_id,
            "common_types": list(common),
            "only_in_a": list(only_a),
            "only_in_b": list(only_b),
            "timestamp": time.time(),
        }
        self._comparisons.append(
            comparison,
        )
        self._stats[
            "comparisons_done"
        ] += 1

        return {
            "comparison_id": cmp_id,
            "common_count": len(common),
            "only_a_count": len(only_a),
            "only_b_count": len(only_b),
            "compared": True,
        }

    def detect_differences(
        self,
        text_a: str,
        text_b: str,
    ) -> dict[str, Any]:
        """Fark tespit eder.

        Args:
            text_a: Metin A.
            text_b: Metin B.

        Returns:
            Fark bilgisi.
        """
        words_a = set(text_a.lower().split())
        words_b = set(text_b.lower().split())

        added = words_b - words_a
        removed = words_a - words_b
        common = words_a & words_b

        similarity = round(
            len(common)
            / max(
                len(words_a | words_b), 1,
            ) * 100, 1,
        )

        self._stats[
            "differences_found"
        ] += len(added) + len(removed)

        return {
            "added_words": len(added),
            "removed_words": len(removed),
            "common_words": len(common),
            "similarity_pct": similarity,
            "significant_change": (
                similarity < 80
            ),
        }

    def track_version(
        self,
        contract_id: str,
        version: str,
        changes: list[str]
        | None = None,
        author: str = "",
    ) -> dict[str, Any]:
        """Versiyon takip eder.

        Args:
            contract_id: Sözleşme ID.
            version: Versiyon.
            changes: Değişiklikler.
            author: Yazar.

        Returns:
            Versiyon bilgisi.
        """
        changes = changes or []

        entry = {
            "version": version,
            "changes": changes,
            "author": author,
            "change_count": len(changes),
            "timestamp": time.time(),
        }

        if (
            contract_id
            not in self._versions
        ):
            self._versions[
                contract_id
            ] = []
        self._versions[
            contract_id
        ].append(entry)
        self._stats[
            "versions_tracked"
        ] += 1

        return {
            "contract_id": contract_id,
            "version": version,
            "change_count": len(changes),
            "tracked": True,
        }

    def highlight_changes(
        self,
        contract_id: str,
        old_version: str = "",
        new_version: str = "",
    ) -> dict[str, Any]:
        """Değişiklikleri işaretler.

        Args:
            contract_id: Sözleşme ID.
            old_version: Eski versiyon.
            new_version: Yeni versiyon.

        Returns:
            İşaretleme bilgisi.
        """
        versions = self._versions.get(
            contract_id, [],
        )

        old_entry = None
        new_entry = None
        for v in versions:
            if v["version"] == old_version:
                old_entry = v
            if v["version"] == new_version:
                new_entry = v

        if not new_entry:
            return {
                "contract_id": contract_id,
                "highlighted": False,
            }

        changes = new_entry.get(
            "changes", [],
        )

        return {
            "contract_id": contract_id,
            "old_version": old_version,
            "new_version": new_version,
            "changes": changes,
            "change_count": len(changes),
            "highlighted": True,
        }

    def analyze_impact(
        self,
        changes: list[str]
        | None = None,
    ) -> dict[str, Any]:
        """Etki analizi yapar.

        Args:
            changes: Değişiklikler.

        Returns:
            Etki bilgisi.
        """
        changes = changes or []

        high_impact_keywords = [
            "liability", "termination",
            "payment", "penalty",
            "indemnification",
        ]

        high_impact = []
        low_impact = []

        for change in changes:
            lower = change.lower()
            if any(
                k in lower
                for k in high_impact_keywords
            ):
                high_impact.append(change)
            else:
                low_impact.append(change)

        impact_level = (
            "high" if high_impact
            else "medium" if changes
            else "none"
        )

        return {
            "total_changes": len(changes),
            "high_impact": high_impact,
            "low_impact": low_impact,
            "high_impact_count": len(
                high_impact,
            ),
            "impact_level": impact_level,
        }

    def get_versions(
        self,
        contract_id: str,
    ) -> list[dict[str, Any]]:
        """Versiyonları listeler."""
        return self._versions.get(
            contract_id, [],
        )

    @property
    def comparison_count(self) -> int:
        """Karşılaştırma sayısı."""
        return self._stats[
            "comparisons_done"
        ]

    @property
    def version_count(self) -> int:
        """Versiyon sayısı."""
        return self._stats[
            "versions_tracked"
        ]
