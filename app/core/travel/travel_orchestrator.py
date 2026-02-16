"""
Seyahat orkestratör modülü.

Tam seyahat yönetimi, Search → Book → Plan → Track,
uçtan uca seyahat ve analitik.
"""

import logging
from typing import Any

from app.core.travel.expense_tracker import (
    TravelExpenseTracker,
)
from app.core.travel.flight_finder import (
    FlightFinder,
)
from app.core.travel.hotel_comparator import (
    HotelComparator,
)
from app.core.travel.itinerary_builder import (
    ItineraryBuilder,
)
from app.core.travel.price_alert_setter import (
    TravelPriceAlertSetter,
)
from app.core.travel.transfer_planner import (
    TransferPlanner,
)
from app.core.travel.travel_document_manager import (
    TravelDocumentManager,
)
from app.core.travel.visa_requirement_checker import (
    VisaRequirementChecker,
)

logger = logging.getLogger(__name__)


class TravelOrchestrator:
    """Seyahat orkestratör.

    Attributes:
        _flight: Uçuş bulucu.
        _hotel: Otel karşılaştırıcı.
        _transfer: Transfer planlayıcı.
        _visa: Vize kontrolcü.
        _itinerary: Gezi planı.
        _price_alert: Fiyat uyarı.
        _document: Belge yönetici.
        _expense: Harcama takip.
    """

    def __init__(self) -> None:
        """Orkestratörü başlatır."""
        self._flight = FlightFinder()
        self._hotel = HotelComparator()
        self._transfer = TransferPlanner()
        self._visa = VisaRequirementChecker()
        self._itinerary = ItineraryBuilder()
        self._price_alert = (
            TravelPriceAlertSetter()
        )
        self._document = TravelDocumentManager()
        self._expense = TravelExpenseTracker()
        logger.info(
            "TravelOrchestrator baslatildi"
        )

    def plan_full_trip(
        self,
        origin: str = "",
        destination: str = "",
        days: int = 5,
        budget: float = 2000.0,
        passport_country: str = "TR",
    ) -> dict[str, Any]:
        """Tam seyahat planlar.

        Search → Book → Plan → Track.

        Args:
            origin: Kalkış.
            destination: Varış.
            days: Gün sayısı.
            budget: Bütçe.
            passport_country: Pasaport ülkesi.

        Returns:
            Tam seyahat planı.
        """
        try:
            flights = self._flight.search_flights(
                origin=origin,
                destination=destination,
            )

            hotels = self._hotel.search_hotels(
                city=destination,
                nights=days,
            )

            visa = self._visa.check_requirements(
                passport_country=passport_country,
                destination=destination,
                stay_days=days,
            )

            itinerary = (
                self._itinerary.create_itinerary(
                    destination=destination,
                    days=days,
                )
            )

            return {
                "flights": flights,
                "hotels": hotels,
                "visa": visa,
                "itinerary": itinerary,
                "budget": budget,
                "planned": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "planned": False,
                "error": str(e),
            }

    def travel_checklist(
        self,
        passport_country: str = "TR",
        destination: str = "",
        stay_days: int = 7,
    ) -> dict[str, Any]:
        """Seyahat kontrol listesi oluşturur.

        Args:
            passport_country: Pasaport ülkesi.
            destination: Hedef.
            stay_days: Kalış süresi.

        Returns:
            Kontrol listesi.
        """
        try:
            visa = self._visa.check_requirements(
                passport_country=passport_country,
                destination=destination,
                stay_days=stay_days,
            )

            docs = (
                self._document.check_expiry_alerts()
            )

            items = [
                "passport_valid",
                "travel_insurance",
                "booking_confirmation",
            ]

            if visa.get("visa_required"):
                items.append("visa_obtained")
                checklist_visa = (
                    self._visa.get_document_checklist(
                        visa_type=visa.get(
                            "visa_type", "tourist"
                        ),
                    )
                )
                items.extend(
                    checklist_visa.get(
                        "documents", []
                    )
                )

            unique_items = list(dict.fromkeys(
                items
            ))

            return {
                "visa_info": visa,
                "document_alerts": docs,
                "checklist": unique_items,
                "item_count": len(unique_items),
                "generated": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "generated": False,
                "error": str(e),
            }

    def get_analytics(
        self,
    ) -> dict[str, Any]:
        """Seyahat analitiklerini getirir.

        Returns:
            Analitik verileri.
        """
        try:
            return {
                "flights_searched": (
                    self._flight.flight_count
                ),
                "hotels_searched": (
                    self._hotel.hotel_count
                ),
                "transfers_planned": (
                    self._transfer.transfer_count
                ),
                "visa_applications": (
                    self._visa.application_count
                ),
                "itineraries_created": (
                    self._itinerary.itinerary_count
                ),
                "price_alerts": (
                    self._price_alert.alert_count
                ),
                "documents_stored": (
                    self._document.document_count
                ),
                "expenses_logged": (
                    self._expense.expense_count
                ),
                "components": 8,
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }
