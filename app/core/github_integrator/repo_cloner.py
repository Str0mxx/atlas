"""ATLAS Repo Klonlayici modulu.

Git clone, branch secimi, sparse checkout,
submodule yonetimi ve versiyon sabitleme.
"""

import logging
from typing import Any

from app.models.github_integrator import CloneResult, RepoInfo

logger = logging.getLogger(__name__)


class RepoCloner:
    """Repo klonlama sistemi.

    Repolari klonlar, branch secer, sparse
    checkout yapar ve versiyonlari sabitler.

    Attributes:
        _clones: Klonlama gecmisi.
        _base_dir: Temel klonlama dizini.
    """

    def __init__(self, base_dir: str = "data/repos") -> None:
        """Repo klonlayiciyi baslatir.

        Args:
            base_dir: Temel dizin.
        """
        self._clones: list[CloneResult] = []
        self._base_dir = base_dir

        logger.info("RepoCloner baslatildi (dir=%s)", base_dir)

    def clone(
        self,
        repo: RepoInfo,
        branch: str = "main",
        sparse_paths: list[str] | None = None,
        depth: int | None = 1,
    ) -> CloneResult:
        """Repoyu klonlar (simule).

        Args:
            repo: Repo bilgisi.
            branch: Branch adi.
            sparse_paths: Sparse checkout yollari.
            depth: Klon derinligi.

        Returns:
            CloneResult nesnesi.
        """
        local_path = f"{self._base_dir}/{repo.name}"

        # Simule edilmis klonlama
        result = CloneResult(
            repo_name=repo.name,
            local_path=local_path,
            branch=branch,
            commit_hash=f"abc{repo.repo_id[:5]}",
            sparse=sparse_paths is not None,
            size_mb=self._estimate_size(repo, sparse_paths),
            success=True,
        )

        self._clones.append(result)

        logger.info(
            "Repo klonlandi: %s -> %s (branch=%s, sparse=%s)",
            repo.full_name, local_path, branch, result.sparse,
        )

        return result

    def clone_with_submodules(
        self, repo: RepoInfo, branch: str = "main"
    ) -> CloneResult:
        """Submodullerle klonlar.

        Args:
            repo: Repo bilgisi.
            branch: Branch adi.

        Returns:
            CloneResult nesnesi.
        """
        result = self.clone(repo, branch)
        # Submodul bilgisi ekle
        result.size_mb *= 1.5  # Submoduller boyutu arttirir
        return result

    def pin_version(
        self, clone: CloneResult, version: str
    ) -> CloneResult:
        """Versiyonu sabitler.

        Args:
            clone: Klon sonucu.
            version: Hedef versiyon/tag.

        Returns:
            Guncellenmis CloneResult.
        """
        clone.commit_hash = f"v{version}"
        clone.branch = f"tags/{version}"
        return clone

    def get_clone(self, repo_name: str) -> CloneResult | None:
        """Klon sonucunu getirir.

        Args:
            repo_name: Repo adi.

        Returns:
            CloneResult veya None.
        """
        for clone in reversed(self._clones):
            if clone.repo_name == repo_name:
                return clone
        return None

    def list_clones(self) -> list[CloneResult]:
        """Tum klonlari listeler.

        Returns:
            CloneResult listesi.
        """
        return list(self._clones)

    def remove_clone(self, repo_name: str) -> bool:
        """Klonu siler (simule).

        Args:
            repo_name: Repo adi.

        Returns:
            Basarili ise True.
        """
        for i, clone in enumerate(self._clones):
            if clone.repo_name == repo_name:
                self._clones.pop(i)
                logger.info("Klon silindi: %s", repo_name)
                return True
        return False

    def _estimate_size(
        self, repo: RepoInfo, sparse_paths: list[str] | None
    ) -> float:
        """Klon boyutunu tahmin eder."""
        # Yildiz sayisina gore tahmini boyut
        base_size = 5.0  # MB
        if repo.stars > 1000:
            base_size = 50.0
        elif repo.stars > 100:
            base_size = 20.0
        elif repo.stars > 10:
            base_size = 10.0

        if sparse_paths:
            # Sparse checkout boyutu dusurur
            ratio = min(len(sparse_paths) / 10, 0.5)
            base_size *= ratio

        return round(base_size, 1)

    @property
    def clone_count(self) -> int:
        """Klon sayisi."""
        return len(self._clones)

    @property
    def total_size_mb(self) -> float:
        """Toplam boyut (MB)."""
        return sum(c.size_mb for c in self._clones)
