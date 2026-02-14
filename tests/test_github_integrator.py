"""ATLAS GitHub Project Integrator testleri.

RepoDiscoverer, RepoAnalyzer, CompatibilityChecker,
RepoCloner, AutoInstaller, AgentWrapper, ToolAdapter,
SecurityScanner ve GitHubOrchestrator testleri.
"""

import pytest

from app.models.github_integrator import (
    CloneResult,
    CompatibilityResult,
    DependencyInfo,
    InstallMethod,
    InstallResult,
    IntegrationReport,
    LicenseType,
    QualityGrade,
    RepoAnalysis,
    RepoInfo,
    RepoStatus,
    SecurityRisk,
    SecurityScanResult,
    TechStackInfo,
    WrapperConfig,
    WrapperType,
)

from app.core.github_integrator import (
    AgentWrapper,
    AutoInstaller,
    CompatibilityChecker,
    GitHubOrchestrator,
    RepoAnalyzer,
    RepoCloner,
    RepoDiscoverer,
    SecurityScanner,
    ToolAdapter,
)


# ============================================================
# Yardimci fonksiyonlar
# ============================================================

def _sample_repo_data(**overrides):
    """Ornek repo verisi olusturur."""
    data = {
        "name": "test-tool",
        "full_name": "owner/test-tool",
        "stars": 150,
        "forks": 30,
        "open_issues": 5,
        "language": "Python",
        "topics": ["ai", "tool"],
        "description": "A useful AI tool",
        "url": "https://github.com/owner/test-tool",
        "license": "mit",
        "archived": False,
        "updated_at": "2026-02-01T10:00:00Z",
    }
    data.update(overrides)
    return data


def _sample_file_contents(**overrides):
    """Ornek dosya icerikleri."""
    contents = {
        "requirements.txt": "fastapi>=0.100\nredis>=4.0\npydantic>=2.0\n",
        "README.md": "# Test Tool\nA useful AI tool for automation.\n## Usage\nInstall and run.\n",
        ".github/workflows/ci.yml": "name: CI\non: push\n",
        "tests/test_main.py": "def test_ok(): pass\n",
        "main.py": "from fastapi import FastAPI\napp = FastAPI()\n@app.get('/health')\ndef health(): return {'ok': True}\n",
    }
    contents.update(overrides)
    return contents


def _make_repo_info(**overrides):
    """RepoInfo olusturur."""
    defaults = {
        "name": "myrepo",
        "full_name": "owner/myrepo",
        "stars": 100,
        "forks": 20,
        "language": "Python",
        "license_type": LicenseType.MIT,
        "activity_score": 0.6,
    }
    defaults.update(overrides)
    return RepoInfo(**defaults)


def _make_analysis(**overrides):
    """RepoAnalysis olusturur."""
    defaults = {
        "repo_name": "myrepo",
        "tech_stack": TechStackInfo(
            languages=["Python"],
            frameworks=["fastapi"],
        ),
        "dependencies": [
            DependencyInfo(name="fastapi", version="0.100"),
            DependencyInfo(name="redis", version="4.0"),
        ],
        "has_tests": True,
        "has_docs": True,
        "has_ci": True,
        "has_api": True,
        "install_methods": [InstallMethod.PIP],
        "quality_grade": QualityGrade.GOOD,
        "quality_score": 0.7,
    }
    defaults.update(overrides)
    return RepoAnalysis(**defaults)


def _make_clone(**overrides):
    """CloneResult olusturur."""
    defaults = {
        "repo_name": "myrepo",
        "local_path": "data/repos/myrepo",
        "branch": "main",
        "commit_hash": "abc123",
        "size_mb": 10.0,
        "success": True,
    }
    defaults.update(overrides)
    return CloneResult(**defaults)


# ============================================================
# Model Testleri
# ============================================================

