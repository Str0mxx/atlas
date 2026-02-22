"""Lobster is akisi motoru - is akislarini olusturma ve yurutme.

Is akislarini tanimlama, adim adim yurutme, hata yonetimi
ve tekrar oynatma ozellikleri saglar.
"""

import logging
import time
import uuid
from typing import Any, Optional

from app.models.lobster_models import (
    PipelineStep, StepStatus, StepType, Workflow, WorkflowExecution, WorkflowStatus,
)

logger = logging.getLogger(__name__)


class LobsterWorkflowEngine:
    """Is akisi yurutme motoru."""

    def __init__(self) -> None:
        """LobsterWorkflowEngine baslatici."""
        self._workflows: dict[str, Workflow] = {}
        self._executions: dict[str, list[WorkflowExecution]] = {}
        self._action_handlers: dict[str, Any] = {}
        self._history: list[dict] = []

    def _record_history(self, action: str, details: dict) -> None:
        """Gecmis kaydini tutar."""
        self._history.append({"action": action, "timestamp": time.time(), "details": details})

    def get_history(self) -> list[dict]:
        """Gecmis kayitlarini dondurur."""
        return list(self._history)

    def get_stats(self) -> dict:
        """Istatistikleri dondurur."""
        status_counts: dict[str, int] = {}
        for wf in self._workflows.values():
            s = wf.status.value
            status_counts[s] = status_counts.get(s, 0) + 1
        total_execs = sum(len(v) for v in self._executions.values())
        return {"total_workflows": len(self._workflows), "status_distribution": status_counts, "total_executions": total_execs, "registered_actions": len(self._action_handlers), "history_count": len(self._history)}

    def register_action(self, name: str, handler: Any) -> None:
        """Aksiyon isleyicisi kaydeder."""
        self._action_handlers[name] = handler
        self._record_history("register_action", {"name": name})

    def create_workflow(
        self,
        name: str,
        steps: list[PipelineStep] | None = None,
        description: str = "",
    ) -> Workflow:
        """Yeni is akisi olusturur.

        Args:
            name: Is akisi adi.
            steps: Adim listesi.
            description: Aciklama.

        Returns:
            Olusturulan is akisi.
        """
        workflow_id = str(uuid.uuid4())
        workflow = Workflow(
            workflow_id=workflow_id,
            name=name,
            description=description,
            steps=steps or [],
            status=WorkflowStatus.DRAFT,
            created_at=time.time(),
        )
        self._workflows[workflow_id] = workflow
        self._record_history(
            "create_workflow",
            {"workflow_id": workflow_id, "name": name},
        )
        return workflow

    def run_workflow(self, workflow_id: str) -> WorkflowExecution:
        """Is akisini yurutur."""
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow not found: {workflow_id}")
        now = time.time()
        execution_id = str(uuid.uuid4())
        workflow.status = WorkflowStatus.RUNNING
        workflow.started_at = now
        workflow.current_step = 0
        execution = WorkflowExecution(execution_id=execution_id, workflow_id=workflow_id, started_at=now, status=WorkflowStatus.RUNNING, steps_total=len(workflow.steps))
        for i, step in enumerate(workflow.steps):
            if workflow.status != WorkflowStatus.RUNNING:
                break
            workflow.current_step = i
            try:
                result = self.execute_step(workflow, step)
                step.output_data = result if isinstance(result, dict) else {"result": result}
                step.status = StepStatus.COMPLETED
                step.completed_at = time.time()
                execution.steps_completed += 1
                if workflow.recording is not None:
                    workflow.recording.append({"step_id": step.step_id, "step_name": step.name, "status": step.status.value, "timestamp": time.time(), "output": step.output_data})
            except Exception as e:
                self.handle_step_failure(workflow, step, str(e))
                if step.retry_count >= step.max_retries:
                    execution.errors.append(f"Step {step.name} failed: {e}")
                    execution.status = WorkflowStatus.FAILED
                    workflow.status = WorkflowStatus.FAILED
                    workflow.error = str(e)
                    break
        if workflow.status == WorkflowStatus.RUNNING:
            workflow.status = WorkflowStatus.COMPLETED
            workflow.completed_at = time.time()
            execution.status = WorkflowStatus.COMPLETED
            execution.completed_at = time.time()
        if workflow_id not in self._executions:
            self._executions[workflow_id] = []
        self._executions[workflow_id].append(execution)
        self._record_history("run_workflow", {"workflow_id": workflow_id, "execution_id": execution_id, "status": execution.status.value})
        return execution

    def execute_step(self, workflow: Workflow, step: PipelineStep) -> dict:
        """Tek bir adimi yurutur."""
        step.status = StepStatus.RUNNING
        step.started_at = time.time()
        if step.step_type == StepType.APPROVAL:
            step.status = StepStatus.WAITING_APPROVAL
            raise ValueError(f"Step {step.name} requires approval")
        if step.step_type == StepType.CONDITION:
            condition_result = self._evaluate_condition(step.condition, workflow.variables)
            return {"condition_result": condition_result}
        if step.step_type == StepType.DELAY:
            return {"delayed": step.timeout_seconds}
        if step.step_type == StepType.ACTION:
            handler = self._action_handlers.get(step.action)
            if handler and callable(handler):
                result = handler(step.input_data)
                return result if isinstance(result, dict) else {"result": result}
            return {"action": step.action, "status": "executed"}
        return {"step_type": step.step_type.value, "status": "processed"}

    def _evaluate_condition(self, condition: str, variables: dict) -> bool:
        """Kosul ifadesini degerlendirir."""
        if not condition:
            return True
        try:
            return bool(eval(condition, {"__builtins__": {}}, variables))
        except Exception:
            return False

    def handle_step_failure(self, workflow: Workflow, step: PipelineStep, error: str) -> None:
        """Adim hatasini isler."""
        step.retry_count += 1
        step.error = error
        step.status = StepStatus.FAILED
        self._record_history("handle_step_failure", {"workflow_id": workflow.workflow_id, "step_id": step.step_id, "error": error, "retry_count": step.retry_count})

    def pause_workflow(self, workflow_id: str) -> bool:
        """Is akisini duraklatir."""
        workflow = self._workflows.get(workflow_id)
        if workflow and workflow.status == WorkflowStatus.RUNNING:
            workflow.status = WorkflowStatus.PAUSED
            self._record_history("pause_workflow", {"workflow_id": workflow_id})
            return True
        return False

    def resume_workflow(self, workflow_id: str) -> bool:
        """Duraklatilmis is akisini devam ettirir."""
        workflow = self._workflows.get(workflow_id)
        if workflow and workflow.status == WorkflowStatus.PAUSED:
            workflow.status = WorkflowStatus.RUNNING
            self._record_history("resume_workflow", {"workflow_id": workflow_id})
            return True
        return False

    def cancel_workflow(self, workflow_id: str) -> bool:
        """Is akisini iptal eder."""
        workflow = self._workflows.get(workflow_id)
        if workflow and workflow.status in (WorkflowStatus.DRAFT, WorkflowStatus.RUNNING, WorkflowStatus.PAUSED):
            workflow.status = WorkflowStatus.CANCELLED
            self._record_history("cancel_workflow", {"workflow_id": workflow_id})
            return True
        return False

    def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        """Is akisini dondurur."""
        return self._workflows.get(workflow_id)

    def list_workflows(self, status: Optional[WorkflowStatus] = None) -> list[Workflow]:
        """Is akislarini listeler."""
        if status is None:
            return list(self._workflows.values())
        return [wf for wf in self._workflows.values() if wf.status == status]

    def replay_workflow(self, workflow_id: str) -> WorkflowExecution:
        """Kaydedilmis is akisini tekrar oynatir."""
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow not found: {workflow_id}")
        for step in workflow.steps:
            step.status = StepStatus.PENDING
            step.retry_count = 0
            step.error = ""
            step.output_data = {}
        workflow.status = WorkflowStatus.DRAFT
        workflow.recording = []
        return self.run_workflow(workflow_id)

    def get_execution_history(self, workflow_id: str) -> list[WorkflowExecution]:
        """Is akisi yurutme gecmisini dondurur."""
        return self._executions.get(workflow_id, [])
