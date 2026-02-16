"""
Tıbbi randevu takip modülü.

Randevu planlama, hatırlatma sistemi, doktor
veritabanı, geçmiş takibi, belge yönetimi.
"""

import logging
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class MedicalAppointmentTracker:
    """Tıbbi randevu takipçisi.

    Attributes:
        _appointments: Randevu kayıtları.
        _doctors: Doktor veritabanı.
        _stats: İstatistikler.
    """

    def __init__(self) -> None:
        """Takipçiyi başlatır."""
        self._appointments: list[dict] = []
        self._doctors: list[dict] = []
        self._stats: dict[str, int] = {
            "appointments_created": 0,
        }
        logger.info(
            "MedicalAppointmentTracker baslatildi"
        )

    @property
    def appointment_count(self) -> int:
        """Randevu sayısı."""
        return len(self._appointments)

    def schedule_appointment(
        self,
        doctor: str = "",
        specialty: str = "general",
        date: str = "",
        notes: str = "",
    ) -> dict[str, Any]:
        """Randevu planlar.

        Args:
            doctor: Doktor adı.
            specialty: Uzmanlık.
            date: Tarih.
            notes: Notlar.

        Returns:
            Randevu bilgisi.
        """
        try:
            aid = f"apt_{uuid4()!s:.8}"

            record = {
                "appointment_id": aid,
                "doctor": doctor,
                "specialty": specialty,
                "date": date,
                "notes": notes,
                "status": "scheduled",
            }
            self._appointments.append(record)
            self._stats[
                "appointments_created"
            ] += 1

            return {
                "appointment_id": aid,
                "doctor": doctor,
                "specialty": specialty,
                "date": date,
                "status": "scheduled",
                "scheduled": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "scheduled": False,
                "error": str(e),
            }

    def set_reminder(
        self,
        appointment_id: str = "",
        days_before: int = 1,
    ) -> dict[str, Any]:
        """Randevu hatırlatması ayarlar.

        Args:
            appointment_id: Randevu ID.
            days_before: Kaç gün önce.

        Returns:
            Hatırlatma bilgisi.
        """
        try:
            apt = None
            for a in self._appointments:
                if (
                    a["appointment_id"]
                    == appointment_id
                ):
                    apt = a
                    break

            if not apt:
                return {
                    "set": False,
                    "error": "appointment_not_found",
                }

            apt["reminder_days"] = days_before

            return {
                "appointment_id": appointment_id,
                "days_before": days_before,
                "doctor": apt["doctor"],
                "set": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "set": False,
                "error": str(e),
            }

    def add_doctor(
        self,
        name: str = "",
        specialty: str = "general",
        hospital: str = "",
        phone: str = "",
    ) -> dict[str, Any]:
        """Doktor kaydı ekler.

        Args:
            name: Doktor adı.
            specialty: Uzmanlık.
            hospital: Hastane.
            phone: Telefon.

        Returns:
            Doktor bilgisi.
        """
        try:
            did = f"doc_{uuid4()!s:.8}"

            record = {
                "doctor_id": did,
                "name": name,
                "specialty": specialty,
                "hospital": hospital,
                "phone": phone,
            }
            self._doctors.append(record)

            return {
                "doctor_id": did,
                "name": name,
                "specialty": specialty,
                "hospital": hospital,
                "added": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "added": False,
                "error": str(e),
            }

    def get_history(
        self,
        specialty: str | None = None,
    ) -> dict[str, Any]:
        """Randevu geçmişini getirir.

        Args:
            specialty: Filtrelenecek uzmanlık.

        Returns:
            Geçmiş bilgisi.
        """
        try:
            if specialty:
                filtered = [
                    a for a in self._appointments
                    if a["specialty"] == specialty
                ]
            else:
                filtered = list(
                    self._appointments
                )

            specialties = list({
                a["specialty"]
                for a in self._appointments
            })

            return {
                "appointments": filtered,
                "total": len(filtered),
                "specialties": specialties,
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }

    def manage_documents(
        self,
        appointment_id: str = "",
        document_type: str = "report",
        document_name: str = "",
    ) -> dict[str, Any]:
        """Randevu belgelerini yönetir.

        Args:
            appointment_id: Randevu ID.
            document_type: Belge türü.
            document_name: Belge adı.

        Returns:
            Belge bilgisi.
        """
        try:
            apt = None
            for a in self._appointments:
                if (
                    a["appointment_id"]
                    == appointment_id
                ):
                    apt = a
                    break

            if not apt:
                return {
                    "managed": False,
                    "error": "appointment_not_found",
                }

            doc_id = f"doc_{uuid4()!s:.8}"

            if "documents" not in apt:
                apt["documents"] = []
            apt["documents"].append({
                "doc_id": doc_id,
                "type": document_type,
                "name": document_name,
            })

            return {
                "doc_id": doc_id,
                "appointment_id": appointment_id,
                "document_type": document_type,
                "document_name": document_name,
                "total_docs": len(
                    apt["documents"]
                ),
                "managed": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "managed": False,
                "error": str(e),
            }
