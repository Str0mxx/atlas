"""ATLAS Otomatik Kurulum modulu.

Kurulum yontemi tespit, setup komutlari,
ortam ayarlama, konfigrasyon uretimi ve bagimlilik kurulumu.
"""

import logging
from typing import Any

from app.models.github_integrator import (
    CloneResult,
    InstallMethod,
    InstallResult,
    RepoAnalysis,
)

logger = logging.getLogger(__name__)

# Kurulum yontemi -> komutlar
_INSTALL_COMMANDS: dict[InstallMethod, list[str]] = {
    InstallMethod.PIP: [
        "pip install -r requirements.txt",
        "pip install -e .",
    ],
    InstallMethod.POETRY: [
        "poetry install",
    ],
    InstallMethod.SETUP_PY: [
        "python setup.py install",
    ],
    InstallMethod.NPM: [
        "npm install",
    ],
    InstallMethod.DOCKER: [
        "docker build -t {name} .",
    ],
    InstallMethod.MAKE: [
        "make install",
    ],
    InstallMethod.CARGO: [
        "cargo build --release",
    ],
    InstallMethod.MANUAL: [
        "# Manuel kurulum gerekli",
    ],
}


class AutoInstaller:
    """Otomatik kurulum sistemi.

    Repolarin kurulum yontemini tespit eder,
    komutlari calistirir ve sonuclari raporlar.

    Attributes:
        _installs: Kurulum gecmisi.
        _approved: Onaylanmis kurulumlar.
    """

    def __init__(self, require_approval: bool = True) -> None:
        """Otomatik kurulumu baslatir.

        Args:
            require_approval: Kurulum onay gerekli mi.
        """
        self._installs: list[InstallResult] = []
        self._require_approval = require_approval
        self._approved: set[str] = set()

        logger.info("AutoInstaller baslatildi (approval=%s)", require_approval)

    def install(
        self,
        clone: CloneResult,
        analysis: RepoAnalysis,
        method: InstallMethod | None = None,
        approved: bool = False,
    ) -> InstallResult:
        """Repoyu kurar (simule).

        Args:
            clone: Klon sonucu.
            analysis: Repo analizi.
            method: Kurulum yontemi (None ise otomatik).
            approved: Onaylandi mi.

        Returns:
            InstallResult nesnesi.
        """
        if self._require_approval and not approved and clone.repo_name not in self._approved:
            return InstallResult(
                repo_name=clone.repo_name,
                success=False,
                error="Kurulum onay bekliyor",
            )

        # Yontem sec
        install_method = method or self._select_method(analysis)

        # Komutlari al
        commands = self._get_commands(install_method, clone.repo_name)

        # Simule edilmis kurulum
        steps_completed: list[str] = []
        installed_pkgs: list[str] = []

        for cmd in commands:
            steps_completed.append(f"[OK] {cmd}")

        # Bagimlilik listesini kaydet
        for dep in analysis.dependencies:
            installed_pkgs.append(dep.name)

        # Config uretimi
        config_generated = self._generate_config(clone, analysis)

        result = InstallResult(
            repo_name=clone.repo_name,
            method=install_method,
            success=True,
            steps_completed=steps_completed,
            installed_packages=installed_pkgs,
            config_generated=config_generated,
        )

        self._installs.append(result)
        self._approved.add(clone.repo_name)

        logger.info(
            "Repo kuruldu: %s (method=%s, pkgs=%d)",
            clone.repo_name, install_method.value, len(installed_pkgs),
        )

        return result

    def approve(self, repo_name: str) -> None:
        """Kurulumu onaylar.

        Args:
            repo_name: Repo adi.
        """
        self._approved.add(repo_name)

    def is_approved(self, repo_name: str) -> bool:
        """Onay durumunu kontrol eder.

        Args:
            repo_name: Repo adi.

        Returns:
            Onaylandi ise True.
        """
        return repo_name in self._approved

    def detect_method(self, analysis: RepoAnalysis) -> InstallMethod:
        """Kurulum yontemini tespit eder.

        Args:
            analysis: Repo analizi.

        Returns:
            InstallMethod degeri.
        """
        return self._select_method(analysis)

    def get_install_commands(
        self, method: InstallMethod, repo_name: str = ""
    ) -> list[str]:
        """Kurulum komutlarini getirir.

        Args:
            method: Kurulum yontemi.
            repo_name: Repo adi.

        Returns:
            Komut listesi.
        """
        return self._get_commands(method, repo_name)

    def rollback(self, repo_name: str) -> dict[str, Any]:
        """Kurulumu geri alir (simule).

        Args:
            repo_name: Repo adi.

        Returns:
            Geri alma sonucu.
        """
        install = None
        for inst in reversed(self._installs):
            if inst.repo_name == repo_name:
                install = inst
                break

        if not install:
            return {"success": False, "error": "Kurulum bulunamadi"}

        uninstall_steps: list[str] = []
        for pkg in install.installed_packages:
            uninstall_steps.append(f"pip uninstall -y {pkg}")

        return {
            "success": True,
            "repo_name": repo_name,
            "uninstalled_packages": install.installed_packages,
            "steps": uninstall_steps,
        }

    def _select_method(self, analysis: RepoAnalysis) -> InstallMethod:
        """En uygun kurulum yontemini secer."""
        if not analysis.install_methods:
            return InstallMethod.MANUAL

        # Oncelik sirasi
        priority = [
            InstallMethod.PIP,
            InstallMethod.POETRY,
            InstallMethod.SETUP_PY,
            InstallMethod.NPM,
            InstallMethod.DOCKER,
            InstallMethod.MAKE,
            InstallMethod.CARGO,
        ]

        for method in priority:
            if method in analysis.install_methods:
                return method

        return analysis.install_methods[0]

    def _get_commands(self, method: InstallMethod, repo_name: str) -> list[str]:
        """Kurulum komutlarini olusturur."""
        base = _INSTALL_COMMANDS.get(method, ["# Bilinmeyen yontem"])
        return [cmd.replace("{name}", repo_name) for cmd in base]

    def _generate_config(
        self, clone: CloneResult, analysis: RepoAnalysis
    ) -> bool:
        """Konfigurasyon dosyasi uretir (simule)."""
        # API varsa config uret
        if analysis.has_api:
            return True
        # Veritabani varsa config uret
        if analysis.tech_stack.databases:
            return True
        return False

    @property
    def install_count(self) -> int:
        """Kurulum sayisi."""
        return len(self._installs)

    @property
    def success_rate(self) -> float:
        """Basari orani."""
        if not self._installs:
            return 0.0
        successes = sum(1 for i in self._installs if i.success)
        return successes / len(self._installs)
