"""
Transfer planlayıcı modülü.

Kara ulaşımı, havaalanı transferleri,
araç kiralama, toplu taşıma, maliyet.
"""

import logging
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class TransferPlanner:
    """Transfer planlayıcı.

    Attributes:
        _transfers: Transfer kayıtları.
        _stats: İstatistikler.
    """

    def __init__(self) -> None:
        """Planlayıcıyı başlatır."""
        self._transfers: list[dict] = []
        self._stats: dict[str, int] = {
            "transfers_planned": 0,
        }
        logger.info(
            "TransferPlanner baslatildi"
        )

    @property
    def transfer_count(self) -> int:
        """Transfer sayısı."""
        return len(self._transfers)

    def plan_ground_transport(
        self,
        origin: str = "",
        destination: str = "",
        distance_km: float = 0.0,
    ) -> dict[str, Any]:
        """Kara ulaşımı planlar.

        Args:
            origin: Kalkış.
            destination: Varış.
            distance_km: Mesafe (km).

        Returns:
            Ulaşım planı.
        """
        try:
            tid = f"tr_{uuid4()!s:.8}"

            options = [
                {
                    "type": "taxi",
                    "price": round(
                        distance_km * 2.5, 2
                    ),
                    "duration_min": int(
                        distance_km * 2
                    ),
                },
                {
                    "type": "shuttle",
                    "price": round(
                        distance_km * 1.0, 2
                    ),
                    "duration_min": int(
                        distance_km * 2.5
                    ),
                },
                {
                    "type": "public_transit",
                    "price": round(
                        distance_km * 0.3, 2
                    ),
                    "duration_min": int(
                        distance_km * 4
                    ),
                },
            ]

            record = {
                "transfer_id": tid,
                "origin": origin,
                "destination": destination,
                "distance_km": distance_km,
                "options": options,
            }
            self._transfers.append(record)
            self._stats[
                "transfers_planned"
            ] += 1

            return {
                "transfer_id": tid,
                "origin": origin,
                "destination": destination,
                "options": options,
                "option_count": len(options),
                "planned": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "planned": False,
                "error": str(e),
            }

    def plan_airport_transfer(
        self,
        airport: str = "",
        hotel: str = "",
        distance_km: float = 30.0,
        passengers: int = 1,
    ) -> dict[str, Any]:
        """Havaalanı transferi planlar.

        Args:
            airport: Havaalanı.
            hotel: Otel.
            distance_km: Mesafe.
            passengers: Yolcu sayısı.

        Returns:
            Transfer planı.
        """
        try:
            tid = f"at_{uuid4()!s:.8}"

            options = [
                {
                    "type": "private_transfer",
                    "price": 50.0 + passengers * 5,
                    "duration_min": int(
                        distance_km * 1.5
                    ),
                    "shared": False,
                },
                {
                    "type": "shared_shuttle",
                    "price": 15.0 * passengers,
                    "duration_min": int(
                        distance_km * 2.5
                    ),
                    "shared": True,
                },
                {
                    "type": "public_bus",
                    "price": 3.0 * passengers,
                    "duration_min": int(
                        distance_km * 3.5
                    ),
                    "shared": True,
                },
            ]

            cheapest = min(
                options,
                key=lambda o: o["price"],
            )

            return {
                "transfer_id": tid,
                "airport": airport,
                "hotel": hotel,
                "options": options,
                "recommended": cheapest["type"],
                "planned": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "planned": False,
                "error": str(e),
            }

    def find_car_rental(
        self,
        city: str = "",
        days: int = 1,
        car_type: str = "economy",
    ) -> dict[str, Any]:
        """Araç kiralama bulur.

        Args:
            city: Şehir.
            days: Gün sayısı.
            car_type: Araç türü.

        Returns:
            Kiralama seçenekleri.
        """
        try:
            daily_rates = {
                "economy": 35.0,
                "compact": 50.0,
                "midsize": 70.0,
                "suv": 100.0,
                "luxury": 180.0,
            }

            rate = daily_rates.get(car_type, 35.0)
            total = round(rate * days, 2)
            insurance = round(total * 0.15, 2)

            return {
                "city": city,
                "car_type": car_type,
                "days": days,
                "daily_rate": rate,
                "total_rental": total,
                "insurance": insurance,
                "grand_total": round(
                    total + insurance, 2
                ),
                "found": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "found": False,
                "error": str(e),
            }

    def check_public_transit(
        self,
        city: str = "",
        has_metro: bool = True,
        has_bus: bool = True,
        has_tram: bool = False,
    ) -> dict[str, Any]:
        """Toplu taşıma kontrol eder.

        Args:
            city: Şehir.
            has_metro: Metro var mı.
            has_bus: Otobüs var mı.
            has_tram: Tramvay var mı.

        Returns:
            Toplu taşıma bilgisi.
        """
        try:
            modes = []
            if has_metro:
                modes.append("metro")
            if has_bus:
                modes.append("bus")
            if has_tram:
                modes.append("tram")

            if len(modes) >= 3:
                coverage = "excellent"
            elif len(modes) >= 2:
                coverage = "good"
            elif len(modes) >= 1:
                coverage = "basic"
            else:
                coverage = "none"

            daily_pass = 5.0 * len(modes)

            return {
                "city": city,
                "modes": modes,
                "mode_count": len(modes),
                "coverage": coverage,
                "daily_pass_estimate": daily_pass,
                "checked": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "checked": False,
                "error": str(e),
            }

    def optimize_costs(
        self,
        options: list[dict] | None = None,
    ) -> dict[str, Any]:
        """Maliyetleri optimize eder.

        Args:
            options: Ulaşım seçenekleri.

        Returns:
            Maliyet optimizasyonu.
        """
        try:
            items = options or []
            if not items:
                return {
                    "optimized": True,
                    "cheapest": None,
                    "count": 0,
                }

            sorted_opts = sorted(
                items,
                key=lambda o: o.get("price", 0),
            )
            cheapest = sorted_opts[0]
            most_expensive = sorted_opts[-1]

            potential_savings = (
                most_expensive.get("price", 0)
                - cheapest.get("price", 0)
            )

            return {
                "cheapest": cheapest,
                "most_expensive": most_expensive,
                "potential_savings": round(
                    potential_savings, 2
                ),
                "count": len(items),
                "optimized": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "optimized": False,
                "error": str(e),
            }
