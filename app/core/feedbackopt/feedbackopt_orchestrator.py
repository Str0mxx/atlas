"""ATLAS Geri Bildirim Optimizasyon Orkestratörü.

Tam optimizasyon pipeline,
Collect → Correlate → Rank → Tune → Measure → Improve,
öz-evrim yakıtı, analitik.
"""

import logging
import time
from typing import Any

from app.core.feedbackopt.auto_tuner import (
    AutoTuner,
)
from app.core.feedbackopt.continuous_improver import (
    ContinuousImprover,
)
from app.core.feedbackopt.experiment_designer import (
    FeedbackExperimentDesigner,
)
from app.core.feedbackopt.impact_measurer import (
    ImpactMeasurer,
)
from app.core.feedbackopt.learning_synthesizer import (
    LearningSynthesizer,
)
from app.core.feedbackopt.outcome_correlator import (
    OutcomeCorrelator,
)
from app.core.feedbackopt.strategy_ranker import (
    StrategyRanker,
)
from app.core.feedbackopt.user_satisfaction_tracker import (
    UserSatisfactionTracker,
)

logger = logging.getLogger(__name__)


class FeedbackOptOrchestrator:
    """Geri bildirim optimizasyon orkestratörü.

    Tüm geri bildirim bileşenlerini
    koordine eder.

    Attributes:
        satisfaction: Memnuniyet takipçisi.
        correlator: Sonuç ilişkilendirici.
        ranker: Strateji sıralayıcı.
        tuner: Otomatik ayarlayıcı.
        experiments: Deney tasarımcısı.
        impact: Etki ölçer.
        improver: Sürekli iyileştirici.
        synthesizer: Öğrenme sentezleyici.
    """

    def __init__(self) -> None:
        """Orkestratörü başlatır."""
        self.satisfaction = (
            UserSatisfactionTracker()
        )
        self.correlator = (
            OutcomeCorrelator()
        )
        self.ranker = StrategyRanker()
        self.tuner = AutoTuner()
        self.experiments = (
            FeedbackExperimentDesigner()
        )
        self.impact = ImpactMeasurer()
        self.improver = (
            ContinuousImprover()
        )
        self.synthesizer = (
            LearningSynthesizer()
        )
        self._stats = {
            "pipelines_run": 0,
            "optimizations": 0,
        }

        logger.info(
            "FeedbackOptOrchestrator "
            "baslatildi",
        )

    def run_optimization_pipeline(
        self,
        user_id: str,
        score: float,
        action_type: str = "default",
        strategy_id: str = "",
    ) -> dict[str, Any]:
        """Tam optimizasyon pipeline çalıştırır.

        Args:
            user_id: Kullanıcı ID.
            score: Memnuniyet puanı.
            action_type: Eylem tipi.
            strategy_id: Strateji ID.

        Returns:
            Pipeline bilgisi.
        """
        # 1. Collect
        sat = self.satisfaction.score_satisfaction(
            user_id, score,
        )

        # 2. Correlate
        self.correlator.link_action_outcome(
            action_id=f"act_{user_id}",
            action_type=action_type,
            outcome_value=score,
        )

        # 3. Rank
        if strategy_id:
            self.ranker.score_strategy(
                strategy_id,
                success_rate=score,
                efficiency=score * 0.9,
                user_satisfaction=score,
            )

        # 4. Extract insight
        self.synthesizer.extract_insight(
            source="pipeline",
            data={
                "score": score,
                "action": action_type,
            },
        )

        self._stats["pipelines_run"] += 1

        return {
            "user_id": user_id,
            "satisfaction_level": sat[
                "level"
            ],
            "score": score,
            "action_type": action_type,
            "pipeline_complete": True,
        }

    def collect_correlate_rank(
        self,
        feedbacks: list[dict[str, Any]]
        | None = None,
    ) -> dict[str, Any]:
        """Collect → Correlate → Rank.

        Args:
            feedbacks: Geri bildirimler.

        Returns:
            Sonuç bilgisi.
        """
        feedbacks = feedbacks or []

        for fb in feedbacks:
            user_id = fb.get(
                "user_id", "unknown",
            )
            score = fb.get("score", 50.0)
            action = fb.get(
                "action_type", "default",
            )

            self.satisfaction.score_satisfaction(
                user_id, score,
            )
            self.correlator.link_action_outcome(
                action_id=f"act_{user_id}",
                action_type=action,
                outcome_value=score,
            )

        ranking = (
            self.ranker.rank_performance()
        )

        return {
            "feedbacks_processed": len(
                feedbacks,
            ),
            "strategies_ranked": (
                ranking.get(
                    "total_strategies", 0,
                )
            ),
            "complete": True,
        }

    def fuel_self_evolution(
        self,
    ) -> dict[str, Any]:
        """Öz-evrim yakıtı sağlar.

        Returns:
            Evrim bilgisi.
        """
        patterns = (
            self.correlator.detect_pattern()
        )
        ranking = (
            self.ranker.rank_performance()
        )

        insights = (
            self.synthesizer.insight_count
        )
        knowledge = (
            self.synthesizer.knowledge_count
        )

        self._stats["optimizations"] += 1

        return {
            "patterns_found": patterns.get(
                "pattern_count", 0,
            ),
            "strategies_ranked": (
                ranking.get(
                    "total_strategies", 0,
                )
            ),
            "insights": insights,
            "knowledge_items": knowledge,
            "evolution_fuel": True,
        }

    def get_analytics(
        self,
    ) -> dict[str, Any]:
        """Analitik döndürür.

        Returns:
            Analitik bilgisi.
        """
        return {
            "pipelines_run": self._stats[
                "pipelines_run"
            ],
            "optimizations": self._stats[
                "optimizations"
            ],
            "feedbacks": (
                self.satisfaction
                .feedback_count
            ),
            "nps_responses": (
                self.satisfaction.nps_count
            ),
            "correlations": (
                self.correlator
                .correlation_count
            ),
            "patterns": (
                self.correlator
                .pattern_count
            ),
            "strategies": (
                self.ranker.strategy_count
            ),
            "rankings": (
                self.ranker.ranking_count
            ),
            "tuner_optimizations": (
                self.tuner
                .optimization_count
            ),
            "tuner_rollbacks": (
                self.tuner.rollback_count
            ),
            "experiments": (
                self.experiments
                .experiment_count
            ),
            "hypotheses": (
                self.experiments
                .hypothesis_count
            ),
            "measurements": (
                self.impact
                .measurement_count
            ),
            "improvements": (
                self.improver
                .improvement_count
            ),
            "insights": (
                self.synthesizer
                .insight_count
            ),
            "knowledge": (
                self.synthesizer
                .knowledge_count
            ),
        }

    @property
    def pipeline_count(self) -> int:
        """Pipeline sayısı."""
        return self._stats[
            "pipelines_run"
        ]

    @property
    def optimization_count(self) -> int:
        """Optimizasyon sayısı."""
        return self._stats[
            "optimizations"
        ]
