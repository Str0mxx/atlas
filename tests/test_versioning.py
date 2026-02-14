"""ATLAS Version Control & Rollback testleri.

VersionManager, SnapshotCreator, ChangeTracker,
RollbackManager, MigrationManager, BranchManager,
ReleaseManager, VersionAuditTrail ve
VersioningOrchestrator testleri.
"""

import time

import pytest

from app.models.versioning import (
    BranchStatus,
    ChangeType,
    MigrationRecord,
    MigrationStatus,
    RollbackType,
    SnapshotRecord,
    SnapshotType,
    VersioningSnapshot,
    VersionRecord,
    VersionStatus,
)
from app.core.versioning.version_manager import (
    VersionManager,
)
from app.core.versioning.snapshot_creator import (
    SnapshotCreator,
)
from app.core.versioning.change_tracker import (
    ChangeTracker,
)
from app.core.versioning.rollback_manager import (
    RollbackManager,
)
from app.core.versioning.migration_manager import (
    MigrationManager,
)
from app.core.versioning.branch_manager import (
    BranchManager,
)
from app.core.versioning.release_manager import (
    ReleaseManager,
)
from app.core.versioning.audit_trail import (
    VersionAuditTrail,
)
from app.core.versioning.versioning_orchestrator import (
    VersioningOrchestrator,
)


# ---- Model Testleri ----

class TestVersioningModels:
    """Model testleri."""

    def test_version_status_values(self):
        assert VersionStatus.DRAFT == "draft"
        assert VersionStatus.RELEASED == "released"
        assert VersionStatus.DEPRECATED == "deprecated"
        assert VersionStatus.ARCHIVED == "archived"

    def test_change_type_values(self):
        assert ChangeType.ADDED == "added"
        assert ChangeType.MODIFIED == "modified"
        assert ChangeType.DELETED == "deleted"
        assert ChangeType.RENAMED == "renamed"

    def test_snapshot_type_values(self):
        assert SnapshotType.FULL == "full"
        assert SnapshotType.INCREMENTAL == "incremental"
        assert SnapshotType.CONFIGURATION == "configuration"
        assert SnapshotType.DATA == "data"

    def test_migration_status_values(self):
        assert MigrationStatus.PENDING == "pending"
        assert MigrationStatus.RUNNING == "running"
        assert MigrationStatus.COMPLETED == "completed"
        assert MigrationStatus.FAILED == "failed"
        assert MigrationStatus.ROLLED_BACK == "rolled_back"

    def test_rollback_type_values(self):
        assert RollbackType.FULL == "full"
        assert RollbackType.SELECTIVE == "selective"
        assert RollbackType.STAGED == "staged"
        assert RollbackType.POINT_IN_TIME == "point_in_time"

    def test_branch_status_values(self):
        assert BranchStatus.ACTIVE == "active"
        assert BranchStatus.MERGED == "merged"
        assert BranchStatus.CLOSED == "closed"
        assert BranchStatus.STALE == "stale"

    def test_version_record(self):
        r = VersionRecord(
            version="1.0.0",
            description="Initial",
            author="fatih",
        )
        assert r.version == "1.0.0"
        assert r.author == "fatih"
        assert r.status == VersionStatus.DRAFT
        assert r.version_id

    def test_snapshot_record(self):
        r = SnapshotRecord(
            source="test",
            data={"key": "val"},
        )
        assert r.source == "test"
        assert r.snapshot_type == SnapshotType.FULL
        assert r.snapshot_id

    def test_migration_record(self):
        r = MigrationRecord(name="add_table")
        assert r.name == "add_table"
        assert r.status == MigrationStatus.PENDING
        assert r.direction == "forward"

    def test_versioning_snapshot(self):
        s = VersioningSnapshot(
            total_versions=5,
            current_version="2.0.0",
        )
        assert s.total_versions == 5
        assert s.current_version == "2.0.0"


# ---- VersionManager Testleri ----

class TestVersionManager:
    """VersionManager testleri."""

    def setup_method(self):
        self.vm = VersionManager()

    def test_create_version(self):
        v = self.vm.create_version(
            "1.0.0", "Initial release", "fatih",
        )
        assert v.version == "1.0.0"
        assert v.author == "fatih"
        assert self.vm.version_count == 1

    def test_release_version(self):
        v = self.vm.create_version("1.0.0")
        ok = self.vm.release_version(v.version_id)
        assert ok is True
        assert v.status == VersionStatus.RELEASED
        assert self.vm.current_version == "1.0.0"

    def test_release_nonexistent(self):
        ok = self.vm.release_version("nope")
        assert ok is False

    def test_deprecate_version(self):
        v = self.vm.create_version("1.0.0")
        ok = self.vm.deprecate_version(v.version_id)
        assert ok is True
        assert v.status == VersionStatus.DEPRECATED

    def test_deprecate_nonexistent(self):
        ok = self.vm.deprecate_version("nope")
        assert ok is False

    def test_parse_semver(self):
        p = self.vm.parse_semver("2.3.4")
        assert p["valid"] is True
        assert p["major"] == 2
        assert p["minor"] == 3
        assert p["patch"] == 4

    def test_parse_semver_prerelease(self):
        p = self.vm.parse_semver("1.0.0-beta")
        assert p["valid"] is True
        assert p["prerelease"] == "beta"

    def test_parse_semver_invalid(self):
        p = self.vm.parse_semver("invalid")
        assert p["valid"] is False

    def test_compare_versions(self):
        assert self.vm.compare_versions("2.0.0", "1.0.0") == 1
        assert self.vm.compare_versions("1.0.0", "2.0.0") == -1
        assert self.vm.compare_versions("1.0.0", "1.0.0") == 0

    def test_compare_minor(self):
        assert self.vm.compare_versions("1.2.0", "1.1.0") == 1
        assert self.vm.compare_versions("1.0.0", "1.1.0") == -1

    def test_compare_patch(self):
        assert self.vm.compare_versions("1.0.2", "1.0.1") == 1

    def test_compare_invalid(self):
        assert self.vm.compare_versions("bad", "1.0.0") == 0

    def test_bump_patch(self):
        assert self.vm.bump_version("1.0.0") == "1.0.1"

    def test_bump_minor(self):
        assert self.vm.bump_version("1.0.0", "minor") == "1.1.0"

    def test_bump_major(self):
        assert self.vm.bump_version("1.2.3", "major") == "2.0.0"

    def test_bump_invalid(self):
        assert self.vm.bump_version("bad") == "bad"

    def test_tag_version(self):
        v = self.vm.create_version("1.0.0")
        ok = self.vm.tag_version(v.version_id, "stable")
        assert ok is True
        assert self.vm.tag_count == 1

    def test_tag_nonexistent(self):
        ok = self.vm.tag_version("nope", "tag")
        assert ok is False

    def test_get_by_tag(self):
        v = self.vm.create_version("1.0.0")
        self.vm.tag_version(v.version_id, "latest")
        found = self.vm.get_by_tag("latest")
        assert found is not None
        assert found.version == "1.0.0"

    def test_get_by_tag_missing(self):
        assert self.vm.get_by_tag("nope") is None

    def test_get_version(self):
        v = self.vm.create_version("1.0.0")
        found = self.vm.get_version(v.version_id)
        assert found is not None

    def test_get_history(self):
        self.vm.create_version("1.0.0")
        self.vm.create_version("1.1.0")
        h = self.vm.get_history()
        assert len(h) == 2


# ---- SnapshotCreator Testleri ----

class TestSnapshotCreator:
    """SnapshotCreator testleri."""

    def setup_method(self):
        self.sc = SnapshotCreator()

    def test_create_snapshot(self):
        s = self.sc.create_snapshot(
            "test", {"key": "val"},
        )
        assert s.source == "test"
        assert s.data == {"key": "val"}
        assert s.size_bytes > 0
        assert self.sc.snapshot_count == 1

    def test_create_incremental(self):
        parent = self.sc.create_snapshot(
            "test", {"a": 1, "b": 2},
        )
        inc = self.sc.create_incremental(
            "test", {"a": 1, "b": 3, "c": 4},
            parent.snapshot_id,
        )
        assert inc.snapshot_type == SnapshotType.INCREMENTAL
        assert inc.parent_id == parent.snapshot_id
        # Only changed/new keys stored
        assert "b" in inc.data
        assert "c" in inc.data

    def test_incremental_no_parent(self):
        s = self.sc.create_incremental(
            "test", {"a": 1}, "nonexistent",
        )
        assert s.snapshot_type == SnapshotType.FULL

    def test_create_config_snapshot(self):
        s = self.sc.create_config_snapshot(
            {"debug": True},
        )
        assert s.snapshot_type == SnapshotType.CONFIGURATION
        assert s.source == "configuration"

    def test_create_data_snapshot(self):
        s = self.sc.create_data_snapshot(
            "users", {"count": 100},
        )
        assert s.snapshot_type == SnapshotType.DATA
        assert s.source == "data:users"

    def test_restore_snapshot(self):
        s = self.sc.create_snapshot(
            "test", {"a": 1, "b": 2},
        )
        data = self.sc.restore_snapshot(
            s.snapshot_id,
        )
        assert data == {"a": 1, "b": 2}

    def test_restore_incremental(self):
        parent = self.sc.create_snapshot(
            "test", {"a": 1, "b": 2},
        )
        inc = self.sc.create_incremental(
            "test", {"a": 1, "b": 3, "c": 4},
            parent.snapshot_id,
        )
        data = self.sc.restore_snapshot(
            inc.snapshot_id,
        )
        assert data["a"] == 1
        assert data["b"] == 3
        assert data["c"] == 4

    def test_restore_nonexistent(self):
        assert self.sc.restore_snapshot("nope") is None

    def test_get_chain(self):
        p = self.sc.create_snapshot(
            "test", {"a": 1},
        )
        c = self.sc.create_incremental(
            "test", {"a": 2}, p.snapshot_id,
        )
        chain = self.sc.get_chain(c.snapshot_id)
        assert len(chain) == 2

    def test_delete_snapshot(self):
        s = self.sc.create_snapshot(
            "test", {"a": 1},
        )
        ok = self.sc.delete_snapshot(s.snapshot_id)
        assert ok is True
        assert self.sc.snapshot_count == 0

    def test_delete_nonexistent(self):
        assert self.sc.delete_snapshot("nope") is False

    def test_get_checksum(self):
        s = self.sc.create_snapshot(
            "test", {"key": "val"},
        )
        cs = self.sc.get_checksum(s.snapshot_id)
        assert len(cs) == 32  # MD5

    def test_checksum_nonexistent(self):
        assert self.sc.get_checksum("nope") == ""

    def test_total_size(self):
        self.sc.create_snapshot("a", {"x": 1})
        self.sc.create_snapshot("b", {"y": 2})
        assert self.sc.total_size > 0


