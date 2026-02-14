"""ATLAS Repo Analizcisi modulu.

README ayrıstirma, tech stack tespit, bagimlilik analizi,
API tespit ve kalite puanlama.
"""

import logging
import re
from typing import Any

from app.models.github_integrator import (
    DependencyInfo,
    InstallMethod,
    QualityGrade,
    RepoAnalysis,
    RepoInfo,
    TechStackInfo,
)

logger = logging.getLogger(__name__)

# Framework tespiti anahtar kelimeleri
_FRAMEWORK_KEYWORDS: dict[str, list[str]] = {
    "fastapi": ["fastapi", "from fastapi"],
    "django": ["django", "from django"],
    "flask": ["flask", "from flask"],
    "express": ["express", "require('express')"],
    "react": ["react", "from 'react'"],
    "pytorch": ["torch", "import torch"],
    "tensorflow": ["tensorflow", "import tensorflow"],
    "langchain": ["langchain", "from langchain"],
    "celery": ["celery", "from celery"],
    "sqlalchemy": ["sqlalchemy", "from sqlalchemy"],
}

# Veritabani tespiti
_DATABASE_KEYWORDS: dict[str, list[str]] = {
    "postgresql": ["postgresql", "psycopg", "asyncpg", "postgres"],
    "mysql": ["mysql", "pymysql", "mysqlclient"],
    "mongodb": ["mongodb", "pymongo", "motor"],
    "redis": ["redis", "aioredis"],
    "sqlite": ["sqlite", "sqlite3"],
    "qdrant": ["qdrant", "qdrant-client"],
    "elasticsearch": ["elasticsearch", "elastic"],
}


