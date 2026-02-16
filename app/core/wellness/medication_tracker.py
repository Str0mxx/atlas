"""
İlaç takip modülü.

İlaç takvimi, doz hatırlatma, yenileme
uyarıları, etkileşim kontrolleri, geçmiş.
"""

import logging
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class MedicationTracker:
    """İlaç takipçisi.

    Attributes:
        _medications: İlaç kayıtları.
        _doses: Doz geçmişi.
        _stats: İstatistikler.
    """

    def __init__(self) -> None:
        """Takipçiyi başlatır."""
        self._medications: list[dict] = []
        self._doses: list[dict] = []
        self._stats: dict[str, int] = {
            "medications_added": 0,
        }
        logger.info(
            "MedicationTracker baslatildi"
        )

    @property
    def medication_count(self) -> int:
        """İlaç sayısı."""
        return len(self._medications)

    def add_medication(
        self,
        name: str = "",
        dosage: str = "",
        frequency: str = "once_daily",
        stock: int = 30,
    ) -> dict[str, Any]:
        """İlaç ekler.

        Args:
            name: İlaç adı.
            dosage: Doz bilgisi.
            frequency: Sıklık.
            stock: Stok miktarı.

        Returns:
            İlaç bilgisi.
        """
        try:
            mid = f"med_{uuid4()!s:.8}"

            doses_per_day = {
                "once_daily": 1,
                "twice_daily": 2,
                "three_daily": 3,
                "weekly": 0.14,
                "as_needed": 0,
                "monthly": 0.033,
            }

            daily = doses_per_day.get(
                frequency, 1
            )
            days_supply = (
                int(stock / daily)
                if daily > 0
                else 999
            )

            record = {
                "medication_id": mid,
                "name": name,
                "dosage": dosage,
                "frequency": frequency,
                "stock": stock,
                "daily_doses": daily,
                "days_supply": days_supply,
                "active": True,
            }
            self._medications.append(record)
            self._stats[
                "medications_added"
            ] += 1

            return {
                "medication_id": mid,
                "name": name,
                "dosage": dosage,
                "frequency": frequency,
                "stock": stock,
                "days_supply": days_supply,
                "added": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "added": False,
                "error": str(e),
            }

    def record_dose(
        self,
        medication_id: str = "",
        taken: bool = True,
    ) -> dict[str, Any]:
        """Doz kaydı ekler.

        Args:
            medication_id: İlaç ID.
            taken: Alındı mı.

        Returns:
            Kayıt bilgisi.
        """
        try:
            med = None
            for m in self._medications:
                if (
                    m["medication_id"]
                    == medication_id
                ):
                    med = m
                    break

            if not med:
                return {
                    "recorded": False,
                    "error": "medication_not_found",
                }

            dose = {
                "medication_id": medication_id,
                "name": med["name"],
                "taken": taken,
            }
            self._doses.append(dose)

            if taken and med["stock"] > 0:
                med["stock"] -= 1

            return {
                "medication_id": medication_id,
                "name": med["name"],
                "taken": taken,
                "remaining_stock": med["stock"],
                "recorded": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "recorded": False,
                "error": str(e),
            }

    def check_refill(
        self,
        threshold_days: int = 7,
    ) -> dict[str, Any]:
        """Yenileme kontrolü yapar.

        Args:
            threshold_days: Eşik gün sayısı.

        Returns:
            Yenileme bilgisi.
        """
        try:
            needs_refill = []
            ok_meds = []

            for med in self._medications:
                if not med["active"]:
                    continue
                if (
                    med["days_supply"]
                    <= threshold_days
                ):
                    needs_refill.append({
                        "name": med["name"],
                        "days_left": med[
                            "days_supply"
                        ],
                        "stock": med["stock"],
                    })
                else:
                    ok_meds.append(med["name"])

            return {
                "needs_refill": needs_refill,
                "refill_count": len(
                    needs_refill
                ),
                "ok_medications": ok_meds,
                "threshold_days": threshold_days,
                "checked": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "checked": False,
                "error": str(e),
            }

    def check_interactions(
        self,
        med_names: list[str] | None = None,
    ) -> dict[str, Any]:
        """İlaç etkileşimlerini kontrol eder.

        Args:
            med_names: Kontrol edilecek ilaçlar.

        Returns:
            Etkileşim bilgisi.
        """
        try:
            names = med_names or [
                m["name"]
                for m in self._medications
            ]

            known_interactions = {
                ("aspirin", "ibuprofen"): (
                    "increased_bleeding_risk"
                ),
                ("warfarin", "aspirin"): (
                    "severe_bleeding_risk"
                ),
                ("metformin", "alcohol"): (
                    "lactic_acidosis_risk"
                ),
            }

            found = []
            checked_pairs = 0

            for i, n1 in enumerate(names):
                for n2 in names[i + 1:]:
                    checked_pairs += 1
                    pair = tuple(sorted(
                        [n1.lower(), n2.lower()]
                    ))
                    if pair in known_interactions:
                        found.append({
                            "drugs": list(pair),
                            "risk": (
                                known_interactions[
                                    pair
                                ]
                            ),
                        })

            if found:
                risk_level = "high"
            elif len(names) > 5:
                risk_level = "moderate"
            else:
                risk_level = "low"

            return {
                "medications_checked": len(
                    names
                ),
                "pairs_checked": checked_pairs,
                "interactions": found,
                "interaction_count": len(found),
                "risk_level": risk_level,
                "checked": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "checked": False,
                "error": str(e),
            }

    def get_history(
        self,
        medication_id: str | None = None,
    ) -> dict[str, Any]:
        """Doz geçmişini getirir.

        Args:
            medication_id: İlaç ID filtresi.

        Returns:
            Geçmiş bilgisi.
        """
        try:
            if medication_id:
                filtered = [
                    d for d in self._doses
                    if d["medication_id"]
                    == medication_id
                ]
            else:
                filtered = list(self._doses)

            taken_count = sum(
                1 for d in filtered
                if d["taken"]
            )
            missed_count = sum(
                1 for d in filtered
                if not d["taken"]
            )

            adherence = (
                round(
                    taken_count
                    / len(filtered)
                    * 100,
                    1,
                )
                if filtered
                else 100.0
            )

            if adherence >= 90:
                compliance = "excellent"
            elif adherence >= 75:
                compliance = "good"
            elif adherence >= 50:
                compliance = "fair"
            else:
                compliance = "poor"

            return {
                "total_doses": len(filtered),
                "taken": taken_count,
                "missed": missed_count,
                "adherence_pct": adherence,
                "compliance": compliance,
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }
