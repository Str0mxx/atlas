"""
Agent performans paneli orkestratoru.

Tam agent paneli, izleme, siralama,
karsilastirma, iyilestirme, analitik.
"""

import logging
from typing import Any

from app.core.agentdash.agent_lifecycle_view import (
    AgentLifecycleView,
)
from app.core.agentdash.agent_ranking import (
    AgentRanking,
)
from app.core.agentdash.agent_scorecard import (
    AgentScorecard,
)
from app.core.agentdash.confidence_trend import (
    ConfidenceTrend,
)
from app.core.agentdash.cost_efficiency_chart import (
    CostEfficiencyChart,
)
from app.core.agentdash.improvement_tracker import (
    AgentImprovementTracker,
)
from app.core.agentdash.performance_comparison import (
    PerformanceComparison,
)
from app.core.agentdash.task_completion_rate import (
    TaskCompletionRate,
)

logger = logging.getLogger(__name__)


class AgentDashOrchestrator:
    """Agent performans paneli orkestratoru.

    Attributes:
        _scorecard: Puan karti.
        _completion: Tamamlama orani.
        _confidence: Guven trendi.
        _cost: Maliyet verimliligi.
        _ranking: Agent siralama.
        _comparison: Performans karsilastirma.
        _improvement: Iyilestirme takipci.
        _lifecycle: Yasam dongusu.
    """

    def __init__(self) -> None:
        """Orkestratoru baslatir."""
        self._scorecard = AgentScorecard()
        self._completion = (
            TaskCompletionRate()
        )
        self._confidence = ConfidenceTrend()
        self._cost = CostEfficiencyChart()
        self._ranking = AgentRanking()
        self._comparison = (
            PerformanceComparison()
        )
        self._improvement = (
            AgentImprovementTracker()
        )
        self._lifecycle = AgentLifecycleView()
        logger.info(
            "AgentDashOrchestrator baslatildi"
        )

    def full_agent_dashboard(
        self,
        agent_id: str = "",
    ) -> dict[str, Any]:
        """Tam agent paneli getirir.

        Args:
            agent_id: Agent ID.

        Returns:
            Panel bilgisi.
        """
        try:
            scorecard = (
                self._scorecard.get_scorecard(
                    agent_id=agent_id
                )
            )
            completion = (
                self._completion
                .get_completion_rate(
                    agent_id=agent_id
                )
            )
            confidence = (
                self._confidence
                .detect_over_under_confidence(
                    agent_id=agent_id
                )
            )
            cost = (
                self._cost.get_cost_per_task(
                    agent_id=agent_id
                )
            )
            lifecycle = (
                self._lifecycle
                .get_lifecycle(
                    agent_id=agent_id
                )
            )

            return {
                "agent_id": agent_id,
                "scorecard": scorecard,
                "completion": completion,
                "confidence": confidence,
                "cost": cost,
                "lifecycle": lifecycle,
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }

    def all_agents_overview(
        self,
    ) -> dict[str, Any]:
        """Tum agentlara genel bakis.

        Returns:
            Genel bakis bilgisi.
        """
        try:
            scorecards = (
                self._scorecard
                .get_all_scorecards()
            )
            rankings = (
                self._ranking.get_ranking()
            )
            health = (
                self._lifecycle
                .get_health_indicators()
            )
            agents_compared = (
                self._completion
                .compare_agents()
            )

            return {
                "scorecards": scorecards,
                "rankings": rankings,
                "health": health,
                "agent_comparison": (
                    agents_compared
                ),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }

    def monitor_and_rank(
        self,
    ) -> dict[str, Any]:
        """Izleme ve siralama yapar.

        Returns:
            Izleme-siralama bilgisi.
        """
        try:
            leaderboard = (
                self._ranking.get_leaderboard()
            )
            category_leaders = (
                self._ranking
                .get_category_leaders()
            )
            optimization = (
                self._cost.track_optimization()
            )
            alerts = (
                self._confidence.check_alerts()
            )

            return {
                "leaderboard": leaderboard,
                "category_leaders": (
                    category_leaders
                ),
                "optimization": optimization,
                "alerts": alerts,
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }

    def compare_and_improve(
        self,
        agent_id: str = "",
    ) -> dict[str, Any]:
        """Karsilastirma ve iyilestirme.

        Args:
            agent_id: Agent ID.

        Returns:
            Karsilastirma-iyilestirme bilgisi.
        """
        try:
            gaps = (
                self._comparison.analyze_gaps()
            )
            efficiency = (
                self._cost.compare_efficiency()
            )
            improvement = (
                self._improvement
                .get_before_after(
                    agent_id=agent_id
                )
            )
            learning = (
                self._improvement
                .get_learning_curve(
                    agent_id=agent_id
                )
            )
            recommendations = (
                self._improvement
                .get_recommendations(
                    agent_id=agent_id
                )
            )

            return {
                "gaps": gaps,
                "efficiency": efficiency,
                "improvement": improvement,
                "learning_curve": learning,
                "recommendations": (
                    recommendations
                ),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }

    def get_analytics(
        self,
    ) -> dict[str, Any]:
        """Analitik bilgileri getirir.

        Returns:
            Analitik bilgisi.
        """
        try:
            return {
                "scorecard_agents": (
                    self._scorecard
                    .agent_count
                ),
                "tasks_tracked": (
                    self._completion
                    .task_count
                ),
                "confidence_records": (
                    self._confidence
                    .record_count
                ),
                "cost_records": (
                    self._cost.cost_count
                ),
                "ranked_agents": (
                    self._ranking.agent_count
                ),
                "comparison_records": (
                    self._comparison
                    .record_count
                ),
                "improvements": (
                    self._improvement
                    .improvement_count
                ),
                "lifecycle_agents": (
                    self._lifecycle
                    .agent_count
                ),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }
