"""ATLAS Release Yoneticisi modulu.

Release olusturma, notlar,
deployment takibi, hotfix
ve dogrulama.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class ReleaseManager:
    """Release yoneticisi.

    Surum yayinlama ve deployment
    takibi saglar.

    Attributes:
        _releases: Release kayitlari.
        _deployments: Deployment gecmisi.
    """

    def __init__(self) -> None:
        """Release yoneticisini baslatir."""
        self._releases: dict[
            str, dict[str, Any]
        ] = {}
        self._deployments: list[
            dict[str, Any]
        ] = []
        self._hotfixes: list[
            dict[str, Any]
        ] = []
        self._validators: dict[
            str, list[str]
        ] = {}

        logger.info(
            "ReleaseManager baslatildi",
        )

    def create_release(
        self,
        version: str,
        notes: str = "",
        changes: list[str] | None = None,
        author: str = "",
    ) -> dict[str, Any]:
        """Release olusturur.

        Args:
            version: Surum numarasi.
            notes: Release notlari.
            changes: Degisiklik listesi.
            author: Yazar.

        Returns:
            Release bilgisi.
        """
        release = {
            "version": version,
            "notes": notes,
            "changes": changes or [],
            "author": author,
            "status": "created",
            "created_at": time.time(),
            "deployed_at": None,
        }
        self._releases[version] = release
        return release

    def add_release_notes(
        self,
        version: str,
        notes: str,
    ) -> bool:
        """Release notlari ekler.

        Args:
            version: Surum numarasi.
            notes: Notlar.

        Returns:
            Basarili ise True.
        """
        release = self._releases.get(version)
        if not release:
            return False

        existing = release.get("notes", "")
        release["notes"] = (
            f"{existing}\n{notes}"
            if existing
            else notes
        )
        return True

    def deploy_release(
        self,
        version: str,
        environment: str = "production",
    ) -> dict[str, Any]:
        """Release deploy eder.

        Args:
            version: Surum numarasi.
            environment: Ortam.

        Returns:
            Deployment sonucu.
        """
        release = self._releases.get(version)
        if not release:
            return {
                "success": False,
                "reason": "release_not_found",
            }

        deployment = {
            "version": version,
            "environment": environment,
            "status": "deployed",
            "at": time.time(),
        }
        self._deployments.append(deployment)
        release["status"] = "deployed"
        release["deployed_at"] = time.time()

        return {
            "success": True,
            "version": version,
            "environment": environment,
        }

    def create_hotfix(
        self,
        version: str,
        description: str,
        fix: str = "",
    ) -> dict[str, Any]:
        """Hotfix olusturur.

        Args:
            version: Ilgili surum.
            description: Aciklama.
            fix: Duzeltme detayi.

        Returns:
            Hotfix bilgisi.
        """
        hotfix = {
            "version": version,
            "description": description,
            "fix": fix,
            "status": "created",
            "at": time.time(),
        }
        self._hotfixes.append(hotfix)
        return hotfix

    def apply_hotfix(
        self,
        index: int,
    ) -> dict[str, Any]:
        """Hotfix uygular.

        Args:
            index: Hotfix indeksi.

        Returns:
            Uygulama sonucu.
        """
        if index < 0 or index >= len(
            self._hotfixes,
        ):
            return {
                "success": False,
                "reason": "hotfix_not_found",
            }

        hotfix = self._hotfixes[index]
        hotfix["status"] = "applied"

        return {
            "success": True,
            "version": hotfix["version"],
            "description": hotfix["description"],
        }

    def validate_release(
        self,
        version: str,
    ) -> dict[str, Any]:
        """Release dogrular.

        Args:
            version: Surum numarasi.

        Returns:
            Dogrulama sonucu.
        """
        release = self._releases.get(version)
        if not release:
            return {
                "valid": False,
                "reason": "release_not_found",
            }

        issues: list[str] = []
        if not release.get("notes"):
            issues.append("missing_notes")
        if not release.get("changes"):
            issues.append("no_changes_listed")
        if not release.get("author"):
            issues.append("missing_author")

        checks = self._validators.get(
            version, [],
        )

        return {
            "valid": len(issues) == 0,
            "version": version,
            "issues": issues,
            "checks_passed": len(checks),
        }

    def add_validation_check(
        self,
        version: str,
        check_name: str,
    ) -> None:
        """Dogrulama kontrolu ekler.

        Args:
            version: Surum numarasi.
            check_name: Kontrol adi.
        """
        if version not in self._validators:
            self._validators[version] = []
        self._validators[version].append(
            check_name,
        )

    def get_release(
        self,
        version: str,
    ) -> dict[str, Any] | None:
        """Release getirir.

        Args:
            version: Surum numarasi.

        Returns:
            Release veya None.
        """
        return self._releases.get(version)

    def get_deployments(
        self,
        environment: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Deployment gecmisi getirir.

        Args:
            environment: Ortam filtresi.
            limit: Limit.

        Returns:
            Deployment listesi.
        """
        deps = self._deployments
        if environment:
            deps = [
                d for d in deps
                if d["environment"] == environment
            ]
        return deps[-limit:]

    @property
    def release_count(self) -> int:
        """Release sayisi."""
        return len(self._releases)

    @property
    def deployment_count(self) -> int:
        """Deployment sayisi."""
        return len(self._deployments)

    @property
    def hotfix_count(self) -> int:
        """Hotfix sayisi."""
        return len(self._hotfixes)