# ---- ChangeTracker Testleri ----

class TestChangeTracker:
    """ChangeTracker testleri."""

    def setup_method(self):
        self.ct = ChangeTracker()

    def test_set_baseline(self):
        self.ct.set_baseline("res", {"a": 1})
        assert self.ct.baseline_count == 1

    def test_detect_added(self):
        self.ct.set_baseline("res", {})
        changes = self.ct.detect_changes(
            "res", {"a": 1},
        )
        assert len(changes) == 1
        assert changes[0]["type"] == ChangeType.ADDED.value

    def test_detect_modified(self):
        self.ct.set_baseline("res", {"a": 1})
        changes = self.ct.detect_changes(
            "res", {"a": 2},
        )
        assert len(changes) == 1
        assert changes[0]["type"] == ChangeType.MODIFIED.value

    def test_detect_deleted(self):
        self.ct.set_baseline("res", {"a": 1})
        changes = self.ct.detect_changes("res", {})
        assert len(changes) == 1
        assert changes[0]["type"] == ChangeType.DELETED.value

    def test_detect_no_changes(self):
        self.ct.set_baseline("res", {"a": 1})
        changes = self.ct.detect_changes(
            "res", {"a": 1},
        )
        assert len(changes) == 0

    def test_record_change(self):
        c = self.ct.record_change(
            "res", "added", "key",
            new_value=42, author="fatih",
        )
        assert c["resource"] == "res"
        assert c["type"] == "added"
        assert self.ct.change_count == 1

    def test_generate_diff(self):
        diff = self.ct.generate_diff(
            {"a": 1, "b": 2},
            {"b": 3, "c": 4},
        )
        assert "a" in diff["deleted"]
        assert "b" in diff["modified"]
        assert "c" in diff["added"]
        assert diff["total_changes"] == 3

    def test_get_history(self):
        self.ct.record_change("r1", "added", "k1")
        self.ct.record_change("r2", "added", "k2")
        h = self.ct.get_history()
        assert len(h) == 2

    def test_get_history_filtered(self):
        self.ct.record_change("r1", "added", "k1")
        self.ct.record_change("r2", "added", "k2")
        h = self.ct.get_history(resource="r1")
        assert len(h) == 1

    def test_categorize_changes(self):
        changes = [
            {"type": "added"},
            {"type": "added"},
            {"type": "modified"},
        ]
        cats = self.ct.categorize_changes(changes)
        assert len(cats["added"]) == 2
        assert len(cats["modified"]) == 1

    def test_analyze_impact(self):
        self.ct.record_change("res", "added", "k")
        self.ct.add_watcher("res", "w1")
        impact = self.ct.analyze_impact("res")
        assert impact["total_changes"] == 1
        assert impact["affected_watchers"] == 1

    def test_add_watcher(self):
        self.ct.add_watcher("res", "w1")
        self.ct.add_watcher("res", "w1")  # dup
        assert self.ct.watcher_count == 1

    def test_remove_watcher(self):
        self.ct.add_watcher("res", "w1")
        ok = self.ct.remove_watcher("res", "w1")
        assert ok is True
        assert self.ct.watcher_count == 0

    def test_remove_watcher_missing(self):
        ok = self.ct.remove_watcher("res", "w1")
        assert ok is False