class TestModels:
    """Model testleri."""

    def test_repo_status_values(self):
        assert RepoStatus.DISCOVERED == "discovered"
        assert RepoStatus.REGISTERED == "registered"
        assert RepoStatus.FAILED == "failed"

    def test_install_method_values(self):
        assert InstallMethod.PIP == "pip"
        assert InstallMethod.DOCKER == "docker"
        assert InstallMethod.CARGO == "cargo"

    def test_license_type_values(self):
        assert LicenseType.MIT == "mit"
        assert LicenseType.GPL_3 == "gpl-3.0"
        assert LicenseType.PROPRIETARY == "proprietary"

    def test_quality_grade_values(self):
        assert QualityGrade.EXCELLENT == "excellent"
        assert QualityGrade.POOR == "poor"

    def test_security_risk_values(self):
        assert SecurityRisk.SAFE == "safe"
        assert SecurityRisk.CRITICAL == "critical"

    def test_wrapper_type_values(self):
        assert WrapperType.AGENT == "agent"
        assert WrapperType.API == "api"

    def test_repo_info_defaults(self):
        info = RepoInfo()
        assert info.repo_id
        assert info.stars == 0
        assert info.license_type == LicenseType.UNKNOWN

    def test_repo_info_custom(self):
        info = RepoInfo(
            name="test", stars=500,
            license_type=LicenseType.MIT,
        )
        assert info.name == "test"
        assert info.stars == 500

    def test_tech_stack_info(self):
        ts = TechStackInfo(
            languages=["Python"],
            frameworks=["fastapi"],
            databases=["postgresql"],
        )
        assert "Python" in ts.languages
        assert "fastapi" in ts.frameworks

    def test_dependency_info(self):
        dep = DependencyInfo(
            name="fastapi", version="0.100", conflict=True,
            conflict_reason="test catisma",
        )
        assert dep.conflict
        assert dep.conflict_reason

    def test_repo_analysis_defaults(self):
        analysis = RepoAnalysis()
        assert analysis.quality_grade == QualityGrade.UNKNOWN
        assert analysis.dependencies == []

    def test_compatibility_result_defaults(self):
        result = CompatibilityResult()
        assert result.compatible
        assert result.overall_score == 1.0

    def test_clone_result(self):
        clone = CloneResult(
            repo_name="test", branch="dev",
            commit_hash="abc123", size_mb=5.5,
        )
        assert clone.clone_id
        assert clone.branch == "dev"

    def test_install_result(self):
        result = InstallResult(
            repo_name="test", method=InstallMethod.POETRY,
            success=True, installed_packages=["flask"],
        )
        assert result.install_id
        assert result.method == InstallMethod.POETRY

    def test_wrapper_config(self):
        config = WrapperConfig(
            repo_name="test", wrapper_type=WrapperType.AGENT,
            agent_name="test_agent",
        )
        assert config.wrapper_id
        assert not config.registered

    def test_security_scan_result(self):
        scan = SecurityScanResult(
            repo_name="test",
            risk_level=SecurityRisk.HIGH,
            malware_detected=True,
        )
        assert scan.scan_id
        assert scan.malware_detected

    def test_integration_report_defaults(self):
        report = IntegrationReport()
        assert report.report_id
        assert report.status == RepoStatus.DISCOVERED
        assert report.timestamp

    def test_integration_report_full(self):
        report = IntegrationReport(
            repo_name="test",
            status=RepoStatus.REGISTERED,
            recommendation="OK",
            processing_ms=123.4,
        )
        assert report.processing_ms == 123.4


# ============================================================
# RepoDiscoverer Testleri
# ============================================================

class TestRepoDiscoverer:
    """Repo kesfedici testleri."""

    def test_init(self):
        d = RepoDiscoverer()
        assert d.discovered_count == 0

    def test_init_custom_min_stars(self):
        d = RepoDiscoverer(min_stars=50)
        assert d._min_stars == 50

    def test_search_empty(self):
        d = RepoDiscoverer()
        results = d.search("test query")
        assert results == []

    def test_evaluate_repo(self):
        d = RepoDiscoverer()
        repo = d.evaluate_repo(_sample_repo_data())
        assert repo.name == "test-tool"
        assert repo.stars == 150
        assert repo.license_type == LicenseType.MIT
        assert d.discovered_count == 1

    def test_evaluate_repo_archived(self):
        d = RepoDiscoverer()
        repo = d.evaluate_repo(_sample_repo_data(archived=True))
        assert repo.is_archived
        assert repo.activity_score <= 0.15

    def test_evaluate_repo_unknown_license(self):
        d = RepoDiscoverer()
        repo = d.evaluate_repo(_sample_repo_data(license="custom"))
        assert repo.license_type == LicenseType.UNKNOWN

    def test_calculate_relevance(self):
        d = RepoDiscoverer()
        repo = d.evaluate_repo(_sample_repo_data())
        score = d.calculate_relevance(repo, ["ai", "tool"])
        assert score > 0.0
        assert repo.relevance_score == score

    def test_calculate_relevance_no_keywords(self):
        d = RepoDiscoverer()
        repo = d.evaluate_repo(_sample_repo_data())
        score = d.calculate_relevance(repo, [])
        assert score == 0.0

    def test_calculate_relevance_no_match(self):
        d = RepoDiscoverer()
        repo = d.evaluate_repo(_sample_repo_data())
        score = d.calculate_relevance(repo, ["zzzzzz"])
        assert score < 0.5

    def test_filter_repos_min_stars(self):
        d = RepoDiscoverer()
        r1 = d.evaluate_repo(_sample_repo_data(name="big", stars=200))
        r2 = d.evaluate_repo(_sample_repo_data(name="small", stars=2))
        filtered = d.filter_repos([r1, r2], min_stars=50)
        assert len(filtered) == 1
        assert filtered[0].name == "big"

    def test_filter_repos_exclude_archived(self):
        d = RepoDiscoverer()
        r1 = d.evaluate_repo(_sample_repo_data(name="active"))
        r2 = d.evaluate_repo(_sample_repo_data(name="old", archived=True))
        filtered = d.filter_repos([r1, r2])
        assert all(not r.is_archived for r in filtered)

    def test_filter_repos_language(self):
        d = RepoDiscoverer()
        r1 = d.evaluate_repo(_sample_repo_data(name="py", language="Python"))
        r2 = d.evaluate_repo(_sample_repo_data(name="js", language="JavaScript"))
        filtered = d.filter_repos([r1, r2], language="python")
        assert len(filtered) == 1
        assert filtered[0].name == "py"

    def test_rank_repos_by_activity(self):
        d = RepoDiscoverer()
        r1 = d.evaluate_repo(_sample_repo_data(name="hot", stars=10000))
        r2 = d.evaluate_repo(_sample_repo_data(name="cold", stars=5))
        ranked = d.rank_repos([r1, r2])
        assert ranked[0].name == "hot"

    def test_rank_repos_by_relevance(self):
        d = RepoDiscoverer()
        r1 = d.evaluate_repo(
            _sample_repo_data(name="ai-tool", topics=["ai", "ml"])
        )
        r2 = d.evaluate_repo(
            _sample_repo_data(name="other", topics=["web"])
        )
        ranked = d.rank_repos([r1, r2], task_keywords=["ai", "ml"])
        assert ranked[0].name == "ai-tool"

    def test_is_trending(self):
        d = RepoDiscoverer()
        repo = _make_repo_info(activity_score=0.8)
        assert d.is_trending(repo, threshold=0.7)
        assert not d.is_trending(repo, threshold=0.9)

    def test_discovered_repos(self):
        d = RepoDiscoverer()
        d.evaluate_repo(_sample_repo_data())
        assert len(d.discovered_repos) == 1