class RepoAnalyzer:
    """Repo analiz sistemi.

    Repo icerigini analiz ederek tech stack,
    bagimlilik, kalite ve API bilgisi cikarir.

    Attributes:
        _analyses: Analiz gecmisi.
    """

    def __init__(self) -> None:
        """Repo analizcisini baslatir."""
        self._analyses: list[RepoAnalysis] = []
        logger.info("RepoAnalyzer baslatildi")

    def analyze(
        self,
        repo: RepoInfo,
        file_contents: dict[str, str] | None = None,
    ) -> RepoAnalysis:
        """Repoyu analiz eder.

        Args:
            repo: Repo bilgisi.
            file_contents: Dosya icerikleri (yol -> icerik).

        Returns:
            RepoAnalysis nesnesi.
        """
        contents = file_contents or {}

        tech_stack = self._detect_tech_stack(repo, contents)
        dependencies = self._analyze_dependencies(contents)
        install_methods = self._detect_install_methods(contents)
        has_tests = self._has_tests(contents)
        has_docs = self._has_docs(contents)
        has_ci = self._has_ci(contents)
        has_api = self._has_api(contents)
        api_endpoints = self._detect_api_endpoints(contents)
        readme_summary = self._parse_readme(contents)
        quality_score = self._calculate_quality(
            repo, has_tests, has_docs, has_ci, dependencies
        )
        quality_grade = self._grade_quality(quality_score)

        analysis = RepoAnalysis(
            repo_id=repo.repo_id,
            repo_name=repo.name,
            tech_stack=tech_stack,
            dependencies=dependencies,
            has_tests=has_tests,
            has_docs=has_docs,
            has_ci=has_ci,
            has_api=has_api,
            install_methods=install_methods,
            quality_grade=quality_grade,
            quality_score=round(quality_score, 3),
            readme_summary=readme_summary,
            api_endpoints=api_endpoints,
        )

        self._analyses.append(analysis)
        return analysis

    def _detect_tech_stack(
        self, repo: RepoInfo, contents: dict[str, str]
    ) -> TechStackInfo:
        """Tech stack tespit eder."""
        languages: list[str] = []
        frameworks: list[str] = []
        databases: list[str] = []
        tools: list[str] = []

        if repo.language:
            languages.append(repo.language)

        all_content = " ".join(contents.values()).lower()

        # Framework tespiti
        for framework, keywords in _FRAMEWORK_KEYWORDS.items():
            if any(kw in all_content for kw in keywords):
                frameworks.append(framework)

        # Veritabani tespiti
        for db, keywords in _DATABASE_KEYWORDS.items():
            if any(kw in all_content for kw in keywords):
                databases.append(db)

        # Arac tespiti
        if "docker" in all_content or "dockerfile" in " ".join(contents.keys()).lower():
            tools.append("docker")
        if "docker-compose" in all_content:
            tools.append("docker-compose")
        if "celery" in all_content:
            tools.append("celery")
        if "nginx" in all_content:
            tools.append("nginx")

        # Python version
        python_version = ""
        for key, content in contents.items():
            if "python_requires" in content:
                match = re.search(r'python_requires\s*=\s*["\']([^"\']+)', content)
                if match:
                    python_version = match.group(1)
            if "python-version" in content:
                match = re.search(r'python-version:\s*["\']?(\d+\.\d+)', content)
                if match:
                    python_version = match.group(1)

        return TechStackInfo(
            languages=languages,
            frameworks=frameworks,
            databases=databases,
            tools=tools,
            python_version=python_version,
        )

    def _analyze_dependencies(
        self, contents: dict[str, str]
    ) -> list[DependencyInfo]:
        """Bagimliliklari analiz eder."""
        deps: list[DependencyInfo] = []
        seen: set[str] = set()

        # requirements.txt
        for key, content in contents.items():
            if "requirements" in key.lower() and key.endswith(".txt"):
                for line in content.strip().split("\n"):
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    parts = re.split(r'[>=<~!]', line, maxsplit=1)
                    name = parts[0].strip()
                    version = parts[1].strip() if len(parts) > 1 else ""
                    if name and name not in seen:
                        seen.add(name)
                        deps.append(DependencyInfo(
                            name=name, version=version, required=True,
                        ))

        # pyproject.toml dependencies
        for key, content in contents.items():
            if key.endswith("pyproject.toml"):
                matches = re.findall(r'"([a-zA-Z0-9_-]+)(?:[>=<~!].+)?"', content)
                for name in matches:
                    if name not in seen and len(name) > 1:
                        seen.add(name)
                        deps.append(DependencyInfo(
                            name=name, version="", required=True,
                        ))

        # package.json dependencies
        for key, content in contents.items():
            if key.endswith("package.json"):
                matches = re.findall(r'"([a-zA-Z0-9@/_-]+)":\s*"([^"]*)"', content)
                for name, version in matches:
                    if name not in seen and not name.startswith("{"):
                        seen.add(name)
                        deps.append(DependencyInfo(
                            name=name, version=version, required=True,
                        ))

        return deps

    def _detect_install_methods(self, contents: dict[str, str]) -> list[InstallMethod]:
        """Kurulum yontemlerini tespit eder."""
        methods: list[InstallMethod] = []
        file_keys = {k.lower() for k in contents}

        if any("requirements" in k for k in file_keys):
            methods.append(InstallMethod.PIP)
        if any("pyproject.toml" in k for k in file_keys):
            methods.append(InstallMethod.POETRY)
        if any("setup.py" in k for k in file_keys):
            methods.append(InstallMethod.SETUP_PY)
        if any("package.json" in k for k in file_keys):
            methods.append(InstallMethod.NPM)
        if any("dockerfile" in k for k in file_keys):
            methods.append(InstallMethod.DOCKER)
        if any("makefile" in k for k in file_keys):
            methods.append(InstallMethod.MAKE)
        if any("cargo.toml" in k for k in file_keys):
            methods.append(InstallMethod.CARGO)

        if not methods:
            methods.append(InstallMethod.MANUAL)

        return methods

    def _has_tests(self, contents: dict[str, str]) -> bool:
        """Test var mi kontrol eder."""
        for key in contents:
            lower = key.lower()
            if "test" in lower and (lower.endswith(".py") or lower.endswith(".js")):
                return True
            if "tests/" in lower or "test/" in lower:
                return True
        return False

    def _has_docs(self, contents: dict[str, str]) -> bool:
        """Dokumantasyon var mi kontrol eder."""
        for key in contents:
            lower = key.lower()
            if "readme" in lower:
                return True
            if "docs/" in lower or "documentation" in lower:
                return True
        return False

    def _has_ci(self, contents: dict[str, str]) -> bool:
        """CI/CD var mi kontrol eder."""
        for key in contents:
            lower = key.lower()
            if ".github/workflows" in lower:
                return True
            if ".gitlab-ci" in lower:
                return True
            if "jenkinsfile" in lower:
                return True
            if ".travis.yml" in lower:
                return True
        return False

    def _has_api(self, contents: dict[str, str]) -> bool:
        """API var mi kontrol eder."""
        all_content = " ".join(contents.values()).lower()
        api_indicators = [
            "fastapi", "flask", "express", "django rest",
            "@app.route", "@router.", "openapi", "swagger",
        ]
        return any(ind in all_content for ind in api_indicators)

    def _detect_api_endpoints(self, contents: dict[str, str]) -> list[str]:
        """API endpoint'lerini tespit eder."""
        endpoints: list[str] = []
        for content in contents.values():
            # FastAPI/Flask route patterns
            matches = re.findall(
                r'@(?:app|router)\.\w+\(["\']([^"\']+)', content
            )
            endpoints.extend(matches)

        return sorted(set(endpoints))

    def _parse_readme(self, contents: dict[str, str]) -> str:
        """README'yi ozetler."""
        for key, content in contents.items():
            if "readme" in key.lower():
                # Ilk 200 karakter
                clean = re.sub(r'[#*`\[\]()]', '', content).strip()
                return clean[:200]
        return ""

    def _calculate_quality(
        self,
        repo: RepoInfo,
        has_tests: bool,
        has_docs: bool,
        has_ci: bool,
        deps: list[DependencyInfo],
    ) -> float:
        """Kalite puani hesaplar."""
        score = 0.0

        # Test varsa
        if has_tests:
            score += 0.25

        # Dokumantasyon varsa
        if has_docs:
            score += 0.2

        # CI/CD varsa
        if has_ci:
            score += 0.15

        # Yildiz katkisi
        if repo.stars > 100:
            score += 0.15
        elif repo.stars > 10:
            score += 0.1
        elif repo.stars > 0:
            score += 0.05

        # Aktivite
        score += repo.activity_score * 0.15

        # Bagimlilik sayisi (cok fazla = negatif)
        if len(deps) < 20:
            score += 0.1
        elif len(deps) < 50:
            score += 0.05

        return min(score, 1.0)

    def _grade_quality(self, score: float) -> QualityGrade:
        """Kalite notu verir."""
        if score >= 0.8:
            return QualityGrade.EXCELLENT
        if score >= 0.6:
            return QualityGrade.GOOD
        if score >= 0.4:
            return QualityGrade.FAIR
        if score > 0:
            return QualityGrade.POOR
        return QualityGrade.UNKNOWN

    @property
    def analysis_count(self) -> int:
        """Analiz sayisi."""
        return len(self._analyses)
