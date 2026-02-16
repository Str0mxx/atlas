"""
Seyahat belgesi yönetim modülü.

Pasaport takibi, vize saklama, sigorta
belgeleri, rezervasyon onayları, süre uyarıları.
"""

import logging
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class TravelDocumentManager:
    """Seyahat belgesi yöneticisi.

    Attributes:
        _documents: Belge kayıtları.
        _stats: İstatistikler.
    """

    def __init__(self) -> None:
        """Yöneticiyi başlatır."""
        self._documents: list[dict] = []
        self._stats: dict[str, int] = {
            "documents_added": 0,
        }
        logger.info(
            "TravelDocumentManager baslatildi"
        )

    @property
    def document_count(self) -> int:
        """Belge sayısı."""
        return len(self._documents)

    def add_passport(
        self,
        holder_name: str = "",
        passport_number: str = "",
        expiry_months: int = 60,
    ) -> dict[str, Any]:
        """Pasaport ekler.

        Args:
            holder_name: Sahip adı.
            passport_number: Pasaport no.
            expiry_months: Kalan ay.

        Returns:
            Pasaport bilgisi.
        """
        try:
            did = f"doc_{uuid4()!s:.8}"

            if expiry_months < 6:
                status = "expiring_soon"
                alert = True
            elif expiry_months < 12:
                status = "renew_recommended"
                alert = True
            else:
                status = "valid"
                alert = False

            record = {
                "document_id": did,
                "type": "passport",
                "holder_name": holder_name,
                "number": passport_number,
                "expiry_months": expiry_months,
                "status": status,
            }
            self._documents.append(record)
            self._stats["documents_added"] += 1

            return {
                "document_id": did,
                "type": "passport",
                "holder_name": holder_name,
                "expiry_months": expiry_months,
                "status": status,
                "alert": alert,
                "added": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "added": False,
                "error": str(e),
            }

    def store_visa(
        self,
        country: str = "",
        visa_type: str = "tourist",
        valid_months: int = 6,
    ) -> dict[str, Any]:
        """Vize saklar.

        Args:
            country: Ülke.
            visa_type: Vize türü.
            valid_months: Geçerlilik (ay).

        Returns:
            Vize bilgisi.
        """
        try:
            did = f"doc_{uuid4()!s:.8}"

            if valid_months <= 0:
                status = "expired"
            elif valid_months < 3:
                status = "expiring_soon"
            else:
                status = "valid"

            record = {
                "document_id": did,
                "type": "visa",
                "country": country,
                "visa_type": visa_type,
                "valid_months": valid_months,
                "status": status,
            }
            self._documents.append(record)
            self._stats["documents_added"] += 1

            return {
                "document_id": did,
                "type": "visa",
                "country": country,
                "visa_type": visa_type,
                "valid_months": valid_months,
                "status": status,
                "stored": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "stored": False,
                "error": str(e),
            }

    def add_insurance(
        self,
        provider: str = "",
        coverage_type: str = "travel",
        valid_months: int = 12,
    ) -> dict[str, Any]:
        """Sigorta belgesi ekler.

        Args:
            provider: Sağlayıcı.
            coverage_type: Kapsam türü.
            valid_months: Geçerlilik (ay).

        Returns:
            Sigorta bilgisi.
        """
        try:
            did = f"doc_{uuid4()!s:.8}"

            record = {
                "document_id": did,
                "type": "insurance",
                "provider": provider,
                "coverage_type": coverage_type,
                "valid_months": valid_months,
            }
            self._documents.append(record)
            self._stats["documents_added"] += 1

            return {
                "document_id": did,
                "type": "insurance",
                "provider": provider,
                "coverage_type": coverage_type,
                "valid_months": valid_months,
                "added": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "added": False,
                "error": str(e),
            }

    def add_booking_confirmation(
        self,
        booking_type: str = "flight",
        reference: str = "",
        provider: str = "",
    ) -> dict[str, Any]:
        """Rezervasyon onayı ekler.

        Args:
            booking_type: Rezervasyon türü.
            reference: Referans no.
            provider: Sağlayıcı.

        Returns:
            Onay bilgisi.
        """
        try:
            did = f"doc_{uuid4()!s:.8}"

            record = {
                "document_id": did,
                "type": "booking",
                "booking_type": booking_type,
                "reference": reference,
                "provider": provider,
            }
            self._documents.append(record)
            self._stats["documents_added"] += 1

            return {
                "document_id": did,
                "type": "booking",
                "booking_type": booking_type,
                "reference": reference,
                "provider": provider,
                "added": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "added": False,
                "error": str(e),
            }

    def check_expiry_alerts(
        self,
        threshold_months: int = 6,
    ) -> dict[str, Any]:
        """Süre dolum uyarılarını kontrol eder.

        Args:
            threshold_months: Eşik (ay).

        Returns:
            Uyarı bilgisi.
        """
        try:
            expiring = []
            valid = []

            for doc in self._documents:
                months = doc.get(
                    "expiry_months",
                    doc.get("valid_months", 999),
                )
                if months <= threshold_months:
                    expiring.append({
                        "document_id": doc[
                            "document_id"
                        ],
                        "type": doc["type"],
                        "months_left": months,
                    })
                else:
                    valid.append(
                        doc["document_id"]
                    )

            return {
                "expiring": expiring,
                "expiring_count": len(expiring),
                "valid_count": len(valid),
                "threshold_months": (
                    threshold_months
                ),
                "checked": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "checked": False,
                "error": str(e),
            }
