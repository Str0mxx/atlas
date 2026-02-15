"""ATLAS Rutin Tespitçisi modülü.

Günlük kalıplar, haftalık kalıplar,
istisna tespiti, alışkanlık öğrenme,
tahmin.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class RoutineDetector:
    """Rutin tespitçisi.

    Kullanıcı rutinlerini tespit eder.

    Attributes:
        _events: Olay kayıtları.
        _routines: Tespit edilen rutinler.
    """

    def __init__(
        self,
        min_occurrences: int = 3,
        confidence_threshold: float = 0.6,
    ) -> None:
        """Tespitçiyi başlatır.

        Args:
            min_occurrences: Minimum tekrar sayısı.
            confidence_threshold: Güven eşiği.
        """
        self._events: list[
            dict[str, Any]
        ] = []
        self._routines: dict[
            str, dict[str, Any]
        ] = {}
        self._exceptions: list[
            dict[str, Any]
        ] = []
        self._habits: dict[
            str, dict[str, Any]
        ] = {}
        self._min_occurrences = min_occurrences
        self._confidence_threshold = (
            confidence_threshold
        )
        self._counter = 0
        self._stats = {
            "events_recorded": 0,
            "routines_detected": 0,
            "exceptions_found": 0,
            "predictions_made": 0,
        }

        logger.info(
            "RoutineDetector baslatildi",
        )

    def record_event(
        self,
        event_type: str,
        hour: int = 12,
        day_of_week: int = 0,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Olay kaydeder.

        Args:
            event_type: Olay türü.
            hour: Saat (0-23).
            day_of_week: Haftanın günü (0-6).
            metadata: Ek veri.

        Returns:
            Kayıt bilgisi.
        """
        self._counter += 1
        eid = f"evt_{self._counter}"

        event = {
            "event_id": eid,
            "event_type": event_type,
            "hour": hour,
            "day_of_week": day_of_week,
            "metadata": metadata or {},
            "timestamp": time.time(),
        }
        self._events.append(event)
        self._stats["events_recorded"] += 1

        return {
            "event_id": eid,
            "event_type": event_type,
            "recorded": True,
        }

    def detect_daily_patterns(
        self,
    ) -> list[dict[str, Any]]:
        """Günlük kalıpları tespit eder.

        Returns:
            Kalıp listesi.
        """
        hour_events: dict[
            int, dict[str, int]
        ] = {}

        for event in self._events:
            hour = event["hour"]
            etype = event["event_type"]
            if hour not in hour_events:
                hour_events[hour] = {}
            hour_events[hour][etype] = (
                hour_events[hour].get(etype, 0)
                + 1
            )

        patterns = []
        for hour, types in hour_events.items():
            for etype, count in types.items():
                if count >= self._min_occurrences:
                    total_at_hour = sum(
                        types.values(),
                    )
                    confidence = round(
                        count / total_at_hour, 2,
                    )
                    if (
                        confidence
                        >= self._confidence_threshold
                    ):
                        pid = (
                            f"daily_{hour}_{etype}"
                        )
                        pattern = {
                            "pattern_id": pid,
                            "type": "daily",
                            "hour": hour,
                            "event_type": etype,
                            "occurrences": count,
                            "confidence": confidence,
                        }
                        patterns.append(pattern)
                        self._routines[pid] = (
                            pattern
                        )

        self._stats["routines_detected"] = len(
            self._routines,
        )
        return patterns

    def detect_weekly_patterns(
        self,
    ) -> list[dict[str, Any]]:
        """Haftalık kalıpları tespit eder.

        Returns:
            Kalıp listesi.
        """
        day_events: dict[
            int, dict[str, int]
        ] = {}

        for event in self._events:
            day = event["day_of_week"]
            etype = event["event_type"]
            if day not in day_events:
                day_events[day] = {}
            day_events[day][etype] = (
                day_events[day].get(etype, 0) + 1
            )

        patterns = []
        for day, types in day_events.items():
            for etype, count in types.items():
                if count >= self._min_occurrences:
                    total_at_day = sum(
                        types.values(),
                    )
                    confidence = round(
                        count / total_at_day, 2,
                    )
                    if (
                        confidence
                        >= self._confidence_threshold
                    ):
                        pid = (
                            f"weekly_{day}_{etype}"
                        )
                        pattern = {
                            "pattern_id": pid,
                            "type": "weekly",
                            "day_of_week": day,
                            "event_type": etype,
                            "occurrences": count,
                            "confidence": confidence,
                        }
                        patterns.append(pattern)
                        self._routines[pid] = (
                            pattern
                        )

        self._stats["routines_detected"] = len(
            self._routines,
        )
        return patterns

    def detect_exceptions(
        self,
    ) -> list[dict[str, Any]]:
        """İstisnaları tespit eder.

        Returns:
            İstisna listesi.
        """
        exceptions = []

        for event in self._events:
            hour = event["hour"]
            etype = event["event_type"]
            pid = f"daily_{hour}_{etype}"

            # Rutin var mı kontrol et
            routine = self._routines.get(pid)
            if not routine:
                # Bu saat için başka rutin var mı
                for rid, r in (
                    self._routines.items()
                ):
                    if (
                        r.get("type") == "daily"
                        and r.get("hour") == hour
                        and r.get("event_type")
                        != etype
                    ):
                        exception = {
                            "event": event,
                            "expected_routine": rid,
                            "expected_type": r[
                                "event_type"
                            ],
                            "actual_type": etype,
                        }
                        exceptions.append(
                            exception,
                        )
                        break

        self._exceptions = exceptions
        self._stats["exceptions_found"] = len(
            exceptions,
        )
        return exceptions

    def learn_habit(
        self,
        name: str,
        event_type: str,
        hour: int,
        days: list[int] | None = None,
    ) -> dict[str, Any]:
        """Alışkanlık öğrenir.

        Args:
            name: Alışkanlık adı.
            event_type: Olay türü.
            hour: Saat.
            days: Günler.

        Returns:
            Öğrenme bilgisi.
        """
        habit = {
            "name": name,
            "event_type": event_type,
            "hour": hour,
            "days": days or list(range(7)),
            "learned_at": time.time(),
        }
        self._habits[name] = habit

        return {
            "name": name,
            "learned": True,
            "event_type": event_type,
            "hour": hour,
        }

    def predict(
        self,
        hour: int,
        day_of_week: int = 0,
    ) -> dict[str, Any]:
        """Rutin tahmini yapar.

        Args:
            hour: Saat.
            day_of_week: Haftanın günü.

        Returns:
            Tahmin bilgisi.
        """
        self._stats["predictions_made"] += 1

        # Günlük kalıp ara
        for rid, routine in (
            self._routines.items()
        ):
            if (
                routine.get("type") == "daily"
                and routine.get("hour") == hour
            ):
                return {
                    "hour": hour,
                    "day_of_week": day_of_week,
                    "predicted_event": routine[
                        "event_type"
                    ],
                    "confidence": routine[
                        "confidence"
                    ],
                    "source": "daily_pattern",
                }

        # Haftalık kalıp ara
        for rid, routine in (
            self._routines.items()
        ):
            if (
                routine.get("type") == "weekly"
                and routine.get("day_of_week")
                == day_of_week
            ):
                return {
                    "hour": hour,
                    "day_of_week": day_of_week,
                    "predicted_event": routine[
                        "event_type"
                    ],
                    "confidence": routine[
                        "confidence"
                    ],
                    "source": "weekly_pattern",
                }

        # Alışkanlık ara
        for name, habit in self._habits.items():
            if (
                habit["hour"] == hour
                and day_of_week in habit["days"]
            ):
                return {
                    "hour": hour,
                    "day_of_week": day_of_week,
                    "predicted_event": habit[
                        "event_type"
                    ],
                    "confidence": 0.5,
                    "source": f"habit:{name}",
                }

        return {
            "hour": hour,
            "day_of_week": day_of_week,
            "predicted_event": "unknown",
            "confidence": 0.0,
            "source": "none",
        }

    def get_routines(
        self,
        routine_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """Rutinleri getirir.

        Args:
            routine_type: Tür filtresi.

        Returns:
            Rutin listesi.
        """
        results = list(self._routines.values())
        if routine_type:
            results = [
                r for r in results
                if r.get("type") == routine_type
            ]
        return results

    @property
    def routine_count(self) -> int:
        """Rutin sayısı."""
        return self._stats["routines_detected"]

    @property
    def event_count(self) -> int:
        """Olay sayısı."""
        return self._stats["events_recorded"]

    @property
    def exception_count(self) -> int:
        """İstisna sayısı."""
        return self._stats["exceptions_found"]

    @property
    def habit_count(self) -> int:
        """Alışkanlık sayısı."""
        return len(self._habits)
