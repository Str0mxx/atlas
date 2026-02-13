"""PackageManager testleri.

Paket kurulum, kaldirma, surum kontrolu,
geri alma ve komut olusturma testleri.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.bootstrap.package_manager import PackageManager
from app.models.bootstrap import (
    InstallationRecord,
    InstallationStatus,
    PackageInfo,
    PackageManagerType,
    PackageStatus,
)


# === Yardimci Fonksiyonlar ===


def _make_manager(**kwargs) -> PackageManager:
    """Test icin PackageManager olusturur."""
    defaults = {
        "allowed_managers": ["pip", "npm"],
        "sandbox_mode": True,
        "dry_run": False,
    }
    defaults.update(kwargs)
    return PackageManager(**defaults)


def _make_install_record(**kwargs) -> InstallationRecord:
    """Test icin InstallationRecord olusturur."""
    defaults = {"package_name": "test-pkg"}
    defaults.update(kwargs)
    return InstallationRecord(**defaults)


# === Enum Testleri ===


class TestPackageStatus:
    """PackageStatus enum testleri."""

    def test_installed(self) -> None:
        assert PackageStatus.INSTALLED == "installed"

    def test_not_installed(self) -> None:
        assert PackageStatus.NOT_INSTALLED == "not_installed"

    def test_outdated(self) -> None:
        assert PackageStatus.OUTDATED == "outdated"

    def test_unknown(self) -> None:
        assert PackageStatus.UNKNOWN == "unknown"


class TestPackageManagerType:
    """PackageManagerType enum testleri."""

    def test_pip(self) -> None:
        assert PackageManagerType.PIP == "pip"

    def test_npm(self) -> None:
        assert PackageManagerType.NPM == "npm"

    def test_apt(self) -> None:
        assert PackageManagerType.APT == "apt"

    def test_brew(self) -> None:
        assert PackageManagerType.BREW == "brew"

    def test_choco(self) -> None:
        assert PackageManagerType.CHOCO == "choco"

    def test_docker(self) -> None:
        assert PackageManagerType.DOCKER == "docker"


class TestInstallationStatus:
    """InstallationStatus enum testleri."""

    def test_pending(self) -> None:
        assert InstallationStatus.PENDING == "pending"

    def test_in_progress(self) -> None:
        assert InstallationStatus.IN_PROGRESS == "in_progress"

    def test_completed(self) -> None:
        assert InstallationStatus.COMPLETED == "completed"

    def test_failed(self) -> None:
        assert InstallationStatus.FAILED == "failed"

    def test_rolled_back(self) -> None:
        assert InstallationStatus.ROLLED_BACK == "rolled_back"


# === Model Testleri ===


class TestPackageInfo:
    """PackageInfo model testleri."""

    def test_defaults(self) -> None:
        info = PackageInfo(name="flask")
        assert info.name == "flask"
        assert info.status == PackageStatus.UNKNOWN
        assert info.manager == PackageManagerType.PIP

    def test_installed_package(self) -> None:
        info = PackageInfo(
            name="flask", version="2.3.0", status=PackageStatus.INSTALLED
        )
        assert info.version == "2.3.0"

    def test_npm_package(self) -> None:
        info = PackageInfo(name="express", manager=PackageManagerType.NPM)
        assert info.manager == PackageManagerType.NPM


class TestInstallationRecord:
    """InstallationRecord model testleri."""

    def test_defaults(self) -> None:
        rec = _make_install_record()
        assert rec.package_name == "test-pkg"
        assert rec.status == InstallationStatus.PENDING
        assert rec.dry_run is False

    def test_unique_ids(self) -> None:
        a = _make_install_record()
        b = _make_install_record()
        assert a.id != b.id

    def test_timestamps(self) -> None:
        rec = _make_install_record()
        assert rec.started_at is not None
        assert rec.completed_at is None

    def test_with_error(self) -> None:
        rec = _make_install_record(
            status=InstallationStatus.FAILED,
            error_message="kurulum hatasi",
        )
        assert rec.error_message == "kurulum hatasi"


# === PackageManager Init Testleri ===


class TestPackageManagerInit:
    """PackageManager init testleri."""

    def test_defaults(self) -> None:
        pm = _make_manager()
        assert pm.sandbox_mode is True
        assert pm.dry_run is False

    def test_allowed_managers(self) -> None:
        pm = _make_manager(allowed_managers=["pip"])
        assert pm.allowed_managers == ["pip"]

    def test_sandbox_mode(self) -> None:
        pm = _make_manager(sandbox_mode=False)
        assert pm.sandbox_mode is False


# === Install Testleri ===


class TestInstall:
    """install testleri."""

    async def test_install_pip_sandbox(self) -> None:
        pm = _make_manager(sandbox_mode=True)
        result = await pm.install("flask")
        assert result.status == InstallationStatus.COMPLETED
        assert result.package_name == "flask"

    async def test_install_npm_sandbox(self) -> None:
        pm = _make_manager(sandbox_mode=True)
        result = await pm.install("express", manager=PackageManagerType.NPM)
        assert result.status == InstallationStatus.COMPLETED
        assert result.manager == PackageManagerType.NPM

    async def test_install_dry_run(self) -> None:
        pm = _make_manager(sandbox_mode=False)
        result = await pm.install("flask", dry_run=True)
        assert result.status == InstallationStatus.COMPLETED
        assert result.dry_run is True

    async def test_install_disallowed_manager(self) -> None:
        pm = _make_manager(allowed_managers=["pip"])
        result = await pm.install("nginx", manager=PackageManagerType.APT)
        assert result.status == InstallationStatus.FAILED
        assert "izinli degil" in result.error_message

    async def test_install_real_success(self) -> None:
        pm = _make_manager(sandbox_mode=False)
        with patch.object(pm, "_run_command", return_value=(0, "ok", "")):
            result = await pm.install("flask")
        assert result.status == InstallationStatus.COMPLETED

    async def test_install_real_failure(self) -> None:
        pm = _make_manager(sandbox_mode=False)
        with patch.object(
            pm, "_run_command", return_value=(1, "", "hata mesaji")
        ):
            result = await pm.install("flask")
        assert result.status == InstallationStatus.FAILED

    async def test_install_with_version(self) -> None:
        pm = _make_manager(sandbox_mode=True)
        result = await pm.install("flask", version="2.3.0")
        assert result.version == "2.3.0"


# === Uninstall Testleri ===


class TestUninstall:
    """uninstall testleri."""

    async def test_uninstall_sandbox(self) -> None:
        pm = _make_manager(sandbox_mode=True)
        result = await pm.uninstall("flask")
        assert result.status == InstallationStatus.COMPLETED

    async def test_uninstall_dry_run(self) -> None:
        pm = _make_manager(sandbox_mode=False)
        result = await pm.uninstall("flask", dry_run=True)
        assert result.status == InstallationStatus.COMPLETED


# === CheckInstalled Testleri ===


class TestCheckInstalled:
    """check_installed testleri."""

    async def test_installed(self) -> None:
        pm = _make_manager()
        with patch.object(
            pm, "_run_command", return_value=(0, "Version: 2.3.0\n", "")
        ):
            info = await pm.check_installed("flask")
        assert info.status == PackageStatus.INSTALLED
        assert info.version == "2.3.0"

    async def test_not_installed(self) -> None:
        pm = _make_manager()
        with patch.object(pm, "_run_command", return_value=(1, "", "not found")):
            info = await pm.check_installed("ghost")
        assert info.status == PackageStatus.NOT_INSTALLED

    async def test_non_pip_manager(self) -> None:
        pm = _make_manager()
        info = await pm.check_installed("express", PackageManagerType.NPM)
        assert info.status == PackageStatus.UNKNOWN


# === Rollback Testleri ===


class TestRollback:
    """rollback testleri."""

    async def test_rollback_completed(self) -> None:
        pm = _make_manager(sandbox_mode=True)
        record = _make_install_record(status=InstallationStatus.COMPLETED)
        success = await pm.rollback(record)
        assert success is True
        assert record.status == InstallationStatus.ROLLED_BACK

    async def test_rollback_already_rolled_back(self) -> None:
        pm = _make_manager()
        record = _make_install_record(status=InstallationStatus.ROLLED_BACK)
        success = await pm.rollback(record)
        assert success is True

    async def test_rollback_failed_status(self) -> None:
        pm = _make_manager()
        record = _make_install_record(status=InstallationStatus.FAILED)
        success = await pm.rollback(record)
        assert success is False


# === BuildCommands Testleri ===


class TestBuildCommands:
    """Komut olusturma testleri."""

    def test_pip_install_cmd(self) -> None:
        pm = _make_manager()
        cmd = pm._build_install_command("flask", None, PackageManagerType.PIP)
        assert cmd == ["pip", "install", "flask"]

    def test_npm_install_cmd(self) -> None:
        pm = _make_manager()
        cmd = pm._build_install_command("express", None, PackageManagerType.NPM)
        assert cmd == ["npm", "install", "express"]

    def test_pip_with_version(self) -> None:
        pm = _make_manager()
        cmd = pm._build_install_command("flask", "2.3.0", PackageManagerType.PIP)
        assert cmd == ["pip", "install", "flask==2.3.0"]

    def test_pip_uninstall_cmd(self) -> None:
        pm = _make_manager()
        cmd = pm._build_uninstall_command("flask", PackageManagerType.PIP)
        assert cmd == ["pip", "uninstall", "-y", "flask"]

    def test_docker_pull_cmd(self) -> None:
        pm = _make_manager()
        cmd = pm._build_install_command("nginx", None, PackageManagerType.DOCKER)
        assert cmd == ["docker", "pull", "nginx"]


# === IsManagerAllowed Testleri ===


class TestIsManagerAllowed:
    """is_manager_allowed testleri."""

    def test_allowed(self) -> None:
        pm = _make_manager(allowed_managers=["pip", "npm"])
        assert pm.is_manager_allowed(PackageManagerType.PIP) is True
        assert pm.is_manager_allowed(PackageManagerType.NPM) is True

    def test_not_allowed(self) -> None:
        pm = _make_manager(allowed_managers=["pip"])
        assert pm.is_manager_allowed(PackageManagerType.APT) is False


# === InstallationHistory Testleri ===


class TestInstallationHistory:
    """Kurulum gecmisi testleri."""

    def test_empty(self) -> None:
        pm = _make_manager()
        assert pm.get_installation_history() == []

    async def test_after_installs(self) -> None:
        pm = _make_manager(sandbox_mode=True)
        await pm.install("flask")
        await pm.install("httpx")
        history = pm.get_installation_history()
        assert len(history) == 2
