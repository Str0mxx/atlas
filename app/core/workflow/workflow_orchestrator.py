"""ATLAS Is Akisi Orkestratoru modulu.

Tam is akisi motoru, calistirma
yonetimi, es zamanli is akislari,
oncelik islemleri ve analitik.
"""

import logging
import time
from typing import Any

from app.models.workflow_engine import (
    NodeType,
    TriggerType,
    WorkflowRecord,
    WorkflowSnapshot,
    WorkflowStatus,
)

from app.core.workflow.workflow_designer import (
    WorkflowDesigner,
)
from app.core.workflow.trigger_manager import (
    TriggerManager,
)
from app.core.workflow.action_executor import (
    ActionExecutor,
)
from app.core.workflow.condition_evaluator import (
    ConditionEvaluator,
)
from app.core.workflow.variable_manager import (
    VariableManager,
)
from app.core.workflow.loop_controller import (
    LoopController,
)
from app.core.workflow.error_handler import (
    WorkflowErrorHandler,
)
from app.core.workflow.execution_tracker import (
    ExecutionTracker,
)

logger = logging.getLogger(__name__)


class WorkflowOrchestrator:
    """Is akisi orkestratoru.

    Tum is akisi alt sistemlerini
    koordine eder ve birlesik
    arayuz saglar.

    Attributes:
        designer: Tasarimci.
        triggers: Tetikleyici yoneticisi.
        actions: Aksiyon yurutucu.
        conditions: Kosul degerlendirici.
        variables: Degisken yoneticisi.
        loops: Dongu kontrolcusu.
        errors: Hata yoneticisi.
        tracker: Yurutme takipcisi.
    """

    def __init__(
        self,
        max_concurrent: int = 10,
        default_timeout: int = 3600,
        max_loop_iterations: int = 1000,
    ) -> None:
        """Orkestratoru baslatir.

        Args:
            max_concurrent: Maks es zamanli.
            default_timeout: Varsayilan zaman asimi.
            max_loop_iterations: Maks dongu.
        """
        self.designer = WorkflowDesigner()
        self.triggers = TriggerManager()
        self.actions = ActionExecutor()
        self.conditions = ConditionEvaluator()
        self.variables = VariableManager()
        self.loops = LoopController(
            max_iterations=max_loop_iterations,
        )
        self.errors = WorkflowErrorHandler()
        self.tracker = ExecutionTracker()

        self._max_concurrent = max_concurrent
        self._default_timeout = default_timeout
        self._running: set[str] = set()

        logger.info(
            "WorkflowOrchestrator baslatildi",
        )

    def execute_workflow(
        self,
        workflow_id: str,
        input_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Is akisi calistirir.

        Args:
            workflow_id: Is akisi ID.
            input_data: Giris verisi.

        Returns:
            Calistirma sonucu.
        """
        wf = self.designer.get_workflow(
            workflow_id,
        )
        if not wf:
            return {
                "success": False,
                "reason": "workflow_not_found",
            }

        # Es zamanli limit
        if len(self._running) >= self._max_concurrent:
            return {
                "success": False,
                "reason": "max_concurrent_reached",
            }

        # Calistirma baslat
        execution = self.tracker.start_execution(
            workflow_id,
        )
        self._running.add(execution.execution_id)

        # Giris degiskenlerini ayarla
        if input_data:
            for key, val in input_data.items():
                self.variables.set_variable(
                    key, val,
                    workflow_id=workflow_id,
                )

        start = time.time()
        steps_done = 0
        steps_failed = 0

        # Dugumleri sirala ve calistir
        for node in wf.nodes:
            node_name = node["name"]
            node_type = node["type"]

            self.tracker.log_step(
                execution.execution_id,
                node_name, "running",
            )

            if node_type == NodeType.ACTION.value:
                result = self.actions.execute(
                    node_name,
                    node.get("config"),
                )
                if result["success"]:
                    steps_done += 1
                    self.tracker.log_step(
                        execution.execution_id,
                        node_name, "completed",
                    )
                else:
                    steps_failed += 1
                    self.tracker.log_step(
                        execution.execution_id,
                        node_name, "failed",
                        {"error": result.get("error")},
                    )

            elif node_type == NodeType.CONDITION.value:
                expr = node.get("config", {}).get(
                    "expression", "true",
                )
                ctx = self.variables.get_scope_variables(
                    workflow_id=workflow_id,
                )
                self.conditions.evaluate(expr, ctx)
                steps_done += 1
                self.tracker.log_step(
                    execution.execution_id,
                    node_name, "completed",
                )
            else:
                steps_done += 1
                self.tracker.log_step(
                    execution.execution_id,
                    node_name, "completed",
                )

        duration = time.time() - start
        success = steps_failed == 0

        self.tracker.complete_execution(
            execution.execution_id, success,
        )
        self._running.discard(
            execution.execution_id,
        )

        return {
            "success": success,
            "execution_id": execution.execution_id,
            "workflow_id": workflow_id,
            "steps_completed": steps_done,
            "steps_failed": steps_failed,
            "duration": round(duration, 4),
        }

    def trigger_workflow(
        self,
        event_name: str,
        data: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Olayla is akisi tetikler.

        Args:
            event_name: Olay adi.
            data: Olay verisi.

        Returns:
            Calistirma sonuclari.
        """
        workflow_ids = self.triggers.fire_event(
            event_name, data,
        )
        results: list[dict[str, Any]] = []

        for wf_id in workflow_ids:
            result = self.execute_workflow(
                wf_id, data,
            )
            results.append(result)

        return results

    def get_analytics(self) -> dict[str, Any]:
        """Analitik verileri getirir.

        Returns:
            Analitik.
        """
        metrics = self.tracker.get_metrics()

        return {
            "total_workflows": (
                self.designer.workflow_count
            ),
            "total_executions": metrics["total"],
            "completed": metrics["completed"],
            "failed": metrics["failed"],
            "running": metrics["running"],
            "success_rate": metrics["success_rate"],
            "avg_duration": metrics["avg_duration"],
            "active_triggers": (
                self.triggers.active_count
            ),
            "total_actions": (
                self.actions.action_count
            ),
            "total_variables": (
                self.variables.total_variables
            ),
        }

    def get_snapshot(self) -> WorkflowSnapshot:
        """Goruntusu getirir.

        Returns:
            Goruntusu.
        """
        analytics = self.get_analytics()

        return WorkflowSnapshot(
            total_workflows=analytics[
                "total_workflows"
            ],
            active=analytics["total_workflows"],
            running=analytics["running"],
            completed=analytics["completed"],
            failed=analytics["failed"],
            total_executions=analytics[
                "total_executions"
            ],
            avg_duration=analytics["avg_duration"],
            active_triggers=analytics[
                "active_triggers"
            ],
        )

    @property
    def running_count(self) -> int:
        """Calisan is akisi sayisi."""
        return len(self._running)