# ---- RollbackManager Testleri ----

class TestRollbackManager:
    """RollbackManager testleri."""

    def setup_method(self):
        self.rm = RollbackManager()

    def test_create_checkpoint(self):
        cp = self.rm.create_checkpoint(
            "v1", {"a": 1},
        )
        assert cp["name"] == "v1"
        assert self.rm.checkpoint_count == 1

    def test_rollback_to_checkpoint(self):
        self.rm.create_checkpoint(
            "v1", {"a": 1, "b": 2},
        )
        result = self.rm.rollback_to_checkpoint("v1")
        assert result["success"] is True
        assert result["state"]["a"] == 1
        assert self.rm.rollback_count == 1

    def test_rollback_nonexistent(self):
        result = self.rm.rollback_to_checkpoint("nope")
        assert result["success"] is False

    def test_selective_rollback(self):
        result = self.rm.selective_rollback(
            ["a", "c"],
            {"a": 1, "b": 2, "c": 3},
        )
        assert result["success"] is True
        assert "a" in result["restored_keys"]
        assert "c" in result["restored_keys"]
        assert "b" not in result["restored_keys"]

    def test_staged_rollback(self):
        stages = [
            {"name": "stage1", "state": {"a": 1}},
            {"name": "stage2", "state": {"b": 2}},
        ]
        result = self.rm.staged_rollback(stages)
        assert result["success"] is True
        assert result["stages_completed"] == 2

    def test_validate_rollback_safe(self):
        result = self.rm.validate_rollback(
            {"a": 1, "b": "x"},
            {"a": 2, "b": "y"},
        )
        assert result["safe"] is True

    def test_validate_rollback_conflict(self):
        result = self.rm.validate_rollback(
            {"a": 1},
            {"a": "string"},
        )
        assert result["safe"] is False
        assert "a" in result["conflicts"]

    def test_validate_missing_keys(self):
        result = self.rm.validate_rollback(
            {"a": 1, "b": 2},
            {"a": 1},
        )
        assert "b" in result["missing_keys"]

    def test_undo_last_rollback(self):
        self.rm.create_checkpoint("v1", {"a": 1})
        self.rm.rollback_to_checkpoint("v1")
        result = self.rm.undo_last_rollback()
        assert result["success"] is True

    def test_undo_empty_stack(self):
        result = self.rm.undo_last_rollback()
        assert result["success"] is False

    def test_get_history(self):
        self.rm.create_checkpoint("v1", {"a": 1})
        self.rm.rollback_to_checkpoint("v1")
        h = self.rm.get_history()
        assert len(h) == 1

    def test_get_checkpoint(self):
        self.rm.create_checkpoint("v1", {"a": 1})
        cp = self.rm.get_checkpoint("v1")
        assert cp is not None
        assert cp["state"]["a"] == 1

    def test_delete_checkpoint(self):
        self.rm.create_checkpoint("v1", {"a": 1})
        ok = self.rm.delete_checkpoint("v1")
        assert ok is True
        assert self.rm.checkpoint_count == 0

    def test_delete_nonexistent(self):
        ok = self.rm.delete_checkpoint("nope")
        assert ok is False


# ---- MigrationManager Testleri ----