# ============================================================
# RepoAnalyzer Testleri
# ============================================================

class TestRepoAnalyzer:
    """Repo analizcisi testleri."""

    def test_init(self):
        a = RepoAnalyzer()
        assert a.analysis_count == 0

    def test_analyze_basic(self):
        a = RepoAnalyzer()
        repo = _make_repo_info()
        analysis = a.analyze(repo)
        assert analysis.repo_name == "myrepo"
        assert a.analysis_count == 1

    def test_analyze_tech_stack(self):
        a = RepoAnalyzer()
        repo = _make_repo_info()
        contents = {
            "main.py": "from fastapi import FastAPI\nimport redis\n",
        }
        analysis = a.analyze(repo, contents)
        assert "fastapi" in analysis.tech_stack.frameworks
        assert "Python" in analysis.tech_stack.languages

    def test_analyze_databases(self):
        a = RepoAnalyzer()
        repo = _make_repo_info()
        contents = {
            "db.py": "import asyncpg\nimport redis\n",
        }
        analysis = a.analyze(repo, contents)
        assert "postgresql" in analysis.tech_stack.databases
        assert "redis" in analysis.tech_stack.databases

    def test_analyze_dependencies_requirements(self):
        a = RepoAnalyzer()
        repo = _make_repo_info()
        contents = {
            "requirements.txt": "flask>=2.0\nrequests==2.28\n",
        }
        analysis = a.analyze(repo, contents)
        dep_names = [d.name for d in analysis.dependencies]
        assert "flask" in dep_names
        assert "requests" in dep_names

    def test_analyze_install_methods(self):
        a = RepoAnalyzer()
        repo = _make_repo_info()
        contents = {
            "requirements.txt": "flask\n",
            "Dockerfile": "FROM python:3.11\n",
        }
        analysis = a.analyze(repo, contents)
        assert InstallMethod.PIP in analysis.install_methods
        assert InstallMethod.DOCKER in analysis.install_methods

    def test_analyze_has_tests(self):
        a = RepoAnalyzer()
        repo = _make_repo_info()
        contents = {"tests/test_main.py": "def test_ok(): pass\n"}
        analysis = a.analyze(repo, contents)
        assert analysis.has_tests

    def test_analyze_has_docs(self):
        a = RepoAnalyzer()
        repo = _make_repo_info()
        contents = {"README.md": "# Docs\n"}
        analysis = a.analyze(repo, contents)
        assert analysis.has_docs

    def test_analyze_has_ci(self):
        a = RepoAnalyzer()
        repo = _make_repo_info()
        contents = {".github/workflows/ci.yml": "name: CI\n"}
        analysis = a.analyze(repo, contents)
        assert analysis.has_ci

    def test_analyze_has_api(self):
        a = RepoAnalyzer()
        repo = _make_repo_info()
        contents = {"main.py": "from fastapi import FastAPI\n"}
        analysis = a.analyze(repo, contents)
        assert analysis.has_api

    def test_analyze_api_endpoints(self):
        a = RepoAnalyzer()
        repo = _make_repo_info()
        contents = {
            "main.py": "@app.get('/health')\ndef h(): pass\n@router.post('/items')\ndef i(): pass\n",
        }
        analysis = a.analyze(repo, contents)
        assert "/health" in analysis.api_endpoints
        assert "/items" in analysis.api_endpoints

    def test_analyze_quality_excellent(self):
        a = RepoAnalyzer()
        repo = _make_repo_info(stars=500, activity_score=0.9)
        contents = _sample_file_contents()
        analysis = a.analyze(repo, contents)
        assert analysis.quality_score > 0.5

    def test_analyze_readme_summary(self):
        a = RepoAnalyzer()
        repo = _make_repo_info()
        contents = {"README.md": "# Great Tool\nThis tool does amazing things.\n"}
        analysis = a.analyze(repo, contents)
        assert "Great Tool" in analysis.readme_summary

    def test_analyze_empty_contents(self):
        a = RepoAnalyzer()
        repo = _make_repo_info()
        analysis = a.analyze(repo, {})
        assert analysis.quality_grade in (QualityGrade.POOR, QualityGrade.FAIR, QualityGrade.UNKNOWN)


# ============================================================
# CompatibilityChecker Testleri
# ============================================================

