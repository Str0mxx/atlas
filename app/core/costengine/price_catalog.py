"""ATLAS Fiyat Katalogu modulu.

Servis fiyatlari, API fiyatlandirma,
kaynak fiyatlandirma, dinamik fiyat, doviz.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class PriceCatalog:
    """Fiyat katalogu.

    Fiyat bilgilerini yonetir.

    Attributes:
        _prices: Fiyat kayitlari.
        _currency_rates: Doviz kurlari.
    """

    def __init__(
        self,
        default_currency: str = "USD",
    ) -> None:
        """Fiyat katalogunu baslatir.

        Args:
            default_currency: Varsayilan doviz.
        """
        self._prices: dict[
            str, dict[str, Any]
        ] = {}
        self._currency_rates: dict[
            str, float
        ] = {"USD": 1.0}
        self._default_currency = default_currency
        self._tiers: dict[
            str, list[dict[str, Any]]
        ] = {}
        self._stats = {
            "entries": 0,
            "lookups": 0,
        }

        logger.info(
            "PriceCatalog baslatildi",
        )

    def set_price(
        self,
        service_id: str,
        price: float,
        unit: str = "per_call",
        currency: str = "USD",
        model: str = "fixed",
    ) -> dict[str, Any]:
        """Fiyat belirler.

        Args:
            service_id: Servis ID.
            price: Fiyat.
            unit: Birim.
            currency: Doviz.
            model: Fiyat modeli.

        Returns:
            Fiyat bilgisi.
        """
        self._prices[service_id] = {
            "service_id": service_id,
            "price": price,
            "unit": unit,
            "currency": currency,
            "model": model,
            "updated_at": time.time(),
        }
        self._stats["entries"] += 1

        return {
            "service_id": service_id,
            "price": price,
            "set": True,
        }

    def get_price(
        self,
        service_id: str,
        quantity: float = 1.0,
        currency: str | None = None,
    ) -> dict[str, Any]:
        """Fiyat sorgular.

        Args:
            service_id: Servis ID.
            quantity: Miktar.
            currency: Hedef doviz.

        Returns:
            Fiyat bilgisi.
        """
        self._stats["lookups"] += 1

        entry = self._prices.get(service_id)
        if not entry:
            return {
                "service_id": service_id,
                "error": "not_found",
            }

        base_price = entry["price"]
        model = entry["model"]

        # Tiered pricing
        if model == "tiered":
            tiers = self._tiers.get(
                service_id, [],
            )
            base_price = self._resolve_tier(
                tiers, quantity,
            )

        total = base_price * quantity

        # Doviz cevirimi
        target = (
            currency or self._default_currency
        )
        if target != entry["currency"]:
            total = self._convert_currency(
                total, entry["currency"], target,
            )

        return {
            "service_id": service_id,
            "unit_price": base_price,
            "quantity": quantity,
            "total": round(total, 6),
            "currency": target,
            "model": model,
        }

    def set_tiered_pricing(
        self,
        service_id: str,
        tiers: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Katmanli fiyat belirler.

        Args:
            service_id: Servis ID.
            tiers: Katmanlar [{min, max, price}].

        Returns:
            Ayarlama bilgisi.
        """
        self._tiers[service_id] = tiers

        # Model'i tiered yap
        if service_id in self._prices:
            self._prices[service_id][
                "model"
            ] = "tiered"

        return {
            "service_id": service_id,
            "tiers": len(tiers),
            "set": True,
        }

    def set_currency_rate(
        self,
        currency: str,
        rate_to_usd: float,
    ) -> dict[str, Any]:
        """Doviz kuru ayarlar.

        Args:
            currency: Doviz kodu.
            rate_to_usd: USD'ye oran.

        Returns:
            Ayarlama bilgisi.
        """
        self._currency_rates[currency] = (
            rate_to_usd
        )

        return {
            "currency": currency,
            "rate": rate_to_usd,
            "set": True,
        }

    def convert_price(
        self,
        amount: float,
        from_currency: str,
        to_currency: str,
    ) -> dict[str, Any]:
        """Doviz cevirir.

        Args:
            amount: Miktar.
            from_currency: Kaynak doviz.
            to_currency: Hedef doviz.

        Returns:
            Cevirim bilgisi.
        """
        converted = self._convert_currency(
            amount, from_currency, to_currency,
        )

        return {
            "amount": amount,
            "from": from_currency,
            "to": to_currency,
            "converted": round(converted, 6),
        }

    def list_prices(
        self,
        model: str | None = None,
    ) -> list[dict[str, Any]]:
        """Fiyatlari listeler.

        Args:
            model: Model filtresi.

        Returns:
            Fiyat listesi.
        """
        prices = list(self._prices.values())
        if model:
            prices = [
                p for p in prices
                if p.get("model") == model
            ]
        return prices

    def remove_price(
        self,
        service_id: str,
    ) -> dict[str, Any]:
        """Fiyat kaldirir.

        Args:
            service_id: Servis ID.

        Returns:
            Kaldirma bilgisi.
        """
        if service_id not in self._prices:
            return {"error": "not_found"}

        del self._prices[service_id]
        return {
            "service_id": service_id,
            "removed": True,
        }

    def _resolve_tier(
        self,
        tiers: list[dict[str, Any]],
        quantity: float,
    ) -> float:
        """Katman fiyatini cozumler.

        Args:
            tiers: Katmanlar.
            quantity: Miktar.

        Returns:
            Birim fiyat.
        """
        for tier in tiers:
            t_min = tier.get("min", 0)
            t_max = tier.get("max", float("inf"))
            if t_min <= quantity <= t_max:
                return tier["price"]

        if tiers:
            return tiers[-1]["price"]
        return 0.0

    def _convert_currency(
        self,
        amount: float,
        from_cur: str,
        to_cur: str,
    ) -> float:
        """Doviz cevirir (dahili).

        Args:
            amount: Miktar.
            from_cur: Kaynak doviz.
            to_cur: Hedef doviz.

        Returns:
            Cevrilen miktar.
        """
        from_rate = self._currency_rates.get(
            from_cur, 1.0,
        )
        to_rate = self._currency_rates.get(
            to_cur, 1.0,
        )

        # USD uzerinden cevir
        usd_amount = amount / from_rate
        return usd_amount * to_rate

    @property
    def price_count(self) -> int:
        """Fiyat sayisi."""
        return len(self._prices)

    @property
    def currency_count(self) -> int:
        """Doviz sayisi."""
        return len(self._currency_rates)
