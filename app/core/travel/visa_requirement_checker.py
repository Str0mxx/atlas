"""
Vize gereksinim kontrol modülü.

Vize gereksinimleri, belge kontrol listesi,
işlem süreleri, başvuru takibi, son tarih uyarıları.
"""

import logging
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class VisaRequirementChecker:
    """Vize gereksinim kontrolcüsü.

    Attributes:
        _applications: Başvuru kayıtları.
        _stats: İstatistikler.
    """

    def __init__(self) -> None:
        """Kontrolcüyü başlatır."""
        self._applications: list[dict] = []
        self._stats: dict[str, int] = {
            "checks_performed": 0,
        }
        logger.info(
            "VisaRequirementChecker baslatildi"
        )

    @property
    def application_count(self) -> int:
        """Başvuru sayısı."""
        return len(self._applications)

    def check_requirements(
        self,
        passport_country: str = "",
        destination: str = "",
        stay_days: int = 7,
    ) -> dict[str, Any]:
        """Vize gereksinimlerini kontrol eder.

        Args:
            passport_country: Pasaport ülkesi.
            destination: Hedef ülke.
            stay_days: Kalış süresi (gün).

        Returns:
            Vize gereksinimleri.
        """
        try:
            visa_free = {
                ("TR", "GE"): 365,
                ("TR", "AZ"): 90,
                ("TR", "KR"): 90,
                ("TR", "JP"): 90,
                ("US", "GB"): 180,
                ("US", "FR"): 90,
                ("US", "DE"): 90,
            }

            pair = (
                passport_country.upper(),
                destination.upper(),
            )
            free_days = visa_free.get(pair, 0)

            if free_days >= stay_days:
                visa_required = False
                visa_type = "visa_free"
            elif stay_days <= 30:
                visa_required = True
                visa_type = "tourist"
            elif stay_days <= 90:
                visa_required = True
                visa_type = "short_stay"
            else:
                visa_required = True
                visa_type = "long_stay"

            self._stats[
                "checks_performed"
            ] += 1

            return {
                "passport_country": passport_country,
                "destination": destination,
                "stay_days": stay_days,
                "visa_required": visa_required,
                "visa_type": visa_type,
                "free_days": free_days,
                "checked": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "checked": False,
                "error": str(e),
            }

    def get_document_checklist(
        self,
        visa_type: str = "tourist",
    ) -> dict[str, Any]:
        """Belge kontrol listesi verir.

        Args:
            visa_type: Vize türü.

        Returns:
            Belge listesi.
        """
        try:
            base_docs = [
                "valid_passport",
                "passport_photos",
                "application_form",
            ]

            type_docs = {
                "tourist": [
                    "hotel_reservation",
                    "return_ticket",
                    "travel_insurance",
                ],
                "short_stay": [
                    "hotel_reservation",
                    "return_ticket",
                    "travel_insurance",
                    "bank_statement",
                ],
                "long_stay": [
                    "invitation_letter",
                    "accommodation_proof",
                    "financial_proof",
                    "health_insurance",
                    "background_check",
                ],
                "business": [
                    "invitation_letter",
                    "company_letter",
                    "travel_insurance",
                    "bank_statement",
                ],
            }

            extra = type_docs.get(
                visa_type, type_docs["tourist"]
            )
            all_docs = base_docs + extra

            return {
                "visa_type": visa_type,
                "documents": all_docs,
                "document_count": len(all_docs),
                "generated": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "generated": False,
                "error": str(e),
            }

    def estimate_processing_time(
        self,
        visa_type: str = "tourist",
        destination: str = "",
    ) -> dict[str, Any]:
        """İşlem süresini tahmin eder.

        Args:
            visa_type: Vize türü.
            destination: Hedef ülke.

        Returns:
            Süre tahmini.
        """
        try:
            base_days = {
                "tourist": 10,
                "short_stay": 15,
                "long_stay": 30,
                "business": 12,
                "visa_free": 0,
            }

            days = base_days.get(visa_type, 15)

            if days == 0:
                urgency = "none"
            elif days <= 10:
                urgency = "low"
            elif days <= 20:
                urgency = "moderate"
            else:
                urgency = "high"

            return {
                "visa_type": visa_type,
                "destination": destination,
                "estimated_days": days,
                "urgency": urgency,
                "estimated": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "estimated": False,
                "error": str(e),
            }

    def track_application(
        self,
        destination: str = "",
        visa_type: str = "tourist",
        status: str = "applied",
    ) -> dict[str, Any]:
        """Başvuruyu takip eder.

        Args:
            destination: Hedef ülke.
            visa_type: Vize türü.
            status: Durum.

        Returns:
            Takip bilgisi.
        """
        try:
            aid = f"visa_{uuid4()!s:.8}"

            record = {
                "application_id": aid,
                "destination": destination,
                "visa_type": visa_type,
                "status": status,
            }
            self._applications.append(record)

            return {
                "application_id": aid,
                "destination": destination,
                "visa_type": visa_type,
                "status": status,
                "tracked": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "tracked": False,
                "error": str(e),
            }

    def check_deadlines(
        self,
        travel_days_away: int = 30,
        processing_days: int = 15,
    ) -> dict[str, Any]:
        """Son tarih uyarıları kontrol eder.

        Args:
            travel_days_away: Seyahate kalan gün.
            processing_days: İşlem süresi (gün).

        Returns:
            Uyarı bilgisi.
        """
        try:
            buffer_days = (
                travel_days_away - processing_days
            )

            if buffer_days < 0:
                alert = "overdue"
                severity = "critical"
            elif buffer_days < 5:
                alert = "urgent"
                severity = "high"
            elif buffer_days < 14:
                alert = "soon"
                severity = "medium"
            else:
                alert = "on_track"
                severity = "low"

            return {
                "travel_days_away": travel_days_away,
                "processing_days": processing_days,
                "buffer_days": buffer_days,
                "alert": alert,
                "severity": severity,
                "checked": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "checked": False,
                "error": str(e),
            }
