"""ATLAS Surum Yoneticisi modulu.

Surum numaralama, semantik versiyon,
metadata, karsilastirma ve
release yonetimi.
"""

import logging
import re
import time
from typing import Any

from app.models.versioning import (
    VersionRecord,
    VersionStatus,
)

logger = logging.getLogger(__name__)


class VersionManager:
    """Surum yoneticisi.

    Surum numaralama, karsilastirma
    ve release yonetimi saglar.

    Attributes:
        _versions: Surum kayitlari.
        _current: Guncel surum.
    """

    def __init__(self) -> None:
        """Surum yoneticisini baslatir."""
        self._versions: dict[
            str, VersionRecord
        ] = {}
        self._current: str = "0.1.0"
        self._tags: dict[str, str] = {}

        logger.info("VersionManager baslatildi")

    def create_version(
        self,
        version: str,
        description: str = "",
        author: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> VersionRecord:
        """Yeni surum olusturur.

        Args:
            version: Surum numarasi.
            description: Aciklama.
            author: Yazar.
            metadata: Ek veri.

        Returns:
            Surum kaydi.
        """
        record = VersionRecord(
            version=version,
            description=description,
            author=author,
            metadata=metadata or {},
        )
        self._versions[record.version_id] = record
        return record

    def release_version(
        self,
        version_id: str,
    ) -> bool:
        """Surumu yayinlar.

        Args:
            version_id: Surum ID.

        Returns:
            Basarili ise True.
        """
        record = self._versions.get(version_id)
        if not record:
            return False

        record.status = VersionStatus.RELEASED
        self._current = record.version
        return True

    def deprecate_version(
        self,
        version_id: str,
    ) -> bool:
        """Surumu kullanim disi birakir.

        Args:
            version_id: Surum ID.

        Returns:
            Basarili ise True.
        """
        record = self._versions.get(version_id)
        if not record:
            return False

        record.status = VersionStatus.DEPRECATED
        return True

    def parse_semver(
        self,
        version: str,
    ) -> dict[str, Any]:
        """Semantik surumu parse eder.

        Args:
            version: Surum string.

        Returns:
            Major, minor, patch bilgisi.
        """
        pattern = r"^(\d+)\.(\d+)\.(\d+)(?:-(.+))?$"
        match = re.match(pattern, version)
        if not match:
            return {
                "valid": False,
                "version": version,
            }

        return {
            "valid": True,
            "major": int(match.group(1)),
            "minor": int(match.group(2)),
            "patch": int(match.group(3)),
            "prerelease": match.group(4) or "",
        }

    def compare_versions(
        self,
        v1: str,
        v2: str,
    ) -> int:
        """Iki surumu karsilastirir.

        Args:
            v1: Birinci surum.
            v2: Ikinci surum.

        Returns:
            -1, 0 veya 1.
        """
        p1 = self.parse_semver(v1)
        p2 = self.parse_semver(v2)

        if not p1.get("valid") or not p2.get("valid"):
            return 0

        for key in ("major", "minor", "patch"):
            if p1[key] > p2[key]:
                return 1
            if p1[key] < p2[key]:
                return -1

        return 0

    def bump_version(
        self,
        version: str,
        bump_type: str = "patch",
    ) -> str:
        """Surumu arttirir.

        Args:
            version: Mevcut surum.
            bump_type: major/minor/patch.

        Returns:
            Yeni surum stringi.
        """
        parsed = self.parse_semver(version)
        if not parsed.get("valid"):
            return version

        major = parsed["major"]
        minor = parsed["minor"]
        patch = parsed["patch"]

        if bump_type == "major":
            major += 1
            minor = 0
            patch = 0
        elif bump_type == "minor":
            minor += 1
            patch = 0
        else:
            patch += 1

        return f"{major}.{minor}.{patch}"

    def tag_version(
        self,
        version_id: str,
        tag: str,
    ) -> bool:
        """Surumu etiketler.

        Args:
            version_id: Surum ID.
            tag: Etiket.

        Returns:
            Basarili ise True.
        """
        if version_id not in self._versions:
            return False

        self._tags[tag] = version_id
        return True

    def get_by_tag(
        self,
        tag: str,
    ) -> VersionRecord | None:
        """Etikete gore surum getirir.

        Args:
            tag: Etiket.

        Returns:
            Surum veya None.
        """
        vid = self._tags.get(tag)
        if vid:
            return self._versions.get(vid)
        return None

    def get_version(
        self,
        version_id: str,
    ) -> VersionRecord | None:
        """Surum getirir.

        Args:
            version_id: Surum ID.

        Returns:
            Surum veya None.
        """
        return self._versions.get(version_id)

    def get_history(
        self,
        limit: int = 50,
    ) -> list[VersionRecord]:
        """Surum gecmisi getirir.

        Args:
            limit: Limit.

        Returns:
            Surum listesi.
        """
        versions = list(self._versions.values())
        return versions[-limit:]

    @property
    def current_version(self) -> str:
        """Guncel surum."""
        return self._current

    @property
    def version_count(self) -> int:
        """Surum sayisi."""
        return len(self._versions)

    @property
    def tag_count(self) -> int:
        """Etiket sayisi."""
        return len(self._tags)
