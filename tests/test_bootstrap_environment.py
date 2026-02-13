"""EnvironmentDetector testleri.

OS tespiti, yazilim tespiti, kaynak tespiti,
ag tespiti ve eksik bagimlilik testleri.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.bootstrap.environment_detector import (
    DEFAULT_SOFTWARE,
    EnvironmentDetector,
)
from app.models.bootstrap import (
    EnvironmentInfo,
    NetworkInfo,
    OSType,
    ResourceInfo,
    SoftwareInfo,
)


# === Yardimci Fonksiyonlar ===


def _make_detector(**kwargs) -> EnvironmentDetector:
    """Test icin EnvironmentDetector olusturur."""
    return EnvironmentDetector(**kwargs)


# === OSType Enum Testleri ===


class TestOSType:
    """OSType enum testleri."""

    def test_windows_value(self) -> None:
        assert OSType.WINDOWS == "windows"

    def test_linux_value(self) -> None:
        assert OSType.LINUX == "linux"

    def test_macos_value(self) -> None:
        assert OSType.MACOS == "macos"

    def test_unknown_value(self) -> None:
        assert OSType.UNKNOWN == "unknown"


# === Model Testleri ===


class TestSoftwareInfo:
    """SoftwareInfo model testleri."""

    def test_defaults(self) -> None:
        info = SoftwareInfo(name="git")
        assert info.name == "git"
        assert info.path is None
        assert info.version is None
        assert info.available is False

    def test_available_software(self) -> None:
        info = SoftwareInfo(
            name="python", path="/usr/bin/python", version="3.11", available=True
        )
        assert info.available is True
        assert info.path == "/usr/bin/python"

    def test_unavailable_software(self) -> None:
        info = SoftwareInfo(name="nonexistent", available=False)
        assert info.available is False


class TestResourceInfo:
    """ResourceInfo model testleri."""

    def test_defaults(self) -> None:
        info = ResourceInfo()
        assert info.cpu_cores == 0
        assert info.total_ram_mb == 0.0
        assert info.available_ram_mb == 0.0

    def test_custom_values(self) -> None:
        info = ResourceInfo(cpu_cores=8, total_ram_mb=16384.0)
        assert info.cpu_cores == 8
        assert info.total_ram_mb == 16384.0


class TestNetworkInfo:
    """NetworkInfo model testleri."""

    def test_defaults(self) -> None:
        info = NetworkInfo()
        assert info.internet_access is False
        assert info.dns_available is False
        assert info.available_ports == []
        assert info.checked_ports == {}

    def test_with_ports(self) -> None:
        info = NetworkInfo(
            internet_access=True,
            available_ports=[8080, 9090],
            checked_ports={8080: True, 5432: False},
        )
        assert info.internet_access is True
        assert len(info.available_ports) == 2


class TestEnvironmentInfo:
    """EnvironmentInfo model testleri."""

    def test_defaults(self) -> None:
        info = EnvironmentInfo()
        assert info.os_type == OSType.UNKNOWN
        assert info.python_version == ""
        assert info.software == []
        assert info.missing_dependencies == []

    def test_unique_ids(self) -> None:
        a = EnvironmentInfo()
        b = EnvironmentInfo()
        assert a.id != b.id

    def test_scanned_at_is_set(self) -> None:
        info = EnvironmentInfo()
        assert info.scanned_at is not None


# === EnvironmentDetector Init Testleri ===


class TestEnvironmentDetectorInit:
    """EnvironmentDetector init testleri."""

    def test_default(self) -> None:
        det = _make_detector()
        assert det.software_list == DEFAULT_SOFTWARE

    def test_custom_software_list(self) -> None:
        det = _make_detector(software_list=["git", "docker"])
        assert det.software_list == ["git", "docker"]
        assert len(det.software_list) == 2


# === DetectOS Testleri ===


class TestDetectOS:
    """detect_os testleri."""

    @patch("app.core.bootstrap.environment_detector.platform")
    def test_detect_windows(self, mock_platform: MagicMock) -> None:
        mock_platform.system.return_value = "Windows"
        mock_platform.version.return_value = "10.0.19041"
        det = _make_detector()
        os_type, version = det.detect_os()
        assert os_type == OSType.WINDOWS
        assert version == "10.0.19041"

    @patch("app.core.bootstrap.environment_detector.platform")
    def test_detect_linux(self, mock_platform: MagicMock) -> None:
        mock_platform.system.return_value = "Linux"
        mock_platform.version.return_value = "5.15.0"
        det = _make_detector()
        os_type, _ = det.detect_os()
        assert os_type == OSType.LINUX

    @patch("app.core.bootstrap.environment_detector.platform")
    def test_detect_macos(self, mock_platform: MagicMock) -> None:
        mock_platform.system.return_value = "Darwin"
        mock_platform.version.return_value = "22.0.0"
        det = _make_detector()
        os_type, _ = det.detect_os()
        assert os_type == OSType.MACOS

    @patch("app.core.bootstrap.environment_detector.platform")
    def test_detect_unknown(self, mock_platform: MagicMock) -> None:
        mock_platform.system.return_value = "FreeBSD"
        mock_platform.version.return_value = "13.0"
        det = _make_detector()
        os_type, _ = det.detect_os()
        assert os_type == OSType.UNKNOWN


# === DetectSoftware Testleri ===


class TestDetectSoftware:
    """detect_software testleri."""

    @patch("app.core.bootstrap.environment_detector.shutil.which")
    def test_found(self, mock_which: MagicMock) -> None:
        mock_which.return_value = "/usr/bin/git"
        det = _make_detector(software_list=["git"])
        results = det.detect_software()
        assert len(results) == 1
        assert results[0].name == "git"
        assert results[0].available is True
        assert results[0].path == "/usr/bin/git"

    @patch("app.core.bootstrap.environment_detector.shutil.which")
    def test_not_found(self, mock_which: MagicMock) -> None:
        mock_which.return_value = None
        det = _make_detector(software_list=["ghost"])
        results = det.detect_software()
        assert results[0].available is False
        assert results[0].path is None

    @patch("app.core.bootstrap.environment_detector.shutil.which")
    def test_multiple(self, mock_which: MagicMock) -> None:
        mock_which.side_effect = ["/usr/bin/git", None, "/usr/bin/curl"]
        det = _make_detector(software_list=["git", "ghost", "curl"])
        results = det.detect_software()
        assert len(results) == 3
        assert results[0].available is True
        assert results[1].available is False
        assert results[2].available is True

    @patch("app.core.bootstrap.environment_detector.shutil.which")
    def test_custom_list(self, mock_which: MagicMock) -> None:
        mock_which.return_value = "/usr/bin/node"
        det = _make_detector(software_list=["git"])
        results = det.detect_software(names=["node"])
        assert len(results) == 1
        assert results[0].name == "node"


# === DetectResources Testleri ===


class TestDetectResources:
    """detect_resources testleri."""

    @patch("app.core.bootstrap.environment_detector.os.cpu_count", return_value=4)
    @patch("app.core.bootstrap.environment_detector.shutil.disk_usage")
    async def test_detect_with_disk(
        self, mock_disk: MagicMock, mock_cpu: MagicMock
    ) -> None:
        mock_disk.return_value = MagicMock(
            total=100 * 1024 * 1024 * 1024,
            free=50 * 1024 * 1024 * 1024,
        )
        det = _make_detector()
        res = await det.detect_resources()
        assert res.cpu_cores == 4
        assert res.total_disk_mb > 0
        assert res.available_disk_mb > 0

    @patch("app.core.bootstrap.environment_detector.os.cpu_count", return_value=2)
    @patch(
        "app.core.bootstrap.environment_detector.shutil.disk_usage",
        side_effect=OSError("erisilemez"),
    )
    async def test_disk_error_fallback(
        self, mock_disk: MagicMock, mock_cpu: MagicMock
    ) -> None:
        det = _make_detector()
        res = await det.detect_resources()
        assert res.cpu_cores == 2
        assert res.total_disk_mb == 0.0


# === DetectNetwork Testleri ===


class TestDetectNetwork:
    """detect_network testleri."""

    async def test_internet_available(self) -> None:
        det = _make_detector()
        with patch.object(det, "_check_internet", return_value=True):
            with patch.object(det, "_check_dns", return_value=True):
                net = await det.detect_network()
        assert net.internet_access is True
        assert net.dns_available is True

    async def test_internet_unavailable(self) -> None:
        det = _make_detector()
        with patch.object(det, "_check_internet", return_value=False):
            with patch.object(det, "_check_dns", return_value=False):
                net = await det.detect_network()
        assert net.internet_access is False
        assert net.dns_available is False

    async def test_port_check(self) -> None:
        det = _make_detector()
        with patch.object(det, "_check_internet", return_value=True):
            with patch.object(det, "_check_dns", return_value=True):
                with patch.object(
                    det, "_check_port", side_effect=[True, False]
                ):
                    net = await det.detect_network(ports_to_check=[8080, 5432])
        assert net.checked_ports == {8080: True, 5432: False}
        assert net.available_ports == [8080]

    async def test_no_ports(self) -> None:
        det = _make_detector()
        with patch.object(det, "_check_internet", return_value=True):
            with patch.object(det, "_check_dns", return_value=True):
                net = await det.detect_network()
        assert net.checked_ports == {}
        assert net.available_ports == []


# === FullDetect Testleri ===


class TestFullDetect:
    """detect (tam tarama) testleri."""

    @patch("app.core.bootstrap.environment_detector.shutil.which")
    async def test_full_scan(self, mock_which: MagicMock) -> None:
        mock_which.return_value = "/usr/bin/test"
        det = _make_detector(software_list=["git"])
        with patch.object(
            det,
            "detect_resources",
            return_value=ResourceInfo(cpu_cores=4),
        ):
            with patch.object(
                det,
                "detect_network",
                return_value=NetworkInfo(internet_access=True),
            ):
                info = await det.detect()
        assert isinstance(info, EnvironmentInfo)
        assert len(info.software) == 1
        assert info.resources.cpu_cores == 4

    @patch("app.core.bootstrap.environment_detector.shutil.which")
    async def test_missing_deps(self, mock_which: MagicMock) -> None:
        mock_which.return_value = None
        det = _make_detector(software_list=["ghost1", "ghost2"])
        with patch.object(
            det, "detect_resources", return_value=ResourceInfo()
        ):
            with patch.object(
                det, "detect_network", return_value=NetworkInfo()
            ):
                info = await det.detect()
        assert len(info.missing_dependencies) == 2


# === DetectMissingDependencies Testleri ===


class TestDetectMissingDependencies:
    """detect_missing_dependencies testleri."""

    @patch("app.core.bootstrap.environment_detector.shutil.which")
    def test_all_present(self, mock_which: MagicMock) -> None:
        mock_which.return_value = "/usr/bin/test"
        det = _make_detector(software_list=["git", "python"])
        missing = det.detect_missing_dependencies()
        assert missing == []

    @patch("app.core.bootstrap.environment_detector.shutil.which")
    def test_some_missing(self, mock_which: MagicMock) -> None:
        mock_which.side_effect = [None, "/usr/bin/python"]
        det = _make_detector(software_list=["ghost", "python"])
        missing = det.detect_missing_dependencies()
        assert missing == ["ghost"]

    @patch("app.core.bootstrap.environment_detector.shutil.which")
    def test_custom_required(self, mock_which: MagicMock) -> None:
        mock_which.return_value = None
        det = _make_detector()
        missing = det.detect_missing_dependencies(required=["exotic_tool"])
        assert missing == ["exotic_tool"]


# === DetectPythonVersion Testleri ===


class TestDetectPythonVersion:
    """detect_python_version testleri."""

    def test_returns_version_string(self) -> None:
        det = _make_detector()
        version = det.detect_python_version()
        assert len(version) > 0
        # Surum en az x.y.z formatinda olmali
        parts = version.split(".")
        assert len(parts) >= 2
