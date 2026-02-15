"""ATLAS Yetenek Haritacisi modulu.

Yetenek envanteri, beceri taksonomisi,
bagimlilik haritasi, surum takibi, kapsam analizi.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class CapabilityMapper:
    """Yetenek haritacisi.

    Mevcut yetenekleri haritalar.

    Attributes:
        _capabilities: Yetenek envanteri.
        _taxonomy: Beceri taksonomisi.
    """

    def __init__(self) -> None:
        """Yetenek haritacisini baslatir."""
        self._capabilities: dict[
            str, dict[str, Any]
        ] = {}
        self._taxonomy: dict[
            str, list[str]
        ] = {}
        self._dependencies: dict[
            str, list[str]
        ] = {}
        self._stats = {
            "mapped": 0,
        }

        logger.info(
            "CapabilityMapper baslatildi",
        )

    def register_capability(
        self,
        name: str,
        category: str = "",
        version: str = "1.0.0",
        description: str = "",
        dependencies: list[str] | None = None,
    ) -> dict[str, Any]:
        """Yetenek kaydeder.

        Args:
            name: Yetenek adi.
            category: Kategori.
            version: Surum.
            description: Aciklama.
            dependencies: Bagimliliklar.

        Returns:
            Kayit bilgisi.
        """
        self._capabilities[name] = {
            "name": name,
            "category": category,
            "version": version,
            "description": description,
            "status": "available",
            "registered_at": time.time(),
        }

        if dependencies:
            self._dependencies[name] = list(
                dependencies,
            )

        # Taksonomiye ekle
        if category:
            if category not in self._taxonomy:
                self._taxonomy[category] = []
            if (
                name
                not in self._taxonomy[category]
            ):
                self._taxonomy[
                    category
                ].append(name)

        self._stats["mapped"] += 1

        return {
            "name": name,
            "registered": True,
        }

    def unregister_capability(
        self,
        name: str,
    ) -> dict[str, Any]:
        """Yetenek siler.

        Args:
            name: Yetenek adi.

        Returns:
            Silme bilgisi.
        """
        if name not in self._capabilities:
            return {
                "error": "capability_not_found",
            }

        cap = self._capabilities.pop(name)
        category = cap.get("category", "")

        if (
            category in self._taxonomy
            and name
            in self._taxonomy[category]
        ):
            self._taxonomy[
                category
            ].remove(name)

        self._dependencies.pop(name, None)

        return {
            "name": name,
            "unregistered": True,
        }

    def get_capability(
        self,
        name: str,
    ) -> dict[str, Any]:
        """Yetenek getirir.

        Args:
            name: Yetenek adi.

        Returns:
            Yetenek bilgisi.
        """
        cap = self._capabilities.get(name)
        if not cap:
            return {
                "error": "capability_not_found",
            }

        result = dict(cap)
        result["dependencies"] = (
            self._dependencies.get(name, [])
        )
        return result

    def list_capabilities(
        self,
        category: str | None = None,
    ) -> list[str]:
        """Yetenek listesi getirir.

        Args:
            category: Kategori filtresi.

        Returns:
            Yetenek adlari.
        """
        if category:
            return list(
                self._taxonomy.get(
                    category, [],
                ),
            )

        return list(
            self._capabilities.keys(),
        )

    def get_taxonomy(self) -> dict[str, list[str]]:
        """Taksonomi getirir.

        Returns:
            Kategori-yetenek haritasi.
        """
        return {
            k: list(v)
            for k, v in self._taxonomy.items()
        }

    def get_dependencies(
        self,
        name: str,
    ) -> list[str]:
        """Bagimliliklari getirir.

        Args:
            name: Yetenek adi.

        Returns:
            Bagimlilik listesi.
        """
        return list(
            self._dependencies.get(name, []),
        )

    def update_version(
        self,
        name: str,
        version: str,
    ) -> dict[str, Any]:
        """Surumu gunceller.

        Args:
            name: Yetenek adi.
            version: Yeni surum.

        Returns:
            Guncelleme bilgisi.
        """
        cap = self._capabilities.get(name)
        if not cap:
            return {
                "error": "capability_not_found",
            }

        old_version = cap["version"]
        cap["version"] = version
        cap["updated_at"] = time.time()

        return {
            "name": name,
            "old_version": old_version,
            "new_version": version,
            "updated": True,
        }

    def coverage_analysis(
        self,
        required: list[str],
    ) -> dict[str, Any]:
        """Kapsam analizi yapar.

        Args:
            required: Gerekli yetenekler.

        Returns:
            Kapsam bilgisi.
        """
        available = set(
            self._capabilities.keys(),
        )
        required_set = set(required)

        covered = available & required_set
        missing = required_set - available
        extra = available - required_set

        coverage_pct = (
            len(covered)
            / max(len(required_set), 1)
            * 100
        )

        return {
            "total_required": len(
                required_set,
            ),
            "covered": sorted(covered),
            "missing": sorted(missing),
            "extra": sorted(extra),
            "coverage_pct": round(
                coverage_pct, 1,
            ),
        }

    @property
    def capability_count(self) -> int:
        """Yetenek sayisi."""
        return len(self._capabilities)

    @property
    def category_count(self) -> int:
        """Kategori sayisi."""
        return len(self._taxonomy)
