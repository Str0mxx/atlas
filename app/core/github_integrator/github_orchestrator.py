"""ATLAS GitHub Orkestrator modulu.

Search -> Analyze -> Check -> Clone -> Install -> Wrap -> Register
pipeline'ini yonetir. Kullanici onayi, rollback ve
kullanim takibi saglar.
"""

import logging
import time
from typing import Any

from app.models.github_integrator import (
    CloneResult,
    CompatibilityResult,
    InstallResult,
    IntegrationReport,
    RepoAnalysis,
    RepoInfo,
    RepoStatus,
    SecurityRisk,
    SecurityScanResult,
    WrapperConfig,
)

from app.core.github_integrator.agent_wrapper import AgentWrapper
from app.core.github_integrator.auto_installer import AutoInstaller
from app.core.github_integrator.compatibility_checker import CompatibilityChecker
from app.core.github_integrator.repo_analyzer import RepoAnalyzer
from app.core.github_integrator.repo_cloner import RepoCloner
from app.core.github_integrator.repo_discoverer import RepoDiscoverer
from app.core.github_integrator.security_scanner import SecurityScanner
from app.core.github_integrator.tool_adapter import ToolAdapter

logger = logging.getLogger(__name__)


class GitHubOrchestrator:
    """GitHub entegrasyon orkestratoru.

    Kesfetten kayda kadar tum pipeline'i yonetir,
    kullanici onayi alir, basarisiz durumlarda rollback yapar.

    Attributes:
        _discoverer: Repo kesfedici.
        _analyzer: Repo analizcisi.
        _checker: Uyumluluk kontrolcusu.
        _cloner: Repo klonlayici.
        _installer: Otomatik kurucu.
        _wrapper: Agent sarmalayici.
        _adapter: Arac adaptoru.
        _scanner: Guvenlik tarayici.
        _reports: Entegrasyon raporlari.
        _integrations: Basarili entegrasyonlar.
    """

    def __init__(
        self,
        min_stars: int = 10,
        require_approval: bool = True,
        sandbox_untrusted: bool = True,
    ) -> None:
        """Orkestratoru baslatir.

        Args:
            min_stars: Minimum yildiz filtresi.
            require_approval: Kurulum onay gerekli mi.
            sandbox_untrusted: Guvenilmeyenleri sandbox'ta calistir.
        """
        self._discoverer = RepoDiscoverer(min_stars=min_stars)
        self._analyzer = RepoAnalyzer()
        self._checker = CompatibilityChecker()
        self._cloner = RepoCloner()
        self._installer = AutoInstaller(require_approval=require_approval)
        self._wrapper = AgentWrapper()
        self._adapter = ToolAdapter()
        self._scanner = SecurityScanner()

        self._require_approval = require_approval
        self._sandbox_untrusted = sandbox_untrusted
        self._reports: list[IntegrationReport] = []
        self._integrations: dict[str, IntegrationReport] = {}

        logger.info(
            "GitHubOrchestrator baslatildi "
            "(min_stars=%d, approval=%s, sandbox=%s)",
            min_stars, require_approval, sandbox_untrusted,
        )

    def integrate(
        self,
        repo_data: dict[str, Any],
        file_contents: dict[str, str] | None = None,
        approved: bool = False,
        wrap_as: str = "agent",
        entry_point: str = "main",
    ) -> IntegrationReport:
        """Tam entegrasyon pipeline'i calistirir.

        Search -> Analyze -> Check -> Clone -> Install -> Wrap -> Register

        Args:
            repo_data: Ham repo verisi.
            file_contents: Dosya icerikleri (opsiyonel).
            approved: Kurulum onayli mi.
            wrap_as: Sarmalama tipi (agent/tool).
            entry_point: Giris noktasi.

        Returns:
            IntegrationReport nesnesi.
        """
        start = time.monotonic()
        report = IntegrationReport()

        try:
            # 1. Kesfet ve degerlendir
            repo = self._discoverer.evaluate_repo(repo_data)
            report.repo_name = repo.name
            report.repo_info = repo
            report.status = RepoStatus.DISCOVERED

            # 2. Analiz et
            analysis = self._analyzer.analyze(repo, file_contents)
            report.analysis = analysis
            report.status = RepoStatus.ANALYZED

            # 3. Uyumluluk kontrolu
            compat = self._checker.check(repo, analysis)
            report.compatibility = compat

            if not compat.compatible:
                report.status = RepoStatus.INCOMPATIBLE
                report.recommendation = (
                    "Uyumsuz: " + "; ".join(compat.issues)
                )
                report.processing_ms = (time.monotonic() - start) * 1000
                self._reports.append(report)
                return report

            report.status = RepoStatus.COMPATIBLE

            # 4. Guvenlik taramasi
            scan = self._scanner.scan(repo.name, file_contents or {})
            report.security_scan = scan

            if scan.risk_level == SecurityRisk.CRITICAL and not approved:
                report.status = RepoStatus.FAILED
                report.recommendation = (
                    "Kritik guvenlik riski tespit edildi. "
                    "Manuel onay gerekli."
                )
                report.processing_ms = (time.monotonic() - start) * 1000
                self._reports.append(report)
                return report

            # 5. Klonla
            clone = self._cloner.clone(repo)
            report.clone_result = clone
            report.status = RepoStatus.CLONED

            # 6. Kur
            install = self._installer.install(
                clone, analysis, approved=approved,
            )
            report.install_result = install

            if not install.success:
                report.status = RepoStatus.FAILED
                report.recommendation = (
                    f"Kurulum basarisiz: {install.error}"
                )
                # Rollback
                self._cloner.remove_clone(repo.name)
                report.processing_ms = (time.monotonic() - start) * 1000
                self._reports.append(report)
                return report

            report.status = RepoStatus.INSTALLED

            # 7. Sarmala
            if wrap_as == "agent":
                wrapper = self._wrapper.wrap_as_agent(
                    repo.name, entry_point, analysis=analysis,
                )
            else:
                wrapper = self._wrapper.wrap_as_tool(
                    repo.name, entry_point,
                )

            report.wrapper = wrapper
            report.status = RepoStatus.WRAPPED

            # 8. Kaydet
            self._wrapper.register(wrapper.agent_name)
            report.status = RepoStatus.REGISTERED

            report.recommendation = "Entegrasyon basarili"
            self._integrations[repo.name] = report

        except Exception as e:
            report.status = RepoStatus.FAILED
            report.recommendation = f"Hata: {e}"
            logger.error("Entegrasyon hatasi: %s", e)

        report.processing_ms = (time.monotonic() - start) * 1000
        self._reports.append(report)
        return report

    def discover_and_rank(
        self,
        query: str,
        task_keywords: list[str] | None = None,
        language: str = "python",
        max_results: int = 10,
    ) -> list[RepoInfo]:
        """Repo kesfeder ve siralar.

        Args:
            query: Arama sorgusu.
            task_keywords: Gorev anahtar kelimeleri.
            language: Dil filtresi.
            max_results: Maks sonuc.

        Returns:
            Siralanmis RepoInfo listesi.
        """
        repos = self._discoverer.search(query, language, max_results)
        filtered = self._discoverer.filter_repos(repos, language=language)
        ranked = self._discoverer.rank_repos(filtered, task_keywords)
        return ranked

    def evaluate_and_check(
        self,
        repo_data: dict[str, Any],
        file_contents: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Repoyu degerlendirir ve uyumluluğunu kontrol eder.

        Args:
            repo_data: Ham repo verisi.
            file_contents: Dosya icerikleri.

        Returns:
            Degerlendirme sonucu.
        """
        repo = self._discoverer.evaluate_repo(repo_data)
        analysis = self._analyzer.analyze(repo, file_contents)
        compat = self._checker.check(repo, analysis)
        scan = self._scanner.scan(repo.name, file_contents or {})

        return {
            "repo": repo,
            "analysis": analysis,
            "compatibility": compat,
            "security": scan,
            "recommended": compat.compatible and scan.safe_to_install,
        }

    def approve_install(self, repo_name: str) -> None:
        """Kurulumu onaylar.

        Args:
            repo_name: Repo adi.
        """
        self._installer.approve(repo_name)
        logger.info("Kurulum onaylandi: %s", repo_name)

    def rollback(self, repo_name: str) -> dict[str, Any]:
        """Entegrasyonu geri alir.

        Args:
            repo_name: Repo adi.

        Returns:
            Geri alma sonucu.
        """
        results: dict[str, Any] = {"repo_name": repo_name, "steps": []}

        # Wrapper kaldir
        wrapper = self._wrapper.get_wrapper(f"{repo_name}_agent")
        if wrapper:
            self._wrapper.unregister(wrapper.agent_name)
            results["steps"].append("wrapper_removed")

        # Kurulumu geri al
        install_rollback = self._installer.rollback(repo_name)
        results["install_rollback"] = install_rollback
        if install_rollback.get("success"):
            results["steps"].append("install_rolled_back")

        # Klonu sil
        if self._cloner.remove_clone(repo_name):
            results["steps"].append("clone_removed")

        # Entegrasyon kaydini guncelle
        if repo_name in self._integrations:
            self._integrations[repo_name].status = RepoStatus.FAILED
            self._integrations[repo_name].recommendation = "Geri alindi"
            results["steps"].append("integration_updated")

        results["success"] = len(results["steps"]) > 0
        logger.info("Rollback: %s -> %s", repo_name, results["steps"])
        return results

    def get_report(self, repo_name: str) -> IntegrationReport | None:
        """Entegrasyon raporunu getirir.

        Args:
            repo_name: Repo adi.

        Returns:
            IntegrationReport veya None.
        """
        return self._integrations.get(repo_name)

    def list_integrations(
        self, status: RepoStatus | None = None
    ) -> list[IntegrationReport]:
        """Entegrasyonlari listeler.

        Args:
            status: Durum filtresi.

        Returns:
            IntegrationReport listesi.
        """
        if status:
            return [
                r for r in self._reports if r.status == status
            ]
        return list(self._reports)

    def get_stats(self) -> dict[str, Any]:
        """Istatistikleri getirir.

        Returns:
            Istatistik sozlugu.
        """
        total = len(self._reports)
        successful = sum(
            1 for r in self._reports
            if r.status == RepoStatus.REGISTERED
        )
        failed = sum(
            1 for r in self._reports
            if r.status == RepoStatus.FAILED
        )
        incompatible = sum(
            1 for r in self._reports
            if r.status == RepoStatus.INCOMPATIBLE
        )

        return {
            "total_integrations": total,
            "successful": successful,
            "failed": failed,
            "incompatible": incompatible,
            "success_rate": successful / total if total > 0 else 0.0,
            "active_integrations": len(self._integrations),
            "total_clones_mb": self._cloner.total_size_mb,
        }

    def check_for_updates(self, repo_name: str) -> dict[str, Any]:
        """Guncelleme kontrol eder.

        Args:
            repo_name: Repo adi.

        Returns:
            Guncelleme bilgisi.
        """
        report = self._integrations.get(repo_name)
        if not report or not report.clone_result:
            return {"has_update": False, "reason": "Entegrasyon bulunamadi"}

        # Simule: Guncelleme kontrol
        return {
            "has_update": False,
            "current_commit": report.clone_result.commit_hash,
            "repo_name": repo_name,
            "status": "guncel",
        }

    @property
    def discoverer(self) -> RepoDiscoverer:
        """Repo kesfedici."""
        return self._discoverer

    @property
    def analyzer(self) -> RepoAnalyzer:
        """Repo analizcisi."""
        return self._analyzer

    @property
    def scanner(self) -> SecurityScanner:
        """Guvenlik tarayici."""
        return self._scanner

    @property
    def report_count(self) -> int:
        """Rapor sayisi."""
        return len(self._reports)

    @property
    def integration_count(self) -> int:
        """Aktif entegrasyon sayisi."""
        return len(self._integrations)
