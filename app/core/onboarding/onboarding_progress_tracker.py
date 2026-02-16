"""ATLAS İlerleme Takipçisi modülü.

Tamamlanma takibi, harcanan zaman,
puan takibi, etkileşim metrikleri,
terk tespiti.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class OnboardingProgressTracker:
    """İlerleme takipçisi.

    Eğitim ilerlemesini takip eder.

    Attributes:
        _progress: İlerleme kayıtları.
        _sessions: Oturum kayıtları.
    """

    def __init__(self) -> None:
        """Takipçiyi başlatır."""
        self._progress: dict[
            str, dict[str, Any]
        ] = {}
        self._sessions: dict[
            str, list[dict[str, Any]]
        ] = {}
        self._stats = {
            "users_tracked": 0,
            "dropouts_detected": 0,
        }

        logger.info(
            "OnboardingProgressTracker "
            "baslatildi",
        )

    def track_completion(
        self,
        user_id: str,
        module_name: str,
        completed: bool = False,
    ) -> dict[str, Any]:
        """Tamamlanma takibi yapar.

        Args:
            user_id: Kullanıcı kimliği.
            module_name: Modül adı.
            completed: Tamamlandı mı.

        Returns:
            Takip bilgisi.
        """
        if user_id not in self._progress:
            self._progress[user_id] = {
                "modules": {},
                "total_completed": 0,
                "total_time_min": 0.0,
                "scores": [],
            }
            self._stats[
                "users_tracked"
            ] += 1

        self._progress[user_id][
            "modules"
        ][module_name] = {
            "completed": completed,
            "timestamp": time.time(),
        }

        if completed:
            self._progress[user_id][
                "total_completed"
            ] += 1

        total = len(
            self._progress[user_id][
                "modules"
            ],
        )
        done = self._progress[user_id][
            "total_completed"
        ]

        return {
            "user_id": user_id,
            "module": module_name,
            "completed": completed,
            "total_modules": total,
            "completed_modules": done,
            "completion_pct": (
                (done / total) * 100
                if total > 0
                else 0.0
            ),
            "tracked": True,
        }

    def record_time_spent(
        self,
        user_id: str,
        module_name: str,
        minutes: float = 0.0,
    ) -> dict[str, Any]:
        """Harcanan zaman kaydeder.

        Args:
            user_id: Kullanıcı kimliği.
            module_name: Modül adı.
            minutes: Dakika.

        Returns:
            Kayıt bilgisi.
        """
        if user_id not in self._sessions:
            self._sessions[user_id] = []

        self._sessions[user_id].append({
            "module": module_name,
            "minutes": minutes,
            "timestamp": time.time(),
        })

        if user_id in self._progress:
            self._progress[user_id][
                "total_time_min"
            ] += minutes

        total = sum(
            s["minutes"]
            for s in self._sessions[user_id]
        )

        return {
            "user_id": user_id,
            "module": module_name,
            "minutes": minutes,
            "total_minutes": total,
            "recorded": True,
        }

    def track_score(
        self,
        user_id: str,
        module_name: str,
        score: float = 0.0,
    ) -> dict[str, Any]:
        """Puan takibi yapar.

        Args:
            user_id: Kullanıcı kimliği.
            module_name: Modül adı.
            score: Puan.

        Returns:
            Takip bilgisi.
        """
        if user_id not in self._progress:
            self._progress[user_id] = {
                "modules": {},
                "total_completed": 0,
                "total_time_min": 0.0,
                "scores": [],
            }

        self._progress[user_id][
            "scores"
        ].append({
            "module": module_name,
            "score": score,
        })

        scores = self._progress[user_id][
            "scores"
        ]
        avg = sum(
            s["score"] for s in scores
        ) / len(scores)

        return {
            "user_id": user_id,
            "module": module_name,
            "score": score,
            "avg_score": avg,
            "tracked": True,
        }

    def get_engagement_metrics(
        self,
        user_id: str,
    ) -> dict[str, Any]:
        """Etkileşim metrikleri verir.

        Args:
            user_id: Kullanıcı kimliği.

        Returns:
            Metrik bilgisi.
        """
        progress = self._progress.get(
            user_id,
        )
        if not progress:
            return {
                "user_id": user_id,
                "found": False,
            }

        sessions = self._sessions.get(
            user_id, [],
        )
        scores = progress.get(
            "scores", [],
        )

        total_time = progress.get(
            "total_time_min", 0.0,
        )
        session_count = len(sessions)
        avg_session = (
            total_time / session_count
            if session_count > 0
            else 0.0
        )
        avg_score = (
            sum(
                s["score"] for s in scores
            ) / len(scores)
            if scores
            else 0.0
        )

        return {
            "user_id": user_id,
            "total_time_min": total_time,
            "session_count": session_count,
            "avg_session_min": avg_session,
            "avg_score": avg_score,
            "modules_completed": (
                progress["total_completed"]
            ),
            "engaged": True,
        }

    def detect_dropout(
        self,
        user_id: str,
        inactive_days: int = 7,
    ) -> dict[str, Any]:
        """Terk tespiti yapar.

        Args:
            user_id: Kullanıcı kimliği.
            inactive_days: İnaktif gün.

        Returns:
            Tespit bilgisi.
        """
        sessions = self._sessions.get(
            user_id, [],
        )

        if not sessions:
            return {
                "user_id": user_id,
                "at_risk": True,
                "reason": "no_sessions",
                "detected": True,
            }

        last = max(
            s["timestamp"]
            for s in sessions
        )
        days_inactive = (
            (time.time() - last) / 86400
        )

        at_risk = (
            days_inactive >= inactive_days
        )

        if at_risk:
            self._stats[
                "dropouts_detected"
            ] += 1

        return {
            "user_id": user_id,
            "at_risk": at_risk,
            "days_inactive": round(
                days_inactive, 1,
            ),
            "threshold": inactive_days,
            "detected": True,
        }

    @property
    def tracked_count(self) -> int:
        """Takip edilen kullanıcı."""
        return self._stats[
            "users_tracked"
        ]

    @property
    def dropout_count(self) -> int:
        """Terk sayısı."""
        return self._stats[
            "dropouts_detected"
        ]
