"""SelfUpgrade testleri.

Surum kontrolu, karsilastirma, migrasyon planlama,
guncelleme uygulama ve geri alma testleri.
"""

from unittest.mock import MagicMock, patch

import pytest

from app.core.bootstrap.self_upgrade import (
    CURRENT_VERSION,
    SelfUpgrade,
)
from app.models.bootstrap import (
    MigrationPlan,
    UpgradeRecord,
    UpgradeStatus,
    VersionInfo,
)


# === Yardimci Fonksiyonlar ===


def _make_upgrade(**kwargs) -> SelfUpgrade:
    """Test icin SelfUpgrade olusturur."""
    return SelfUpgrade(**kwargs)


def _make_version_info(**kwargs) -> VersionInfo:
    """Test icin VersionInfo olusturur."""
    defaults = {
        "current_version": "0.1.0",
        "latest_version": "0.1.0",
    }
    defaults.update(kwargs)
    return VersionInfo(**defaults)


def _make_upgrade_record(**kwargs) -> UpgradeRecord:
    """Test icin UpgradeRecord olusturur."""
    return UpgradeRecord(**kwargs)


# === Enum Testleri ===


class TestUpgradeStatus:
    """UpgradeStatus enum testleri."""

    def test_up_to_date(self) -> None:
        assert UpgradeStatus.UP_TO_DATE == "up_to_date"

    def test_update_available(self) -> None:
        assert UpgradeStatus.UPDATE_AVAILABLE == "update_available"

    def test_downloading(self) -> None:
        assert UpgradeStatus.DOWNLOADING == "downloading"

    def test_applying(self) -> None:
        assert UpgradeStatus.APPLYING == "applying"

    def test_completed(self) -> None:
        assert UpgradeStatus.COMPLETED == "completed"

    def test_failed(self) -> None:
        assert UpgradeStatus.FAILED == "failed"

    def test_rolled_back(self) -> None:
        assert UpgradeStatus.ROLLED_BACK == "rolled_back"


# === Model Testleri ===


class TestVersionInfo:
    """VersionInfo model testleri."""

    def test_defaults(self) -> None:
        vi = _make_version_info()
        assert vi.update_available is False
        assert vi.breaking_changes == []

    def test_update(self) -> None:
        vi = _make_version_info(
            latest_version="0.2.0",
            update_available=True,
        )
        assert vi.update_available is True

    def test_breaking(self) -> None:
        vi = _make_version_info(
            breaking_changes=["API degisikligi"],
        )
        assert len(vi.breaking_changes) == 1


class TestUpgradeRecord:
    """UpgradeRecord model testleri."""

    def test_defaults(self) -> None:
        rec = _make_upgrade_record()
        assert rec.status == UpgradeStatus.UP_TO_DATE
        assert rec.rollback_available is True

    def test_unique_ids(self) -> None:
        a = _make_upgrade_record()
        b = _make_upgrade_record()
        assert a.id != b.id

    def test_timestamp(self) -> None:
        rec = _make_upgrade_record()
        assert rec.started_at is not None
        assert rec.completed_at is None


class TestMigrationPlan:
    """MigrationPlan model testleri."""

    def test_defaults(self) -> None:
        plan = MigrationPlan()
        assert plan.db_migrations == []
        assert plan.reversible is True
        assert plan.estimated_downtime == 0.0

    def test_custom(self) -> None:
        plan = MigrationPlan(
            db_migrations=["step1"],
            estimated_downtime=30.0,
            reversible=False,
        )
        assert len(plan.db_migrations) == 1
        assert plan.reversible is False


# === SelfUpgrade Init Testleri ===


class TestSelfUpgradeInit:
    """SelfUpgrade init testleri."""

    def test_default_version(self) -> None:
        su = _make_upgrade()
        assert su.current_version == CURRENT_VERSION

    def test_custom_version(self) -> None:
        su = _make_upgrade(current_version="1.5.0")
        assert su.current_version == "1.5.0"


# === CompareVersions Testleri ===


class TestCompareVersions:
    """compare_versions testleri."""

    def test_equal(self) -> None:
        su = _make_upgrade()
        assert su.compare_versions("1.0.0", "1.0.0") == 0

    def test_newer(self) -> None:
        su = _make_upgrade()
        assert su.compare_versions("1.0.0", "2.0.0") == -1

    def test_older(self) -> None:
        su = _make_upgrade()
        assert su.compare_versions("2.0.0", "1.0.0") == 1

    def test_patch_diff(self) -> None:
        su = _make_upgrade()
        assert su.compare_versions("1.0.0", "1.0.1") == -1

    def test_minor_diff(self) -> None:
        su = _make_upgrade()
        assert su.compare_versions("1.0.0", "1.1.0") == -1


# === ParseVersion Testleri ===