class TestCompatibilityChecker:
    """Uyumluluk kontrolcusu testleri."""

    def test_init(self):
        c = CompatibilityChecker()
        assert c.check_count == 0

    def test_check_compatible(self):
        c = CompatibilityChecker()
        repo = _make_repo_info()
        analysis = _make_analysis()
        result = c.check(repo, analysis)
        assert result.compatible
        assert result.overall_score > 0.5
        assert c.check_count == 1

    def test_check_no_analysis(self):
        c = CompatibilityChecker()
        repo = _make_repo_info()
        result = c.check(repo)
        assert result.compatible

    def test_check_proprietary_license(self):
        c = CompatibilityChecker()
        repo = _make_repo_info(license_type=LicenseType.PROPRIETARY)
        result = c.check(repo)
        assert not result.license_compatible
        assert not result.compatible

    def test_check_dependency_conflict(self):
        c = CompatibilityChecker(installed_packages=["torch"])
        repo = _make_repo_info()
        analysis = _make_analysis(dependencies=[
            DependencyInfo(name="tensorflow", version="2.0"),
        ])
        result = c.check(repo, analysis)
        assert not result.deps_compatible

    def test_check_linux_only(self):
        c = CompatibilityChecker()
        repo = _make_repo_info(description="Linux only tool")
        result = c.check(repo)
        # Windows'ta ise uyumsuz olmali
        import platform
        if platform.system().lower() != "linux":
            assert not result.os_compatible

    def test_check_resource_warning(self):
        c = CompatibilityChecker()
        repo = _make_repo_info()
        many_deps = [DependencyInfo(name=f"pkg{i}") for i in range(55)]
        analysis = _make_analysis(dependencies=many_deps)
        result = c.check(repo, analysis)
        assert any("bagimlilik" in w for w in result.warnings)

    def test_check_heavy_framework(self):
        c = CompatibilityChecker()
        repo = _make_repo_info()
        analysis = _make_analysis(dependencies=[
            DependencyInfo(name="tensorflow", version="2.15"),
        ])
        result = c.check(repo, analysis)
        assert any("GPU" in w or "RAM" in w for w in result.warnings)

    def test_check_dependency_single(self):
        c = CompatibilityChecker(installed_packages=["flask"])
        dep = DependencyInfo(name="flask", version="2.0")
        result = c.check_dependency(dep)
        assert result.available

    def test_check_dependency_not_installed(self):
        c = CompatibilityChecker()
        dep = DependencyInfo(name="rare-package", version="1.0")
        result = c.check_dependency(dep)
        assert not result.available

    def test_add_installed_package(self):
        c = CompatibilityChecker()
        c.add_installed_package("newpkg")
        dep = DependencyInfo(name="newpkg")
        result = c.check_dependency(dep)
        assert result.available

    def test_unknown_license_passes(self):
        c = CompatibilityChecker()
        repo = _make_repo_info(license_type=LicenseType.UNKNOWN)
        result = c.check(repo)
        assert result.license_compatible
        assert any("Lisans" in w for w in result.warnings)


# ============================================================
# RepoCloner Testleri
# ============================================================

class TestRepoCloner:
    """Repo klonlayici testleri."""

    def test_init(self):
        c = RepoCloner()
        assert c.clone_count == 0

    def test_clone(self):
        c = RepoCloner()
        repo = _make_repo_info()
        result = c.clone(repo)
        assert result.success
        assert result.repo_name == "myrepo"
        assert "myrepo" in result.local_path
        assert c.clone_count == 1

    def test_clone_custom_branch(self):
        c = RepoCloner()
        repo = _make_repo_info()
        result = c.clone(repo, branch="develop")
        assert result.branch == "develop"

    def test_clone_sparse(self):
        c = RepoCloner()
        repo = _make_repo_info()
        result = c.clone(repo, sparse_paths=["src/"])
        assert result.sparse

    def test_clone_with_submodules(self):
        c = RepoCloner()
        repo = _make_repo_info()
        result = c.clone_with_submodules(repo)
        assert result.success
        assert result.size_mb > 0

    def test_pin_version(self):
        c = RepoCloner()
        repo = _make_repo_info()
        clone = c.clone(repo)
        pinned = c.pin_version(clone, "2.1.0")
        assert pinned.commit_hash == "v2.1.0"
        assert "2.1.0" in pinned.branch

    def test_get_clone(self):
        c = RepoCloner()
        repo = _make_repo_info()
        c.clone(repo)
        found = c.get_clone("myrepo")
        assert found is not None
        assert found.repo_name == "myrepo"

    def test_get_clone_not_found(self):
        c = RepoCloner()
        assert c.get_clone("nonexistent") is None

    def test_list_clones(self):
        c = RepoCloner()
        r1 = _make_repo_info(name="r1")
        r2 = _make_repo_info(name="r2")
        c.clone(r1)
        c.clone(r2)
        assert len(c.list_clones()) == 2

    def test_remove_clone(self):
        c = RepoCloner()
        repo = _make_repo_info()
        c.clone(repo)
        assert c.remove_clone("myrepo")
        assert c.clone_count == 0

    def test_remove_clone_not_found(self):
        c = RepoCloner()
        assert not c.remove_clone("nonexistent")

    def test_total_size(self):
        c = RepoCloner()
        r1 = _make_repo_info(name="r1", stars=50)
        r2 = _make_repo_info(name="r2", stars=50)
        c.clone(r1)
        c.clone(r2)
        assert c.total_size_mb > 0

    def test_estimate_size_by_stars(self):
        c = RepoCloner()
        big = _make_repo_info(name="big", stars=5000)
        small = _make_repo_info(name="small", stars=5)
        c1 = c.clone(big)
        c2 = c.clone(small)
        assert c1.size_mb > c2.size_mb


# ============================================================
# AutoInstaller Testleri
# ============================================================

