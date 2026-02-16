"""ATLAS Deney Arşivi modülü.

Geçmiş deneyler, öğrenim veritabanı,
arama ve filtreleme, tekrarlama desteği,
bilgi çıkarma.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class ExperimentArchive:
    """Deney arşivi.

    Tamamlanmış deneyleri arşivler.

    Attributes:
        _archive: Arşiv kayıtları.
        _learnings: Öğrenim kayıtları.
    """

    def __init__(self) -> None:
        """Arşivi başlatır."""
        self._archive: dict[
            str, dict[str, Any]
        ] = {}
        self._learnings: list[
            dict[str, Any]
        ] = []
        self._counter = 0
        self._stats = {
            "experiments_archived": 0,
            "learnings_extracted": 0,
        }

        logger.info(
            "ExperimentArchive baslatildi",
        )

    def archive_experiment(
        self,
        experiment_id: str,
        name: str = "",
        winner: str = "",
        lift_pct: float = 0.0,
        duration_days: int = 0,
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        """Deney arşivler.

        Args:
            experiment_id: Deney kimliği.
            name: Deney adı.
            winner: Kazanan.
            lift_pct: Artış yüzdesi.
            duration_days: Süre (gün).
            tags: Etiketler.

        Returns:
            Arşivleme bilgisi.
        """
        tags = tags or []

        self._archive[experiment_id] = {
            "experiment_id": experiment_id,
            "name": name,
            "winner": winner,
            "lift_pct": lift_pct,
            "duration_days": duration_days,
            "tags": tags,
            "status": "archived",
            "timestamp": time.time(),
        }

        self._stats[
            "experiments_archived"
        ] += 1

        return {
            "experiment_id": experiment_id,
            "name": name,
            "archived": True,
        }

    def add_learning(
        self,
        experiment_id: str,
        learning: str,
        category: str = "general",
    ) -> dict[str, Any]:
        """Öğrenim ekler.

        Args:
            experiment_id: Deney kimliği.
            learning: Öğrenim.
            category: Kategori.

        Returns:
            Ekleme bilgisi.
        """
        self._counter += 1
        lid = f"lrn_{self._counter}"

        self._learnings.append({
            "learning_id": lid,
            "experiment_id": experiment_id,
            "learning": learning,
            "category": category,
            "timestamp": time.time(),
        })

        self._stats[
            "learnings_extracted"
        ] += 1

        return {
            "learning_id": lid,
            "added": True,
        }

    def search(
        self,
        query: str = "",
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        """Arama yapar.

        Args:
            query: Sorgu.
            tags: Etiketler.

        Returns:
            Arama bilgisi.
        """
        tags = tags or []
        results = []

        for eid, exp in (
            self._archive.items()
        ):
            match = True

            if query:
                name = exp.get(
                    "name", "",
                ).lower()
                if (
                    query.lower()
                    not in name
                ):
                    match = False

            if tags:
                exp_tags = exp.get(
                    "tags", [],
                )
                if not any(
                    t in exp_tags
                    for t in tags
                ):
                    match = False

            if match:
                results.append({
                    "experiment_id": eid,
                    "name": exp.get(
                        "name", "",
                    ),
                    "winner": exp.get(
                        "winner", "",
                    ),
                    "lift_pct": exp.get(
                        "lift_pct", 0,
                    ),
                })

        return {
            "results": results,
            "count": len(results),
            "searched": True,
        }

    def replicate(
        self,
        experiment_id: str,
        new_name: str = "",
    ) -> dict[str, Any]:
        """Tekrarlama yapar.

        Args:
            experiment_id: Deney kimliği.
            new_name: Yeni ad.

        Returns:
            Tekrarlama bilgisi.
        """
        original = self._archive.get(
            experiment_id,
        )
        if not original:
            return {
                "experiment_id": experiment_id,
                "found": False,
            }

        self._counter += 1
        new_id = f"rep_{self._counter}"

        return {
            "original_id": experiment_id,
            "new_id": new_id,
            "new_name": (
                new_name
                or f"Replication: "
                f"{original.get('name', '')}"
            ),
            "replicated": True,
        }

    def extract_knowledge(
        self,
        category: str = "",
    ) -> dict[str, Any]:
        """Bilgi çıkarır.

        Args:
            category: Kategori filtresi.

        Returns:
            Çıkarma bilgisi.
        """
        filtered = [
            l for l in self._learnings
            if not category
            or l.get("category") == category
        ]

        total_experiments = len(
            self._archive,
        )
        with_winners = sum(
            1
            for e in self._archive.values()
            if e.get("winner")
        )
        avg_lift = (
            round(
                sum(
                    e.get("lift_pct", 0)
                    for e in (
                        self._archive
                        .values()
                    )
                )
                / max(
                    total_experiments, 1,
                ),
                2,
            )
            if total_experiments
            else 0
        )

        return {
            "learnings": filtered,
            "learning_count": len(
                filtered,
            ),
            "total_experiments": (
                total_experiments
            ),
            "experiments_with_winners": (
                with_winners
            ),
            "avg_lift_pct": avg_lift,
            "extracted": True,
        }

    @property
    def archive_count(self) -> int:
        """Arşiv sayısı."""
        return self._stats[
            "experiments_archived"
        ]

    @property
    def learning_count(self) -> int:
        """Öğrenim sayısı."""
        return self._stats[
            "learnings_extracted"
        ]
