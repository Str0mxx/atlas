"""AutoInstaller testleri.

Kurulum plani olusturma, calistirma, dogrulama,
geri alma ve temizlik testleri.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.bootstrap.auto_installer import AutoInstaller
from app.core.bootstrap.dependency_resolver import DependencyResolver
from app.core.bootstrap.package_manager import PackageManager
from app.models.bootstrap import (
    InstallationPlan,
    InstallationRecord,
    InstallationResult,
    InstallationStatus,
    PackageInfo,
    PackageManagerType,
    PackageStatus,
)


# === Yardimci Fonksiyonlar ===


def _make_installer(**kwargs) -> AutoInstaller:
    """Test icin AutoInstaller olusturur."""
    defaults = {
        "package_manager": PackageManager(
            allowed_managers=["pip", "npm"],
            sandbox_mode=True,
        ),
        "require_approval": False,
        "auto_install": True,
    }
    defaults.update(kwargs)
    return AutoInstaller(**defaults)


def _make_plan(**kwargs) -> InstallationPlan:
    """Test icin InstallationPlan olusturur."""
    defaults: dict = {"packages": [], "total_packages": 0}
    defaults.update(kwargs)
    return InstallationPlan(**defaults)


def _make_result(**kwargs) -> InstallationResult:
    """Test icin InstallationResult olusturur."""
    defaults = {"plan_id": "test-plan"}
    defaults.update(kwargs)
    return InstallationResult(**defaults)


# === Model Testleri ===


class TestInstallationPlan:
    """InstallationPlan model testleri."""

    def test_defaults(self) -> None:
        plan = _make_plan()
        assert plan.status == InstallationStatus.PENDING
        assert plan.packages == []
        assert plan.requires_approval is True

    def test_custom(self) -> None:
        plan = _make_plan(total_packages=3, dry_run=True)
        assert plan.total_packages == 3
        assert plan.dry_run is True

    def test_unique_id(self) -> None:
        a = _make_plan()
        b = _make_plan()
        assert a.id != b.id


class TestInstallationResult:
    """InstallationResult model testleri."""

    def test_defaults(self) -> None:
        result = _make_result()
        assert result.success is True
        assert result.installed == []
        assert result.failed == []

    def test_success(self) -> None:
        result = _make_result(installed=["flask", "httpx"])
        assert len(result.installed) == 2

    def test_failed(self) -> None:
        result = _make_result(success=False, failed=["ghost"])
        assert result.success is False
        assert len(result.failed) == 1


# === AutoInstaller Init Testleri ===


class TestAutoInstallerInit:
    """AutoInstaller init testleri."""

    def test_defaults(self) -> None:
        ai = _make_installer()
        assert ai.require_approval is False
        assert ai.auto_install is True

    def test_custom_managers(self) -> None:
        pm = PackageManager(
            allowed_managers=["pip"], sandbox_mode=True
        )
        ai = _make_installer(package_manager=pm)
        assert ai.package_manager.allowed_managers == ["pip"]

    def test_approval_override(self) -> None:
        ai = _make_installer(require_approval=True)
        assert ai.require_approval is True


# === CreatePlan Testleri ===


class TestCreatePlan:
    """create_plan testleri."""

    async def test_single_package(self) -> None:
        ai = _make_installer()
        plan = await ai.create_plan(["flask"])
        assert plan.total_packages >= 1
        assert plan.status == InstallationStatus.PENDING

    async def test_multiple_packages(self) -> None:
        ai = _make_installer()
        plan = await ai.create_plan(["flask", "httpx", "uvicorn"])
        assert plan.total_packages >= 3

    async def test_dry_run(self) -> None:
        ai = _make_installer()
        plan = await ai.create_plan(["flask"], dry_run=True)
        assert plan.dry_run is True

    async def test_estimated_duration(self) -> None:
        ai = _make_installer()
        plan = await ai.create_plan(["flask", "httpx"])
        assert plan.estimated_duration > 0


# === ExecutePlan Testleri ===


class TestExecutePlan:
    """execute_plan testleri."""

    async def test_approved(self) -> None:
        ai = _make_installer(require_approval=False)
        plan = await ai.create_plan(["flask"])
        result = await ai.execute_plan(plan, approved=True)
        assert result.success is True
        assert len(result.installed) >= 1

    async def test_requires_approval_denied(self) -> None:
        ai = _make_installer(require_approval=True)
        plan = await ai.create_plan(["flask"])
        result = await ai.execute_plan(plan, approved=False)
        assert result.success is False

    async def test_dry_run_no_install(self) -> None:
        ai = _make_installer()
        plan = await ai.create_plan(["flask"], dry_run=True)
        result = await ai.execute_plan(plan, approved=True)
        assert result.success is True

    async def test_plan_status_updated(self) -> None:
        ai = _make_installer(require_approval=False)
        plan = await ai.create_plan(["flask"])
        await ai.execute_plan(plan, approved=True)
        assert plan.status in (
            InstallationStatus.COMPLETED,
            InstallationStatus.FAILED,
        )

    async def test_duration_tracked(self) -> None:
        ai = _make_installer(require_approval=False)
        plan = await ai.create_plan(["flask"])
        result = await ai.execute_plan(plan, approved=True)
        assert result.total_duration >= 0


# === InstallSingle Testleri ===


class TestInstallSingle:
    """install_single testleri."""

    async def test_success(self) -> None:
        ai = _make_installer()
        record = await ai.install_single("flask")
        assert record.status == InstallationStatus.COMPLETED

    async def test_with_version(self) -> None:
        ai = _make_installer()
        record = await ai.install_single("flask", version="2.3.0")
        assert record.version == "2.3.0"

    async def test_history_updated(self) -> None:
        ai = _make_installer()
        await ai.install_single("flask")
        assert len(ai.get_history()) == 1


# === VerifyInstallation Testleri ===


class TestVerifyInstallation:
    """verify_installation testleri."""

    async def test_verified(self) -> None:
        ai = _make_installer()
        with patch.object(
            ai.package_manager,
            "check_installed",
            return_value=PackageInfo(
                name="flask", status=PackageStatus.INSTALLED
            ),
        ):
            result = await ai.verify_installation("flask")
        assert result is True

    async def test_not_found(self) -> None:
        ai = _make_installer()
        with patch.object(
            ai.package_manager,
            "check_installed",
            return_value=PackageInfo(
                name="ghost", status=PackageStatus.NOT_INSTALLED
            ),
        ):
            result = await ai.verify_installation("ghost")
        assert result is False


# === RollbackPlan Testleri ===


class TestRollbackPlan:
    """rollback_plan testleri."""

    async def test_rollback_installed(self) -> None:
        ai = _make_installer()
        # Once bir paket kur
        await ai.install_single("flask")
        result = _make_result(installed=["flask"])
        rolled = await ai.rollback_plan(result)
        assert "flask" in rolled

    async def test_no_rollback_needed(self) -> None:
        ai = _make_installer()
        result = _make_result(installed=[])
        rolled = await ai.rollback_plan(result)
        assert rolled == []


# === History Testleri ===


class TestHistory:
    """Kurulum gecmisi testleri."""

    def test_empty(self) -> None:
        ai = _make_installer()
        assert ai.get_history() == []

    async def test_after_operations(self) -> None:
        ai = _make_installer()
        await ai.install_single("flask")
        await ai.install_single("httpx")
        assert len(ai.get_history()) == 2


# === CleanupFailed Testleri ===


class TestCleanupFailed:
    """cleanup_failed testleri."""

    async def test_nothing_to_clean(self) -> None:
        ai = _make_installer()
        await ai.install_single("flask")  # sandbox = basarili
        count = await ai.cleanup_failed()
        assert count == 0

    async def test_cleanup_failed_records(self) -> None:
        ai = _make_installer()
        # Basarisiz kayit ekle
        record = InstallationRecord(
            package_name="ghost",
            status=InstallationStatus.FAILED,
        )
        ai._history.append(record)
        count = await ai.cleanup_failed()
        assert count == 1
        assert len(ai.get_history()) == 0


# === CheckApproval Testleri ===


class TestCheckApproval:
    """_check_approval testleri."""

    def test_dry_run_always_passes(self) -> None:
        ai = _make_installer(require_approval=True)
        plan = _make_plan(dry_run=True)
        assert ai._check_approval(plan, approved=False) is True

    def test_no_approval_required(self) -> None:
        ai = _make_installer()
        plan = _make_plan(requires_approval=False)
        assert ai._check_approval(plan, approved=False) is True

    def test_approval_granted(self) -> None:
        ai = _make_installer()
        plan = _make_plan(requires_approval=True)
        assert ai._check_approval(plan, approved=True) is True

    def test_approval_denied(self) -> None:
        ai = _make_installer()
        plan = _make_plan(requires_approval=True)
        assert ai._check_approval(plan, approved=False) is False
