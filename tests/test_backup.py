"""ATLAS Backup & Disaster Recovery sistemi testleri."""

import time

import pytest

from app.core.backup.backup_scheduler import (
    BackupScheduler,
)
from app.core.backup.backup_executor import (
    BackupExecutor,
)
from app.core.backup.storage_backend import (
    BackupStorageBackend,
)
from app.core.backup.restore_manager import (
    RestoreManager,
)
from app.core.backup.replication_manager import (
    BackupReplicationManager,
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
from app.core.backup.backup_orchestrator import (
    BackupOrchestrator,
)
from app.models.backup_models import (
    BackupType,
    BackupStatus,
    StorageType,
    FailoverMode,
    DisasterSeverity,
    ReplicationMode,
    BackupRecord,
    RestoreRecord,
    DRPlanRecord,
    BackupSnapshot,
)


# ==================== BackupScheduler ====================


class TestBackupScheduler:
    """BackupScheduler testleri."""

    def test_init(self):
        """Baslatma testi."""
        bs = BackupScheduler()
        assert bs.schedule_count == 0
        assert bs.retention_policy_count == 0
        assert bs.window_count == 0

    def test_add_schedule(self):
        """Zamanlama ekleme."""
        bs = BackupScheduler()
        result = bs.add_schedule(
            "daily_full", "full",
            cron="0 2 * * *",
            target="db",
        )
        assert result["schedule_id"] == "daily_full"
        assert bs.schedule_count == 1

    def test_add_schedule_with_priority(self):
        """Oncelikli zamanlama."""
        bs = BackupScheduler()
        bs.add_schedule(
            "s1", priority=10,
        )
        sched = bs.get_schedule("s1")
        assert sched["priority"] == 10

    def test_remove_schedule(self):
        """Zamanlama kaldirma."""
        bs = BackupScheduler()
        bs.add_schedule("s1")
        assert bs.remove_schedule("s1")
        assert bs.schedule_count == 0

    def test_remove_nonexistent(self):
        """Olmayan zamanlama kaldirma."""
        bs = BackupScheduler()
        assert not bs.remove_schedule("x")

    def test_enable_disable(self):
        """Etkinlestirme/devre disi."""
        bs = BackupScheduler()
        bs.add_schedule("s1")
        assert bs.disable_schedule("s1")
        sched = bs.get_schedule("s1")
        assert not sched["enabled"]
        assert bs.enable_schedule("s1")
        sched = bs.get_schedule("s1")
        assert sched["enabled"]

    def test_enable_nonexistent(self):
        """Olmayan etkinlestirme."""
        bs = BackupScheduler()
        assert not bs.enable_schedule("x")
        assert not bs.disable_schedule("x")

    def test_get_schedule(self):
        """Zamanlama getirme."""
        bs = BackupScheduler()
        bs.add_schedule("s1", "full", target="db")
        sched = bs.get_schedule("s1")
        assert sched is not None
        assert sched["target"] == "db"

    def test_get_nonexistent(self):
        """Olmayan zamanlama."""
        bs = BackupScheduler()
        assert bs.get_schedule("x") is None

    def test_set_retention_policy(self):
        """Saklama politikasi."""
        bs = BackupScheduler()
        result = bs.set_retention_policy(
            "standard",
            daily=7, weekly=4,
            monthly=12, yearly=1,
        )
        assert result["total_kept"] == 24
        assert bs.retention_policy_count == 1

    def test_get_retention_policy(self):
        """Saklama politikasi getirme."""
        bs = BackupScheduler()
        bs.set_retention_policy(
            "p1", daily=14,
        )
        p = bs.get_retention_policy("p1")
        assert p["daily"] == 14

    def test_get_retention_nonexistent(self):
        """Olmayan politika."""
        bs = BackupScheduler()
        assert bs.get_retention_policy("x") is None

    def test_set_backup_window(self):
        """Yedekleme penceresi."""
        bs = BackupScheduler()
        result = bs.set_backup_window(
            "night", start_hour=2, end_hour=6,
        )
        assert result["hours"] == "2-6"
        assert bs.window_count == 1

    def test_is_in_window(self):
        """Pencere icinde mi."""
        bs = BackupScheduler()
        bs.set_backup_window(
            "night", start_hour=2, end_hour=6,
        )
        assert bs.is_in_window("night", 3)
        assert not bs.is_in_window("night", 10)

    def test_is_in_window_day_filter(self):
        """Gun filtreli pencere."""
        bs = BackupScheduler()
        bs.set_backup_window(
            "weekday", start_hour=2, end_hour=6,
            days=["mon", "tue", "wed"],
        )
        assert bs.is_in_window(
            "weekday", 3, "mon",
        )
        assert not bs.is_in_window(
            "weekday", 3, "sat",
        )

    def test_is_in_window_nonexistent(self):
        """Olmayan pencere - varsayilan True."""
        bs = BackupScheduler()
        assert bs.is_in_window("x", 3)

    def test_get_due_schedules(self):
        """Zamani gelen zamanlamalar."""
        bs = BackupScheduler()
        bs.add_schedule("s1", priority=5)
        bs.add_schedule("s2", priority=10)
        due = bs.get_due_schedules()
        assert len(due) == 2
        assert due[0]["priority"] >= due[1]["priority"]

    def test_get_due_skips_disabled(self):
        """Devre disi atlama."""
        bs = BackupScheduler()
        bs.add_schedule("s1")
        bs.add_schedule("s2", enabled=False)
        due = bs.get_due_schedules()
        assert len(due) == 1

    def test_mark_executed(self):
        """Calistirildi isareti."""
        bs = BackupScheduler()
        bs.add_schedule("s1")
        assert bs.mark_executed("s1")
        sched = bs.get_schedule("s1")
        assert sched["last_run"] is not None

    def test_mark_executed_nonexistent(self):
        """Olmayan zamanlama isareti."""
        bs = BackupScheduler()
        assert not bs.mark_executed("x")

    def test_add_calendar_event(self):
        """Takvim olayi."""
        bs = BackupScheduler()
        event = bs.add_calendar_event(
            "maintenance", time.time(),
        )
        assert event["type"] == "maintenance"
        assert bs.calendar_count == 1

    def test_list_schedules(self):
        """Zamanlama listeleme."""
        bs = BackupScheduler()
        bs.add_schedule("s1")
        bs.add_schedule("s2", enabled=False)
        assert len(bs.list_schedules()) == 2
        assert len(
            bs.list_schedules(enabled_only=True),
        ) == 1


# ==================== BackupExecutor ====================


class TestBackupExecutor:
    """BackupExecutor testleri."""

    def test_init(self):
        """Baslatma testi."""
        be = BackupExecutor()
        assert be.backup_count == 0
        assert be.full_count == 0

    def test_run_full(self):
        """Tam yedekleme."""
        be = BackupExecutor()
        result = be.run_full(
            "b1", "db", {"table": "users"},
        )
        assert result["status"] == "completed"
        assert result["type"] == "full"
        assert be.backup_count == 1
        assert be.full_count == 1

    def test_run_incremental(self):
        """Artimsal yedekleme."""
        be = BackupExecutor()
        be.run_full("b0", "db", {"a": 1})
        result = be.run_incremental(
            "b1", "db", {"b": 2},
        )
        assert result["status"] == "completed"
        assert result["type"] == "incremental"
        assert be.incremental_count == 1

    def test_run_incremental_no_parent(self):
        """Ebeveyn olmadan artimsal."""
        be = BackupExecutor()
        result = be.run_incremental(
            "b1", "db", {"a": 1},
        )
        assert result["status"] == "failed"
        assert "no_parent" in result["error"]

    def test_run_differential(self):
        """Diferansiyel yedekleme."""
        be = BackupExecutor()
        be.run_full("b0", "db", {"a": 1})
        result = be.run_differential(
            "b1", "db", {"b": 2},
        )
        assert result["status"] == "completed"
        assert result["type"] == "differential"

    def test_run_differential_no_full(self):
        """Full olmadan diferansiyel."""
        be = BackupExecutor()
        result = be.run_differential(
            "b1", "db", {"a": 1},
        )
        assert result["status"] == "failed"

    def test_run_parallel(self):
        """Paralel yedekleme."""
        be = BackupExecutor()
        jobs = [
            {"backup_id": "b1", "type": "full",
             "target": "db1", "data": {"a": 1}},
            {"backup_id": "b2", "type": "full",
             "target": "db2", "data": {"b": 2}},
        ]
        result = be.run_parallel(jobs)
        assert result["total"] == 2
        assert result["completed"] == 2
        assert result["failed"] == 0

    def test_run_parallel_mixed(self):
        """Karisik paralel."""
        be = BackupExecutor()
        be.run_full("base", "db", {"x": 1})
        jobs = [
            {"backup_id": "b1", "type": "full",
             "target": "db", "data": {"a": 1}},
            {"backup_id": "b2",
             "type": "incremental",
             "target": "db", "data": {"b": 2}},
        ]
        result = be.run_parallel(jobs)
        assert result["completed"] == 2

    def test_get_backup(self):
        """Yedekleme getirme."""
        be = BackupExecutor()
        be.run_full("b1", "db", {"a": 1})
        backup = be.get_backup("b1")
        assert backup is not None
        assert backup["type"] == "full"

    def test_get_backup_nonexistent(self):
        """Olmayan yedekleme."""
        be = BackupExecutor()
        assert be.get_backup("x") is None

    def test_get_progress_completed(self):
        """Tamamlanmis ilerleme."""
        be = BackupExecutor()
        be.run_full("b1", "db")
        progress = be.get_progress("b1")
        assert progress["progress"] == 100

    def test_get_progress_not_found(self):
        """Bulunamayan ilerleme."""
        be = BackupExecutor()
        progress = be.get_progress("x")
        assert progress["status"] == "not_found"

    def test_list_backups(self):
        """Yedekleme listeleme."""
        be = BackupExecutor()
        be.run_full("b1", "db1")
        be.run_full("b2", "db2")
        assert len(be.list_backups()) == 2

    def test_list_backups_by_target(self):
        """Hedef filtreli listeleme."""
        be = BackupExecutor()
        be.run_full("b1", "db1")
        be.run_full("b2", "db2")
        result = be.list_backups(target="db1")
        assert len(result) == 1

    def test_list_backups_by_type(self):
        """Tip filtreli listeleme."""
        be = BackupExecutor()
        be.run_full("b1", "db")
        be.run_full("base", "db2")
        be.run_incremental("b2", "db2", {"a": 1})
        result = be.list_backups(
            backup_type="incremental",
        )
        assert len(result) == 1

    def test_total_bytes(self):
        """Toplam boyut."""
        be = BackupExecutor()
        be.run_full("b1", "db", {"data": "x"})
        assert be.total_bytes > 0

    def test_get_stats(self):
        """Istatistikler."""
        be = BackupExecutor()
        be.run_full("b1", "db")
        stats = be.get_stats()
        assert stats["full"] == 1


# ==================== BackupStorageBackend ====================


class TestBackupStorageBackend:
    """BackupStorageBackend testleri."""

    def test_init(self):
        """Baslatma testi."""
        sb = BackupStorageBackend()
        assert sb.file_count == 0
        assert sb.backend_type == "local"
        assert not sb.encryption_enabled
        assert not sb.compression_enabled

    def test_init_with_options(self):
        """Secenekli baslatma."""
        sb = BackupStorageBackend(
            "s3", encryption=True,
            compression=True,
        )
        assert sb.backend_type == "s3"
        assert sb.encryption_enabled
        assert sb.compression_enabled

    def test_store(self):
        """Veri depolama."""
        sb = BackupStorageBackend()
        result = sb.store(
            "backup/b1", {"data": "test"},
        )
        assert result["status"] == "stored"
        assert sb.file_count == 1

    def test_store_with_compression(self):
        """Sikistirmali depolama."""
        sb = BackupStorageBackend(
            compression=True,
        )
        result = sb.store(
            "backup/b1", {"data": "test"},
        )
        assert result["stored_size"] < (
            result["raw_size"]
        )

    def test_store_with_metadata(self):
        """Metadatali depolama."""
        sb = BackupStorageBackend()
        sb.store(
            "b1", "data",
            metadata={"type": "full"},
        )
        entry = sb.retrieve("b1")
        assert entry["metadata"]["type"] == "full"

    def test_retrieve(self):
        """Veri getirme."""
        sb = BackupStorageBackend()
        sb.store("b1", {"key": "value"})
        entry = sb.retrieve("b1")
        assert entry is not None
        assert entry["data"]["key"] == "value"

    def test_retrieve_nonexistent(self):
        """Olmayan veri."""
        sb = BackupStorageBackend()
        assert sb.retrieve("x") is None

    def test_delete(self):
        """Veri silme."""
        sb = BackupStorageBackend()
        sb.store("b1", "data")
        assert sb.delete("b1")
        assert sb.file_count == 0

    def test_delete_nonexistent(self):
        """Olmayan veri silme."""
        sb = BackupStorageBackend()
        assert not sb.delete("x")

    def test_exists(self):
        """Var mi kontrolu."""
        sb = BackupStorageBackend()
        sb.store("b1", "data")
        assert sb.exists("b1")
        assert not sb.exists("x")

    def test_list_files(self):
        """Dosya listeleme."""
        sb = BackupStorageBackend()
        sb.store("backup/b1", "d1")
        sb.store("backup/b2", "d2")
        sb.store("other/o1", "d3")
        assert len(sb.list_files()) == 3
        assert len(
            sb.list_files(prefix="backup/"),
        ) == 2

    def test_get_usage(self):
        """Kullanim bilgisi."""
        sb = BackupStorageBackend()
        sb.store("b1", "data")
        usage = sb.get_usage()
        assert usage["file_count"] == 1
        assert usage["total_bytes"] > 0

    def test_copy(self):
        """Dosya kopyalama."""
        sb = BackupStorageBackend()
        sb.store("b1", {"key": "val"})
        result = sb.copy("b1", "b2")
        assert result["status"] == "copied"
        assert sb.file_count == 2

    def test_copy_nonexistent(self):
        """Olmayan dosya kopyalama."""
        sb = BackupStorageBackend()
        result = sb.copy("x", "y")
        assert "error" in result

    def test_get_stats(self):
        """Istatistikler."""
        sb = BackupStorageBackend()
        sb.store("b1", "data")
        stats = sb.get_stats()
        assert stats["stored"] == 1


# ==================== RestoreManager ====================


class TestRestoreManager:
    """RestoreManager testleri."""

    def test_init(self):
        """Baslatma testi."""
        rm = RestoreManager()
        assert rm.restore_count == 0
        assert rm.verified_count == 0

    def test_restore_full(self):
        """Tam geri yukleme."""
        rm = RestoreManager()
        result = rm.restore_full(
            "r1", {"table": "users"}, "db",
        )
        assert result["status"] == "completed"
        assert result["type"] == "full"
        assert rm.restore_count == 1

    def test_restore_selective(self):
        """Secmeli geri yukleme."""
        rm = RestoreManager()
        result = rm.restore_selective(
            "r1",
            {"a": 1, "b": 2, "c": 3},
            ["a", "c"],
        )
        assert result["status"] == "completed"
        assert result["restored_count"] == 2

    def test_restore_point_in_time(self):
        """Zamana gore geri yukleme."""
        rm = RestoreManager()
        now = time.time()
        backups = [
            {"backup_id": "b1",
             "completed_at": now - 100,
             "data": {"v": 1}},
            {"backup_id": "b2",
             "completed_at": now - 50,
             "data": {"v": 2}},
            {"backup_id": "b3",
             "completed_at": now + 100,
             "data": {"v": 3}},
        ]
        result = rm.restore_point_in_time(
            "r1", backups, now,
        )
        assert result["status"] == "completed"
        assert result["source_backup"] == "b2"

    def test_restore_point_in_time_no_backup(self):
        """Yedek bulunamayan zamana gore."""
        rm = RestoreManager()
        result = rm.restore_point_in_time(
            "r1", [], time.time(),
        )
        assert result["status"] == "failed"
        assert rm.failed_count == 1

    def test_verify_success(self):
        """Basarili dogrulama."""
        rm = RestoreManager()
        rm.restore_full(
            "r1", {"key": "value"},
        )
        result = rm.verify(
            "r1", {"key": "value"},
        )
        assert result["verified"]
        assert rm.verified_count == 1

    def test_verify_failure(self):
        """Basarisiz dogrulama."""
        rm = RestoreManager()
        rm.restore_full(
            "r1", {"key": "wrong"},
        )
        result = rm.verify(
            "r1", {"key": "expected"},
        )
        assert not result["verified"]

    def test_verify_not_found(self):
        """Bulunamayan dogrulama."""
        rm = RestoreManager()
        result = rm.verify("x")
        assert not result["verified"]

    def test_verify_no_expected(self):
        """Beklenen yok - durum kontrolu."""
        rm = RestoreManager()
        rm.restore_full("r1", {"a": 1})
        result = rm.verify("r1")
        assert result["verified"]

    def test_rollback(self):
        """Geri alma."""
        rm = RestoreManager()
        rm.restore_full("r1", {"a": 1})
        result = rm.rollback("r1")
        assert result["status"] == "rolled_back"
        assert rm.rolled_back_count == 1

    def test_rollback_not_found(self):
        """Bulunamayan geri alma."""
        rm = RestoreManager()
        result = rm.rollback("x")
        assert "error" in result

    def test_get_restore(self):
        """Geri yukleme getirme."""
        rm = RestoreManager()
        rm.restore_full("r1", {"a": 1})
        r = rm.get_restore("r1")
        assert r is not None

    def test_get_restore_nonexistent(self):
        """Olmayan geri yukleme."""
        rm = RestoreManager()
        assert rm.get_restore("x") is None

    def test_list_restores(self):
        """Geri yukleme listeleme."""
        rm = RestoreManager()
        rm.restore_full("r1", {})
        rm.restore_full("r2", {})
        assert len(rm.list_restores()) == 2


# ==================== BackupReplicationManager ====================


class TestBackupReplicationManager:
    """BackupReplicationManager testleri."""

    def test_init(self):
        """Baslatma testi."""
        rm = BackupReplicationManager()
        assert rm.target_count == 0
        assert rm.replication_count == 0

    def test_add_target(self):
        """Hedef ekleme."""
        rm = BackupReplicationManager()
        result = rm.add_target(
            "eu", region="eu-west-1",
            mode="async",
        )
        assert result["status"] == "added"
        assert rm.target_count == 1

    def test_remove_target(self):
        """Hedef kaldirma."""
        rm = BackupReplicationManager()
        rm.add_target("eu")
        assert rm.remove_target("eu")
        assert rm.target_count == 0

    def test_remove_nonexistent(self):
        """Olmayan hedef."""
        rm = BackupReplicationManager()
        assert not rm.remove_target("x")

    def test_replicate(self):
        """Replikasyon."""
        rm = BackupReplicationManager()
        rm.add_target("eu")
        result = rm.replicate(
            "b1", "eu", 1000,
        )
        assert result["status"] == "completed"
        assert rm.replication_count == 1
        assert rm.replicated_total == 1

    def test_replicate_not_found(self):
        """Hedef bulunamayan."""
        rm = BackupReplicationManager()
        result = rm.replicate("b1", "x")
        assert "error" in result

    def test_replicate_disabled(self):
        """Devre disi hedef."""
        rm = BackupReplicationManager()
        rm.add_target("eu")
        rm.disable_target("eu")
        result = rm.replicate("b1", "eu")
        assert "error" in result

    def test_replicate_to_all(self):
        """Tum hedeflere replikasyon."""
        rm = BackupReplicationManager()
        rm.add_target("eu")
        rm.add_target("us")
        result = rm.replicate_to_all(
            "b1", 500,
        )
        assert result["total"] == 2
        assert result["success"] == 2

    def test_check_consistency(self):
        """Tutarlilik kontrolu."""
        rm = BackupReplicationManager()
        rm.add_target("eu")
        rm.replicate("b1", "eu")
        rm.replicate("b2", "eu")
        result = rm.check_consistency(
            "eu", ["b1", "b2", "b3"],
        )
        assert not result["consistent"]
        assert "b3" in result["missing"]

    def test_check_consistency_ok(self):
        """Tutarli kontrol."""
        rm = BackupReplicationManager()
        rm.add_target("eu")
        rm.replicate("b1", "eu")
        result = rm.check_consistency(
            "eu", ["b1"],
        )
        assert result["consistent"]

    def test_get_lag(self):
        """Gecikme bilgisi."""
        rm = BackupReplicationManager()
        rm.add_target("eu")
        rm.replicate("b1", "eu")
        lag = rm.get_lag("eu")
        assert lag["samples"] == 1

    def test_get_lag_empty(self):
        """Bos gecikme."""
        rm = BackupReplicationManager()
        lag = rm.get_lag("x")
        assert lag["samples"] == 0

    def test_enable_disable_target(self):
        """Hedef etkinlestirme/devre disi."""
        rm = BackupReplicationManager()
        rm.add_target("eu")
        assert rm.disable_target("eu")
        t = rm.get_target("eu")
        assert not t["enabled"]
        assert rm.enable_target("eu")

    def test_enable_nonexistent(self):
        """Olmayan etkinlestirme."""
        rm = BackupReplicationManager()
        assert not rm.enable_target("x")
        assert not rm.disable_target("x")

    def test_get_target(self):
        """Hedef getirme."""
        rm = BackupReplicationManager()
        rm.add_target("eu", region="eu-west-1")
        t = rm.get_target("eu")
        assert t["region"] == "eu-west-1"

    def test_list_targets(self):
        """Hedef listeleme."""
        rm = BackupReplicationManager()
        rm.add_target("eu")
        rm.add_target("us")
        assert len(rm.list_targets()) == 2

    def test_bytes_transferred(self):
        """Aktarilan bayt."""
        rm = BackupReplicationManager()
        rm.add_target("eu")
        rm.replicate("b1", "eu", 1000)
        assert rm.bytes_transferred == 1000


# ==================== DisasterPlanner ====================


class TestDisasterPlanner:
    """DisasterPlanner testleri."""

    def test_init(self):
        """Baslatma testi."""
        dp = DisasterPlanner()
        assert dp.plan_count == 0
        assert dp.contact_count == 0

    def test_create_plan(self):
        """Plan olusturma."""
        dp = DisasterPlanner()
        result = dp.create_plan(
            "dr1", "Database DR",
            rto_minutes=30,
            rpo_minutes=5,
        )
        assert result["plan_id"] == "dr1"
        assert result["rto"] == 30
        assert dp.plan_count == 1

    def test_get_plan(self):
        """Plan getirme."""
        dp = DisasterPlanner()
        dp.create_plan("dr1", "Test DR")
        plan = dp.get_plan("dr1")
        assert plan is not None
        assert plan["name"] == "Test DR"

    def test_get_plan_nonexistent(self):
        """Olmayan plan."""
        dp = DisasterPlanner()
        assert dp.get_plan("x") is None

    def test_remove_plan(self):
        """Plan kaldirma."""
        dp = DisasterPlanner()
        dp.create_plan("dr1", "Test")
        assert dp.remove_plan("dr1")
        assert dp.plan_count == 0

    def test_remove_nonexistent(self):
        """Olmayan plan kaldirma."""
        dp = DisasterPlanner()
        assert not dp.remove_plan("x")

    def test_add_step(self):
        """Adim ekleme."""
        dp = DisasterPlanner()
        dp.create_plan("dr1", "Test")
        result = dp.add_step(
            "dr1", "Stop traffic",
            action="dns_switch",
        )
        assert result["order"] == 1

    def test_add_step_not_found(self):
        """Olmayan plana adim."""
        dp = DisasterPlanner()
        result = dp.add_step("x", "step1")
        assert "error" in result

    def test_add_contact(self):
        """Iletisim ekleme."""
        dp = DisasterPlanner()
        result = dp.add_contact(
            "c1", "Fatih", role="admin",
            email="f@x.com",
        )
        assert result["name"] == "Fatih"
        assert dp.contact_count == 1

    def test_remove_contact(self):
        """Iletisim kaldirma."""
        dp = DisasterPlanner()
        dp.add_contact("c1", "Fatih")
        assert dp.remove_contact("c1")
        assert dp.contact_count == 0

    def test_remove_contact_nonexistent(self):
        """Olmayan iletisim."""
        dp = DisasterPlanner()
        assert not dp.remove_contact("x")

    def test_get_contacts(self):
        """Iletisim listeleme."""
        dp = DisasterPlanner()
        dp.add_contact(
            "c1", "A", role="admin", priority=1,
        )
        dp.add_contact(
            "c2", "B", role="dev", priority=2,
        )
        contacts = dp.get_contacts()
        assert len(contacts) == 2
        assert contacts[0]["priority"] <= (
            contacts[1]["priority"]
        )

    def test_get_contacts_by_role(self):
        """Role gore iletisim."""
        dp = DisasterPlanner()
        dp.add_contact("c1", "A", role="admin")
        dp.add_contact("c2", "B", role="dev")
        admins = dp.get_contacts(role="admin")
        assert len(admins) == 1

    def test_create_runbook(self):
        """Runbook olusturma."""
        dp = DisasterPlanner()
        result = dp.create_runbook(
            "rb1", "DB Recovery",
            ["Stop app", "Restore DB", "Verify"],
        )
        assert result["steps_count"] == 3
        assert dp.runbook_count == 1

    def test_get_runbook(self):
        """Runbook getirme."""
        dp = DisasterPlanner()
        dp.create_runbook(
            "rb1", "Test", ["s1"],
        )
        rb = dp.get_runbook("rb1")
        assert rb is not None
        assert rb["title"] == "Test"

    def test_get_runbook_nonexistent(self):
        """Olmayan runbook."""
        dp = DisasterPlanner()
        assert dp.get_runbook("x") is None

    def test_set_escalation(self):
        """Eskalasyon ayarlama."""
        dp = DisasterPlanner()
        result = dp.set_escalation([
            {"level": 1, "min_severity": 1},
            {"level": 2, "min_severity": 3},
        ])
        assert result["levels"] == 2
        assert dp.escalation_level_count == 2

    def test_get_escalation_path(self):
        """Eskalasyon yolu."""
        dp = DisasterPlanner()
        dp.set_escalation([
            {"level": 1, "min_severity": 1},
            {"level": 2, "min_severity": 3},
            {"level": 3, "min_severity": 5},
        ])
        path = dp.get_escalation_path("high")
        assert len(path) == 2

    def test_activate_plan(self):
        """Plan aktivasyonu."""
        dp = DisasterPlanner()
        dp.create_plan("dr1", "Test")
        result = dp.activate_plan("dr1")
        assert result["status"] == "activated"
        assert dp.activation_count == 1

    def test_activate_nonexistent(self):
        """Olmayan plan aktivasyonu."""
        dp = DisasterPlanner()
        result = dp.activate_plan("x")
        assert "error" in result

    def test_list_plans(self):
        """Plan listeleme."""
        dp = DisasterPlanner()
        dp.create_plan("dr1", "A")
        dp.create_plan("dr2", "B")
        assert len(dp.list_plans()) == 2

    def test_list_plans_by_status(self):
        """Duruma gore listeleme."""
        dp = DisasterPlanner()
        dp.create_plan("dr1", "A")
        dp.create_plan("dr2", "B")
        dp.activate_plan("dr1")
        active = dp.list_plans(
            status="activated",
        )
        assert len(active) == 1


# ==================== FailoverController ====================


class TestFailoverController:
    """FailoverController testleri."""

    def test_init(self):
        """Baslatma testi."""
        fc = FailoverController()
        assert fc.node_count == 0
        assert fc.failover_count == 0
        assert fc.get_active_node() is None

    def test_add_node(self):
        """Dugum ekleme."""
        fc = FailoverController()
        result = fc.add_node(
            "n1", endpoint="10.0.0.1",
            is_primary=True,
        )
        assert result["status"] == "added"
        assert fc.node_count == 1
        assert fc.get_active_node() == "n1"

    def test_add_secondary_node(self):
        """Ikincil dugum."""
        fc = FailoverController()
        fc.add_node("n1", is_primary=True)
        fc.add_node("n2")
        assert fc.node_count == 2
        assert fc.get_active_node() == "n1"

    def test_remove_node(self):
        """Dugum kaldirma."""
        fc = FailoverController()
        fc.add_node("n1")
        assert fc.remove_node("n1")
        assert fc.node_count == 0

    def test_remove_nonexistent(self):
        """Olmayan dugum."""
        fc = FailoverController()
        assert not fc.remove_node("x")

    def test_remove_active_node(self):
        """Aktif dugum kaldirma."""
        fc = FailoverController()
        fc.add_node("n1", is_primary=True)
        fc.remove_node("n1")
        assert fc.get_active_node() is None

    def test_check_health_healthy(self):
        """Saglikli kontrol."""
        fc = FailoverController()
        fc.add_node("n1")
        result = fc.check_health(
            "n1", healthy=True,
        )
        assert result["healthy"]
        assert not result["trigger_failover"]

    def test_check_health_unhealthy(self):
        """Sagliksiz kontrol."""
        fc = FailoverController()
        fc.add_node("n1", is_primary=True)
        result = fc.check_health(
            "n1", healthy=False,
        )
        assert not result["healthy"]
        assert result["trigger_failover"]

    def test_check_health_not_found(self):
        """Olmayan dugum kontrolu."""
        fc = FailoverController()
        result = fc.check_health("x")
        assert "error" in result

    def test_automatic_failover(self):
        """Otomatik yuk devri."""
        fc = FailoverController()
        fc.add_node("n1", is_primary=True)
        fc.add_node("n2", priority=8)
        result = fc.failover(
            mode="automatic",
        )
        assert result["status"] == "completed"
        assert result["to_node"] == "n2"
        assert fc.auto_failover_count == 1

    def test_manual_failover(self):
        """Manuel yuk devri."""
        fc = FailoverController()
        fc.add_node("n1", is_primary=True)
        fc.add_node("n2")
        result = fc.failover(
            target_node="n2",
            mode="manual",
        )
        assert result["status"] == "completed"
        assert fc.get_active_node() == "n2"
        assert fc.failover_count == 1

    def test_failover_no_healthy(self):
        """Saglikli dugum yok."""
        fc = FailoverController()
        fc.add_node("n1", is_primary=True)
        fc.check_health("n1", healthy=False)
        result = fc.failover()
        assert "error" in result

    def test_failover_target_not_found(self):
        """Hedef bulunamayan yuk devri."""
        fc = FailoverController()
        result = fc.failover(target_node="x")
        assert "error" in result

    def test_set_dns_record(self):
        """DNS kaydi."""
        fc = FailoverController()
        result = fc.set_dns_record(
            "app.example.com", "10.0.0.1",
        )
        assert result["target"] == "10.0.0.1"
        assert fc.dns_record_count == 1

    def test_switch_dns(self):
        """DNS degistirme."""
        fc = FailoverController()
        fc.set_dns_record(
            "app.example.com", "10.0.0.1",
        )
        result = fc.switch_dns(
            "app.example.com", "10.0.0.2",
        )
        assert result["old_target"] == "10.0.0.1"
        assert result["new_target"] == "10.0.0.2"

    def test_add_traffic_rule(self):
        """Trafik kurali."""
        fc = FailoverController()
        result = fc.add_traffic_rule(
            "r1", target="n1", weight=80,
        )
        assert result["weight"] == 80
        assert fc.traffic_rule_count == 1

    def test_get_node(self):
        """Dugum bilgisi."""
        fc = FailoverController()
        fc.add_node("n1", region="eu")
        node = fc.get_node("n1")
        assert node["region"] == "eu"

    def test_list_nodes(self):
        """Dugum listeleme."""
        fc = FailoverController()
        fc.add_node("n1")
        fc.add_node("n2")
        assert len(fc.list_nodes()) == 2

    def test_list_healthy_only(self):
        """Sadece saglikliler."""
        fc = FailoverController()
        fc.add_node("n1")
        fc.add_node("n2")
        fc.check_health("n2", healthy=False)
        healthy = fc.list_nodes(
            healthy_only=True,
        )
        assert len(healthy) == 1

    def test_get_history(self):
        """Yuk devri gecmisi."""
        fc = FailoverController()
        fc.add_node("n1", is_primary=True)
        fc.add_node("n2")
        fc.failover()
        history = fc.get_history()
        assert len(history) == 1


# ==================== RecoveryTester ====================


class TestRecoveryTester:
    """RecoveryTester testleri."""

    def test_init(self):
        """Baslatma testi."""
        rt = RecoveryTester()
        assert rt.test_count == 0
        assert rt.drill_count == 0

    def test_run_restore_test_pass(self):
        """Gecen geri yukleme testi."""
        rt = RecoveryTester()
        result = rt.run_restore_test(
            "t1", {"a": 1}, {"a": 1},
        )
        assert result["passed"]
        assert rt.passed_count == 1

    def test_run_restore_test_fail(self):
        """Kalan geri yukleme testi."""
        rt = RecoveryTester()
        result = rt.run_restore_test(
            "t1", {"a": 1}, {"a": 2},
        )
        assert not result["passed"]
        assert rt.failed_count == 1

    def test_run_restore_test_no_expected(self):
        """Beklenen olmadan test."""
        rt = RecoveryTester()
        result = rt.run_restore_test(
            "t1", {"a": 1},
        )
        assert result["passed"]

    def test_run_drill(self):
        """DR tatbikati."""
        rt = RecoveryTester()
        result = rt.run_drill(
            "d1", "dr1",
            ["Stop", "Restore", "Verify"],
        )
        assert result["passed"]
        assert result["steps_completed"] == 3
        assert rt.drill_count == 1

    def test_validate_backup(self):
        """Yedekleme dogrulama."""
        rt = RecoveryTester()
        result = rt.validate_backup(
            "v1", {"data": "test"},
        )
        assert result["passed"]
        assert rt.validation_count == 1

    def test_validate_backup_empty(self):
        """Bos yedekleme dogrulama."""
        rt = RecoveryTester()
        result = rt.validate_backup(
            "v1", {},
            checks=["not_empty"],
        )
        assert not result["passed"]

    def test_validate_with_metadata(self):
        """Metadata kontrollü dogrulama."""
        rt = RecoveryTester()
        result = rt.validate_backup(
            "v1",
            {"metadata": {}, "data": "x"},
            checks=["has_metadata"],
        )
        assert result["passed"]

    def test_measure_performance(self):
        """Performans olcumu."""
        rt = RecoveryTester()
        result = rt.measure_performance(
            "t1", data_size=1000, duration=0.5,
        )
        assert result["throughput_bps"] == 2000

    def test_get_test(self):
        """Test getirme."""
        rt = RecoveryTester()
        rt.run_restore_test("t1", {"a": 1})
        t = rt.get_test("t1")
        assert t is not None

    def test_get_test_nonexistent(self):
        """Olmayan test."""
        rt = RecoveryTester()
        assert rt.get_test("x") is None

    def test_get_drill(self):
        """Tatbikat getirme."""
        rt = RecoveryTester()
        rt.run_drill("d1", "p1", ["s1"])
        d = rt.get_drill("d1")
        assert d is not None

    def test_get_drill_nonexistent(self):
        """Olmayan tatbikat."""
        rt = RecoveryTester()
        assert rt.get_drill("x") is None

    def test_get_report(self):
        """Rapor."""
        rt = RecoveryTester()
        rt.run_restore_test("t1", {"a": 1})
        report = rt.get_report()
        assert report["total_tests"] == 1
        assert report["passed"] == 1

    def test_list_tests(self):
        """Test listeleme."""
        rt = RecoveryTester()
        rt.run_restore_test("t1", {"a": 1})
        rt.run_restore_test("t2", {"b": 2})
        assert len(rt.list_tests()) == 2

    def test_list_drills(self):
        """Tatbikat listeleme."""
        rt = RecoveryTester()
        rt.run_drill("d1", "p1", ["s1"])
        assert len(rt.list_drills()) == 1


# ==================== BackupOrchestrator ====================


class TestBackupOrchestrator:
    """BackupOrchestrator testleri."""

    def test_init(self):
        """Baslatma testi."""
        orch = BackupOrchestrator()
        assert orch.backup_run_count == 0
        assert orch.restore_run_count == 0
        assert orch.alert_count == 0

    def test_init_with_options(self):
        """Secenekli baslatma."""
        orch = BackupOrchestrator(
            storage_type="s3",
            encryption=True,
            compression=True,
        )
        assert orch.storage.backend_type == "s3"
        assert orch.storage.encryption_enabled
        assert orch.storage.compression_enabled

    def test_components_initialized(self):
        """Bilesenlerin baslatilmasi."""
        orch = BackupOrchestrator()
        assert orch.scheduler is not None
        assert orch.executor is not None
        assert orch.storage is not None
        assert orch.restore_manager is not None
        assert orch.replication is not None
        assert orch.disaster_planner is not None
        assert orch.failover is not None
        assert orch.tester is not None

    def test_backup_full(self):
        """Tam yedekleme."""
        orch = BackupOrchestrator()
        result = orch.backup(
            "b1", "db", {"table": "users"},
        )
        assert result["status"] == "completed"
        assert orch.backup_run_count == 1

    def test_backup_incremental(self):
        """Artimsal yedekleme."""
        orch = BackupOrchestrator()
        orch.backup("b0", "db", {"a": 1})
        result = orch.backup(
            "b1", "db", {"b": 2},
            backup_type="incremental",
        )
        assert result["status"] == "completed"

    def test_backup_with_replication(self):
        """Replikasyonlu yedekleme."""
        orch = BackupOrchestrator()
        orch.replication.add_target("eu")
        result = orch.backup(
            "b1", "db", {"a": 1},
            replicate=True,
        )
        assert result["replicated"]

    def test_backup_stored(self):
        """Yedekleme depolanmis mi."""
        orch = BackupOrchestrator()
        orch.backup("b1", "db", {"a": 1})
        assert orch.storage.exists("backup/b1")

    def test_restore(self):
        """Geri yukleme."""
        orch = BackupOrchestrator()
        orch.backup(
            "b1", "db", {"table": "users"},
        )
        result = orch.restore(
            "r1", "b1", "db",
        )
        assert result["status"] == "completed"
        assert orch.restore_run_count == 1

    def test_restore_not_found(self):
        """Bulunamayan geri yukleme."""
        orch = BackupOrchestrator()
        result = orch.restore("r1", "x")
        assert "error" in result

    def test_scheduled_backup(self):
        """Zamanlanmis yedekleme."""
        orch = BackupOrchestrator()
        orch.scheduler.add_schedule(
            "daily", "full", target="db",
        )
        result = orch.scheduled_backup(
            {"data": "test"},
        )
        assert result["executed"] == 1

    def test_trigger_failover(self):
        """Yuk devri tetikleme."""
        orch = BackupOrchestrator()
        orch.failover.add_node(
            "n1", is_primary=True,
        )
        orch.failover.add_node("n2")
        result = orch.trigger_failover()
        assert result["status"] == "completed"
        assert orch.failover_trigger_count == 1
        assert orch.alert_count >= 1

    def test_run_dr_drill(self):
        """DR tatbikati."""
        orch = BackupOrchestrator()
        orch.disaster_planner.create_plan(
            "dr1", "Test DR",
        )
        orch.disaster_planner.add_step(
            "dr1", "Stop traffic",
        )
        orch.disaster_planner.add_step(
            "dr1", "Restore DB",
        )
        result = orch.run_dr_drill(
            "d1", "dr1",
        )
        assert result["passed"]

    def test_run_dr_drill_not_found(self):
        """Olmayan plan tatbikati."""
        orch = BackupOrchestrator()
        result = orch.run_dr_drill("d1", "x")
        assert "error" in result

    def test_verify_backup(self):
        """Yedekleme dogrulama."""
        orch = BackupOrchestrator()
        orch.backup("b1", "db", {"a": 1})
        result = orch.verify_backup("b1")
        assert result["passed"]

    def test_verify_backup_not_found(self):
        """Bulunamayan yedekleme dogrulama."""
        orch = BackupOrchestrator()
        result = orch.verify_backup("x")
        assert "error" in result

    def test_get_alerts(self):
        """Uyari getirme."""
        orch = BackupOrchestrator()
        orch.failover.add_node(
            "n1", is_primary=True,
        )
        orch.failover.add_node("n2")
        orch.trigger_failover()
        alerts = orch.get_alerts()
        assert len(alerts) >= 1

    def test_get_status(self):
        """Durum bilgisi."""
        orch = BackupOrchestrator()
        orch.backup("b1", "db", {"a": 1})
        status = orch.get_status()
        assert status["backups"] >= 1
        assert status["stored_files"] >= 1


# ==================== Models ====================


class TestBackupModels:
    """Backup model testleri."""

    def test_backup_type_values(self):
        """BackupType degerleri."""
        assert BackupType.FULL == "full"
        assert BackupType.INCREMENTAL == (
            "incremental"
        )
        assert BackupType.DIFFERENTIAL == (
            "differential"
        )
        assert BackupType.SNAPSHOT == "snapshot"

    def test_backup_status_values(self):
        """BackupStatus degerleri."""
        assert BackupStatus.PENDING == "pending"
        assert BackupStatus.RUNNING == "running"
        assert BackupStatus.COMPLETED == (
            "completed"
        )
        assert BackupStatus.FAILED == "failed"

    def test_storage_type_values(self):
        """StorageType degerleri."""
        assert StorageType.LOCAL == "local"
        assert StorageType.S3 == "s3"
        assert StorageType.REMOTE == "remote"

    def test_failover_mode_values(self):
        """FailoverMode degerleri."""
        assert FailoverMode.AUTOMATIC == (
            "automatic"
        )
        assert FailoverMode.MANUAL == "manual"
        assert FailoverMode.DNS_BASED == (
            "dns_based"
        )

    def test_disaster_severity_values(self):
        """DisasterSeverity degerleri."""
        assert DisasterSeverity.LOW == "low"
        assert DisasterSeverity.CRITICAL == (
            "critical"
        )
        assert DisasterSeverity.CATASTROPHIC == (
            "catastrophic"
        )

    def test_replication_mode_values(self):
        """ReplicationMode degerleri."""
        assert ReplicationMode.SYNC == "sync"
        assert ReplicationMode.ASYNC == "async"
        assert ReplicationMode.STREAMING == (
            "streaming"
        )

    def test_backup_record(self):
        """BackupRecord modeli."""
        r = BackupRecord(
            backup_type=BackupType.FULL,
            size_bytes=1024,
        )
        assert r.backup_type == BackupType.FULL
        assert r.size_bytes == 1024
        assert len(r.backup_id) == 8

    def test_restore_record(self):
        """RestoreRecord modeli."""
        r = RestoreRecord(
            source_backup_id="b1",
            target="db",
        )
        assert r.source_backup_id == "b1"
        assert not r.verified

    def test_dr_plan_record(self):
        """DRPlanRecord modeli."""
        r = DRPlanRecord(
            name="DB DR",
            rto_minutes=30,
            rpo_minutes=5,
            severity=DisasterSeverity.HIGH,
        )
        assert r.rto_minutes == 30
        assert r.severity == (
            DisasterSeverity.HIGH
        )

    def test_backup_snapshot(self):
        """BackupSnapshot modeli."""
        s = BackupSnapshot(
            total_backups=50,
            total_size_bytes=1024000,
            dr_plans=3,
        )
        assert s.total_backups == 50
        assert s.dr_plans == 3


# ==================== Config ====================


class TestBackupConfig:
    """Backup config testleri."""

    def test_backup_enabled(self):
        """backup_enabled ayari."""
        from app.config import settings
        assert hasattr(settings, "backup_enabled")

    def test_default_retention_days(self):
        """default_retention_days ayari."""
        from app.config import settings
        assert hasattr(
            settings, "default_retention_days",
        )

    def test_backup_compression(self):
        """backup_compression_enabled ayari."""
        from app.config import settings
        assert hasattr(
            settings,
            "backup_compression_enabled",
        )

    def test_backup_encryption(self):
        """backup_encryption_enabled ayari."""
        from app.config import settings
        assert hasattr(
            settings,
            "backup_encryption_enabled",
        )

    def test_rpo_hours(self):
        """rpo_hours ayari."""
        from app.config import settings
        assert hasattr(settings, "rpo_hours")


# ==================== Imports ====================


class TestBackupImports:
    """Backup import testleri."""

    def test_import_all_from_package(self):
        """Paket uzerinden import."""
        from app.core.backup import (
            BackupExecutor,
            BackupOrchestrator,
            BackupReplicationManager,
            BackupScheduler,
            BackupStorageBackend,
            DisasterPlanner,
            FailoverController,
            RecoveryTester,
            RestoreManager,
        )
        assert BackupExecutor is not None
        assert BackupOrchestrator is not None
        assert BackupReplicationManager is not None
        assert BackupScheduler is not None
        assert BackupStorageBackend is not None
        assert DisasterPlanner is not None
        assert FailoverController is not None
        assert RecoveryTester is not None
        assert RestoreManager is not None

    def test_import_models(self):
        """Model import."""
        from app.models.backup_models import (
            BackupType,
            BackupStatus,
            StorageType,
            FailoverMode,
            DisasterSeverity,
            ReplicationMode,
            BackupRecord,
            RestoreRecord,
            DRPlanRecord,
            BackupSnapshot,
        )
        assert BackupType is not None
        assert BackupSnapshot is not None
