"""ATLAS Yedekleme Orkestrator modulu.

Tam yedekleme/DR pipeline, izleme,
uyari, uyumluluk ve analitik.
"""

import logging
import time
from typing import Any

from app.core.backup.backup_executor import (
    BackupExecutor,
)
from app.core.backup.backup_scheduler import (
    BackupScheduler,
)
from app.core.backup.disaster_planner import (
    DisasterPlanner,
)
from app.core.backup.failover_controller import (
    FailoverController,
)
from app.core.backup.recovery_tester import (
    RecoveryTester,
)
from app.core.backup.replication_manager import (
    BackupReplicationManager,
)
from app.core.backup.restore_manager import (
    RestoreManager,
)
from app.core.backup.storage_backend import (
    BackupStorageBackend,
)

logger = logging.getLogger(__name__)


class BackupOrchestrator:
    """Yedekleme orkestrator.

    Tum yedekleme bilesenleri koordine eder.

    Attributes:
        scheduler: Zamanlayici.
        executor: Yurutucu.
        storage: Depolama.
        restore_manager: Geri yukleme.
        replication: Replikasyon.
        disaster_planner: Felaket planlayici.
        failover: Yuk devri.
        tester: Kurtarma test edici.
    """

    def __init__(
        self,
        storage_type: str = "local",
        encryption: bool = False,
        compression: bool = False,
    ) -> None:
        """Orkestratoru baslatir.

        Args:
            storage_type: Depolama tipi.
            encryption: Sifreleme.
            compression: Sikistirma.
        """
        self.scheduler = BackupScheduler()
        self.executor = BackupExecutor()
        self.storage = BackupStorageBackend(
            backend_type=storage_type,
            encryption=encryption,
            compression=compression,
        )
        self.restore_manager = RestoreManager()
        self.replication = (
            BackupReplicationManager()
        )
        self.disaster_planner = (
            DisasterPlanner()
        )
        self.failover = FailoverController()
        self.tester = RecoveryTester()

        self._alerts: list[
            dict[str, Any]
        ] = []
        self._stats = {
            "backups_run": 0,
            "restores_run": 0,
            "failovers_triggered": 0,
        }

        logger.info(
            "BackupOrchestrator baslatildi",
        )

    def backup(
        self,
        backup_id: str,
        target: str,
        data: dict[str, Any],
        backup_type: str = "full",
        replicate: bool = False,
    ) -> dict[str, Any]:
        """Yedekleme yapar.

        Args:
            backup_id: Yedekleme ID.
            target: Hedef.
            data: Veri.
            backup_type: Tip.
            replicate: Replike et mi.

        Returns:
            Yedekleme sonucu.
        """
        # Yedekleme calistir
        if backup_type == "full":
            result = self.executor.run_full(
                backup_id, target, data,
            )
        elif backup_type == "incremental":
            result = self.executor.run_incremental(
                backup_id, target, data,
            )
        elif backup_type == "differential":
            result = self.executor.run_differential(
                backup_id, target, data,
            )
        else:
            result = self.executor.run_full(
                backup_id, target, data,
            )

        if result.get("status") != "completed":
            self._alerts.append({
                "type": "backup_failed",
                "backup_id": backup_id,
                "timestamp": time.time(),
            })
            return result

        # Depolama
        self.storage.store(
            f"backup/{backup_id}",
            data,
            {"type": backup_type, "target": target},
        )

        # Replikasyon
        if replicate:
            self.replication.replicate_to_all(
                backup_id,
                result.get("size_bytes", 0),
            )

        self._stats["backups_run"] += 1

        return {
            "backup_id": backup_id,
            "type": backup_type,
            "status": "completed",
            "replicated": replicate,
        }

    def restore(
        self,
        restore_id: str,
        backup_id: str,
        target: str = "",
    ) -> dict[str, Any]:
        """Geri yukleme yapar.

        Args:
            restore_id: Geri yukleme ID.
            backup_id: Yedekleme ID.
            target: Hedef.

        Returns:
            Geri yukleme sonucu.
        """
        # Yedekleme verisini al
        stored = self.storage.retrieve(
            f"backup/{backup_id}",
        )
        if not stored:
            return {
                "error": "backup_not_found",
            }

        # Geri yukle
        result = self.restore_manager.restore_full(
            restore_id,
            stored["data"],
            target,
        )

        self._stats["restores_run"] += 1

        return result

    def scheduled_backup(
        self,
        data: dict[str, Any],
        current_hour: int = 0,
    ) -> dict[str, Any]:
        """Zamanlanmis yedekleme calistirir.

        Args:
            data: Veri.
            current_hour: Mevcut saat.

        Returns:
            Sonuc.
        """
        due = self.scheduler.get_due_schedules(
            current_hour,
        )

        results: list[dict[str, Any]] = []
        for job in due:
            bid = f"sched_{job['schedule_id']}_{int(time.time())}"
            result = self.backup(
                bid,
                job["target"],
                data,
                job["backup_type"],
            )
            results.append(result)
            self.scheduler.mark_executed(
                job["schedule_id"],
            )

        return {
            "executed": len(results),
            "results": results,
        }

    def trigger_failover(
        self,
        target_node: str | None = None,
        mode: str = "automatic",
    ) -> dict[str, Any]:
        """Yuk devri tetikler.

        Args:
            target_node: Hedef dugum.
            mode: Mod.

        Returns:
            Yuk devri sonucu.
        """
        result = self.failover.failover(
            target_node, mode,
        )

        if result.get("status") == "completed":
            self._stats[
                "failovers_triggered"
            ] += 1

            self._alerts.append({
                "type": "failover_triggered",
                "from": result.get("from_node"),
                "to": result.get("to_node"),
                "mode": mode,
                "timestamp": time.time(),
            })

        return result

    def run_dr_drill(
        self,
        drill_id: str,
        plan_id: str,
    ) -> dict[str, Any]:
        """DR tatbikati calistirir.

        Args:
            drill_id: Tatbikat ID.
            plan_id: Plan ID.

        Returns:
            Tatbikat sonucu.
        """
        plan = self.disaster_planner.get_plan(
            plan_id,
        )
        if not plan:
            return {"error": "plan_not_found"}

        steps = [
            s["name"] for s in plan["steps"]
        ]
        return self.tester.run_drill(
            drill_id, plan_id, steps,
        )

    def verify_backup(
        self,
        backup_id: str,
    ) -> dict[str, Any]:
        """Yedeklemeyi dogrular.

        Args:
            backup_id: Yedekleme ID.

        Returns:
            Dogrulama sonucu.
        """
        stored = self.storage.retrieve(
            f"backup/{backup_id}",
        )
        if not stored:
            return {
                "error": "backup_not_found",
            }

        return self.tester.validate_backup(
            f"val_{backup_id}",
            stored["data"],
        )

    def get_alerts(
        self,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Uyarilari getirir.

        Args:
            limit: Limit.

        Returns:
            Uyari listesi.
        """
        return self._alerts[-limit:]

    def get_status(self) -> dict[str, Any]:
        """Genel durum bilgisi.

        Returns:
            Durum bilgisi.
        """
        return {
            "schedules": (
                self.scheduler.schedule_count
            ),
            "backups": (
                self.executor.backup_count
            ),
            "stored_files": (
                self.storage.file_count
            ),
            "restores": (
                self.restore_manager.restore_count
            ),
            "replication_targets": (
                self.replication.target_count
            ),
            "dr_plans": (
                self.disaster_planner.plan_count
            ),
            "failover_nodes": (
                self.failover.node_count
            ),
            "tests": (
                self.tester.test_count
            ),
            "alerts": len(self._alerts),
            "stats": dict(self._stats),
        }

    @property
    def alert_count(self) -> int:
        """Uyari sayisi."""
        return len(self._alerts)

    @property
    def backup_run_count(self) -> int:
        """Yedekleme calistirma sayisi."""
        return self._stats["backups_run"]

    @property
    def restore_run_count(self) -> int:
        """Geri yukleme calistirma sayisi."""
        return self._stats["restores_run"]

    @property
    def failover_trigger_count(self) -> int:
        """Yuk devri tetikleme sayisi."""
        return self._stats[
            "failovers_triggered"
        ]