class TestAutoInstaller:
    """Otomatik kurucu testleri."""

    def test_init(self):
        ai = AutoInstaller()
        assert ai.install_count == 0

    def test_install_without_approval(self):
        ai = AutoInstaller(require_approval=True)
        clone = _make_clone()
        analysis = _make_analysis()
        result = ai.install(clone, analysis)
        assert not result.success
        assert "onay" in result.error.lower()

    def test_install_with_approval(self):
        ai = AutoInstaller(require_approval=True)
        clone = _make_clone()
        analysis = _make_analysis()
        result = ai.install(clone, analysis, approved=True)
        assert result.success
        assert ai.install_count == 1

    def test_install_no_approval_required(self):
        ai = AutoInstaller(require_approval=False)
        clone = _make_clone()
        analysis = _make_analysis()
        result = ai.install(clone, analysis)
        assert result.success

    def test_install_pre_approved(self):
        ai = AutoInstaller(require_approval=True)
        ai.approve("myrepo")
        clone = _make_clone()
        analysis = _make_analysis()
        result = ai.install(clone, analysis)
        assert result.success

    def test_approve_and_check(self):
        ai = AutoInstaller()
        assert not ai.is_approved("myrepo")
        ai.approve("myrepo")
        assert ai.is_approved("myrepo")

    def test_detect_method_pip(self):
        ai = AutoInstaller()
        analysis = _make_analysis(
            install_methods=[InstallMethod.PIP, InstallMethod.DOCKER],
        )
        method = ai.detect_method(analysis)
        assert method == InstallMethod.PIP

    def test_detect_method_manual(self):
        ai = AutoInstaller()
        analysis = _make_analysis(install_methods=[])
        method = ai.detect_method(analysis)
        assert method == InstallMethod.MANUAL

    def test_get_install_commands(self):
        ai = AutoInstaller()
        cmds = ai.get_install_commands(InstallMethod.PIP)
        assert any("pip" in c for c in cmds)

    def test_get_install_commands_docker(self):
        ai = AutoInstaller()
        cmds = ai.get_install_commands(InstallMethod.DOCKER, "myapp")
        assert any("myapp" in c for c in cmds)

    def test_rollback(self):
        ai = AutoInstaller(require_approval=False)
        clone = _make_clone()
        analysis = _make_analysis()
        ai.install(clone, analysis)
        result = ai.rollback("myrepo")
        assert result["success"]

    def test_rollback_not_found(self):
        ai = AutoInstaller()
        result = ai.rollback("nonexistent")
        assert not result["success"]

    def test_success_rate(self):
        ai = AutoInstaller(require_approval=False)
        clone = _make_clone()
        analysis = _make_analysis()
        ai.install(clone, analysis)
        assert ai.success_rate == 1.0

    def test_success_rate_empty(self):
        ai = AutoInstaller()
        assert ai.success_rate == 0.0


# ============================================================
# AgentWrapper Testleri
# ============================================================

class TestAgentWrapper:
    """Agent sarmalayici testleri."""

    def test_init(self):
        w = AgentWrapper()
        assert w.wrapper_count == 0
        assert w.registered_count == 0

    def test_wrap_as_agent(self):
        w = AgentWrapper()
        config = w.wrap_as_agent("myrepo", "main.run")
        assert config.wrapper_type == WrapperType.AGENT
        assert config.agent_name == "myrepo_agent"
        assert w.wrapper_count == 1

    def test_wrap_as_agent_custom_name(self):
        w = AgentWrapper()
        config = w.wrap_as_agent("myrepo", "main.run", agent_name="custom")
        assert config.agent_name == "custom"

    def test_wrap_as_agent_with_analysis(self):
        w = AgentWrapper()
        analysis = _make_analysis(has_api=True)
        config = w.wrap_as_agent("myrepo", "main.run", analysis=analysis)
        assert "endpoint" in config.input_mapping
        assert "status_code" in config.output_mapping

    def test_wrap_as_tool(self):
        w = AgentWrapper()
        config = w.wrap_as_tool("myrepo", "main.process")
        assert config.wrapper_type == WrapperType.TOOL
        assert config.agent_name == "myrepo_tool"

    def test_register(self):
        w = AgentWrapper()
        w.wrap_as_agent("myrepo", "main.run")
        assert w.register("myrepo_agent")
        assert w.registered_count == 1

    def test_register_not_found(self):
        w = AgentWrapper()
        assert not w.register("nonexistent")

    def test_unregister(self):
        w = AgentWrapper()
        w.wrap_as_agent("myrepo", "main.run")
        w.register("myrepo_agent")
        assert w.unregister("myrepo_agent")
        assert w.registered_count == 0

    def test_unregister_not_found(self):
        w = AgentWrapper()
        assert not w.unregister("nonexistent")

    def test_get_wrapper(self):
        w = AgentWrapper()
        w.wrap_as_agent("myrepo", "main.run")
        config = w.get_wrapper("myrepo_agent")
        assert config is not None
        assert config.repo_name == "myrepo"

    def test_get_wrapper_not_found(self):
        w = AgentWrapper()
        assert w.get_wrapper("nonexistent") is None

    def test_list_wrappers(self):
        w = AgentWrapper()
        w.wrap_as_agent("r1", "main")
        w.wrap_as_agent("r2", "main")
        assert len(w.list_wrappers()) == 2

    def test_list_wrappers_registered_only(self):
        w = AgentWrapper()
        w.wrap_as_agent("r1", "main")
        w.wrap_as_agent("r2", "main")
        w.register("r1_agent")
        registered = w.list_wrappers(registered_only=True)
        assert len(registered) == 1

    def test_generate_agent_code(self):
        w = AgentWrapper()
        w.wrap_as_agent("myrepo", "main.run")
        code = w.generate_agent_code("myrepo_agent")
        assert "class MyrepoAgent" in code
        assert "BaseAgent" in code
        assert "execute" in code

    def test_generate_agent_code_not_found(self):
        w = AgentWrapper()
        assert w.generate_agent_code("nonexistent") == ""


