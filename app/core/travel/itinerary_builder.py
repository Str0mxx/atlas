"""
Gezi planı oluşturucu modülü.

Gün planlama, aktivite zamanlama, rota
optimizasyonu, zaman yönetimi, esneklik.
"""

import logging
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class ItineraryBuilder:
    """Gezi planı oluşturucu.

    Attributes:
        _itineraries: Plan kayıtları.
        _stats: İstatistikler.
    """

    def __init__(self) -> None:
        """Oluşturucuyu başlatır."""
        self._itineraries: list[dict] = []
        self._stats: dict[str, int] = {
            "itineraries_created": 0,
        }
        logger.info(
            "ItineraryBuilder baslatildi"
        )

    @property
    def itinerary_count(self) -> int:
        """Plan sayısı."""
        return len(self._itineraries)

    def create_itinerary(
        self,
        destination: str = "",
        days: int = 3,
        style: str = "balanced",
    ) -> dict[str, Any]:
        """Gezi planı oluşturur.

        Args:
            destination: Hedef.
            days: Gün sayısı.
            style: Plan stili.

        Returns:
            Plan bilgisi.
        """
        try:
            iid = f"itn_{uuid4()!s:.8}"

            day_plans = []
            for d in range(1, days + 1):
                activities = []

                if style in (
                    "balanced", "cultural"
                ):
                    activities.append({
                        "time": "09:00",
                        "activity": "sightseeing",
                        "duration_h": 3,
                    })
                if style in (
                    "balanced", "adventure"
                ):
                    activities.append({
                        "time": "13:00",
                        "activity": "exploration",
                        "duration_h": 3,
                    })
                activities.append({
                    "time": "18:00",
                    "activity": "dinner",
                    "duration_h": 2,
                })

                day_plans.append({
                    "day": d,
                    "activities": activities,
                    "activity_count": len(
                        activities
                    ),
                })

            record = {
                "itinerary_id": iid,
                "destination": destination,
                "days": days,
                "style": style,
                "day_plans": day_plans,
            }
            self._itineraries.append(record)
            self._stats[
                "itineraries_created"
            ] += 1

            return {
                "itinerary_id": iid,
                "destination": destination,
                "days": days,
                "style": style,
                "day_plans": day_plans,
                "total_activities": sum(
                    dp["activity_count"]
                    for dp in day_plans
                ),
                "created": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "created": False,
                "error": str(e),
            }

    def add_activity(
        self,
        itinerary_id: str = "",
        day: int = 1,
        time: str = "10:00",
        activity: str = "",
        duration_h: int = 2,
    ) -> dict[str, Any]:
        """Aktivite ekler.

        Args:
            itinerary_id: Plan ID.
            day: Gün numarası.
            time: Saat.
            activity: Aktivite.
            duration_h: Süre (saat).

        Returns:
            Ekleme bilgisi.
        """
        try:
            itn = None
            for i in self._itineraries:
                if (
                    i["itinerary_id"]
                    == itinerary_id
                ):
                    itn = i
                    break

            if not itn:
                return {
                    "added": False,
                    "error": "itinerary_not_found",
                }

            for dp in itn["day_plans"]:
                if dp["day"] == day:
                    dp["activities"].append({
                        "time": time,
                        "activity": activity,
                        "duration_h": duration_h,
                    })
                    dp["activity_count"] += 1
                    return {
                        "itinerary_id": itinerary_id,
                        "day": day,
                        "activity": activity,
                        "added": True,
                    }

            return {
                "added": False,
                "error": "day_not_found",
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "added": False,
                "error": str(e),
            }

    def optimize_route(
        self,
        activities: list[dict] | None = None,
    ) -> dict[str, Any]:
        """Rota optimize eder.

        Args:
            activities: Aktivite listesi.

        Returns:
            Optimizasyon sonucu.
        """
        try:
            items = activities or []
            if not items:
                return {
                    "optimized": True,
                    "activities": [],
                    "count": 0,
                }

            sorted_acts = sorted(
                items,
                key=lambda a: a.get("time", ""),
            )

            total_hours = sum(
                a.get("duration_h", 0)
                for a in sorted_acts
            )

            return {
                "activities": sorted_acts,
                "count": len(sorted_acts),
                "total_hours": total_hours,
                "optimized": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "optimized": False,
                "error": str(e),
            }

    def check_time_management(
        self,
        planned_hours: float = 8.0,
        available_hours: float = 12.0,
    ) -> dict[str, Any]:
        """Zaman yönetimini kontrol eder.

        Args:
            planned_hours: Planlanan saat.
            available_hours: Müsait saat.

        Returns:
            Zaman analizi.
        """
        try:
            free_hours = (
                available_hours - planned_hours
            )
            utilization = round(
                planned_hours
                / available_hours
                * 100,
                1,
            ) if available_hours > 0 else 0.0

            if utilization > 90:
                status = "overbooked"
            elif utilization > 70:
                status = "packed"
            elif utilization > 40:
                status = "balanced"
            else:
                status = "relaxed"

            return {
                "planned_hours": planned_hours,
                "available_hours": available_hours,
                "free_hours": round(
                    free_hours, 1
                ),
                "utilization_pct": utilization,
                "status": status,
                "checked": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "checked": False,
                "error": str(e),
            }

    def handle_flexibility(
        self,
        itinerary_id: str = "",
        flexibility_level: str = "moderate",
    ) -> dict[str, Any]:
        """Esneklik yönetir.

        Args:
            itinerary_id: Plan ID.
            flexibility_level: Esneklik seviyesi.

        Returns:
            Esneklik ayarları.
        """
        try:
            buffers = {
                "strict": 0,
                "moderate": 30,
                "flexible": 60,
                "very_flexible": 120,
            }

            buffer_min = buffers.get(
                flexibility_level, 30
            )

            alternatives = (
                flexibility_level
                in ("flexible", "very_flexible")
            )

            return {
                "itinerary_id": itinerary_id,
                "flexibility_level": (
                    flexibility_level
                ),
                "buffer_minutes": buffer_min,
                "allow_alternatives": alternatives,
                "configured": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "configured": False,
                "error": str(e),
            }
