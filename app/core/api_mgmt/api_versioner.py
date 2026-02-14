"""ATLAS API Surumleyici modulu.

URL surumleme, baslik surumleme,
sorgu surumleme, geriye uyumluluk
ve migrasyon destegi.
"""

import logging
import time
from typing import Any

from app.models.api_mgmt import (
    VersioningStrategy,
)

logger = logging.getLogger(__name__)


class APIVersioner:
    """API surumleyici.

    API surumlerini yonetir ve
    uyumluluk saglar.

    Attributes:
        _versions: Surum kayitlari.
        _active: Aktif surum.
    """

    def __init__(
        self,
        strategy: VersioningStrategy = VersioningStrategy.URL,
    ) -> None:
        """API surumleyiciyi baslatir.

        Args:
            strategy: Surumleme stratejisi.
        """
        self._strategy = strategy
        self._versions: dict[
            str, dict[str, Any]
        ] = {}
        self._active_version = ""
        self._deprecated: set[str] = set()
        self._migrations: dict[
            str, dict[str, Any]
        ] = {}

        logger.info(
            "APIVersioner baslatildi",
        )

    def register_version(
        self,
        version: str,
        description: str = "",
        endpoints: list[str] | None = None,
    ) -> dict[str, Any]:
        """Surum kaydeder.

        Args:
            version: Surum adi.
            description: Aciklama.
            endpoints: Endpoint listesi.

        Returns:
            Surum bilgisi.
        """
        info = {
            "version": version,
            "description": description,
            "endpoints": endpoints or [],
            "status": "active",
            "created_at": time.time(),
        }
        self._versions[version] = info

        if not self._active_version:
            self._active_version = version

        return info

    def set_active(
        self,
        version: str,
    ) -> bool:
        """Aktif surumu ayarlar.

        Args:
            version: Surum adi.

        Returns:
            Basarili ise True.
        """
        if version not in self._versions:
            return False
        self._active_version = version
        return True

    def deprecate_version(
        self,
        version: str,
    ) -> bool:
        """Surumu kullanim disi birakir.

        Args:
            version: Surum adi.

        Returns:
            Basarili ise True.
        """
        if version not in self._versions:
            return False
        self._deprecated.add(version)
        self._versions[version]["status"] = (
            "deprecated"
        )
        return True

    def resolve_version(
        self,
        request: dict[str, Any],
    ) -> str:
        """Istekten surum cozumler.

        Args:
            request: Istek bilgisi.

        Returns:
            Surum adi.
        """
        if self._strategy == VersioningStrategy.URL:
            path = request.get("path", "")
            parts = path.strip("/").split("/")
            if parts and parts[0].startswith("v"):
                return parts[0]

        elif self._strategy == VersioningStrategy.HEADER:
            headers = request.get("headers", {})
            return headers.get(
                "API-Version",
                self._active_version,
            )

        elif self._strategy == VersioningStrategy.QUERY:
            params = request.get("params", {})
            return params.get(
                "version",
                self._active_version,
            )

        return self._active_version

    def is_compatible(
        self,
        source: str,
        target: str,
    ) -> dict[str, Any]:
        """Uyumluluk kontrol eder.

        Args:
            source: Kaynak surum.
            target: Hedef surum.

        Returns:
            Uyumluluk bilgisi.
        """
        src = self._versions.get(source)
        tgt = self._versions.get(target)

        if not src or not tgt:
            return {
                "compatible": False,
                "reason": "version_not_found",
            }

        src_eps = set(src.get("endpoints", []))
        tgt_eps = set(tgt.get("endpoints", []))

        missing = src_eps - tgt_eps
        added = tgt_eps - src_eps

        return {
            "compatible": len(missing) == 0,
            "missing_endpoints": list(missing),
            "added_endpoints": list(added),
        }

    def add_migration(
        self,
        from_version: str,
        to_version: str,
        steps: list[str] | None = None,
    ) -> dict[str, Any]:
        """Migrasyon ekler.

        Args:
            from_version: Kaynak surum.
            to_version: Hedef surum.
            steps: Migrasyon adimlari.

        Returns:
            Migrasyon bilgisi.
        """
        key = f"{from_version}->{to_version}"
        migration = {
            "from": from_version,
            "to": to_version,
            "steps": steps or [],
            "at": time.time(),
        }
        self._migrations[key] = migration
        return migration

    def get_migration_path(
        self,
        from_version: str,
        to_version: str,
    ) -> list[dict[str, Any]]:
        """Migrasyon yolunu getirir.

        Args:
            from_version: Kaynak surum.
            to_version: Hedef surum.

        Returns:
            Migrasyon yolu.
        """
        key = f"{from_version}->{to_version}"
        migration = self._migrations.get(key)
        if migration:
            return [migration]
        return []

    def get_version(
        self,
        version: str,
    ) -> dict[str, Any] | None:
        """Surum bilgisi getirir.

        Args:
            version: Surum adi.

        Returns:
            Surum bilgisi veya None.
        """
        return self._versions.get(version)

    def is_deprecated(
        self,
        version: str,
    ) -> bool:
        """Kullanim disi mi kontrol eder.

        Args:
            version: Surum adi.

        Returns:
            Kullanim disi ise True.
        """
        return version in self._deprecated

    def list_versions(
        self,
    ) -> list[dict[str, Any]]:
        """Surumleri listeler.

        Returns:
            Surum listesi.
        """
        return list(self._versions.values())

    @property
    def version_count(self) -> int:
        """Surum sayisi."""
        return len(self._versions)

    @property
    def active_version(self) -> str:
        """Aktif surum."""
        return self._active_version

    @property
    def deprecated_count(self) -> int:
        """Kullanim disi surum sayisi."""
        return len(self._deprecated)

    @property
    def migration_count(self) -> int:
        """Migrasyon sayisi."""
        return len(self._migrations)