class TestMigrationManager:
    """MigrationManager testleri."""

    def setup_method(self):
        self.mm = MigrationManager()

    def test_register_migration(self):
        m = self.mm.register_migration(
            "add_users",
            lambda: None,
            lambda: None,
        )
        assert m.name == "add_users"
        assert self.mm.migration_count == 1

    def test_run_forward(self):
        executed = []
        m = self.mm.register_migration(
            "m1",
            lambda: executed.append("fwd"),
            lambda: executed.append("bwd"),
        )
        result = self.mm.run_forward(
            m.migration_id,
        )
        assert result["success"] is True
        assert "fwd" in executed
        assert self.mm.applied_count == 1

    def test_run_forward_fail(self):
        def fail():
            raise RuntimeError("oops")

        m = self.mm.register_migration(
            "m1", fail,
        )
        result = self.mm.run_forward(
            m.migration_id,
        )
        assert result["success"] is False
        assert "oops" in result["error"]

    def test_run_forward_nonexistent(self):
        result = self.mm.run_forward("nope")
        assert result["success"] is False

    def test_run_backward(self):
        executed = []
        m = self.mm.register_migration(
            "m1",
            lambda: executed.append("fwd"),
            lambda: executed.append("bwd"),
        )
        self.mm.run_forward(m.migration_id)
        result = self.mm.run_backward(
            m.migration_id,
        )
        assert result["success"] is True
        assert "bwd" in executed

    def test_run_backward_no_fn(self):
        m = self.mm.register_migration(
            "m1", lambda: None,
        )
        result = self.mm.run_backward(
            m.migration_id,
        )
        assert result["success"] is False
        assert result["reason"] == "no_backward_function"

    def test_run_backward_nonexistent(self):
        result = self.mm.run_backward("nope")
        assert result["success"] is False

    def test_run_all_pending(self):
        self.mm.register_migration(
            "m1", lambda: None, lambda: None,
        )
        self.mm.register_migration(
            "m2", lambda: None, lambda: None,
        )
        results = self.mm.run_all_pending()
        assert len(results) == 2
        assert all(r["success"] for r in results)
        assert self.mm.pending_count == 0

    def test_run_all_pending_stops_on_fail(self):
        self.mm.register_migration(
            "m1", lambda: None,
        )

        def fail():
            raise RuntimeError("fail")

        self.mm.register_migration("m2", fail)
        self.mm.register_migration(
            "m3", lambda: None,
        )
        results = self.mm.run_all_pending()
        assert results[0]["success"] is True
        assert results[1]["success"] is False
        assert len(results) == 2  # Stopped at m2

    def test_rollback_last(self):
        m = self.mm.register_migration(
            "m1",
            lambda: None,
            lambda: None,
        )
        self.mm.run_forward(m.migration_id)
        result = self.mm.rollback_last()
        assert result["success"] is True

    def test_rollback_last_empty(self):
        result = self.mm.rollback_last()
        assert result["success"] is False

    def test_test_migration(self):
        m = self.mm.register_migration(
            "m1", lambda: None, lambda: None,
        )
        info = self.mm.test_migration(
            m.migration_id,
        )
        assert info["has_forward"] is True
        assert info["has_backward"] is True
        assert info["reversible"] is True

    def test_test_nonexistent(self):
        info = self.mm.test_migration("nope")
        assert info["success"] is False

    def test_get_pending(self):
        self.mm.register_migration(
            "m1", lambda: None,
        )
        pending = self.mm.get_pending()
        assert len(pending) == 1

    def test_get_applied(self):
        m = self.mm.register_migration(
            "m1", lambda: None,
        )
        self.mm.run_forward(m.migration_id)
        applied = self.mm.get_applied()
        assert len(applied) == 1


# ---- BranchManager Testleri ----

class TestBranchManager:
    """BranchManager testleri."""

    def setup_method(self):
        self.bm = BranchManager()

    def test_init_main_branch(self):
        assert self.bm.active_branch == "main"
        assert self.bm.branch_count == 1

    def test_create_branch(self):
        b = self.bm.create_branch("feature")
        assert b["name"] == "feature"
        assert b["parent"] == "main"
        assert self.bm.branch_count == 2

    def test_create_branch_with_state(self):
        b = self.bm.create_branch(
            "dev", state={"a": 1},
        )
        assert b["state"]["a"] == 1

    def test_switch_branch(self):
        self.bm.create_branch("dev")
        ok = self.bm.switch_branch("dev")
        assert ok is True
        assert self.bm.active_branch == "dev"

    def test_switch_nonexistent(self):
        ok = self.bm.switch_branch("nope")
        assert ok is False

    def test_commit_to_branch(self):
        self.bm.create_branch(
            "dev", state={"a": 1},
        )
        result = self.bm.commit_to_branch(
            "dev", {"b": 2}, "add b",
        )
        assert result["success"] is True
        branch = self.bm.get_branch("dev")
        assert branch["state"]["b"] == 2
        assert len(branch["history"]) == 1

    def test_commit_nonexistent(self):
        result = self.bm.commit_to_branch(
            "nope", {}, "",
        )
        assert result["success"] is False

    def test_merge_branch(self):
        self.bm.create_branch(
            "feat", state={"a": 1},
        )
        self.bm.commit_to_branch(
            "feat", {"b": 2}, "add b",
        )
        result = self.bm.merge_branch(
            "feat", "main",
        )
        assert result["success"] is True
        main = self.bm.get_branch("main")
        assert main["state"]["b"] == 2

    def test_merge_nonexistent(self):
        result = self.bm.merge_branch("nope")
        assert result["success"] is False

    def test_compare_branches(self):
        self.bm.create_branch(
            "b1", state={"a": 1, "b": 2},
        )
        self.bm.create_branch(
            "b2", state={"b": 3, "c": 4},
        )
        cmp = self.bm.compare_branches("b1", "b2")
        assert "a" in cmp["only_in_first"]
        assert "c" in cmp["only_in_second"]
        assert "b" in cmp["different"]

    def test_compare_nonexistent(self):
        cmp = self.bm.compare_branches(
            "nope", "main",
        )
        assert cmp["success"] is False

    def test_detect_conflicts_type_mismatch(self):
        self.bm.create_branch(
            "b1", state={"a": 1},
        )
        self.bm.create_branch(
            "b2", state={"a": "string"},
        )
        conflicts = self.bm.detect_conflicts(
            "b1", "b2",
        )
        assert "a" in conflicts

    def test_detect_no_conflicts(self):
        self.bm.create_branch(
            "b1", state={"a": 1},
        )
        self.bm.create_branch(
            "b2", state={"a": 2},
        )
        conflicts = self.bm.detect_conflicts(
            "b1", "b2",
        )
        assert len(conflicts) == 0

    def test_close_branch(self):
        self.bm.create_branch("feat")
        ok = self.bm.close_branch("feat")
        assert ok is True
        b = self.bm.get_branch("feat")
        assert b["status"] == BranchStatus.CLOSED.value

    def test_close_main(self):
        ok = self.bm.close_branch("main")
        assert ok is False

    def test_close_nonexistent(self):
        ok = self.bm.close_branch("nope")
        assert ok is False

    def test_delete_branch(self):
        self.bm.create_branch("feat")
        ok = self.bm.delete_branch("feat")
        assert ok is True
        assert self.bm.branch_count == 1

    def test_delete_main(self):
        ok = self.bm.delete_branch("main")
        assert ok is False

    def test_delete_nonexistent(self):
        ok = self.bm.delete_branch("nope")
        assert ok is False

    def test_active_count(self):
        self.bm.create_branch("b1")
        self.bm.create_branch("b2")
        assert self.bm.active_count == 3  # main + b1 + b2

    def test_switch_closed_branch(self):
        self.bm.create_branch("feat")
        self.bm.close_branch("feat")
        ok = self.bm.switch_branch("feat")
        assert ok is False

    def test_close_active_switches_to_main(self):
        self.bm.create_branch("feat")
        self.bm.switch_branch("feat")
        self.bm.close_branch("feat")
        assert self.bm.active_branch == "main"


