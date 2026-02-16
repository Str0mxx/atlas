"""ATLAS Ortak Keşifçisi.

Ortak arama, sektör filtreleme, boyut eşleme,
coğrafi hedefleme ve yetenek eşleme.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class PartnerDiscovery:
    """Ortak keşifçisi.

    Potansiyel ortakları keşfeder, filtreler
    ve sıralar.

    Attributes:
        _partners: Keşfedilen ortaklar.
        _stats: İstatistikler.
    """

    def __init__(self) -> None:
        """Keşifçiyi başlatır."""
        self._partners: dict[str, dict] = {}
        self._stats = {
            "partners_discovered": 0,
            "searches_run": 0,
        }
        logger.info(
            "PartnerDiscovery baslatildi",
        )

    @property
    def discovered_count(self) -> int:
        """Keşfedilen ortak sayısı."""
        return self._stats[
            "partners_discovered"
        ]

    @property
    def search_count(self) -> int:
        """Yapılan arama sayısı."""
        return self._stats["searches_run"]

    def search_partners(
        self,
        query: str,
        industry: str = "",
        region: str = "",
    ) -> dict[str, Any]:
        """Ortak arar.

        Args:
            query: Arama sorgusu.
            industry: Sektör filtresi.
            region: Bölge filtresi.

        Returns:
            Arama sonucu.
        """
        partner_id = (
            f"ptr_{len(self._partners)}"
        )
        self._partners[partner_id] = {
            "query": query,
            "industry": industry,
            "region": region,
            "discovered_at": time.time(),
        }
        self._stats[
            "partners_discovered"
        ] += 1
        self._stats["searches_run"] += 1

        logger.info(
            "Ortak arama: '%s' "
            "(sektor: %s, bolge: %s)",
            query,
            industry or "all",
            region or "global",
        )

        return {
            "partner_id": partner_id,
            "query": query,
            "industry": industry,
            "region": region,
            "discovered": True,
        }

    def filter_by_industry(
        self,
        industry: str,
        sub_industry: str = "",
    ) -> dict[str, Any]:
        """Sektöre göre filtreler.

        Args:
            industry: Ana sektör.
            sub_industry: Alt sektör.

        Returns:
            Filtre sonucu.
        """
        matches = [
            pid
            for pid, p in self._partners.items()
            if p.get("industry") == industry
        ]

        return {
            "industry": industry,
            "sub_industry": sub_industry,
            "matches": len(matches),
            "filtered": True,
        }

    def match_by_size(
        self,
        min_employees: int = 0,
        max_employees: int = 0,
        min_revenue: float = 0.0,
    ) -> dict[str, Any]:
        """Boyuta göre eşler.

        Args:
            min_employees: Minimum çalışan.
            max_employees: Maksimum çalışan.
            min_revenue: Minimum gelir.

        Returns:
            Eşleme sonucu.
        """
        size_category = "small"
        if min_employees >= 1000:
            size_category = "enterprise"
        elif min_employees >= 250:
            size_category = "large"
        elif min_employees >= 50:
            size_category = "medium"

        return {
            "size_category": size_category,
            "min_employees": min_employees,
            "max_employees": max_employees,
            "min_revenue": min_revenue,
            "matched": True,
        }

    def target_geography(
        self,
        country: str = "",
        city: str = "",
        radius_km: int = 0,
    ) -> dict[str, Any]:
        """Coğrafi hedefleme yapar.

        Args:
            country: Ülke.
            city: Şehir.
            radius_km: Yarıçap (km).

        Returns:
            Hedefleme sonucu.
        """
        scope = "global"
        if city:
            scope = "local"
        elif country:
            scope = "national"

        return {
            "country": country,
            "city": city,
            "radius_km": radius_km,
            "scope": scope,
            "targeted": True,
        }

    def match_capabilities(
        self,
        required: list[str] | None = None,
        offered: list[str] | None = None,
    ) -> dict[str, Any]:
        """Yetenek eşlemesi yapar.

        Args:
            required: Gereken yetenekler.
            offered: Sunulan yetenekler.

        Returns:
            Eşleme sonucu.
        """
        if required is None:
            required = []
        if offered is None:
            offered = []

        req_set = set(required)
        off_set = set(offered)
        overlap = req_set & off_set
        coverage = (
            len(overlap) / len(req_set)
            if req_set
            else 0.0
        )

        return {
            "required": required,
            "offered": offered,
            "overlap": list(overlap),
            "coverage": round(coverage, 2),
            "matched": True,
        }
