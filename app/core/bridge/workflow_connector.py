"""ATLAS Is Akisi Baglayici modulu.

Sistemler arasi is akislari, islem yonetimi,
telafi mantigi, durum senkronizasyonu ve geri alma.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Callable

from app.models.bridge import WorkflowRecord, WorkflowState

logger = logging.getLogger(__name__)


class WorkflowConnector:
    """Is akisi baglayici.

    Sistemler arasi is akislarini yonetir,
    islemleri koordine eder ve telafi saglar.

    Attributes:
        _workflows: Is akislari.
        _step_handlers: Adim isleyicileri.
        _compensations: Telafi fonksiyonlari.
    """

    def __init__(self) -> None:
        """Is akisi baglayiciyi baslatir."""
        self._workflows: dict[str, WorkflowRecord] = {}
        self._step_handlers: dict[str, Callable] = {}
        self._compensations: dict[str, Callable] = {}
        self._state_store: dict[str, dict[str, Any]] = {}

        logger.info("WorkflowConnector baslatildi")

    def register_step(
        self,
        step_name: str,
        handler: Callable,
        compensation: Callable | None = None,
    ) -> None:
        """Adim isleyici kaydeder.

        Args:
            step_name: Adim adi.
            handler: Isleyici.
            compensation: Telafi fonksiyonu.
        """
        self._step_handlers[step_name] = handler
        if compensation:
            self._compensations[step_name] = compensation

    def create_workflow(
        self,
        name: str,
        steps: list[str],
        systems: list[str] | None = None,
    ) -> WorkflowRecord:
        """Is akisi olusturur.

        Args:
            name: Is akisi adi.
            steps: Adim listesi.
            systems: Ilgili sistemler.

        Returns:
            WorkflowRecord nesnesi.
        """
        workflow = WorkflowRecord(
            name=name,
            steps=steps,
            systems_involved=systems or [],
        )
        self._workflows[workflow.workflow_id] = workflow

        logger.info("Is akisi olusturuldu: %s", name)
        return workflow

    def execute_workflow(
        self,
        workflow_id: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Is akisini calistirir.

        Args:
            workflow_id: Is akisi ID.
            context: Calisma baglami.

        Returns:
            Calisma sonucu.
        """
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            return {"success": False, "reason": "Is akisi bulunamadi"}

        if workflow.state != WorkflowState.PENDING:
            return {"success": False, "reason": "Is akisi zaten calistirildi"}

        workflow.state = WorkflowState.RUNNING
        workflow.started_at = datetime.now(timezone.utc)
        ctx = dict(context or {})
        self._state_store[workflow_id] = ctx

        for step in workflow.steps:
            handler = self._step_handlers.get(step)
            if not handler:
                workflow.state = WorkflowState.FAILED
                return {
                    "success": False,
                    "reason": f"Adim isleyici bulunamadi: {step}",
                    "completed_steps": list(workflow.completed_steps),
                }

            try:
                ctx = handler(ctx) or ctx
                workflow.completed_steps.append(step)
                self._state_store[workflow_id] = ctx
            except Exception as e:
                workflow.state = WorkflowState.FAILED
                logger.error("Adim hatasi %s: %s", step, e)
                return {
                    "success": False,
                    "reason": f"Adim hatasi: {step} - {e}",
                    "completed_steps": list(workflow.completed_steps),
                }

        workflow.state = WorkflowState.COMPLETED
        workflow.completed_at = datetime.now(timezone.utc)

        return {
            "success": True,
            "workflow_id": workflow_id,
            "completed_steps": list(workflow.completed_steps),
            "context": ctx,
        }

    def rollback_workflow(
        self,
        workflow_id: str,
    ) -> dict[str, Any]:
        """Is akisini geri alir.

        Args:
            workflow_id: Is akisi ID.

        Returns:
            Geri alma sonucu.
        """
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            return {"success": False, "reason": "Is akisi bulunamadi"}

        if workflow.state != WorkflowState.FAILED:
            return {"success": False, "reason": "Sadece basarisiz is akislari geri alinabilir"}

        ctx = self._state_store.get(workflow_id, {})
        rolled_back = []

        # Tamamlanan adimlari tersten geri al
        for step in reversed(workflow.completed_steps):
            compensation = self._compensations.get(step)
            if compensation:
                try:
                    compensation(ctx)
                    rolled_back.append(step)
                except Exception as e:
                    logger.error("Telafi hatasi %s: %s", step, e)

        workflow.state = WorkflowState.ROLLED_BACK
        workflow.completed_steps.clear()

        return {
            "success": True,
            "rolled_back_steps": rolled_back,
        }

    def sync_state(
        self,
        workflow_id: str,
        key: str,
        value: Any,
    ) -> bool:
        """Durum senkronize eder.

        Args:
            workflow_id: Is akisi ID.
            key: Anahtar.
            value: Deger.

        Returns:
            Basarili ise True.
        """
        if workflow_id not in self._workflows:
            return False

        self._state_store.setdefault(workflow_id, {})[key] = value
        return True

    def get_state(
        self,
        workflow_id: str,
    ) -> dict[str, Any]:
        """Durumu getirir.

        Args:
            workflow_id: Is akisi ID.

        Returns:
            Durum sozlugu.
        """
        return dict(self._state_store.get(workflow_id, {}))

    def get_workflow(
        self,
        workflow_id: str,
    ) -> WorkflowRecord | None:
        """Is akisini getirir.

        Args:
            workflow_id: Is akisi ID.

        Returns:
            WorkflowRecord veya None.
        """
        return self._workflows.get(workflow_id)

    def get_workflows(
        self,
        state: WorkflowState | None = None,
    ) -> list[WorkflowRecord]:
        """Is akislarini getirir.

        Args:
            state: Durum filtresi.

        Returns:
            Is akisi listesi.
        """
        workflows = list(self._workflows.values())
        if state:
            workflows = [w for w in workflows if w.state == state]
        return workflows

    @property
    def total_workflows(self) -> int:
        """Toplam is akisi sayisi."""
        return len(self._workflows)

    @property
    def active_count(self) -> int:
        """Aktif is akisi sayisi."""
        return sum(
            1 for w in self._workflows.values()
            if w.state == WorkflowState.RUNNING
        )

    @property
    def registered_steps(self) -> int:
        """Kayitli adim sayisi."""
        return len(self._step_handlers)
