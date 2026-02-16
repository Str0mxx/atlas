"""ATLAS Tedarikçi Bulucu modülü.

Tedarikçi arama, yeterlilik puanlama,
güvenilirlik değerlendirme, konum filtreleme,
kapasite kontrolü.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class SupplierFinder:
    """Tedarikçi bulucu.

    Tedarikçileri bulur ve değerlendirir.

    Attributes:
        _suppliers: Tedarikçi kayıtları.
    """

    def __init__(self) -> None:
        """Bulucuyu başlatır."""
        self._suppliers: dict[
            str, dict[str, Any]
        ] = {}
        self._counter = 0
        self._stats = {
            "searches_done": 0,
            "qualifications_done": 0,
        }

        logger.info(
            "SupplierFinder baslatildi",
        )

    def register_supplier(
        self,
        name: str,
        location: str = "",
        categories: list[str]
        | None = None,
        capacity: int = 0,
        reliability: float = 0.0,
    ) -> dict[str, Any]:
        """Tedarikçi kaydeder.

        Args:
            name: Ad.
            location: Konum.
            categories: Kategoriler.
            capacity: Kapasite.
            reliability: Güvenilirlik.

        Returns:
            Kayıt bilgisi.
        """
        self._counter += 1
        sid = f"sup_{self._counter}"
        categories = categories or []

        supplier = {
            "supplier_id": sid,
            "name": name,
            "location": location,
            "categories": categories,
            "capacity": capacity,
            "reliability": reliability,
            "timestamp": time.time(),
        }
        self._suppliers[sid] = supplier

        return {
            "supplier_id": sid,
            "name": name,
            "registered": True,
        }

    def search(
        self,
        category: str = "",
        location: str = "",
        min_reliability: float = 0.0,
    ) -> dict[str, Any]:
        """Tedarikçi arar.

        Args:
            category: Kategori.
            location: Konum.
            min_reliability: Min güvenilirlik.

        Returns:
            Arama bilgisi.
        """
        results = list(
            self._suppliers.values(),
        )

        if category:
            results = [
                s for s in results
                if category in s["categories"]
            ]
        if location:
            results = [
                s for s in results
                if location.lower()
                in s["location"].lower()
            ]
        if min_reliability > 0:
            results = [
                s for s in results
                if s["reliability"]
                >= min_reliability
            ]

        self._stats[
            "searches_done"
        ] += 1

        return {
            "results": [
                {
                    "supplier_id": s[
                        "supplier_id"
                    ],
                    "name": s["name"],
                    "reliability": s[
                        "reliability"
                    ],
                }
                for s in results
            ],
            "count": len(results),
            "searched": True,
        }

    def qualify_supplier(
        self,
        supplier_id: str,
        quality_score: float = 0.0,
        delivery_score: float = 0.0,
        price_score: float = 0.0,
    ) -> dict[str, Any]:
        """Tedarikçi yeterliliği puanlar.

        Args:
            supplier_id: Tedarikçi ID.
            quality_score: Kalite puanı.
            delivery_score: Teslimat puanı.
            price_score: Fiyat puanı.

        Returns:
            Yeterlilik bilgisi.
        """
        if supplier_id not in self._suppliers:
            return {
                "supplier_id": supplier_id,
                "qualified": False,
                "reason": "Not found",
            }

        overall = round(
            quality_score * 0.4
            + delivery_score * 0.35
            + price_score * 0.25, 1,
        )

        tier = (
            "platinum" if overall >= 90
            else "gold" if overall >= 75
            else "silver" if overall >= 60
            else "bronze" if overall >= 40
            else "new"
        )

        self._stats[
            "qualifications_done"
        ] += 1

        return {
            "supplier_id": supplier_id,
            "overall_score": overall,
            "tier": tier,
            "quality": quality_score,
            "delivery": delivery_score,
            "price": price_score,
            "qualified": overall >= 40,
        }

    def rate_reliability(
        self,
        supplier_id: str,
        on_time_pct: float = 0.0,
        defect_rate: float = 0.0,
        response_time_hrs: float = 24.0,
    ) -> dict[str, Any]:
        """Güvenilirlik değerlendirir.

        Args:
            supplier_id: Tedarikçi ID.
            on_time_pct: Zamanında teslimat %.
            defect_rate: Hata oranı %.
            response_time_hrs: Yanıt süresi.

        Returns:
            Güvenilirlik bilgisi.
        """
        score = 0.0
        score += on_time_pct * 0.5
        score += (100 - defect_rate) * 0.3
        if response_time_hrs <= 4:
            score += 20
        elif response_time_hrs <= 12:
            score += 15
        elif response_time_hrs <= 24:
            score += 10

        score = round(min(score, 100), 1)

        level = (
            "excellent" if score >= 85
            else "good" if score >= 65
            else "average" if score >= 45
            else "poor"
        )

        if supplier_id in self._suppliers:
            self._suppliers[supplier_id][
                "reliability"
            ] = score

        return {
            "supplier_id": supplier_id,
            "reliability_score": score,
            "level": level,
            "on_time": on_time_pct,
            "defect_rate": defect_rate,
        }

    def filter_by_location(
        self,
        location: str,
    ) -> dict[str, Any]:
        """Konum filtreler.

        Args:
            location: Konum.

        Returns:
            Filtreleme bilgisi.
        """
        results = [
            s for s in
            self._suppliers.values()
            if location.lower()
            in s["location"].lower()
        ]

        return {
            "location": location,
            "results": [
                {
                    "supplier_id": s[
                        "supplier_id"
                    ],
                    "name": s["name"],
                }
                for s in results
            ],
            "count": len(results),
        }

    def check_capacity(
        self,
        supplier_id: str,
        required: int = 0,
    ) -> dict[str, Any]:
        """Kapasite kontrol eder.

        Args:
            supplier_id: Tedarikçi ID.
            required: Gerekli miktar.

        Returns:
            Kapasite bilgisi.
        """
        if supplier_id not in self._suppliers:
            return {
                "supplier_id": supplier_id,
                "sufficient": False,
            }

        sup = self._suppliers[supplier_id]
        capacity = sup["capacity"]
        sufficient = capacity >= required

        return {
            "supplier_id": supplier_id,
            "capacity": capacity,
            "required": required,
            "sufficient": sufficient,
            "surplus": max(
                capacity - required, 0,
            ),
        }

    def get_supplier(
        self,
        supplier_id: str,
    ) -> dict[str, Any] | None:
        """Tedarikçi döndürür."""
        return self._suppliers.get(
            supplier_id,
        )

    @property
    def supplier_count(self) -> int:
        """Tedarikçi sayısı."""
        return len(self._suppliers)

    @property
    def search_count(self) -> int:
        """Arama sayısı."""
        return self._stats[
            "searches_done"
        ]
