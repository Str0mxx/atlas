"""ATLAS Teklif Üretici modülü.

İlk teklif hesaplama, değer paketleme,
koşul yapılandırma, sunum formatlama,
gerekçelendirme.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class OfferGenerator:
    """Teklif üretici.

    Müzakere teklifleri üretir.

    Attributes:
        _offers: Teklif kayıtları.
        _templates: Teklif şablonları.
    """

    def __init__(
        self,
        currency: str = "TRY",
    ) -> None:
        """Üreticiyi başlatır.

        Args:
            currency: Para birimi.
        """
        self._offers: list[
            dict[str, Any]
        ] = []
        self._templates: dict[
            str, dict[str, Any]
        ] = {}
        self._currency = currency
        self._counter = 0
        self._stats = {
            "offers_generated": 0,
            "bundles_created": 0,
        }

        logger.info(
            "OfferGenerator baslatildi",
        )

    def generate_initial_offer(
        self,
        target_value: float,
        strategy: str = "collaborative",
        anchor_multiplier: float = 1.15,
        items: list[str] | None = None,
    ) -> dict[str, Any]:
        """İlk teklif üretir.

        Args:
            target_value: Hedef değer.
            strategy: Strateji.
            anchor_multiplier: Çapa çarpanı.
            items: Teklif kalemleri.

        Returns:
            Teklif bilgisi.
        """
        self._counter += 1
        oid = f"offer_{self._counter}"

        # Stratejiye göre çapa
        if strategy == "competitive":
            offer_value = round(
                target_value
                * anchor_multiplier
                * 1.1, 2,
            )
        elif strategy == "accommodating":
            offer_value = round(
                target_value * 0.95, 2,
            )
        else:
            offer_value = round(
                target_value
                * anchor_multiplier, 2,
            )

        offer = {
            "offer_id": oid,
            "amount": offer_value,
            "target_value": target_value,
            "strategy": strategy,
            "items": items or [],
            "currency": self._currency,
            "status": "draft",
            "justification": (
                self._build_justification(
                    offer_value,
                    target_value,
                    strategy,
                )
            ),
            "timestamp": time.time(),
        }
        self._offers.append(offer)
        self._stats["offers_generated"] += 1

        return {
            "offer_id": oid,
            "amount": offer_value,
            "currency": self._currency,
            "items": items or [],
            "justification": offer[
                "justification"
            ],
            "generated": True,
        }

    def create_bundle(
        self,
        items: list[dict[str, Any]],
        discount_rate: float = 0.0,
        name: str = "",
    ) -> dict[str, Any]:
        """Değer paketi oluşturur.

        Args:
            items: Paket kalemleri.
            discount_rate: İndirim oranı.
            name: Paket adı.

        Returns:
            Paket bilgisi.
        """
        self._counter += 1
        bid = f"bundle_{self._counter}"

        total = sum(
            i.get("value", 0) for i in items
        )
        discount = round(
            total * discount_rate, 2,
        )
        bundle_price = round(
            total - discount, 2,
        )

        bundle = {
            "bundle_id": bid,
            "name": name or f"Bundle {bid}",
            "items": items,
            "total_value": round(total, 2),
            "discount": discount,
            "discount_rate": discount_rate,
            "bundle_price": bundle_price,
            "item_count": len(items),
        }
        self._stats["bundles_created"] += 1

        return bundle

    def structure_terms(
        self,
        offer_id: str,
        payment_terms: str = "net_30",
        delivery: str = "",
        warranty: str = "",
        conditions: list[str] | None = None,
    ) -> dict[str, Any]:
        """Koşul yapılandırır.

        Args:
            offer_id: Teklif ID.
            payment_terms: Ödeme koşulları.
            delivery: Teslimat.
            warranty: Garanti.
            conditions: Ek koşullar.

        Returns:
            Koşul bilgisi.
        """
        terms = {
            "offer_id": offer_id,
            "payment_terms": payment_terms,
            "delivery": delivery,
            "warranty": warranty,
            "conditions": conditions or [],
            "structured": True,
        }

        # Teklifi güncelle
        for offer in self._offers:
            if offer["offer_id"] == offer_id:
                offer["terms"] = terms
                break

        return terms

    def format_presentation(
        self,
        offer_id: str,
        format_type: str = "formal",
    ) -> dict[str, Any]:
        """Sunum formatlar.

        Args:
            offer_id: Teklif ID.
            format_type: Format tipi.

        Returns:
            Sunum bilgisi.
        """
        offer = None
        for o in self._offers:
            if o["offer_id"] == offer_id:
                offer = o
                break

        if not offer:
            return {
                "offer_id": offer_id,
                "found": False,
            }

        if format_type == "formal":
            title = "Resmi Teklif"
            sections = [
                "executive_summary",
                "pricing",
                "terms",
                "timeline",
            ]
        elif format_type == "brief":
            title = "Kısa Teklif"
            sections = [
                "pricing",
                "key_terms",
            ]
        else:
            title = "Teklif"
            sections = ["details"]

        return {
            "offer_id": offer_id,
            "title": title,
            "format": format_type,
            "amount": offer["amount"],
            "currency": self._currency,
            "sections": sections,
            "formatted": True,
        }

    def _build_justification(
        self,
        offer_value: float,
        target_value: float,
        strategy: str,
    ) -> str:
        """Gerekçe oluşturur."""
        if strategy == "competitive":
            return (
                "Premium value based on "
                "market analysis and "
                "unique differentiators"
            )
        if strategy == "accommodating":
            return (
                "Competitive pricing to "
                "build long-term partnership"
            )
        return (
            "Fair market value reflecting "
            "quality and mutual benefit"
        )

    def get_offer(
        self,
        offer_id: str,
    ) -> dict[str, Any] | None:
        """Teklif döndürür."""
        for o in self._offers:
            if o["offer_id"] == offer_id:
                return o
        return None

    @property
    def offer_count(self) -> int:
        """Teklif sayısı."""
        return self._stats[
            "offers_generated"
        ]

    @property
    def bundle_count(self) -> int:
        """Paket sayısı."""
        return self._stats[
            "bundles_created"
        ]