# ============================================================
# ToolAdapter Testleri
# ============================================================

class TestToolAdapter:
    """Arac adaptoru testleri."""

    def test_init(self):
        t = ToolAdapter()
        assert t.adapter_count == 0

    def test_wrap_cli(self):
        t = ToolAdapter()
        adapter = t.wrap_cli("grep", "grep", ["-r", "pattern"])
        assert adapter["type"] == WrapperType.CLI.value
        assert adapter["command"] == "grep"
        assert t.adapter_count == 1

    def test_wrap_library(self):
        t = ToolAdapter()
        adapter = t.wrap_library(
            "numpy_tool", "numpy", ["array", "zeros"],
        )
        assert adapter["type"] == WrapperType.LIBRARY.value
        assert "import" in adapter["import_statement"]

    def test_wrap_api(self):
        t = ToolAdapter()
        adapter = t.wrap_api(
            "weather", "https://api.weather.com",
            endpoints=[{"path": "/current", "method": "GET"}],
            auth_type="api_key",
        )
        assert adapter["type"] == WrapperType.API.value
        assert adapter["auth_type"] == "api_key"

    def test_extract_functions(self):
        t = ToolAdapter()
        source = """
def hello(name: str) -> str:
    \"\"\"Selamlar.\"\"\"
    return f"Hello {name}"

def add(a: int, b: int) -> int:
    \"\"\"Toplar.\"\"\"
    return a + b

def _private():
    pass
"""
        funcs = t.extract_functions(source)
        names = [f["name"] for f in funcs]
        assert "hello" in names
        assert "add" in names
        assert "_private" not in names

    def test_extract_functions_params(self):
        t = ToolAdapter()
        source = 'def greet(name: str, greeting: str = "Hi") -> str:\n    pass\n'
        funcs = t.extract_functions(source)
        assert len(funcs) == 1
        params = funcs[0]["params"]
        assert any(p["name"] == "name" for p in params)

    def test_extract_functions_async(self):
        t = ToolAdapter()
        source = "async def fetch(url: str) -> dict:\n    pass\n"
        funcs = t.extract_functions(source)
        assert funcs[0]["is_async"]

    def test_parse_documentation(self):
        t = ToolAdapter()
        doc = "# Title\nOverview text.\n## Installation\npip install pkg\n## Usage\n```python\nimport pkg\n```\n"
        result = t.parse_documentation(doc)
        assert "title" in result["sections"]
        assert result["has_installation"]
        assert result["has_usage"]
        assert len(result["code_examples"]) >= 1

    def test_get_adapter(self):
        t = ToolAdapter()
        t.wrap_cli("test", "test")
        assert t.get_adapter("test") is not None

    def test_get_adapter_not_found(self):
        t = ToolAdapter()
        assert t.get_adapter("nonexistent") is None

    def test_list_adapters(self):
        t = ToolAdapter()
        t.wrap_cli("a", "a")
        t.wrap_library("b", "b")
        assert len(t.list_adapters()) == 2

    def test_remove_adapter(self):
        t = ToolAdapter()
        t.wrap_cli("test", "test")
        assert t.remove_adapter("test")
        assert t.adapter_count == 0

    def test_remove_adapter_not_found(self):
        t = ToolAdapter()
        assert not t.remove_adapter("nonexistent")


# ============================================================
# SecurityScanner Testleri
# ============================================================

class TestSecurityScanner:
    """Guvenlik tarayici testleri."""

    def test_init(self):
        s = SecurityScanner()
        assert s.scan_count == 0

    def test_scan_safe(self):
        s = SecurityScanner()
        result = s.scan("myrepo", {"main.py": "print('hello')\n"})
        assert result.safe_to_install
        assert result.risk_level == SecurityRisk.SAFE
        assert s.scan_count == 1

    def test_scan_eval_critical(self):
        s = SecurityScanner()
        result = s.scan("myrepo", {"main.py": "eval(input())\n"})
        assert result.risk_level == SecurityRisk.CRITICAL
        assert not result.safe_to_install

    def test_scan_exec_critical(self):
        s = SecurityScanner()
        result = s.scan("myrepo", {"main.py": "exec(code)\n"})
        assert result.risk_level == SecurityRisk.CRITICAL

    def test_scan_os_system_high(self):
        s = SecurityScanner()
        result = s.scan("myrepo", {"main.py": "os.system('ls')\n"})
        assert result.risk_level in (SecurityRisk.HIGH, SecurityRisk.CRITICAL)

    def test_scan_pickle_high(self):
        s = SecurityScanner()
        result = s.scan("myrepo", {"main.py": "pickle.loads(data)\n"})
        assert result.risk_level in (SecurityRisk.HIGH, SecurityRisk.CRITICAL)

    def test_scan_network_access(self):
        s = SecurityScanner()
        result = s.scan("myrepo", {"main.py": "import requests\nrequests.get('http://example.com')\n"})
        assert result.network_access
        assert "network_access" in result.permissions_required

    def test_scan_fs_access(self):
        s = SecurityScanner()
        result = s.scan("myrepo", {"main.py": "open('file.txt')\n"})
        assert result.file_system_access
        assert "file_system_access" in result.permissions_required

    def test_scan_malware_detected(self):
        s = SecurityScanner()
        result = s.scan("myrepo", {"main.py": "# this is a keylogger\n"})
        assert result.malware_detected

    def test_scan_crypto_miner(self):
        s = SecurityScanner()
        result = s.scan("myrepo", {"main.py": "coinhive.start()\n"})
        assert result.malware_detected or result.risk_level == SecurityRisk.CRITICAL

    def test_scan_requires_sandbox(self):
        s = SecurityScanner()
        result = s.scan("myrepo", {"main.py": "eval('1+1')\n"})
        assert result.requires_sandbox

    def test_scan_multiple_findings(self):
        s = SecurityScanner()
        result = s.scan("myrepo", {
            "a.py": "eval(x)\n",
            "b.py": "os.system('cmd')\n",
        })
        assert len(result.findings) >= 2

    def test_quick_scan_safe(self):
        s = SecurityScanner()
        risk = s.quick_scan("myrepo", "print('hello')")
        assert risk == SecurityRisk.SAFE

    def test_quick_scan_critical(self):
        s = SecurityScanner()
        risk = s.quick_scan("myrepo", "eval(user_input)")
        assert risk == SecurityRisk.CRITICAL

    def test_is_safe_to_install(self):
        s = SecurityScanner()
        result = s.scan("myrepo", {"main.py": "print('ok')\n"})
        assert s.is_safe_to_install(result)

    def test_risk_summary_empty(self):
        s = SecurityScanner()
        summary = s.get_risk_summary()
        assert summary["total_scans"] == 0

    def test_risk_summary(self):
        s = SecurityScanner()
        s.scan("safe", {"main.py": "print('ok')\n"})
        s.scan("risky", {"main.py": "eval(x)\n"})
        summary = s.get_risk_summary()
        assert summary["total_scans"] == 2
        assert summary["safe_count"] >= 1
        assert summary["risky_count"] >= 1


