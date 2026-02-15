"""ATLAS Müsaitlik Öğrenici modülü.

Kullanıcı müsaitlik kalıplarını öğrenme,
zamanlama tespiti, davranış analizi,
anomali yönetimi, tahmin modeli.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class AvailabilityLearner:
    """Müsaitlik öğrenici.

    Kullanıcı müsaitlik kalıplarını öğrenir.

    Attributes:
        _observations: Gözlem kayıtları.
        _patterns: Öğrenilen kalıplar.
    """

    def __init__(
        self,
        learning_rate: float = 0.1,
        min_observations: int = 5,
    ) -> None:
        """Öğreniciyi başlatır.

        Args:
            learning_rate: Öğrenme hızı.
            min_observations: Minimum gözlem sayısı.
        """
        self._observations: list[
            dict[str, Any]
        ] = []
        self._patterns: dict[
            str, dict[str, Any]
        ] = {}
        self._schedules: dict[
            str, dict[str, Any]
        ] = {}
        self._anomalies: list[
            dict[str, Any]
        ] = []
        self._learning_rate = learning_rate
        self._min_observations = min_observations
        self._counter = 0
        self._stats = {
            "observations": 0,
            "patterns_learned": 0,
            "anomalies_detected": 0,
            "predictions_made": 0,
        }

        logger.info(
            "AvailabilityLearner baslatildi",
        )

    def observe(
        self,
        state: str,
        hour: int = 12,
        day_of_week: int = 0,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Müsaitlik gözlemi kaydeder.

        Args:
            state: Müsaitlik durumu.
            hour: Saat (0-23).
            day_of_week: Haftanın günü (0-6).
            context: Ek bağlam.

        Returns:
            Gözlem bilgisi.
        """
        self._counter += 1
        oid = f"obs_{self._counter}"

        observation = {
            "observation_id": oid,
            "state": state,
            "hour": hour,
            "day_of_week": day_of_week,
            "context": context or {},
            "timestamp": time.time(),
        }
        self._observations.append(observation)
        self._stats["observations"] += 1

        # Anomali kontrolü
        if self._is_anomaly(
            state, hour, day_of_week,
        ):
            self._anomalies.append(observation)
            self._stats["anomalies_detected"] += 1

        # Yeterli gözlem varsa kalıp öğren
        if (
            len(self._observations)
            >= self._min_observations
        ):
            self._learn_patterns()

        return {
            "observation_id": oid,
            "state": state,
            "hour": hour,
            "day_of_week": day_of_week,
            "recorded": True,
        }

    def _is_anomaly(
        self,
        state: str,
        hour: int,
        day_of_week: int,
    ) -> bool:
        """Anomali tespiti yapar."""
        key = f"h{hour}_d{day_of_week}"
        pattern = self._patterns.get(key)
        if not pattern:
            return False
        return (
            pattern.get("expected_state") != state
            and pattern.get("confidence", 0) > 0.7
        )

    def _learn_patterns(self) -> None:
        """Kalıpları öğrenir."""
        hour_states: dict[
            str, dict[str, int]
        ] = {}

        for obs in self._observations:
            key = (
                f"h{obs['hour']}"
                f"_d{obs['day_of_week']}"
            )
            if key not in hour_states:
                hour_states[key] = {}
            state = obs["state"]
            hour_states[key][state] = (
                hour_states[key].get(state, 0) + 1
            )

        for key, states in hour_states.items():
            total = sum(states.values())
            if total < 2:
                continue
            best_state = max(
                states, key=states.get,
            )
            confidence = states[best_state] / total

            self._patterns[key] = {
                "expected_state": best_state,
                "confidence": round(confidence, 2),
                "sample_count": total,
            }

        self._stats["patterns_learned"] = len(
            self._patterns,
        )

    def detect_schedule(
        self,
        user_id: str = "default",
    ) -> dict[str, Any]:
        """Zamanlama tespiti yapar.

        Args:
            user_id: Kullanıcı ID.

        Returns:
            Zamanlama bilgisi.
        """
        if not self._patterns:
            return {
                "user_id": user_id,
                "schedule_detected": False,
                "reason": "insufficient_data",
            }

        # Aktif saatleri bul
        active_hours = []
        busy_hours = []
        for key, pattern in (
            self._patterns.items()
        ):
            hour = int(
                key.split("_")[0].replace("h", ""),
            )
            state = pattern["expected_state"]
            if state == "available":
                active_hours.append(hour)
            elif state in ("busy", "dnd"):
                busy_hours.append(hour)

        schedule = {
            "user_id": user_id,
            "schedule_detected": True,
            "active_hours": sorted(
                set(active_hours),
            ),
            "busy_hours": sorted(
                set(busy_hours),
            ),
            "pattern_count": len(self._patterns),
        }
        self._schedules[user_id] = schedule

        return schedule

    def analyze_behavior(
        self,
        user_id: str = "default",
    ) -> dict[str, Any]:
        """Davranış analizi yapar.

        Args:
            user_id: Kullanıcı ID.

        Returns:
            Analiz bilgisi.
        """
        if not self._observations:
            return {
                "user_id": user_id,
                "analyzed": False,
            }

        state_counts: dict[str, int] = {}
        for obs in self._observations:
            s = obs["state"]
            state_counts[s] = (
                state_counts.get(s, 0) + 1
            )

        total = len(self._observations)
        dominant_state = max(
            state_counts, key=state_counts.get,
        )
        availability_rate = round(
            state_counts.get("available", 0)
            / total
            * 100,
            1,
        )

        return {
            "user_id": user_id,
            "analyzed": True,
            "total_observations": total,
            "state_distribution": state_counts,
            "dominant_state": dominant_state,
            "availability_rate": availability_rate,
            "anomaly_count": len(self._anomalies),
        }

    def predict(
        self,
        hour: int,
        day_of_week: int = 0,
    ) -> dict[str, Any]:
        """Müsaitlik tahmini yapar.

        Args:
            hour: Saat (0-23).
            day_of_week: Haftanın günü.

        Returns:
            Tahmin bilgisi.
        """
        self._stats["predictions_made"] += 1

        key = f"h{hour}_d{day_of_week}"
        pattern = self._patterns.get(key)

        if pattern:
            return {
                "hour": hour,
                "day_of_week": day_of_week,
                "predicted_state": pattern[
                    "expected_state"
                ],
                "confidence": pattern[
                    "confidence"
                ],
                "based_on": pattern[
                    "sample_count"
                ],
            }

        return {
            "hour": hour,
            "day_of_week": day_of_week,
            "predicted_state": "unknown",
            "confidence": 0.0,
            "based_on": 0,
        }

    def get_anomalies(
        self,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Anomalileri getirir.

        Args:
            limit: Maks kayıt.

        Returns:
            Anomali listesi.
        """
        return list(self._anomalies[-limit:])

    @property
    def observation_count(self) -> int:
        """Gözlem sayısı."""
        return self._stats["observations"]

    @property
    def pattern_count(self) -> int:
        """Kalıp sayısı."""
        return self._stats["patterns_learned"]

    @property
    def anomaly_count(self) -> int:
        """Anomali sayısı."""
        return self._stats[
            "anomalies_detected"
        ]

    @property
    def prediction_count(self) -> int:
        """Tahmin sayısı."""
        return self._stats["predictions_made"]
