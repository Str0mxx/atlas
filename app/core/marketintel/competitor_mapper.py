"""ATLAS Rakip Haritacısı modülü.

Rakip tespiti, konumlandırma analizi,
güçlü/zayıf yönler, strateji tespiti,
hareket takibi.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class CompetitorMapper:
    """Rakip haritacısı.

    Rakipleri tespit eder ve analiz eder.

    Attributes:
        _competitors: Rakip kayıtları.
        _movements: Hareket geçmişi.
    """

    THREAT_LEVELS = [
        "critical", "high", "medium",
        "low", "minimal",
    ]

    def __init__(self) -> None:
        """Haritacıyı başlatır."""
        self._competitors: dict[
            str, dict[str, Any]
        ] = {}
        self._movements: list[
            dict[str, Any]
        ] = []
        self._counter = 0
        self._stats = {
            "competitors_added": 0,
            "analyses_done": 0,
            "movements_tracked": 0,
        }

        logger.info(
            "CompetitorMapper baslatildi",
        )

    def add_competitor(
        self,
        name: str,
        market: str = "",
        products: list[str] | None = None,
        market_share: float = 0.0,
    ) -> dict[str, Any]:
        """Rakip ekler.

        Args:
            name: Rakip adı.
            market: Pazar.
            products: Ürünler.
            market_share: Pazar payı.

        Returns:
            Ekleme bilgisi.
        """
        self._counter += 1
        cid = f"comp_{self._counter}"

        competitor = {
            "competitor_id": cid,
            "name": name,
            "market": market,
            "products": products or [],
            "market_share": market_share,
            "strengths": [],
            "weaknesses": [],
            "threat_level": "medium",
            "strategy": "",
            "created_at": time.time(),
        }
        self._competitors[cid] = competitor
        self._stats[
            "competitors_added"
        ] += 1

        return {
            "competitor_id": cid,
            "name": name,
            "added": True,
        }

    def analyze_positioning(
        self,
        competitor_id: str,
    ) -> dict[str, Any]:
        """Konumlandırma analiz eder.

        Args:
            competitor_id: Rakip ID.

        Returns:
            Analiz bilgisi.
        """
        comp = self._competitors.get(
            competitor_id,
        )
        if not comp:
            return {
                "error": (
                    "competitor_not_found"
                ),
            }

        self._stats["analyses_done"] += 1

        return {
            "competitor_id": competitor_id,
            "name": comp["name"],
            "market": comp["market"],
            "market_share": comp[
                "market_share"
            ],
            "product_count": len(
                comp["products"],
            ),
            "positioning": (
                "leader"
                if comp["market_share"] > 30
                else "challenger"
                if comp["market_share"] > 15
                else "follower"
                if comp["market_share"] > 5
                else "niche"
            ),
        }

    def set_strengths_weaknesses(
        self,
        competitor_id: str,
        strengths: list[str],
        weaknesses: list[str],
    ) -> dict[str, Any]:
        """Güçlü/zayıf yönleri ayarlar.

        Args:
            competitor_id: Rakip ID.
            strengths: Güçlü yönler.
            weaknesses: Zayıf yönler.

        Returns:
            Güncelleme bilgisi.
        """
        comp = self._competitors.get(
            competitor_id,
        )
        if not comp:
            return {
                "error": (
                    "competitor_not_found"
                ),
            }

        comp["strengths"] = strengths
        comp["weaknesses"] = weaknesses

        # Tehdit seviyesi güncelle
        strength_score = len(strengths)
        weakness_score = len(weaknesses)
        ratio = (
            strength_score
            / max(
                strength_score
                + weakness_score, 1,
            )
        )

        if ratio > 0.7:
            comp["threat_level"] = "high"
        elif ratio > 0.5:
            comp["threat_level"] = "medium"
        else:
            comp["threat_level"] = "low"

        return {
            "competitor_id": competitor_id,
            "strengths": len(strengths),
            "weaknesses": len(weaknesses),
            "threat_level": comp[
                "threat_level"
            ],
            "updated": True,
        }

    def detect_strategy(
        self,
        competitor_id: str,
        observations: list[str],
    ) -> dict[str, Any]:
        """Strateji tespit eder.

        Args:
            competitor_id: Rakip ID.
            observations: Gözlemler.

        Returns:
            Tespit bilgisi.
        """
        comp = self._competitors.get(
            competitor_id,
        )
        if not comp:
            return {
                "error": (
                    "competitor_not_found"
                ),
            }

        # Basit strateji çıkarımı
        obs_text = " ".join(
            o.lower() for o in observations
        )
        if "price" in obs_text or "cheap" in obs_text:
            strategy = "cost_leadership"
        elif "premium" in obs_text or "quality" in obs_text:
            strategy = "differentiation"
        elif "niche" in obs_text or "specific" in obs_text:
            strategy = "focus"
        elif "expand" in obs_text or "new market" in obs_text:
            strategy = "expansion"
        else:
            strategy = "unknown"

        comp["strategy"] = strategy

        return {
            "competitor_id": competitor_id,
            "strategy": strategy,
            "observations": len(
                observations,
            ),
            "detected": True,
        }

    def track_movement(
        self,
        competitor_id: str,
        movement_type: str,
        description: str = "",
    ) -> dict[str, Any]:
        """Hareketi takip eder.

        Args:
            competitor_id: Rakip ID.
            movement_type: Hareket tipi.
            description: Açıklama.

        Returns:
            Takip bilgisi.
        """
        comp = self._competitors.get(
            competitor_id,
        )
        if not comp:
            return {
                "error": (
                    "competitor_not_found"
                ),
            }

        self._counter += 1
        mid = f"mov_{self._counter}"

        movement = {
            "movement_id": mid,
            "competitor_id": competitor_id,
            "competitor_name": comp["name"],
            "type": movement_type,
            "description": description,
            "tracked_at": time.time(),
        }
        self._movements.append(movement)
        self._stats[
            "movements_tracked"
        ] += 1

        return {
            "movement_id": mid,
            "competitor_id": competitor_id,
            "type": movement_type,
            "tracked": True,
        }

    def get_competitor(
        self,
        competitor_id: str,
    ) -> dict[str, Any]:
        """Rakibi getirir."""
        comp = self._competitors.get(
            competitor_id,
        )
        if not comp:
            return {
                "error": (
                    "competitor_not_found"
                ),
            }
        return dict(comp)

    def get_competitors(
        self,
        market: str | None = None,
        threat_level: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Rakipleri getirir."""
        results = list(
            self._competitors.values(),
        )
        if market:
            results = [
                c for c in results
                if c["market"] == market
            ]
        if threat_level:
            results = [
                c for c in results
                if c["threat_level"]
                == threat_level
            ]
        return results[:limit]

    @property
    def competitor_count(self) -> int:
        """Rakip sayısı."""
        return len(self._competitors)

    @property
    def movement_count(self) -> int:
        """Hareket sayısı."""
        return self._stats[
            "movements_tracked"
        ]