# ============================================================
# GitHubOrchestrator Testleri
# ============================================================

class TestGitHubOrchestrator:
    """GitHub orkestrator testleri."""

    def test_init(self):
        o = GitHubOrchestrator()
        assert o.report_count == 0
        assert o.integration_count == 0

    def test_integrate_full_approved(self):
        o = GitHubOrchestrator(require_approval=False)
        report = o.integrate(
            _sample_repo_data(),
            _sample_file_contents(),
            approved=True,
        )
        assert report.status == RepoStatus.REGISTERED
        assert report.repo_name == "test-tool"
        assert report.repo_info is not None
        assert report.analysis is not None
        assert report.compatibility is not None
        assert report.clone_result is not None
        assert report.install_result is not None
        assert report.wrapper is not None
        assert report.processing_ms > 0
        assert o.report_count == 1
        assert o.integration_count == 1

    def test_integrate_as_tool(self):
        o = GitHubOrchestrator(require_approval=False)
        report = o.integrate(
            _sample_repo_data(),
            _sample_file_contents(),
            approved=True,
            wrap_as="tool",
        )
        assert report.status == RepoStatus.REGISTERED
        assert report.wrapper.wrapper_type == WrapperType.TOOL

    def test_integrate_incompatible(self):
        o = GitHubOrchestrator()
        # linux only -> OS uyumsuzlugu (Windows'ta)
        import platform
        if platform.system().lower() != "linux":
            report = o.integrate(
                _sample_repo_data(description="Linux only tool"),
                {},
            )
            assert report.status == RepoStatus.INCOMPATIBLE
            assert "Uyumsuz" in report.recommendation
        else:
            # Linux'ta GPL lisans kullan (allowed_licenses'ta degil)
            report = o.integrate(
                _sample_repo_data(license="gpl-3.0"),
                {},
            )
            # GPL allowed_licenses default'ta yok
            assert report.status in (RepoStatus.INCOMPATIBLE, RepoStatus.FAILED)

    def test_integrate_critical_security(self):
        o = GitHubOrchestrator(require_approval=True)
        report = o.integrate(
            _sample_repo_data(),
            {"main.py": "eval(input())\nkeylogger_start()\n"},
            approved=False,
        )
        assert report.status == RepoStatus.FAILED
        assert "guvenlik" in report.recommendation.lower()

    def test_integrate_unapproved(self):
        o = GitHubOrchestrator(require_approval=True)
        report = o.integrate(
            _sample_repo_data(),
            _sample_file_contents(),
            approved=False,
        )
        # Kurulum onay gerektirir
        assert report.status == RepoStatus.FAILED
        assert "basarisiz" in report.recommendation.lower() or "onay" in report.recommendation.lower()

    def test_evaluate_and_check(self):
        o = GitHubOrchestrator()
        result = o.evaluate_and_check(
            _sample_repo_data(),
            _sample_file_contents(),
        )
        assert "repo" in result
        assert "analysis" in result
        assert "compatibility" in result
        assert "security" in result
        assert "recommended" in result

    def test_approve_install(self):
        o = GitHubOrchestrator()
        o.approve_install("myrepo")
        assert o._installer.is_approved("myrepo")

    def test_rollback(self):
        o = GitHubOrchestrator(require_approval=False)
        o.integrate(
            _sample_repo_data(),
            _sample_file_contents(),
            approved=True,
        )
        result = o.rollback("test-tool")
        assert result["success"]
        assert len(result["steps"]) > 0

    def test_rollback_not_found(self):
        o = GitHubOrchestrator()
        result = o.rollback("nonexistent")
        # Hicbir adim yapilmamis olabilir
        assert isinstance(result["steps"], list)

    def test_get_report(self):
        o = GitHubOrchestrator(require_approval=False)
        o.integrate(
            _sample_repo_data(),
            _sample_file_contents(),
            approved=True,
        )
        report = o.get_report("test-tool")
        assert report is not None
        assert report.repo_name == "test-tool"

    def test_get_report_not_found(self):
        o = GitHubOrchestrator()
        assert o.get_report("nonexistent") is None

    def test_list_integrations(self):
        o = GitHubOrchestrator(require_approval=False)
        o.integrate(
            _sample_repo_data(name="r1"),
            _sample_file_contents(),
            approved=True,
        )
        o.integrate(
            _sample_repo_data(name="r2"),
            _sample_file_contents(),
            approved=True,
        )
        all_reports = o.list_integrations()
        assert len(all_reports) == 2

    def test_list_integrations_by_status(self):
        o = GitHubOrchestrator(require_approval=False)
        o.integrate(
            _sample_repo_data(name="good"),
            _sample_file_contents(),
            approved=True,
        )
        import platform
        if platform.system().lower() != "linux":
            o.integrate(
                _sample_repo_data(name="bad", description="Linux only tool"),
                {},
            )
            registered = o.list_integrations(status=RepoStatus.REGISTERED)
            incomp = o.list_integrations(status=RepoStatus.INCOMPATIBLE)
            assert len(registered) >= 1
            assert len(incomp) >= 1
        else:
            registered = o.list_integrations(status=RepoStatus.REGISTERED)
            assert len(registered) >= 1

    def test_get_stats(self):
        o = GitHubOrchestrator(require_approval=False)
        o.integrate(
            _sample_repo_data(),
            _sample_file_contents(),
            approved=True,
        )
        stats = o.get_stats()
        assert stats["total_integrations"] == 1
        assert stats["successful"] == 1
        assert stats["success_rate"] == 1.0

    def test_get_stats_empty(self):
        o = GitHubOrchestrator()
        stats = o.get_stats()
        assert stats["total_integrations"] == 0
        assert stats["success_rate"] == 0.0

    def test_check_for_updates(self):
        o = GitHubOrchestrator(require_approval=False)
        o.integrate(
            _sample_repo_data(),
            _sample_file_contents(),
            approved=True,
        )
        update = o.check_for_updates("test-tool")
        assert "has_update" in update

    def test_check_for_updates_not_found(self):
        o = GitHubOrchestrator()
        update = o.check_for_updates("nonexistent")
        assert not update["has_update"]

    def test_sub_components_accessible(self):
        o = GitHubOrchestrator()
        assert o.discoverer is not None
        assert o.analyzer is not None
        assert o.scanner is not None

    def test_discover_and_rank(self):
        o = GitHubOrchestrator()
        # search returns empty (simulated)
        results = o.discover_and_rank("test", task_keywords=["ai"])
        assert isinstance(results, list)


