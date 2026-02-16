"""ATLAS Pazar Büyüklüğü Tahmincisi modülü.

TAM/SAM/SOM hesaplama, büyüme projeksiyonu,
segment analizi, coğrafi dağılım,
metodoloji.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class MarketSizeEstimator:
    """Pazar büyüklüğü tahmincisi.

    Pazar boyutunu tahmin eder ve analiz eder.

    Attributes:
        _estimates: Tahmin kayıtları.
    """

    def __init__(self) -> None:
        """Tahminciyı başlatır."""
        self._estimates: dict[
            str, dict[str, Any]
        ] = {}
        self._projections: list[
            dict[str, Any]
        ] = []
        self._counter = 0
        self._stats = {
            "estimates_made": 0,
            "projections_made": 0,
        }

        logger.info(
            "MarketSizeEstimator baslatildi",
        )

    def estimate_tam_sam_som(
        self,
        market_name: str,
        tam: float,
        sam_ratio: float = 0.3,
        som_ratio: float = 0.1,
        currency: str = "USD",
    ) -> dict[str, Any]:
        """TAM/SAM/SOM hesaplar.

        Args:
            market_name: Pazar adı.
            tam: Toplam adreslenebilir pazar.
            sam_ratio: SAM oranı.
            som_ratio: SOM oranı.
            currency: Para birimi.

        Returns:
            Tahmin bilgisi.
        """
        self._counter += 1
        eid = f"est_{self._counter}"

        sam = tam * sam_ratio
        som = tam * som_ratio

        estimate = {
            "estimate_id": eid,
            "market_name": market_name,
            "tam": tam,
            "sam": round(sam, 2),
            "som": round(som, 2),
            "sam_ratio": sam_ratio,
            "som_ratio": som_ratio,
            "currency": currency,
            "created_at": time.time(),
        }
        self._estimates[eid] = estimate
        self._stats["estimates_made"] += 1

        return {
            "estimate_id": eid,
            "market_name": market_name,
            "tam": tam,
            "sam": estimate["sam"],
            "som": estimate["som"],
            "currency": currency,
            "estimated": True,
        }

    def project_growth(
        self,
        estimate_id: str,
        growth_rate: float,
        years: int = 5,
    ) -> dict[str, Any]:
        """Büyüme projeksiyonu yapar.

        Args:
            estimate_id: Tahmin ID.
            growth_rate: Büyüme oranı (0-1).
            years: Yıl sayısı.

        Returns:
            Projeksiyon bilgisi.
        """
        est = self._estimates.get(
            estimate_id,
        )
        if not est:
            return {
                "error": "estimate_not_found",
            }

        projections = []
        current_tam = est["tam"]
        for y in range(1, years + 1):
            projected = current_tam * (
                (1 + growth_rate) ** y
            )
            projections.append({
                "year": y,
                "tam": round(projected, 2),
                "sam": round(
                    projected
                    * est["sam_ratio"], 2,
                ),
                "som": round(
                    projected
                    * est["som_ratio"], 2,
                ),
            })

        self._stats[
            "projections_made"
        ] += 1

        proj = {
            "estimate_id": estimate_id,
            "growth_rate": growth_rate,
            "years": years,
            "projections": projections,
        }
        self._projections.append(proj)

        return {
            "estimate_id": estimate_id,
            "growth_rate": growth_rate,
            "projections": projections,
            "final_tam": projections[-1][
                "tam"
            ],
            "projected": True,
        }

    def analyze_segments(
        self,
        market_name: str,
        segments: dict[str, float],
    ) -> dict[str, Any]:
        """Segment analizi yapar.

        Args:
            market_name: Pazar adı.
            segments: Segment dağılımı.

        Returns:
            Analiz bilgisi.
        """
        total = sum(segments.values())
        if total == 0:
            return {
                "market_name": market_name,
                "segments": {},
                "largest": None,
            }

        shares = {
            name: round(val / total * 100, 1)
            for name, val in segments.items()
        }
        largest = max(
            shares, key=shares.get,
        )

        return {
            "market_name": market_name,
            "segments": shares,
            "largest_segment": largest,
            "largest_share": shares[largest],
            "segment_count": len(segments),
        }

    def geographic_breakdown(
        self,
        estimate_id: str,
        regions: dict[str, float],
    ) -> dict[str, Any]:
        """Coğrafi dağılım yapar.

        Args:
            estimate_id: Tahmin ID.
            regions: Bölge oranları.

        Returns:
            Dağılım bilgisi.
        """
        est = self._estimates.get(
            estimate_id,
        )
        if not est:
            return {
                "error": "estimate_not_found",
            }

        tam = est["tam"]
        breakdown = {
            region: round(tam * ratio, 2)
            for region, ratio
            in regions.items()
        }

        return {
            "estimate_id": estimate_id,
            "tam": tam,
            "breakdown": breakdown,
            "regions": len(regions),
        }

    def get_methodology(
        self,
        estimate_id: str,
    ) -> dict[str, Any]:
        """Metodolojiyi getirir.

        Args:
            estimate_id: Tahmin ID.

        Returns:
            Metodoloji bilgisi.
        """
        est = self._estimates.get(
            estimate_id,
        )
        if not est:
            return {
                "error": "estimate_not_found",
            }

        return {
            "estimate_id": estimate_id,
            "approach": "top_down",
            "tam_source": "total_market_data",
            "sam_method": (
                f"tam * {est['sam_ratio']}"
            ),
            "som_method": (
                f"tam * {est['som_ratio']}"
            ),
            "assumptions": [
                f"SAM ratio: {est['sam_ratio'] * 100}%",
                f"SOM ratio: {est['som_ratio'] * 100}%",
            ],
        }

    @property
    def estimate_count(self) -> int:
        """Tahmin sayısı."""
        return len(self._estimates)

    @property
    def projection_count(self) -> int:
        """Projeksiyon sayısı."""
        return self._stats[
            "projections_made"
        ]
