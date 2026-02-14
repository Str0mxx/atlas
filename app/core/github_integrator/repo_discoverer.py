"""ATLAS Repo Kesfedici modulu.

GitHub'da topic/keyword ile arama, trending tespit,
stars/forks analizi, aktivite puanlama ve uygunluk esleme.
"""

import logging
import math
from datetime import datetime, timezone, timedelta
from typing import Any

from app.models.github_integrator import (
    LicenseType,
    RepoInfo,
)

logger = logging.getLogger(__name__)

# Bilinen lisans eslesmesi
_LICENSE_MAP: dict[str, LicenseType] = {
    "mit": LicenseType.MIT,
    "apache-2.0": LicenseType.APACHE_2,
    "gpl-3.0": LicenseType.GPL_3,
    "bsd-2-clause": LicenseType.BSD_2,
    "bsd-3-clause": LicenseType.BSD_3,
    "lgpl-2.1": LicenseType.LGPL,
    "lgpl-3.0": LicenseType.LGPL,
    "isc": LicenseType.ISC,
    "unlicense": LicenseType.UNLICENSE,
}


class RepoDiscoverer:
    """Repo kesfetme sistemi.

    GitHub uzerinde arama, trending analizi,
    aktivite puanlama ve uygunluk esleme yapar.

    Attributes:
        _discovered: Kesfedilen repolar.
        _min_stars: Minimum yildiz filtresi.
        _allowed_licenses: Izin verilen lisanslar.
    """

    def __init__(
        self,
        min_stars: int = 10,
        allowed_licenses: list[str] | None = None,
    ) -> None:
        """Repo kesfediciyi baslatir.

        Args:
            min_stars: Minimum yildiz sayisi.
            allowed_licenses: Izin verilen lisanslar.
        """
        self._discovered: list[RepoInfo] = []
        self._min_stars = min_stars
        self._allowed_licenses = allowed_licenses or [
            "mit", "apache-2.0", "bsd-2-clause", "bsd-3-clause", "isc", "unlicense",
        ]

        logger.info("RepoDiscoverer baslatildi (min_stars=%d)", min_stars)

    def search(
        self,
        query: str,
        language: str = "python",
        max_results: int = 10,
        sort_by: str = "stars",
    ) -> list[RepoInfo]:
        """GitHub'da arama yapar (simule).

        Args:
            query: Arama sorgusu.
            language: Programlama dili.
            max_results: Maks sonuc.
            sort_by: Siralama (stars, forks, updated).

        Returns:
            RepoInfo listesi.
        """
        # Simule edilmis arama - gercekte GitHub API kullanilir
        results: list[RepoInfo] = []

        logger.info(
            "GitHub araması: query=%s, lang=%s, sort=%s",
            query, language, sort_by,
        )

        return results

    def evaluate_repo(self, repo_data: dict[str, Any]) -> RepoInfo:
        """Ham repo verisini degerlendirir.

        Args:
            repo_data: GitHub API'den gelen ham veri.

        Returns:
            RepoInfo nesnesi.
        """
        name = repo_data.get("name", "")
        full_name = repo_data.get("full_name", name)
        stars = repo_data.get("stars", 0)
        forks = repo_data.get("forks", 0)
        open_issues = repo_data.get("open_issues", 0)
        language = repo_data.get("language", "")
        topics = repo_data.get("topics", [])
        description = repo_data.get("description", "")
        url = repo_data.get("url", f"https://github.com/{full_name}")
        license_key = repo_data.get("license", "unknown")
        is_archived = repo_data.get("archived", False)
        last_updated_str = repo_data.get("updated_at", "")

        # Lisans esleme
        license_type = _LICENSE_MAP.get(license_key.lower(), LicenseType.UNKNOWN)

        # Aktivite puani
        activity = self._calculate_activity_score(
            stars, forks, open_issues, last_updated_str, is_archived
        )

        # Son guncelleme
        if last_updated_str:
            try:
                last_updated = datetime.fromisoformat(last_updated_str.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                last_updated = datetime.now(timezone.utc)
        else:
            last_updated = datetime.now(timezone.utc)

        info = RepoInfo(
            name=name,
            full_name=full_name,
            url=url,
            description=description,
            stars=stars,
            forks=forks,
            open_issues=open_issues,
            language=language,
            topics=topics,
            license_type=license_type,
            last_updated=last_updated,
            is_archived=is_archived,
            activity_score=round(activity, 3),
        )

        self._discovered.append(info)
        return info

    def calculate_relevance(
        self, repo: RepoInfo, task_keywords: list[str]
    ) -> float:
        """Goreve uygunluk puani hesaplar.

        Args:
            repo: Repo bilgisi.
            task_keywords: Gorev anahtar kelimeleri.

        Returns:
            Uygunluk puani (0-1).
        """
        if not task_keywords:
            return 0.0

        score = 0.0
        searchable = (
            f"{repo.name} {repo.description} {' '.join(repo.topics)}".lower()
        )

        matches = sum(1 for kw in task_keywords if kw.lower() in searchable)
        keyword_score = matches / len(task_keywords)
        score += keyword_score * 0.5

        # Aktivite etkisi
        score += repo.activity_score * 0.3

        # Yildiz etkisi (logaritmik)
        if repo.stars > 0:
            star_score = min(math.log10(repo.stars) / 5, 1.0)
            score += star_score * 0.2

        repo.relevance_score = round(min(score, 1.0), 3)
        return repo.relevance_score

    def filter_repos(
        self,
        repos: list[RepoInfo],
        min_stars: int | None = None,
        language: str | None = None,
        exclude_archived: bool = True,
        allowed_licenses: list[str] | None = None,
    ) -> list[RepoInfo]:
        """Repolari filtreler.

        Args:
            repos: Repo listesi.
            min_stars: Minimum yildiz.
            language: Dil filtresi.
            exclude_archived: Arsivlenmisleri haric tut.
            allowed_licenses: Izin verilen lisanslar.

        Returns:
            Filtrelenmis RepoInfo listesi.
        """
        min_s = min_stars if min_stars is not None else self._min_stars
        licenses = allowed_licenses or self._allowed_licenses

        filtered: list[RepoInfo] = []
        for repo in repos:
            if repo.stars < min_s:
                continue
            if exclude_archived and repo.is_archived:
                continue
            if language and repo.language.lower() != language.lower():
                continue
            if licenses and repo.license_type != LicenseType.UNKNOWN:
                if repo.license_type.value not in licenses:
                    continue
            filtered.append(repo)

        return filtered

    def rank_repos(
        self, repos: list[RepoInfo], task_keywords: list[str] | None = None
    ) -> list[RepoInfo]:
        """Repolari siralar.

        Args:
            repos: Repo listesi.
            task_keywords: Gorev anahtar kelimeleri.

        Returns:
            Siralanmis RepoInfo listesi.
        """
        if task_keywords:
            for repo in repos:
                self.calculate_relevance(repo, task_keywords)
            return sorted(repos, key=lambda r: r.relevance_score, reverse=True)

        return sorted(repos, key=lambda r: r.activity_score, reverse=True)

    def is_trending(self, repo: RepoInfo, threshold: float = 0.7) -> bool:
        """Repo trending mi kontrol eder.

        Args:
            repo: Repo bilgisi.
            threshold: Esik degeri.

        Returns:
            Trending ise True.
        """
        return repo.activity_score >= threshold

    def _calculate_activity_score(
        self,
        stars: int,
        forks: int,
        open_issues: int,
        last_updated: str,
        is_archived: bool,
    ) -> float:
        """Aktivite puani hesaplar."""
        if is_archived:
            return 0.1

        score = 0.0

        # Yildiz katkisi (logaritmik)
        if stars > 0:
            score += min(math.log10(stars) / 5, 0.3)

        # Fork katkisi
        if forks > 0:
            score += min(math.log10(forks) / 4, 0.2)

        # Guncellik katkisi
        if last_updated:
            try:
                updated = datetime.fromisoformat(last_updated.replace("Z", "+00:00"))
                days_ago = (datetime.now(timezone.utc) - updated).days
                if days_ago < 7:
                    score += 0.3
                elif days_ago < 30:
                    score += 0.2
                elif days_ago < 90:
                    score += 0.1
                elif days_ago < 365:
                    score += 0.05
            except (ValueError, AttributeError):
                score += 0.1
        else:
            score += 0.1

        # Acik issue orani (cok fazla = negatif)
        if stars > 0:
            issue_ratio = open_issues / stars
            if issue_ratio > 0.5:
                score -= 0.1

        return max(0.0, min(1.0, score))

    @property
    def discovered_count(self) -> int:
        """Kesfedilen repo sayisi."""
        return len(self._discovered)

    @property
    def discovered_repos(self) -> list[RepoInfo]:
        """Kesfedilen repolar."""
        return list(self._discovered)