# ---- ReleaseManager Testleri ----

class TestReleaseManager:
    """ReleaseManager testleri."""

    def setup_method(self):
        self.rm = ReleaseManager()

    def test_create_release(self):
        r = self.rm.create_release(
            "1.0.0",
            notes="Initial",
            changes=["feat1"],
            author="fatih",
        )
        assert r["version"] == "1.0.0"
        assert self.rm.release_count == 1

    def test_add_release_notes(self):
        self.rm.create_release("1.0.0")
        ok = self.rm.add_release_notes(
            "1.0.0", "Extra notes",
        )
        assert ok is True
        r = self.rm.get_release("1.0.0")
        assert "Extra notes" in r["notes"]

    def test_add_notes_nonexistent(self):
        ok = self.rm.add_release_notes(
            "nope", "notes",
        )
        assert ok is False

    def test_deploy_release(self):
        self.rm.create_release("1.0.0")
        result = self.rm.deploy_release(
            "1.0.0", "staging",
        )
        assert result["success"] is True
        assert self.rm.deployment_count == 1

    def test_deploy_nonexistent(self):
        result = self.rm.deploy_release("nope")
        assert result["success"] is False

    def test_create_hotfix(self):
        hf = self.rm.create_hotfix(
            "1.0.0", "Fix bug", "patch",
        )
        assert hf["version"] == "1.0.0"
        assert self.rm.hotfix_count == 1

    def test_apply_hotfix(self):
        self.rm.create_hotfix("1.0.0", "Fix")
        result = self.rm.apply_hotfix(0)
        assert result["success"] is True

    def test_apply_hotfix_invalid(self):
        result = self.rm.apply_hotfix(99)
        assert result["success"] is False

    def test_validate_release_valid(self):
        self.rm.create_release(
            "1.0.0",
            notes="Release",
            changes=["feat"],
            author="fatih",
        )
        v = self.rm.validate_release("1.0.0")
        assert v["valid"] is True

    def test_validate_release_incomplete(self):
        self.rm.create_release("1.0.0")
        v = self.rm.validate_release("1.0.0")
        assert v["valid"] is False
        assert "missing_notes" in v["issues"]

    def test_validate_nonexistent(self):
        v = self.rm.validate_release("nope")
        assert v["valid"] is False

    def test_add_validation_check(self):
        self.rm.create_release("1.0.0")
        self.rm.add_validation_check(
            "1.0.0", "lint",
        )
        v = self.rm.validate_release("1.0.0")
        assert v["checks_passed"] == 1

    def test_get_deployments(self):
        self.rm.create_release("1.0.0")
        self.rm.deploy_release("1.0.0", "staging")
        self.rm.deploy_release("1.0.0", "prod")
        deps = self.rm.get_deployments(
            environment="staging",
        )
        assert len(deps) == 1

    def test_get_all_deployments(self):
        self.rm.create_release("1.0.0")
        self.rm.deploy_release("1.0.0", "staging")
        self.rm.deploy_release("1.0.0", "prod")
        deps = self.rm.get_deployments()
        assert len(deps) == 2


