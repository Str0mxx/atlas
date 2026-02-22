"""Pipeline olusturucu - is akisi adimlarini zincirleme tanimi."""

import logging
import time
import uuid
from typing import Any, Optional

from app.models.lobster_models import (
    PipelineStep, StepStatus, StepType, Workflow, WorkflowStatus,
)

logger = logging.getLogger(__name__)


class PipelineBuilder:
    """Akici arayuz ile is akisi olusturucu."""

    def __init__(self) -> None:
        """PipelineBuilder baslatici."""
        self._name: str = ""
        self._description: str = ""
        self._steps: list[PipelineStep] = []
        self._variables: dict[str, Any] = {}
        self._tags: list[str] = []
        self._history: list[dict] = []

    def _record_history(self, action: str, details: dict) -> None:
        """Gecmis kaydini tutar."""
        self._history.append({"action": action, "timestamp": time.time(), "details": details})

    def get_history(self) -> list[dict]:
        """Gecmis kayitlarini dondurur."""
        return list(self._history)

    def get_stats(self) -> dict:
        """Istatistikleri dondurur."""
        tc: dict[str, int] = {}
        for step in self._steps:
            t = step.step_type.value
            tc[t] = tc.get(t, 0) + 1
        return {"name": self._name, "step_count": len(self._steps), "variable_count": len(self._variables), "type_distribution": tc, "history_count": len(self._history)}

    def new(self, name: str, description: str = "") -> "PipelineBuilder":
        """Yeni pipeline baslatir."""
        self._name = name
        self._description = description
        self._steps = []
        self._variables = {}
        self._tags = []
        self._record_history("new", {"name": name})
        return self

    def add_step(self, name: str, action: str, input_schema: Optional[dict] = None, timeout: int = 300, max_retries: int = 3) -> "PipelineBuilder":
        """Aksiyon adimi ekler."""
        step = PipelineStep(step_id=str(uuid.uuid4()), name=name, step_type=StepType.ACTION, action=action, input_schema=input_schema or {}, timeout_seconds=timeout, max_retries=max_retries)
        self._steps.append(step)
        self._record_history("add_step", {"name": name, "action": action})
        return self

    def add_approval(self, name: str, approver: str = "", description: str = "") -> "PipelineBuilder":
        """Onay kapisi ekler."""
        step = PipelineStep(step_id=str(uuid.uuid4()), name=name, step_type=StepType.APPROVAL, requires_approval=True, approver=approver, action=description)
        self._steps.append(step)
        self._record_history("add_approval", {"name": name, "approver": approver})
        return self

    def add_condition(self, name: str, condition: str) -> "PipelineBuilder":
        """Kosullu adim ekler."""
        step = PipelineStep(step_id=str(uuid.uuid4()), name=name, step_type=StepType.CONDITION, condition=condition)
        self._steps.append(step)
        self._record_history("add_condition", {"name": name, "condition": condition})
        return self

    def add_delay(self, name: str, seconds: int) -> "PipelineBuilder":
        """Gecikme adimi ekler."""
        step = PipelineStep(step_id=str(uuid.uuid4()), name=name, step_type=StepType.DELAY, timeout_seconds=seconds)
        self._steps.append(step)
        self._record_history("add_delay", {"name": name, "seconds": seconds})
        return self

    def set_variable(self, key: str, value: Any) -> "PipelineBuilder":
        """Is akisi degiskeni ayarlar."""
        self._variables[key] = value
        self._record_history("set_variable", {"key": key})
        return self

    def add_tag(self, tag: str) -> "PipelineBuilder":
        """Etiket ekler."""
        if tag not in self._tags:
            self._tags.append(tag)
        return self

    def build(self) -> Workflow:
        """Is akisini kesinlestirir."""
        errors = self.validate()
        if errors:
            raise ValueError("Validation errors: " + "; ".join(errors))
        workflow = Workflow(workflow_id=str(uuid.uuid4()), name=self._name, description=self._description, steps=list(self._steps), status=WorkflowStatus.DRAFT, created_at=time.time(), variables=dict(self._variables), tags=list(self._tags))
        self._record_history("build", {"workflow_id": workflow.workflow_id, "step_count": len(workflow.steps)})
        return workflow

    def validate(self) -> list[str]:
        """Pipeline dogrulamasi yapar."""
        errors: list[str] = []
        if not self._name:
            errors.append("Pipeline name is required")
        if not self._steps:
            errors.append("Pipeline must have at least one step")
        names = [s.name for s in self._steps]
        if len(names) != len(set(names)):
            errors.append("Step names must be unique")
        for step in self._steps:
            if not step.name:
                errors.append("Step name is required")
            if step.step_type == StepType.ACTION and not step.action:
                errors.append("Step " + step.name + " requires an action")
        return errors

    @staticmethod
    def from_dict(data: dict) -> Workflow:
        """Sozlukten is akisi yukleme."""
        steps = [PipelineStep(**sd) for sd in data.get("steps", [])]
        return Workflow(workflow_id=data.get("workflow_id", str(uuid.uuid4())), name=data.get("name", ""), description=data.get("description", ""), steps=steps, status=WorkflowStatus(data.get("status", "draft")), created_at=data.get("created_at", time.time()), variables=data.get("variables", {}), tags=data.get("tags", []))

    @staticmethod
    def to_dict(workflow: Workflow) -> dict:
        """Is akisini sozluge donusturur."""
        return workflow.model_dump()
