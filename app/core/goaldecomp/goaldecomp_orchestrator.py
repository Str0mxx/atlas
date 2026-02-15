"""ATLAS GoalDecomp Orkestrator modulu.

Tam hedef-gorev pipeline,
Parse > Decompose > Generate > Assign > Track.
"""

import logging
import time
from typing import Any

from app.core.goaldecomp.decomposition_engine import (
    DecompositionEngine,
)
from app.core.goaldecomp.goal_parser import (
    GoalParser,
)
from app.core.goaldecomp.goal_validator import (
    GoalValidator,
)
from app.core.goaldecomp.prerequisite_analyzer import (
    PrerequisiteAnalyzer,
)
from app.core.goaldecomp.progress_synthesizer import (
    ProgressSynthesizer,
)
from app.core.goaldecomp.replanning_engine import (
    ReplanningEngine,
)
from app.core.goaldecomp.self_assigner import (
    SelfAssigner,
)
from app.core.goaldecomp.task_generator import (
    TaskGenerator,
)

logger = logging.getLogger(__name__)


class GoalDecompOrchestrator:
    """GoalDecomp orkestrator.

    Tum hedef ayristirma bilesenleri koordine eder.

    Attributes:
        parser: Hedef ayristirici.
        decomposer: Ayristirma motoru.
        generator: Gorev uretici.
        analyzer: Onkosul analizcisi.
        assigner: Kendine atayici.
        synthesizer: Ilerleme sentezleyici.
        replanner: Yeniden planlama motoru.
        validator: Hedef dogrulayici.
    """

    def __init__(
        self,
        max_depth: int = 5,
        auto_assign: bool = False,
        validate_first: bool = True,
    ) -> None:
        """Orkestratoru baslatir.

        Args:
            max_depth: Maks ayristirma derinligi.
            auto_assign: Otomatik atama.
            validate_first: Once dogrula.
        """
        self.parser = GoalParser()
        self.decomposer = (
            DecompositionEngine(
                max_depth=max_depth,
            )
        )
        self.generator = TaskGenerator()
        self.analyzer = (
            PrerequisiteAnalyzer()
        )
        self.assigner = SelfAssigner()
        self.synthesizer = (
            ProgressSynthesizer()
        )
        self.replanner = ReplanningEngine()
        self.validator = GoalValidator()

        self._auto_assign = auto_assign
        self._validate_first = validate_first
        self._stats = {
            "pipelines_run": 0,
        }

        logger.info(
            "GoalDecompOrchestrator "
            "baslatildi",
        )

    def process_goal(
        self,
        goal_id: str,
        description: str,
        subtasks: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Hedefi isle (tam pipeline).

        Args:
            goal_id: Hedef ID.
            description: Hedef aciklamasi.
            subtasks: Alt gorev tanimlari.

        Returns:
            Pipeline sonucu.
        """
        # 1) Dogrulama
        if self._validate_first:
            validation = (
                self.validator.validate_goal(
                    goal_id, description,
                )
            )
            if validation["result"] != "valid":
                return {
                    "goal_id": goal_id,
                    "status": "invalid",
                    "validation": validation,
                    "pipeline_completed": False,
                }

        # 2) Parse
        parsed = self.parser.parse_goal(
            goal_id, description,
        )

        # 3) Decompose
        decomposed = (
            self.decomposer.decompose(
                goal_id, description,
                subtasks,
            )
        )

        # 4) Generate tasks
        # Yaprak dugumleri topla
        leaves = [
            {
                "node_id": sub.get(
                    "node_id",
                    f"node_{goal_id}_{i}",
                ),
                "description": sub.get(
                    "description", "",
                ),
                "is_leaf": True,
            }
            for i, sub in enumerate(subtasks)
        ]

        gen_result = (
            self.generator.generate_from_nodes(
                goal_id, leaves,
            )
        )

        # 5) Auto-assign
        assigned = 0
        if self._auto_assign:
            for tid in gen_result["task_ids"]:
                result = (
                    self.assigner.assign_task(
                        tid,
                    )
                )
                if result.get("assigned"):
                    assigned += 1

        self._stats["pipelines_run"] += 1

        return {
            "goal_id": goal_id,
            "status": "processed",
            "parsed": parsed["is_clear"],
            "intent": parsed["intent"],
            "nodes": decomposed[
                "node_count"
            ],
            "tasks_generated": gen_result[
                "tasks_generated"
            ],
            "tasks_assigned": assigned,
            "pipeline_completed": True,
        }

    def get_goal_status(
        self,
        goal_id: str,
    ) -> dict[str, Any]:
        """Hedef durumu getirir.

        Args:
            goal_id: Hedef ID.

        Returns:
            Durum bilgisi.
        """
        tasks = (
            self.generator.get_tasks_by_goal(
                goal_id,
            )
        )

        progress = (
            self.synthesizer
            .synthesize_progress(
                goal_id, tasks,
            )
        )

        return {
            "goal_id": goal_id,
            "task_count": len(tasks),
            "progress": progress,
        }

    def handle_failure(
        self,
        goal_id: str,
        failed_task_ids: list[str],
    ) -> dict[str, Any]:
        """Hata durumunu yonetir.

        Args:
            goal_id: Hedef ID.
            failed_task_ids: Basarisiz gorevler.

        Returns:
            Yeniden planlama sonucu.
        """
        replan = self.replanner.replan(
            goal_id,
            reason="failure",
            failed_tasks=failed_task_ids,
        )

        return {
            "goal_id": goal_id,
            "replan": replan,
            "handled": True,
        }

    def get_analytics(self) -> dict[str, Any]:
        """Analitik raporu.

        Returns:
            Rapor.
        """
        return {
            "pipelines_run": self._stats[
                "pipelines_run"
            ],
            "goals_parsed": (
                self.parser.parse_count
            ),
            "decompositions": (
                self.decomposer
                .decomposition_count
            ),
            "tasks_generated": (
                self.generator.task_count
            ),
            "tasks_assigned": (
                self.assigner
                .assignment_count
            ),
            "replans": (
                self.replanner.replan_count
            ),
            "validations": (
                self.validator
                .validation_count
            ),
            "validation_pass_rate": (
                self.validator.pass_rate
            ),
        }

    def get_status(self) -> dict[str, Any]:
        """Genel durum bilgisi.

        Returns:
            Durum bilgisi.
        """
        return {
            "pipelines_run": self._stats[
                "pipelines_run"
            ],
            "total_nodes": (
                self.decomposer.node_count
            ),
            "total_tasks": (
                self.generator.task_count
            ),
            "pending_tasks": (
                self.generator.pending_count
            ),
            "total_assignments": (
                self.assigner
                .assignment_count
            ),
            "total_replans": (
                self.replanner.replan_count
            ),
        }

    @property
    def pipelines_run(self) -> int:
        """Calisan pipeline sayisi."""
        return self._stats["pipelines_run"]
