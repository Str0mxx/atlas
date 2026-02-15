"""ATLAS Benzerlik Analizcisi modulu.

Alan benzerligi, gorev benzerligi,
yapi benzerligi, baglam benzerligi, transfer potansiyeli.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class SimilarityAnalyzer:
    """Benzerlik analizcisi.

    Sistemler arasi benzerlikleri analiz eder.

    Attributes:
        _analyses: Analiz kayitlari.
        _stats: Istatistikler.
    """

    def __init__(
        self,
        min_threshold: float = 0.3,
    ) -> None:
        """Benzerlik analizcisini baslatir.

        Args:
            min_threshold: Minimum esik.
        """
        self._analyses: dict[
            str, dict[str, Any]
        ] = {}
        self._min_threshold = min_threshold
        self._stats = {
            "analyzed": 0,
        }

        logger.info(
            "SimilarityAnalyzer baslatildi",
        )

    def analyze_similarity(
        self,
        source: dict[str, Any],
        target: dict[str, Any],
    ) -> dict[str, Any]:
        """Benzerlik analizi yapar.

        Args:
            source: Kaynak sistem bilgisi.
            target: Hedef sistem bilgisi.

        Returns:
            Benzerlik sonucu.
        """
        source_id = source.get("system_id", "")
        target_id = target.get("system_id", "")

        # Boyut benzerlikleri
        domain_sim = self._domain_similarity(
            source, target,
        )
        task_sim = self._task_similarity(
            source, target,
        )
        structure_sim = (
            self._structure_similarity(
                source, target,
            )
        )
        context_sim = (
            self._context_similarity(
                source, target,
            )
        )

        # Agirlikli ortalama
        weights = {
            "domain": 0.3,
            "task": 0.3,
            "structure": 0.2,
            "context": 0.2,
        }

        overall = round(
            domain_sim * weights["domain"]
            + task_sim * weights["task"]
            + structure_sim
            * weights["structure"]
            + context_sim
            * weights["context"],
            3,
        )

        # Transfer potansiyeli
        if overall >= 0.7:
            potential = "high"
        elif overall >= 0.4:
            potential = "medium"
        else:
            potential = "low"

        key = f"{source_id}_{target_id}"

        result = {
            "source": source_id,
            "target": target_id,
            "overall_score": overall,
            "dimension_scores": {
                "domain": domain_sim,
                "task": task_sim,
                "structure": structure_sim,
                "context": context_sim,
            },
            "transfer_potential": potential,
            "above_threshold": (
                overall >= self._min_threshold
            ),
        }

        self._analyses[key] = result
        self._stats["analyzed"] += 1

        return result

    def _domain_similarity(
        self,
        source: dict[str, Any],
        target: dict[str, Any],
    ) -> float:
        """Alan benzerligi hesaplar.

        Args:
            source: Kaynak bilgisi.
            target: Hedef bilgisi.

        Returns:
            Benzerlik skoru (0-1).
        """
        s_domain = set(
            source.get("domains", []),
        )
        t_domain = set(
            target.get("domains", []),
        )

        if not s_domain and not t_domain:
            return 0.5

        union = s_domain | t_domain
        if not union:
            return 0.0

        overlap = s_domain & t_domain
        return round(
            len(overlap) / len(union), 3,
        )

    def _task_similarity(
        self,
        source: dict[str, Any],
        target: dict[str, Any],
    ) -> float:
        """Gorev benzerligi hesaplar.

        Args:
            source: Kaynak bilgisi.
            target: Hedef bilgisi.

        Returns:
            Benzerlik skoru (0-1).
        """
        s_tasks = set(
            source.get("task_types", []),
        )
        t_tasks = set(
            target.get("task_types", []),
        )

        if not s_tasks and not t_tasks:
            return 0.5

        union = s_tasks | t_tasks
        if not union:
            return 0.0

        overlap = s_tasks & t_tasks
        return round(
            len(overlap) / len(union), 3,
        )

    def _structure_similarity(
        self,
        source: dict[str, Any],
        target: dict[str, Any],
    ) -> float:
        """Yapi benzerligi hesaplar.

        Args:
            source: Kaynak bilgisi.
            target: Hedef bilgisi.

        Returns:
            Benzerlik skoru (0-1).
        """
        s_comps = set(
            source.get("components", []),
        )
        t_comps = set(
            target.get("components", []),
        )

        if not s_comps and not t_comps:
            return 0.5

        union = s_comps | t_comps
        if not union:
            return 0.0

        overlap = s_comps & t_comps
        return round(
            len(overlap) / len(union), 3,
        )

    def _context_similarity(
        self,
        source: dict[str, Any],
        target: dict[str, Any],
    ) -> float:
        """Baglam benzerligi hesaplar.

        Args:
            source: Kaynak bilgisi.
            target: Hedef bilgisi.

        Returns:
            Benzerlik skoru (0-1).
        """
        s_ctx = set(
            source.get("context_tags", []),
        )
        t_ctx = set(
            target.get("context_tags", []),
        )

        if not s_ctx and not t_ctx:
            return 0.5

        union = s_ctx | t_ctx
        if not union:
            return 0.0

        overlap = s_ctx & t_ctx
        return round(
            len(overlap) / len(union), 3,
        )

    def find_similar_systems(
        self,
        source: dict[str, Any],
        candidates: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Benzer sistemleri bulur.

        Args:
            source: Kaynak sistem bilgisi.
            candidates: Aday sistemler.

        Returns:
            Benzerlik sonuclari (esik ustu).
        """
        results = []
        for cand in candidates:
            sim = self.analyze_similarity(
                source, cand,
            )
            if sim["above_threshold"]:
                results.append(sim)

        results.sort(
            key=lambda x: x["overall_score"],
            reverse=True,
        )
        return results

    def get_analysis(
        self,
        source_id: str,
        target_id: str,
    ) -> dict[str, Any]:
        """Analiz sonucu getirir.

        Args:
            source_id: Kaynak ID.
            target_id: Hedef ID.

        Returns:
            Analiz bilgisi.
        """
        key = f"{source_id}_{target_id}"
        a = self._analyses.get(key)
        if not a:
            return {
                "error": "analysis_not_found",
            }
        return dict(a)

    @property
    def analysis_count(self) -> int:
        """Analiz sayisi."""
        return self._stats["analyzed"]
