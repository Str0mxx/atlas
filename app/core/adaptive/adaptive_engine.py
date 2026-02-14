"""ATLAS Adaptif Motor modulu.

Tam ogrenme pipeline'i, surekli
iyilestirme, coklu strateji ogrenme,
performans izleme ve ogrenme hizi
kontrolu.
"""

import logging
import time
from typing import Any

from app.models.adaptive import (
    AdaptiveSnapshot,
    ExperienceType,
    OutcomeType,
)

from app.core.adaptive.experience_collector import ExperienceCollector
from app.core.adaptive.pattern_miner import PatternMiner
from app.core.adaptive.strategy_evolver import StrategyEvolver
from app.core.adaptive.knowledge_distiller import KnowledgeDistiller
from app.core.adaptive.skill_optimizer import SkillOptimizer
from app.core.adaptive.feedback_processor import FeedbackProcessor
from app.core.adaptive.transfer_learner import TransferLearner
from app.core.adaptive.curriculum_manager import CurriculumManager

logger = logging.getLogger(__name__)


class AdaptiveEngine:
    """Adaptif motor orkestratoru.

    Tum ogrenme bilesenlerini koordine
    eder ve surekli iyilestirme saglar.

    Attributes:
        experiences: Deneyim toplayici.
        patterns: Oruntu madencisi.
        strategies: Strateji evrimcisi.
        knowledge: Bilgi damitici.
        skills: Yetenek optimizasyonu.
        feedback: Geri bildirim isleyici.
        transfer: Transfer ogrenici.
        curriculum: Mufredat yoneticisi.
    """

    def __init__(
        self,
        learning_rate: float = 0.1,
        exploration_rate: float = 0.2,
    ) -> None:
        """Adaptif motoru baslatir.

        Args:
            learning_rate: Ogrenme hizi.
            exploration_rate: Kesif orani.
        """
        self.experiences = ExperienceCollector()
        self.patterns = PatternMiner()
        self.strategies = StrategyEvolver()
        self.knowledge = KnowledgeDistiller()
        self.skills = SkillOptimizer()
        self.feedback = FeedbackProcessor()
        self.transfer = TransferLearner()
        self.curriculum = CurriculumManager()

        self._learning_rate = max(0.01, min(1.0, learning_rate))
        self._exploration_rate = max(0.0, min(1.0, exploration_rate))
        self._cycles: int = 0
        self._start_time = time.time()
        self._improvements: list[dict[str, Any]] = []

        logger.info(
            "AdaptiveEngine baslatildi "
            "(lr=%.3f, explore=%.2f)",
            self._learning_rate, self._exploration_rate,
        )

    def learn_from_experience(
        self,
        action: str,
        outcome: OutcomeType,
        reward: float = 0.0,
        context: dict[str, Any] | None = None,
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        """Deneyimden ogrenir.

        Args:
            action: Aksiyon.
            outcome: Sonuc.
            reward: Odul.
            context: Baglam.
            tags: Etiketler.

        Returns:
            Ogrenme sonucu.
        """
        # 1. Deneyim kaydet
        exp = self.experiences.record(
            action=action,
            outcome=outcome,
            reward=reward,
            context=context,
            tags=tags,
        )

        result: dict[str, Any] = {
            "experience_id": exp.experience_id,
            "patterns_found": 0,
            "rules_created": 0,
        }

        # 2. Periyodik oruntu madenciligi
        if self.experiences.total_count % 10 == 0:
            new_patterns = self.patterns.mine_success_patterns(
                self.experiences._experiences,
            )
            result["patterns_found"] = len(new_patterns)

        # 3. Periyodik bilgi damitma
        if self.experiences.total_count % 20 == 0:
            new_rules = self.knowledge.extract_generalizations(
                self.experiences._experiences,
            )
            result["rules_created"] = len(new_rules)

        self._cycles += 1
        return result

    def process_feedback(
        self,
        source: str,
        content: str,
        rating: float = 0.0,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Geri bildirimi isler ve ogrenir.

        Args:
            source: Kaynak.
            content: Icerik.
            rating: Puan.
            context: Baglam.

        Returns:
            Isleme sonucu.
        """
        fb = self.feedback.process_explicit(
            source, content, rating, context,
        )

        # Deneyim olarak da kaydet
        outcome = OutcomeType.SUCCESS if rating > 0 else (
            OutcomeType.FAILURE if rating < 0
            else OutcomeType.UNKNOWN
        )
        self.experiences.record(
            action=f"feedback:{content[:30]}",
            experience_type=ExperienceType.FEEDBACK,
            outcome=outcome,
            reward=rating,
            context=context,
        )

        return fb

    def run_improvement_cycle(self) -> dict[str, Any]:
        """Iyilestirme dongusu calistirir.

        Returns:
            Dongu sonucu.
        """
        result: dict[str, Any] = {
            "cycle": self._cycles,
            "actions": [],
        }

        exps = self.experiences._experiences

        # 1. Oruntuler
        success_patterns = self.patterns.mine_success_patterns(exps)
        failure_patterns = self.patterns.mine_failure_patterns(exps)
        result["actions"].append({
            "step": "pattern_mining",
            "success_patterns": len(success_patterns),
            "failure_patterns": len(failure_patterns),
        })

        # 2. Trendler
        trends = self.patterns.identify_trends(exps)
        result["actions"].append({
            "step": "trend_analysis",
            "trends_found": len(trends),
        })

        # 3. Bilgi damitma
        rules = self.knowledge.extract_generalizations(exps)
        result["actions"].append({
            "step": "knowledge_distillation",
            "rules_created": len(rules),
        })

        # 4. Eski bilgi budama
        pruned = self.knowledge.prune_outdated(0.3)
        result["actions"].append({
            "step": "knowledge_pruning",
            "pruned": pruned,
        })

        # 5. Darbogazlar
        bottlenecks = self.skills.identify_bottlenecks()
        result["actions"].append({
            "step": "bottleneck_detection",
            "bottlenecks": len(bottlenecks),
        })

        self._cycles += 1
        self._improvements.append(result)
        return result

    def get_learning_summary(self) -> dict[str, Any]:
        """Ogrenme ozeti getirir.

        Returns:
            Ozet bilgisi.
        """
        return {
            "total_experiences": self.experiences.total_count,
            "success_rate": self.experiences.get_success_rate(),
            "patterns_discovered": self.patterns.pattern_count,
            "knowledge_rules": self.knowledge.rule_count,
            "active_strategies": self.strategies.active_count,
            "skills_tracked": self.skills.skill_count,
            "feedback_received": self.feedback.feedback_count,
            "domains_registered": self.transfer.domain_count,
            "topics_in_curriculum": self.curriculum.topic_count,
            "learning_cycles": self._cycles,
            "learning_rate": self._learning_rate,
            "exploration_rate": self._exploration_rate,
        }

    def adjust_learning_rate(
        self,
        new_rate: float,
    ) -> float:
        """Ogrenme hizini ayarlar.

        Args:
            new_rate: Yeni hiz.

        Returns:
            Ayarlanan hiz.
        """
        self._learning_rate = max(0.01, min(1.0, new_rate))
        return self._learning_rate

    def adjust_exploration_rate(
        self,
        new_rate: float,
    ) -> float:
        """Kesif oranini ayarlar.

        Args:
            new_rate: Yeni oran.

        Returns:
            Ayarlanan oran.
        """
        self._exploration_rate = max(0.0, min(1.0, new_rate))
        return self._exploration_rate

    def get_snapshot(self) -> AdaptiveSnapshot:
        """Adaptif ogrenme goruntusunu getirir.

        Returns:
            Goruntusu.
        """
        return AdaptiveSnapshot(
            total_experiences=self.experiences.total_count,
            patterns_discovered=self.patterns.pattern_count,
            active_strategies=self.strategies.active_count,
            knowledge_rules=self.knowledge.rule_count,
            skills_tracked=self.skills.skill_count,
            feedback_processed=self.feedback.feedback_count,
            transfer_count=self.transfer.transfer_count,
            avg_learning_rate=self._learning_rate,
        )

    @property
    def cycle_count(self) -> int:
        """Dongu sayisi."""
        return self._cycles

    @property
    def learning_rate(self) -> float:
        """Ogrenme hizi."""
        return self._learning_rate

    @property
    def exploration_rate(self) -> float:
        """Kesif orani."""
        return self._exploration_rate

    @property
    def improvement_count(self) -> int:
        """Iyilestirme sayisi."""
        return len(self._improvements)
