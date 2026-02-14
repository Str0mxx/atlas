"""ATLAS Yurutme Takipcisi modulu.

Calistirma gecmisi, adim durumu,
performans metrikleri, debug
loglama ve denetim izi.
"""

import logging
import time
from typing import Any

from app.models.workflow_engine import (
    ExecutionRecord,
    WorkflowStatus,
)

logger = logging.getLogger(__name__)


class ExecutionTracker:
    """Yurutme takipcisi.

    Is akisi calistirmalarini takip
    eder ve raporlar.

    Attributes:
        _executions: Calistirma kayitlari.
        _step_logs: Adim loglari.
        _audit: Denetim kayitlari.
    """

    def __init__(self) -> None:
        """Yurutme takipcisini baslatir."""
        self._executions: dict[
            str, ExecutionRecord
        ] = {}
        self._step_logs: dict[
            str, list[dict[str, Any]]
        ] = {}
        self._audit: list[dict[str, Any]] = []
        self._debug_logs: list[
            dict[str, Any]
        ] = []

        logger.info("ExecutionTracker baslatildi")

    def start_execution(
        self,
        workflow_id: str,
    ) -> ExecutionRecord:
        """Calistirma baslatir.

        Args:
            workflow_id: Is akisi ID.

        Returns:
            Calistirma kaydi.
        """
        execution = ExecutionRecord(
            workflow_id=workflow_id,
            status=WorkflowStatus.RUNNING,
        )
        self._executions[
            execution.execution_id
        ] = execution
        self._step_logs[
            execution.execution_id
        ] = []

        self._audit.append({
            "event": "execution_started",
            "execution_id": execution.execution_id,
            "workflow_id": workflow_id,
            "at": time.time(),
        })

        return execution

    def log_step(
        self,
        execution_id: str,
        step_name: str,
        status: str,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Adim loglar.

        Args:
            execution_id: Calistirma ID.
            step_name: Adim adi.
            status: Durum.
            data: Ek veri.

        Returns:
            Log kaydi.
        """
        log = {
            "step": step_name,
            "status": status,
            "data": data or {},
            "at": time.time(),
        }

        logs = self._step_logs.get(execution_id)
        if logs is not None:
            logs.append(log)

        return log

    def complete_execution(
        self,
        execution_id: str,
        success: bool = True,
    ) -> bool:
        """Calistirma tamamlar.

        Args:
            execution_id: Calistirma ID.
            success: Basarili mi.

        Returns:
            Basarili ise True.
        """
        execution = self._executions.get(
            execution_id,
        )
        if not execution:
            return False

        execution.status = (
            WorkflowStatus.COMPLETED
            if success
            else WorkflowStatus.FAILED
        )
        execution.duration = (
            time.time()
            - execution.started_at.timestamp()
        )

        self._audit.append({
            "event": "execution_completed",
            "execution_id": execution_id,
            "success": success,
            "duration": execution.duration,
            "at": time.time(),
        })

        return True

    def fail_execution(
        self,
        execution_id: str,
        error: str = "",
    ) -> bool:
        """Calistirma basarisiz isaretler.

        Args:
            execution_id: Calistirma ID.
            error: Hata mesaji.

        Returns:
            Basarili ise True.
        """
        execution = self._executions.get(
            execution_id,
        )
        if not execution:
            return False

        execution.status = WorkflowStatus.FAILED
        execution.duration = (
            time.time()
            - execution.started_at.timestamp()
        )

        self._audit.append({
            "event": "execution_failed",
            "execution_id": execution_id,
            "error": error,
            "at": time.time(),
        })

        return True

    def debug_log(
        self,
        execution_id: str,
        message: str,
        data: dict[str, Any] | None = None,
    ) -> None:
        """Debug log ekler.

        Args:
            execution_id: Calistirma ID.
            message: Mesaj.
            data: Ek veri.
        """
        self._debug_logs.append({
            "execution_id": execution_id,
            "message": message,
            "data": data or {},
            "at": time.time(),
        })

    def get_execution(
        self,
        execution_id: str,
    ) -> ExecutionRecord | None:
        """Calistirma getirir.

        Args:
            execution_id: Calistirma ID.

        Returns:
            Calistirma veya None.
        """
        return self._executions.get(execution_id)

    def get_step_logs(
        self,
        execution_id: str,
    ) -> list[dict[str, Any]]:
        """Adim loglarini getirir.

        Args:
            execution_id: Calistirma ID.

        Returns:
            Adim loglari.
        """
        return self._step_logs.get(
            execution_id, [],
        )

    def get_history(
        self,
        workflow_id: str | None = None,
        limit: int = 50,
    ) -> list[ExecutionRecord]:
        """Gecmis getirir.

        Args:
            workflow_id: Is akisi filtresi.
            limit: Limit.

        Returns:
            Calistirma gecmisi.
        """
        executions = list(
            self._executions.values(),
        )
        if workflow_id:
            executions = [
                e for e in executions
                if e.workflow_id == workflow_id
            ]
        return executions[-limit:]

    def get_metrics(self) -> dict[str, Any]:
        """Performans metrikleri getirir.

        Returns:
            Metrikler.
        """
        total = len(self._executions)
        completed = sum(
            1 for e in self._executions.values()
            if e.status == WorkflowStatus.COMPLETED
        )
        failed = sum(
            1 for e in self._executions.values()
            if e.status == WorkflowStatus.FAILED
        )
        running = sum(
            1 for e in self._executions.values()
            if e.status == WorkflowStatus.RUNNING
        )

        durations = [
            e.duration
            for e in self._executions.values()
            if e.duration > 0
        ]
        avg_duration = (
            round(
                sum(durations) / len(durations), 4,
            )
            if durations
            else 0.0
        )

        return {
            "total": total,
            "completed": completed,
            "failed": failed,
            "running": running,
            "success_rate": round(
                completed / max(1, total), 3,
            ),
            "avg_duration": avg_duration,
        }

    def get_audit_trail(
        self,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Denetim izini getirir.

        Args:
            limit: Limit.

        Returns:
            Denetim kayitlari.
        """
        return self._audit[-limit:]

    @property
    def execution_count(self) -> int:
        """Calistirma sayisi."""
        return len(self._executions)

    @property
    def audit_count(self) -> int:
        """Denetim sayisi."""
        return len(self._audit)

    @property
    def debug_count(self) -> int:
        """Debug log sayisi."""
        return len(self._debug_logs)
