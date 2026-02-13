"""ATLAS Uygulama Motoru modulu.

Gorev zamanlama, agent delegasyonu, ilerleme takibi,
checkpoint yonetimi ve geri alma islemleri.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from app.models.business import (
    ActionStep,
    Checkpoint,
    CheckpointStatus,
    ExecutionStatus,
    Strategy,
    StrategyStatus,
    TaskExecution,
)

logger = logging.getLogger(__name__)


class ExecutionEngine:
    """Uygulama motoru.

    Strateji aksiyon adimlarini zamanlayarak agent'lara
    delege eder, ilerlemeyi takip eder, checkpoint'ler
    olusturur ve gerekirse geri alir.

    Attributes:
        _executions: Yurutme kayitlari (id -> TaskExecution).
        _checkpoints: Checkpoint'ler (id -> Checkpoint).
        _strategies: Iliskili stratejiler (id -> Strategy).
        _max_retries: Maksimum tekrar deneme sayisi.
    """

    def __init__(self, max_retries: int = 3) -> None:
        """Uygulama motorunu baslatir.

        Args:
            max_retries: Maksimum tekrar deneme sayisi.
        """
        self._executions: dict[str, TaskExecution] = {}
        self._checkpoints: dict[str, Checkpoint] = {}
        self._strategies: dict[str, Strategy] = {}
        self._max_retries = max_retries

        logger.info("ExecutionEngine baslatildi (max_retries=%d)", max_retries)

    def register_strategy(self, strategy: Strategy) -> None:
        """Stratejiyi uygulama motoru ile kaydeder.

        Args:
            strategy: Kaydedilecek strateji.
        """
        self._strategies[strategy.id] = strategy
        logger.info("Strateji kaydedildi: %s", strategy.title[:30])

    def schedule_tasks(self, strategy_id: str) -> list[TaskExecution]:
        """Strateji aksiyon adimlarini gorev olarak zamanlar.

        Her aksiyon adimi icin bir TaskExecution olusturur
        ve bagimliliklari kontrol eder.

        Args:
            strategy_id: Strateji ID.

        Returns:
            Zamanlanan gorevler listesi. Strateji bulunamazsa bos liste.
        """
        strategy = self._strategies.get(strategy_id)
        if not strategy:
            return []

        executions: list[TaskExecution] = []
        for step in strategy.action_steps:
            # Bagimlilik kontrolu: bagimliliklari yoksa hemen zamanla
            has_deps = bool(step.dependencies)
            status = ExecutionStatus.SCHEDULED if not has_deps else ExecutionStatus.PENDING

            execution = TaskExecution(
                strategy_id=strategy_id,
                action_step_id=step.id,
                status=status,
                agent_id=step.agent_type,
                scheduled_at=datetime.now(timezone.utc) if not has_deps else None,
            )
            self._executions[execution.id] = execution
            executions.append(execution)

        logger.info("Gorev zamanlama: %s -> %d gorev", strategy.title[:30], len(executions))
        return executions

    def delegate_task(self, execution_id: str, agent_id: str) -> bool:
        """Gorevi agent'a delege eder.

        Args:
            execution_id: Yurutme ID.
            agent_id: Atanacak agent ID.

        Returns:
            Basarili mi.
        """
        execution = self._executions.get(execution_id)
        if not execution:
            return False

        if execution.status not in (ExecutionStatus.PENDING, ExecutionStatus.SCHEDULED):
            return False

        execution.agent_id = agent_id
        execution.status = ExecutionStatus.RUNNING
        execution.started_at = datetime.now(timezone.utc)
        logger.info("Gorev delege edildi: %s -> agent=%s", execution_id[:8], agent_id)
        return True

    def start_task(self, execution_id: str) -> bool:
        """Gorevi baslatir.

        Args:
            execution_id: Yurutme ID.

        Returns:
            Basarili mi.
        """
        execution = self._executions.get(execution_id)
        if not execution:
            return False

        if execution.status not in (ExecutionStatus.PENDING, ExecutionStatus.SCHEDULED):
            return False

        execution.status = ExecutionStatus.RUNNING
        execution.started_at = datetime.now(timezone.utc)
        logger.info("Gorev baslatildi: %s", execution_id[:8])
        return True

    def complete_task(self, execution_id: str, result: dict[str, Any] | None = None) -> bool:
        """Gorevi tamamlar.

        Args:
            execution_id: Yurutme ID.
            result: Sonuc verisi.

        Returns:
            Basarili mi.
        """
        execution = self._executions.get(execution_id)
        if not execution:
            return False

        if execution.status != ExecutionStatus.RUNNING:
            return False

        execution.status = ExecutionStatus.COMPLETED
        execution.completed_at = datetime.now(timezone.utc)
        execution.result = result or {}
        logger.info("Gorev tamamlandi: %s", execution_id[:8])

        # Bagimli gorevleri zamanla
        self._unblock_dependents(execution)
        return True

    def fail_task(self, execution_id: str, error: str = "") -> bool:
        """Gorevi basarisiz olarak isaretler.

        Tekrar deneme limiti asildiysa FAILED, degilse
        PENDING durumuna geri doner.

        Args:
            execution_id: Yurutme ID.
            error: Hata mesaji.

        Returns:
            Basarili mi.
        """
        execution = self._executions.get(execution_id)
        if not execution:
            return False

        execution.retry_count += 1
        execution.error = error

        if execution.retry_count >= self._max_retries:
            execution.status = ExecutionStatus.FAILED
            logger.error("Gorev basarisiz (max retry): %s - %s", execution_id[:8], error)
        else:
            execution.status = ExecutionStatus.PENDING
            execution.started_at = None
            logger.warning("Gorev tekrar deneme %d/%d: %s", execution.retry_count, self._max_retries, execution_id[:8])

        return True

    def _unblock_dependents(self, completed_execution: TaskExecution) -> None:
        """Tamamlanan gorev sonrasi bagimli gorevleri cozumler.

        Args:
            completed_execution: Tamamlanan yurutme.
        """
        strategy = self._strategies.get(completed_execution.strategy_id)
        if not strategy:
            return

        completed_step_id = completed_execution.action_step_id
        for execution in self._executions.values():
            if execution.strategy_id != completed_execution.strategy_id:
                continue
            if execution.status != ExecutionStatus.PENDING:
                continue

            # Bu gorev tamamlanan adima bagimli mi?
            step = next(
                (s for s in strategy.action_steps if s.id == execution.action_step_id),
                None,
            )
            if step and completed_step_id in step.dependencies:
                # Tum bagimliliklar tamamlandi mi?
                all_deps_done = all(
                    any(
                        e.action_step_id == dep_id and e.status == ExecutionStatus.COMPLETED
                        for e in self._executions.values()
                    )
                    for dep_id in step.dependencies
                )
                if all_deps_done:
                    execution.status = ExecutionStatus.SCHEDULED
                    execution.scheduled_at = datetime.now(timezone.utc)
                    logger.info("Bagimli gorev acildi: %s", execution.id[:8])

    def get_progress(self, strategy_id: str) -> dict[str, Any]:
        """Strateji ilerleme durumunu getirir.

        Args:
            strategy_id: Strateji ID.

        Returns:
            Ilerleme bilgileri iceren dict:
            - total: Toplam gorev sayisi
            - completed: Tamamlanan gorev sayisi
            - running: Calisan gorev sayisi
            - failed: Basarisiz gorev sayisi
            - progress_pct: Ilerleme yuzdesi
        """
        execs = [e for e in self._executions.values() if e.strategy_id == strategy_id]
        total = len(execs)
        if total == 0:
            return {"total": 0, "completed": 0, "running": 0, "failed": 0, "progress_pct": 0.0}

        completed = sum(1 for e in execs if e.status == ExecutionStatus.COMPLETED)
        running = sum(1 for e in execs if e.status == ExecutionStatus.RUNNING)
        failed = sum(1 for e in execs if e.status == ExecutionStatus.FAILED)

        return {
            "total": total,
            "completed": completed,
            "running": running,
            "failed": failed,
            "progress_pct": (completed / total) * 100,
        }

    def create_checkpoint(self, strategy_id: str, description: str = "") -> Checkpoint:
        """Checkpoint olusturur.

        Strateji durumunu ve yurutme durumlarini kaydeder.

        Args:
            strategy_id: Strateji ID.
            description: Checkpoint aciklamasi.

        Returns:
            Olusturulan Checkpoint nesnesi.
        """
        execs = {
            eid: {"status": e.status.value, "result": e.result}
            for eid, e in self._executions.items()
            if e.strategy_id == strategy_id
        }

        checkpoint = Checkpoint(
            strategy_id=strategy_id,
            state_snapshot={"executions": execs},
            description=description,
        )
        self._checkpoints[checkpoint.id] = checkpoint
        logger.info("Checkpoint olusturuldu: %s (%s)", checkpoint.id[:8], description[:20])
        return checkpoint

    def rollback_to_checkpoint(self, checkpoint_id: str) -> bool:
        """Checkpoint'e geri doner.

        Tamamlanmis gorevlerin sonuclarini temizler ve
        durumlarini PENDING'e cevirir.

        Args:
            checkpoint_id: Checkpoint ID.

        Returns:
            Basarili mi.
        """
        checkpoint = self._checkpoints.get(checkpoint_id)
        if not checkpoint:
            return False

        snapshot = checkpoint.state_snapshot.get("executions", {})
        for eid, state in snapshot.items():
            execution = self._executions.get(eid)
            if execution:
                try:
                    execution.status = ExecutionStatus(state["status"])
                except (ValueError, KeyError):
                    execution.status = ExecutionStatus.PENDING
                execution.result = state.get("result", {})

        checkpoint.status = CheckpointStatus.RESTORED
        logger.info("Checkpoint'e geri donuldu: %s", checkpoint_id[:8])
        return True

    def pause_strategy(self, strategy_id: str) -> int:
        """Strateji gorevlerini duraklatir.

        Calisan gorevleri PAUSED durumuna cevirir.

        Args:
            strategy_id: Strateji ID.

        Returns:
            Durdurulan gorev sayisi.
        """
        paused = 0
        for execution in self._executions.values():
            if execution.strategy_id == strategy_id and execution.status == ExecutionStatus.RUNNING:
                execution.status = ExecutionStatus.PAUSED
                paused += 1

        strategy = self._strategies.get(strategy_id)
        if strategy:
            strategy.status = StrategyStatus.PAUSED

        logger.info("Strateji durduruldu: %s (%d gorev)", strategy_id[:8], paused)
        return paused

    def resume_strategy(self, strategy_id: str) -> int:
        """Durdurulan strateji gorevlerini devam ettirir.

        Args:
            strategy_id: Strateji ID.

        Returns:
            Devam ettirilen gorev sayisi.
        """
        resumed = 0
        for execution in self._executions.values():
            if execution.strategy_id == strategy_id and execution.status == ExecutionStatus.PAUSED:
                execution.status = ExecutionStatus.RUNNING
                resumed += 1

        strategy = self._strategies.get(strategy_id)
        if strategy:
            strategy.status = StrategyStatus.ACTIVE

        logger.info("Strateji devam ettirildi: %s (%d gorev)", strategy_id[:8], resumed)
        return resumed

    def get_execution(self, execution_id: str) -> TaskExecution | None:
        """Yurutme kaydini getirir.

        Args:
            execution_id: Yurutme ID.

        Returns:
            TaskExecution nesnesi veya None.
        """
        return self._executions.get(execution_id)

    @property
    def execution_count(self) -> int:
        """Toplam yurutme sayisi."""
        return len(self._executions)
