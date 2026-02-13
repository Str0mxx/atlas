"""ATLAS Bilgi Ogrenici modulu.

Basarili fix'lerden ogrenme, kalip dokumantasyonu,
en iyi pratik guncelleme, agentler arasi paylasim
ve kurumsal bilgi birikimi.
"""

import logging
from typing import Any

from app.models.evolution import (
    CodeChange,
    ExperimentResult,
    ExperimentStatus,
    LearnedPattern,
)

logger = logging.getLogger(__name__)


class KnowledgeLearner:
    """Bilgi ogrenme sistemi.

    Basarili degisikliklerden kaliplar ogrenir,
    en iyi pratikleri gunceller ve agentler arasi paylasirir.

    Attributes:
        _patterns: Ogrenilmis kaliplar.
        _best_practices: En iyi pratikler.
        _shared_knowledge: Paylasilan bilgi.
    """

    def __init__(self) -> None:
        """Bilgi ogreniciyi baslatir."""
        self._patterns: list[LearnedPattern] = []
        self._best_practices: dict[str, str] = {}
        self._shared_knowledge: dict[str, list[str]] = {}

        logger.info("KnowledgeLearner baslatildi")

    def learn_from_fix(self, change: CodeChange, experiment: ExperimentResult) -> LearnedPattern | None:
        """Basarili fix'ten ogrenir.

        Args:
            change: Uygulanan degisiklik.
            experiment: Deney sonucu.

        Returns:
            LearnedPattern veya None (basarisiz ise).
        """
        if experiment.status != ExperimentStatus.PASSED:
            return None

        # Mevcut kalip var mi?
        existing = self._find_similar_pattern(change.change_type, change.file_path)
        if existing:
            existing.success_count += 1
            existing.applicability_score = min(
                existing.applicability_score + 0.1, 1.0
            )
            return existing

        pattern = LearnedPattern(
            pattern_name=f"{change.change_type}_{change.file_path.split('/')[-1]}",
            category=change.change_type,
            description=change.description,
            solution=change.diff,
            success_count=1,
            applicability_score=0.5,
            source_components=[change.file_path],
        )

        self._patterns.append(pattern)
        logger.info("Yeni kalip ogrenildi: %s", pattern.pattern_name)
        return pattern

    def learn_from_experiment(self, experiment: ExperimentResult) -> LearnedPattern | None:
        """Deney sonucundan ogrenir.

        Args:
            experiment: Deney sonucu.

        Returns:
            LearnedPattern veya None.
        """
        if experiment.status == ExperimentStatus.INCONCLUSIVE:
            return None

        category = "success" if experiment.status == ExperimentStatus.PASSED else "failure"

        pattern = LearnedPattern(
            pattern_name=f"exp_{experiment.experiment_name}",
            category=category,
            description=f"Deney: {experiment.experiment_name} -> {experiment.status.value}",
            solution=f"Improvement: {experiment.improvement_pct:.1f}%",
            success_count=1 if experiment.status == ExperimentStatus.PASSED else 0,
            applicability_score=experiment.confidence,
        )

        self._patterns.append(pattern)
        return pattern

    def document_pattern(self, name: str, category: str, description: str, solution: str) -> LearnedPattern:
        """Kalip dokumante eder.

        Args:
            name: Kalip adi.
            category: Kategori.
            description: Aciklama.
            solution: Cozum.

        Returns:
            LearnedPattern nesnesi.
        """
        pattern = LearnedPattern(
            pattern_name=name,
            category=category,
            description=description,
            solution=solution,
            success_count=0,
            applicability_score=0.3,
        )

        self._patterns.append(pattern)
        logger.info("Kalip dokumante edildi: %s", name)
        return pattern

    def update_best_practice(self, category: str, practice: str) -> None:
        """En iyi pratigi gunceller.

        Args:
            category: Kategori.
            practice: Pratik aciklamasi.
        """
        self._best_practices[category] = practice
        logger.info("Best practice guncellendi: %s", category)

    def get_best_practice(self, category: str) -> str:
        """En iyi pratigi getirir.

        Args:
            category: Kategori.

        Returns:
            Pratik aciklamasi.
        """
        return self._best_practices.get(category, "")

    def share_with_agent(self, agent_name: str, knowledge: str) -> None:
        """Bilgiyi agent ile paylasirir.

        Args:
            agent_name: Agent adi.
            knowledge: Paylasilan bilgi.
        """
        shared = self._shared_knowledge.setdefault(agent_name, [])
        shared.append(knowledge)

    def get_agent_knowledge(self, agent_name: str) -> list[str]:
        """Agent'in bilgilerini getirir.

        Args:
            agent_name: Agent adi.

        Returns:
            Bilgi listesi.
        """
        return list(self._shared_knowledge.get(agent_name, []))

    def find_patterns(self, category: str = "", min_score: float = 0.0) -> list[LearnedPattern]:
        """Kalip arar.

        Args:
            category: Kategori filtresi.
            min_score: Minimum uygulanabilirlik puani.

        Returns:
            LearnedPattern listesi.
        """
        results = self._patterns

        if category:
            results = [p for p in results if p.category == category]
        if min_score > 0:
            results = [p for p in results if p.applicability_score >= min_score]

        results.sort(key=lambda p: p.applicability_score, reverse=True)
        return results

    def get_statistics(self) -> dict[str, Any]:
        """Ogrenme istatistiklerini getirir.

        Returns:
            Istatistik sozlugu.
        """
        categories: dict[str, int] = {}
        for p in self._patterns:
            categories[p.category] = categories.get(p.category, 0) + 1

        total_successes = sum(p.success_count for p in self._patterns)
        avg_score = (
            sum(p.applicability_score for p in self._patterns) / len(self._patterns)
            if self._patterns else 0.0
        )

        return {
            "total_patterns": len(self._patterns),
            "total_successes": total_successes,
            "avg_applicability": round(avg_score, 3),
            "categories": categories,
            "best_practices": len(self._best_practices),
            "shared_agents": len(self._shared_knowledge),
        }

    def build_knowledge_base(self) -> dict[str, Any]:
        """Kurumsal bilgi tabanini olusturur.

        Returns:
            Bilgi tabani.
        """
        return {
            "patterns": [
                {
                    "name": p.pattern_name,
                    "category": p.category,
                    "description": p.description,
                    "solution": p.solution,
                    "success_count": p.success_count,
                    "score": p.applicability_score,
                }
                for p in sorted(self._patterns, key=lambda p: p.applicability_score, reverse=True)
            ],
            "best_practices": dict(self._best_practices),
            "statistics": self.get_statistics(),
        }

    def _find_similar_pattern(self, category: str, component: str) -> LearnedPattern | None:
        """Benzer kalip arar."""
        for pattern in self._patterns:
            if pattern.category == category and component in pattern.source_components:
                return pattern
        return None

    @property
    def pattern_count(self) -> int:
        """Kalip sayisi."""
        return len(self._patterns)

    @property
    def practice_count(self) -> int:
        """Pratik sayisi."""
        return len(self._best_practices)

    @property
    def patterns(self) -> list[LearnedPattern]:
        """Tum kaliplar."""
        return list(self._patterns)