# ---- VersionAuditTrail Testleri ----

class TestVersionAuditTrail:
    """VersionAuditTrail testleri."""

    def setup_method(self):
        self.at = VersionAuditTrail()

    def test_log_action(self):
        e = self.at.log_action(
            "create", "fatih", "version:1.0",
        )
        assert e["action"] == "create"
        assert self.at.entry_count == 1

    def test_request_approval(self):
        a = self.at.request_approval(
            "req1", "deploy", "fatih", "v1",
        )
        assert a["status"] == "pending"
        assert self.at.pending_count == 1

    def test_approve(self):
        self.at.request_approval(
            "req1", "deploy", "fatih", "v1",
        )
        result = self.at.approve(
            "req1", "admin",
        )
        assert result["success"] is True
        a = self.at.get_approval("req1")
        assert a["status"] == "approved"

    def test_approve_nonexistent(self):
        result = self.at.approve("nope", "admin")
        assert result["success"] is False

    def test_reject(self):
        self.at.request_approval(
            "req1", "deploy", "fatih", "v1",
        )
        result = self.at.reject(
            "req1", "admin", "not ready",
        )
        assert result["success"] is True
        a = self.at.get_approval("req1")
        assert a["status"] == "rejected"

    def test_reject_nonexistent(self):
        result = self.at.reject("nope", "admin")
        assert result["success"] is False

    def test_add_compliance_rule(self):
        r = self.at.add_compliance_rule(
            "audit", "Must have audit trail",
        )
        assert r["active"] is True
        assert self.at.rule_count == 1

    def test_check_compliance(self):
        self.at.log_action(
            "create", "fatih", "v1",
            reason="initial",
        )
        c = self.at.check_compliance("v1")
        assert c["compliant"] is True
        assert c["has_author"] is True
        assert c["has_reason"] is True

    def test_check_compliance_no_entries(self):
        c = self.at.check_compliance("empty")
        assert c["total_entries"] == 0

    def test_get_entries_by_actor(self):
        self.at.log_action("a", "fatih", "r1")
        self.at.log_action("b", "admin", "r2")
        entries = self.at.get_entries(
            actor="fatih",
        )
        assert len(entries) == 1

    def test_get_entries_by_resource(self):
        self.at.log_action("a", "fatih", "r1")
        self.at.log_action("b", "admin", "r1")
        entries = self.at.get_entries(
            resource="r1",
        )
        assert len(entries) == 2

    def test_get_entries_by_action(self):
        self.at.log_action("create", "f", "r")
        self.at.log_action("delete", "f", "r")
        entries = self.at.get_entries(
            action="create",
        )
        assert len(entries) == 1

    def test_get_pending_approvals(self):
        self.at.request_approval(
            "r1", "deploy", "f", "v1",
        )
        self.at.request_approval(
            "r2", "deploy", "f", "v2",
        )
        self.at.approve("r1", "admin")
        pending = self.at.get_pending_approvals()
        assert len(pending) == 1


# ---- VersioningOrchestrator Testleri ----