# ============================================================
# Entegrasyon Testleri
# ============================================================

class TestIntegration:
    """Entegrasyon testleri."""

    def test_full_pipeline(self):
        """Tam pipeline: kesfet -> analiz -> kontrol -> kur -> sarmala."""
        o = GitHubOrchestrator(require_approval=False)
        report = o.integrate(
            _sample_repo_data(name="ai-pipeline", stars=500),
            _sample_file_contents(),
            approved=True,
        )
        assert report.status == RepoStatus.REGISTERED
        assert report.analysis.has_api
        assert report.compatibility.compatible
        assert report.install_result.success

    def test_security_blocks_install(self):
        """Guvenlik riski kurulumu engeller."""
        o = GitHubOrchestrator(require_approval=True)
        malicious_contents = {
            "main.py": "import os\neval(input())\nkeylogger = True\n",
        }
        report = o.integrate(
            _sample_repo_data(name="malware-tool"),
            malicious_contents,
            approved=False,
        )
        assert report.status == RepoStatus.FAILED

    def test_incompatible_blocks(self):
        """Uyumsuzluk entegrasyonu engeller."""
        o = GitHubOrchestrator()
        import platform
        if platform.system().lower() != "linux":
            report = o.integrate(
                _sample_repo_data(
                    name="linux-tool",
                    description="Linux only tool",
                ),
                {},
            )
            assert report.status == RepoStatus.INCOMPATIBLE
        else:
            report = o.integrate(
                _sample_repo_data(name="gpl-tool", license="gpl-3.0"),
                {},
            )
            assert report.status in (RepoStatus.INCOMPATIBLE, RepoStatus.FAILED)

    def test_rollback_after_integration(self):
        """Entegrasyon sonrasi rollback."""
        o = GitHubOrchestrator(require_approval=False)
        o.integrate(
            _sample_repo_data(name="rollback-test"),
            _sample_file_contents(),
            approved=True,
        )
        result = o.rollback("rollback-test")
        assert result["success"]
        report = o.get_report("rollback-test")
        assert report.status == RepoStatus.FAILED
        assert "Geri alindi" in report.recommendation

    def test_multiple_integrations(self):
        """Birden fazla entegrasyon."""
        o = GitHubOrchestrator(require_approval=False)
        for i in range(3):
            o.integrate(
                _sample_repo_data(name=f"tool-{i}"),
                _sample_file_contents(),
                approved=True,
            )
        assert o.integration_count == 3
        stats = o.get_stats()
        assert stats["successful"] == 3

    def test_evaluate_then_integrate(self):
        """Once degerlendir, sonra entegre et."""
        o = GitHubOrchestrator(require_approval=False)
        eval_result = o.evaluate_and_check(
            _sample_repo_data(),
            _sample_file_contents(),
        )
        assert eval_result["recommended"]

        report = o.integrate(
            _sample_repo_data(),
            _sample_file_contents(),
            approved=True,
        )
        assert report.status == RepoStatus.REGISTERED