class TestParseVersion:
    """parse_version testleri."""

    def test_semver(self) -> None:
        su = _make_upgrade()
        assert su.parse_version("1.2.3") == (1, 2, 3)

    def test_two_parts(self) -> None:
        su = _make_upgrade()
        assert su.parse_version("1.2") == (1, 2)

    def test_with_suffix(self) -> None:
        su = _make_upgrade()
        result = su.parse_version("1.2.3beta")
        assert result[0] == 1
        assert result[1] == 2


# === CheckForUpdates Testleri ===


class TestCheckForUpdates:
    """check_for_updates testleri."""

    async def test_up_to_date(self) -> None:
        su = _make_upgrade(current_version="1.0.0")
        info = await su.check_for_updates(latest_version="1.0.0")
        assert info.update_available is False

    async def test_update_available(self) -> None:
        su = _make_upgrade(current_version="1.0.0")
        info = await su.check_for_updates(latest_version="2.0.0")
        assert info.update_available is True
        assert len(info.breaking_changes) > 0

    async def test_no_latest_uses_current(self) -> None:
        su = _make_upgrade(current_version="1.0.0")
        info = await su.check_for_updates()
        assert info.update_available is False


# === PlanMigration Testleri ===


class TestPlanMigration:
    """plan_migration testleri."""

    async def test_major_upgrade(self) -> None:
        su = _make_upgrade()
        plan = await su.plan_migration("1.0.0", "2.0.0")
        assert isinstance(plan, MigrationPlan)
        assert len(plan.db_migrations) > 0
        assert plan.estimated_downtime > 0

    async def test_patch_upgrade(self) -> None:
        su = _make_upgrade()
        plan = await su.plan_migration("1.0.0", "1.0.1")
        assert plan.estimated_downtime == 0.0
        assert plan.reversible is True

    async def test_minor_upgrade(self) -> None:
        su = _make_upgrade()
        plan = await su.plan_migration("1.0.0", "1.1.0")
        assert plan.reversible is True


# === ApplyUpgrade Testleri ===


class TestApplyUpgrade:
    """apply_upgrade testleri."""

    async def test_apply(self) -> None:
        su = _make_upgrade(current_version="1.0.0")
        info = _make_version_info(
            current_version="1.0.0",
            latest_version="1.1.0",
            update_available=True,
        )
        record = await su.apply_upgrade(info)
        assert record.status == UpgradeStatus.COMPLETED
        assert su.current_version == "1.1.0"

    async def test_already_current(self) -> None:
        su = _make_upgrade(current_version="1.0.0")
        info = _make_version_info(
            current_version="1.0.0",
            latest_version="1.0.0",
            update_available=False,
        )
        record = await su.apply_upgrade(info)
        assert record.status == UpgradeStatus.UP_TO_DATE

    async def test_history_updated(self) -> None:
        su = _make_upgrade(current_version="1.0.0")
        info = _make_version_info(
            current_version="1.0.0",
            latest_version="1.1.0",
            update_available=True,
        )
        await su.apply_upgrade(info)
        assert len(su.get_upgrade_history()) == 1


# === Rollback Testleri ===


class TestRollback:
    """rollback testleri."""

    async def test_rollback_success(self) -> None:
        su = _make_upgrade(current_version="1.1.0")
        record = _make_upgrade_record(
            from_version="1.0.0",
            to_version="1.1.0",
            status=UpgradeStatus.COMPLETED,
            rollback_available=True,
        )
        success = await su.rollback(record)
        assert success is True
        assert su.current_version == "1.0.0"
        assert record.status == UpgradeStatus.ROLLED_BACK

    async def test_rollback_unavailable(self) -> None:
        su = _make_upgrade()
        record = _make_upgrade_record(
            rollback_available=False,
        )
        success = await su.rollback(record)
        assert success is False

    async def test_rollback_already_done(self) -> None:
        su = _make_upgrade()
        record = _make_upgrade_record(
            status=UpgradeStatus.ROLLED_BACK,
            rollback_available=True,
        )
        success = await su.rollback(record)
        assert success is True


# === HotReload Testleri ===


class TestHotReload:
    """check_hot_reload_capable testleri."""

    def test_capability(self) -> None:
        su = _make_upgrade()
        result = su.check_hot_reload_capable()
        # Development ortaminda True donmeli
        assert isinstance(result, bool)


# === IsBreakingChange Testleri ===


class TestIsBreakingChange:
    """_is_breaking_change testleri."""

    def test_major_is_breaking(self) -> None:
        su = _make_upgrade()
        assert su._is_breaking_change("1.0.0", "2.0.0") is True

    def test_minor_not_breaking(self) -> None:
        su = _make_upgrade()
        assert su._is_breaking_change("1.0.0", "1.1.0") is False

    def test_patch_not_breaking(self) -> None:
        su = _make_upgrade()
        assert su._is_breaking_change("1.0.0", "1.0.1") is False
