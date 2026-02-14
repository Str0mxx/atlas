"""ATLAS Uyumluluk Kontrolcusu modulu.

Python versiyon uyumlulugu, bagimlilik catismalari,
OS uyumlulugu, kaynak gereksinimleri ve lisans kontrolu.
"""

import logging
import platform
import sys
from typing import Any

from app.models.github_integrator import (
    CompatibilityResult,
    DependencyInfo,
    LicenseType,
    RepoAnalysis,
    RepoInfo,
)

logger = logging.getLogger(__name__)

# Uyumlu lisanslar
_COMPATIBLE_LICENSES: set[LicenseType] = {
    LicenseType.MIT,
    LicenseType.APACHE_2,
    LicenseType.BSD_2,
    LicenseType.BSD_3,
    LicenseType.ISC,
    LicenseType.UNLICENSE,
}

# Bilinen catisma paketleri
_KNOWN_CONFLICTS: dict[str, set[str]] = {
    "tensorflow": {"torch", "jax"},
    "django": {"flask"},
}


class CompatibilityChecker:
    """Uyumluluk kontrol sistemi.

    Repolarun mevcut sistemle uyumlulugunu
    kontrol eder ve sorunlari raporlar.

    Attributes:
        _checks: Kontrol gecmisi.
        _installed_packages: Kurulu paketler.
        _allowed_licenses: Izin verilen lisanslar.
    """

    def __init__(
        self,
        installed_packages: list[str] | None = None,
        allowed_licenses: list[str] | None = None,
    ) -> None:
        """Uyumluluk kontrolcusunu baslatir.

        Args:
            installed_packages: Kurulu paket listesi.
            allowed_licenses: Izin verilen lisanslar.
        """
        self._checks: list[CompatibilityResult] = []
        self._installed_packages: set[str] = set(installed_packages or [])
        self._allowed_licenses = set(
            allowed_licenses or [lt.value for lt in _COMPATIBLE_LICENSES]
        )

        logger.info("CompatibilityChecker baslatildi")

    def check(
        self,
        repo: RepoInfo,
        analysis: RepoAnalysis | None = None,
    ) -> CompatibilityResult:
        """Tam uyumluluk kontrolu yapar.

        Args:
            repo: Repo bilgisi.
            analysis: Repo analizi.

        Returns:
            CompatibilityResult nesnesi.
        """
        issues: list[str] = []
        warnings: list[str] = []

        # Python uyumlulugu
        python_ok = self._check_python_version(analysis, issues, warnings)

        # Bagimlilik catismalari
        deps_ok = self._check_dependency_conflicts(analysis, issues, warnings)

        # OS uyumlulugu
        os_ok = self._check_os_compatibility(repo, analysis, issues, warnings)

        # Lisans kontrolu
        license_ok = self._check_license(repo, issues, warnings)

        # Kaynak gereksinimleri
        resource_ok = self._check_resources(analysis, issues, warnings)

        # Genel skor
        compatible = python_ok and deps_ok and os_ok and license_ok and resource_ok
        score = self._calculate_score(
            python_ok, deps_ok, os_ok, license_ok, resource_ok, len(warnings)
        )

        result = CompatibilityResult(
            compatible=compatible,
            python_compatible=python_ok,
            deps_compatible=deps_ok,
            os_compatible=os_ok,
            license_compatible=license_ok,
            resource_ok=resource_ok,
            issues=issues,
            warnings=warnings,
            overall_score=round(score, 3),
        )

        self._checks.append(result)
        return result

    def check_dependency(
        self, dep: DependencyInfo
    ) -> DependencyInfo:
        """Tek bagimlilik kontrol eder.

        Args:
            dep: Bagimlilik bilgisi.

        Returns:
            Guncellenmis DependencyInfo.
        """
        # Kurulu mu kontrol
        dep.available = dep.name.lower() in {p.lower() for p in self._installed_packages}

        # Catisma kontrolu
        for pkg, conflicts in _KNOWN_CONFLICTS.items():
            if dep.name.lower() == pkg:
                overlap = conflicts & {p.lower() for p in self._installed_packages}
                if overlap:
                    dep.conflict = True
                    dep.conflict_reason = f"{pkg} ile {', '.join(overlap)} catisiyor"

        return dep

    def add_installed_package(self, package: str) -> None:
        """Kurulu paket ekler.

        Args:
            package: Paket adi.
        """
        self._installed_packages.add(package)

    def _check_python_version(
        self,
        analysis: RepoAnalysis | None,
        issues: list[str],
        warnings: list[str],
    ) -> bool:
        """Python versiyon uyumlulugunu kontrol eder."""
        if not analysis or not analysis.tech_stack.python_version:
            return True

        required = analysis.tech_stack.python_version
        current = f"{sys.version_info.major}.{sys.version_info.minor}"

        # Basit versiyon karsilastirmasi
        if ">=" in required:
            min_ver = required.replace(">=", "").strip()
            if self._version_lt(current, min_ver):
                issues.append(
                    f"Python {current} < gerekli {min_ver}"
                )
                return False
        elif required and not required.startswith((">=", "<=", "~", "^")):
            # Tam versiyon eslesmesi
            if not current.startswith(required.split(".")[0]):
                warnings.append(
                    f"Python versiyon farki: mevcut={current}, gerekli={required}"
                )

        return True

    def _check_dependency_conflicts(
        self,
        analysis: RepoAnalysis | None,
        issues: list[str],
        warnings: list[str],
    ) -> bool:
        """Bagimlilik catismalarini kontrol eder."""
        if not analysis:
            return True

        has_conflict = False
        for dep in analysis.dependencies:
            self.check_dependency(dep)
            if dep.conflict:
                issues.append(dep.conflict_reason)
                has_conflict = True

        return not has_conflict

    def _check_os_compatibility(
        self,
        repo: RepoInfo,
        analysis: RepoAnalysis | None,
        issues: list[str],
        warnings: list[str],
    ) -> bool:
        """OS uyumlulugunu kontrol eder."""
        current_os = platform.system().lower()

        # Bilinen OS-spesifik paketler
        if analysis:
            linux_only = {"apt", "systemd", "crontab"}
            for dep in analysis.dependencies:
                if dep.name.lower() in linux_only and current_os == "windows":
                    warnings.append(
                        f"{dep.name} Linux'a ozeldir, Windows'ta sorun olabilir"
                    )

        # Repo aciklamasinda OS kisitlamasi
        desc_lower = repo.description.lower()
        if "linux only" in desc_lower and current_os != "linux":
            issues.append("Repo sadece Linux destekliyor")
            return False
        if "macos only" in desc_lower and current_os != "darwin":
            issues.append("Repo sadece macOS destekliyor")
            return False

        return True

    def _check_license(
        self,
        repo: RepoInfo,
        issues: list[str],
        warnings: list[str],
    ) -> bool:
        """Lisans uyumlulugunu kontrol eder."""
        if repo.license_type == LicenseType.UNKNOWN:
            warnings.append("Lisans bilgisi bulunamadi")
            return True

        if repo.license_type == LicenseType.PROPRIETARY:
            issues.append("Proprietary lisans - ticari kullanim kisitli olabilir")
            return False

        if repo.license_type.value not in self._allowed_licenses:
            issues.append(
                f"Lisans ({repo.license_type.value}) izin verilenler arasinda degil"
            )
            return False

        if repo.license_type == LicenseType.GPL_3:
            warnings.append("GPL-3 lisansi - turev eser GPL olmali")

        return True

    def _check_resources(
        self,
        analysis: RepoAnalysis | None,
        issues: list[str],
        warnings: list[str],
    ) -> bool:
        """Kaynak gereksinimlerini kontrol eder."""
        if not analysis:
            return True

        # Buyuk bagimlilik sayisi = yuksek kaynak
        if len(analysis.dependencies) > 50:
            warnings.append(
                f"Cok fazla bagimlilik ({len(analysis.dependencies)}), yuksek kaynak gerektirebilir"
            )

        # Buyuk framework'ler
        heavy_frameworks = {"tensorflow", "pytorch", "torch"}
        for dep in analysis.dependencies:
            if dep.name.lower() in heavy_frameworks:
                warnings.append(
                    f"{dep.name} GPU/yuksek RAM gerektirebilir"
                )

        return True

    def _version_lt(self, current: str, required: str) -> bool:
        """Versiyon karsilastirmasi yapar."""
        try:
            c_parts = [int(x) for x in current.split(".")]
            r_parts = [int(x) for x in required.split(".")]
            return c_parts < r_parts
        except (ValueError, IndexError):
            return False

    def _calculate_score(
        self,
        python_ok: bool,
        deps_ok: bool,
        os_ok: bool,
        license_ok: bool,
        resource_ok: bool,
        warning_count: int,
    ) -> float:
        """Uyumluluk puani hesaplar."""
        score = 1.0

        if not python_ok:
            score -= 0.3
        if not deps_ok:
            score -= 0.25
        if not os_ok:
            score -= 0.2
        if not license_ok:
            score -= 0.15
        if not resource_ok:
            score -= 0.1

        # Uyarilar skor dusurur
        score -= warning_count * 0.05

        return max(0.0, min(1.0, score))

    @property
    def check_count(self) -> int:
        """Kontrol sayisi."""
        return len(self._checks)