class TestVersioningOrchestrator:
    """VersioningOrchestrator testleri."""

    def setup_method(self):
        self.vo = VersioningOrchestrator()

    def test_init(self):
        assert self.vo.versions is not None
        assert self.vo.snapshots is not None
        assert self.vo.changes is not None
        assert self.vo.rollbacks is not None
        assert self.vo.migrations is not None
        assert self.vo.branches is not None
        assert self.vo.releases is not None
        assert self.vo.audit is not None

    def test_create_version_with_snapshot(self):
        result = self.vo.create_version_with_snapshot(
            "1.0.0",
            {"config": "val"},
            "First version",
            "fatih",
        )
        assert result["success"] is True
        assert result["version"] == "1.0.0"
        assert self.vo.versions.version_count == 1
        assert self.vo.snapshots.snapshot_count == 1
        assert self.vo.rollbacks.checkpoint_count == 1
        assert self.vo.audit.entry_count == 1

    def test_release_version(self):
        cr = self.vo.create_version_with_snapshot(
            "1.0.0", {}, "Init", "fatih",
        )
        result = self.vo.release_version(
            "1.0.0",
            cr["version_id"],
            "Release notes",
            ["feat1"],
            "fatih",
        )
        assert result["success"] is True
        assert self.vo.releases.release_count == 1

    def test_release_nonexistent(self):
        result = self.vo.release_version(
            "1.0.0", "nope",
        )
        assert result["success"] is False

    def test_rollback_to_version(self):
        self.vo.create_version_with_snapshot(
            "1.0.0", {"a": 1}, "Init", "fatih",
        )
        result = self.vo.rollback_to_version(
            "1.0.0", "fatih",
        )
        assert result["success"] is True
        assert self.vo.audit.entry_count >= 2

    def test_rollback_nonexistent(self):
        result = self.vo.rollback_to_version("nope")
        assert result["success"] is False

    def test_track_and_snapshot(self):
        self.vo.changes.set_baseline(
            "res", {"a": 1},
        )
        result = self.vo.track_and_snapshot(
            "res", {"a": 2, "b": 3}, "fatih",
        )
        assert result["changes_detected"] == 2
        assert result["snapshot_created"] is True

    def test_track_no_changes(self):
        self.vo.changes.set_baseline(
            "res", {"a": 1},
        )
        result = self.vo.track_and_snapshot(
            "res", {"a": 1},
        )
        assert result["changes_detected"] == 0
        assert result["snapshot_created"] is False

    def test_get_analytics(self):
        self.vo.create_version_with_snapshot(
            "1.0.0", {}, "", "fatih",
        )
        a = self.vo.get_analytics()
        assert a["total_versions"] == 1
        assert a["total_snapshots"] == 1
        assert a["audit_entries"] >= 1

    def test_get_snapshot(self):
        self.vo.create_version_with_snapshot(
            "1.0.0", {}, "", "fatih",
        )
        s = self.vo.get_snapshot()
        assert isinstance(s, VersioningSnapshot)
        assert s.total_versions == 1
        assert s.total_snapshots == 1

    def test_full_workflow(self):
        # Create v1
        cr1 = self.vo.create_version_with_snapshot(
            "1.0.0", {"a": 1}, "v1", "fatih",
        )
        # Release v1
        self.vo.release_version(
            "1.0.0", cr1["version_id"],
            "First", ["init"], "fatih",
        )
        # Create v2
        cr2 = self.vo.create_version_with_snapshot(
            "1.1.0", {"a": 2, "b": 3}, "v2", "fatih",
        )
        # Release v2
        self.vo.release_version(
            "1.1.0", cr2["version_id"],
            "Second", ["feat"], "fatih",
        )
        # Rollback to v1
        rb = self.vo.rollback_to_version(
            "1.0.0", "fatih",
        )
        assert rb["success"] is True
        assert rb["state"]["a"] == 1

        a = self.vo.get_analytics()
        assert a["total_versions"] == 2
        assert a["total_releases"] == 2
        assert a["total_rollbacks"] == 1


# ---- Config Testleri ----

class TestVersioningConfig:
    """Config testleri."""

    def test_config_defaults(self):
        from app.config import Settings
        s = Settings()
        assert s.versioning_enabled is True
        assert s.max_snapshots == 100
        assert s.auto_snapshot_interval == 3600
        assert s.retention_days == 90
        assert s.compression_enabled is True

    def test_config_values(self):
        from app.config import Settings
        s = Settings()
        assert isinstance(s.max_snapshots, int)
        assert isinstance(
            s.auto_snapshot_interval, int,
        )


# ---- Import Testleri ----

class TestVersioningImports:
    """Import testleri."""

    def test_import_all(self):
        from app.core.versioning import (
            BranchManager,
            ChangeTracker,
            MigrationManager,
            ReleaseManager,
            RollbackManager,
            SnapshotCreator,
            VersionAuditTrail,
            VersionManager,
            VersioningOrchestrator,
        )
        assert VersionManager is not None
        assert SnapshotCreator is not None
        assert ChangeTracker is not None
        assert RollbackManager is not None
        assert MigrationManager is not None
        assert BranchManager is not None
        assert ReleaseManager is not None
        assert VersionAuditTrail is not None
        assert VersioningOrchestrator is not None

    def test_import_models(self):
        from app.models.versioning import (
            BranchStatus,
            ChangeType,
            MigrationRecord,
            MigrationStatus,
            RollbackType,
            SnapshotRecord,
            SnapshotType,
            VersioningSnapshot,
            VersionRecord,
            VersionStatus,
        )
        assert VersionStatus is not None
        assert ChangeType is not None
        assert SnapshotType is not None
        assert MigrationStatus is not None
        assert RollbackType is not None
        assert BranchStatus is not None
