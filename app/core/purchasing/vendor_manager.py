"""ATLAS Satıcı Yöneticisi modülü.

Satıcı profilleri, performans takibi,
sözleşme yönetimi, ilişki puanlama,
müzakere geçmişi.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class VendorManager:
    """Satıcı yöneticisi.

    Satıcı ilişkilerini yönetir.

    Attributes:
        _vendors: Satıcı kayıtları.
        _contracts: Sözleşme kayıtları.
    """

    def __init__(self) -> None:
        """Yöneticiyi başlatır."""
        self._vendors: dict[
            str, dict[str, Any]
        ] = {}
        self._contracts: dict[
            str, dict[str, Any]
        ] = {}
        self._negotiations: list[
            dict[str, Any]
        ] = []
        self._counter = 0
        self._stats = {
            "vendors_managed": 0,
            "contracts_tracked": 0,
            "negotiations_logged": 0,
        }

        logger.info(
            "VendorManager baslatildi",
        )

    def create_profile(
        self,
        name: str,
        contact: str = "",
        categories: list[str]
        | None = None,
        location: str = "",
    ) -> dict[str, Any]:
        """Satıcı profili oluşturur.

        Args:
            name: Ad.
            contact: İletişim.
            categories: Kategoriler.
            location: Konum.

        Returns:
            Profil bilgisi.
        """
        self._counter += 1
        vid = f"vnd_{self._counter}"
        categories = categories or []

        vendor = {
            "vendor_id": vid,
            "name": name,
            "contact": contact,
            "categories": categories,
            "location": location,
            "performance_scores": [],
            "relationship_score": 50.0,
            "timestamp": time.time(),
        }
        self._vendors[vid] = vendor
        self._stats[
            "vendors_managed"
        ] += 1

        return {
            "vendor_id": vid,
            "name": name,
            "created": True,
        }

    def track_performance(
        self,
        vendor_id: str,
        quality: float = 0.0,
        delivery: float = 0.0,
        price: float = 0.0,
        communication: float = 0.0,
    ) -> dict[str, Any]:
        """Performans takip eder.

        Args:
            vendor_id: Satıcı ID.
            quality: Kalite puanı.
            delivery: Teslimat puanı.
            price: Fiyat puanı.
            communication: İletişim puanı.

        Returns:
            Performans bilgisi.
        """
        if vendor_id not in self._vendors:
            return {
                "vendor_id": vendor_id,
                "tracked": False,
            }

        overall = round(
            quality * 0.3
            + delivery * 0.3
            + price * 0.2
            + communication * 0.2, 1,
        )

        self._vendors[vendor_id][
            "performance_scores"
        ].append(overall)

        level = (
            "excellent" if overall >= 85
            else "good" if overall >= 70
            else "average" if overall >= 50
            else "poor"
        )

        return {
            "vendor_id": vendor_id,
            "overall": overall,
            "level": level,
            "tracked": True,
        }

    def manage_contract(
        self,
        vendor_id: str,
        contract_type: str = "supply",
        value: float = 0.0,
        duration_months: int = 12,
    ) -> dict[str, Any]:
        """Sözleşme yönetir.

        Args:
            vendor_id: Satıcı ID.
            contract_type: Sözleşme tipi.
            value: Değer.
            duration_months: Süre.

        Returns:
            Sözleşme bilgisi.
        """
        self._counter += 1
        cid = f"vc_{self._counter}"

        contract = {
            "contract_id": cid,
            "vendor_id": vendor_id,
            "type": contract_type,
            "value": value,
            "duration_months": (
                duration_months
            ),
            "status": "active",
            "timestamp": time.time(),
        }
        self._contracts[cid] = contract
        self._stats[
            "contracts_tracked"
        ] += 1

        return {
            "contract_id": cid,
            "vendor_id": vendor_id,
            "value": value,
            "created": True,
        }

    def score_relationship(
        self,
        vendor_id: str,
    ) -> dict[str, Any]:
        """İlişki puanlar.

        Args:
            vendor_id: Satıcı ID.

        Returns:
            İlişki bilgisi.
        """
        if vendor_id not in self._vendors:
            return {
                "vendor_id": vendor_id,
                "scored": False,
            }

        vendor = self._vendors[vendor_id]
        scores = vendor[
            "performance_scores"
        ]

        if scores:
            avg_perf = round(
                sum(scores) / len(scores),
                1,
            )
        else:
            avg_perf = 50.0

        # Sözleşme sayısı bonusu
        contracts = [
            c for c in
            self._contracts.values()
            if c["vendor_id"] == vendor_id
        ]
        contract_bonus = min(
            len(contracts) * 5, 15,
        )

        rel_score = round(
            min(avg_perf + contract_bonus, 100),
            1,
        )
        vendor["relationship_score"] = (
            rel_score
        )

        level = (
            "strategic" if rel_score >= 80
            else "preferred" if rel_score >= 60
            else "approved" if rel_score >= 40
            else "probation"
        )

        return {
            "vendor_id": vendor_id,
            "relationship_score": rel_score,
            "level": level,
            "avg_performance": avg_perf,
            "contracts": len(contracts),
            "scored": True,
        }

    def log_negotiation(
        self,
        vendor_id: str,
        topic: str = "",
        outcome: str = "",
        savings: float = 0.0,
    ) -> dict[str, Any]:
        """Müzakere kaydeder.

        Args:
            vendor_id: Satıcı ID.
            topic: Konu.
            outcome: Sonuç.
            savings: Tasarruf.

        Returns:
            Kayıt bilgisi.
        """
        entry = {
            "vendor_id": vendor_id,
            "topic": topic,
            "outcome": outcome,
            "savings": savings,
            "timestamp": time.time(),
        }
        self._negotiations.append(entry)
        self._stats[
            "negotiations_logged"
        ] += 1

        return {
            "vendor_id": vendor_id,
            "topic": topic,
            "outcome": outcome,
            "savings": savings,
            "logged": True,
        }

    def get_vendor(
        self,
        vendor_id: str,
    ) -> dict[str, Any] | None:
        """Satıcı döndürür."""
        return self._vendors.get(vendor_id)

    @property
    def vendor_count(self) -> int:
        """Satıcı sayısı."""
        return self._stats[
            "vendors_managed"
        ]

    @property
    def contract_count(self) -> int:
        """Sözleşme sayısı."""
        return self._stats[
            "contracts_tracked"
        ]
