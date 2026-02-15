"""ATLAS Dongu Izleyici modulu.

Dongu sagligi, tamamlanma oranlari,
ogrenme hizi, geri bildirim kalitesi, bosluk tespiti.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class LoopMonitor:
    """Dongu izleyici.

    Kapali dongu sagligini izler.

    Attributes:
        _loop_records: Dongu kayitlari.
        _health_history: Saglik gecmisi.
    """

    def __init__(self) -> None:
        """Dongu izleyiciyi baslatir."""
        self._loop_records: list[
            dict[str, Any]
        ] = []
        self._health_history: list[
            dict[str, Any]
        ] = []
        self._gaps: list[
            dict[str, Any]
        ] = []
        self._velocity_samples: list[float] = []
        self._quality_samples: list[float] = []
        self._stats = {
            "loops_tracked": 0,
            "completed": 0,
            "incomplete": 0,
            "gaps_detected": 0,
        }

        logger.info(
            "LoopMonitor baslatildi",
        )

    def track_loop(
        self,
        action_id: str,
        stages: dict[str, bool] | None = None,
    ) -> dict[str, Any]:
        """Donguyu izler.

        Args:
            action_id: Aksiyon ID.
            stages: Asama durumu
                (action, outcome, feedback, learn, improve).

        Returns:
            Izleme bilgisi.
        """
        default_stages = {
            "action": False,
            "outcome": False,
            "feedback": False,
            "learn": False,
            "improve": False,
        }
        if stages:
            default_stages.update(stages)

        completed_count = sum(
            1
            for v in default_stages.values()
            if v
        )
        total = len(default_stages)
        completion = completed_count / total

        record = {
            "action_id": action_id,
            "stages": default_stages,
            "completion": round(completion, 2),
            "is_complete": completion == 1.0,
            "tracked_at": time.time(),
        }

        self._loop_records.append(record)
        self._stats["loops_tracked"] += 1

        if record["is_complete"]:
            self._stats["completed"] += 1
        else:
            self._stats["incomplete"] += 1

        return {
            "action_id": action_id,
            "completion": record["completion"],
            "is_complete": record["is_complete"],
            "missing": [
                k
                for k, v in default_stages.items()
                if not v
            ],
        }

    def check_health(self) -> dict[str, Any]:
        """Dongu sagligini kontrol eder.

        Returns:
            Saglik bilgisi.
        """
        total = self._stats["loops_tracked"]
        completed = self._stats["completed"]

        if total == 0:
            health = {
                "status": "no_data",
                "completion_rate": 0.0,
                "score": 0.0,
                "timestamp": time.time(),
            }
            self._health_history.append(health)
            return health

        completion_rate = completed / total

        # Ogrenme hizi
        velocity = self._compute_velocity()

        # Geri bildirim kalitesi
        quality = self._compute_quality()

        score = (
            completion_rate * 0.4
            + velocity * 0.3
            + quality * 0.3
        )

        if score >= 0.8:
            status = "healthy"
        elif score >= 0.5:
            status = "moderate"
        else:
            status = "unhealthy"

        health = {
            "status": status,
            "score": round(score, 3),
            "completion_rate": round(
                completion_rate, 3,
            ),
            "velocity": round(velocity, 3),
            "quality": round(quality, 3),
            "total_loops": total,
            "completed_loops": completed,
            "timestamp": time.time(),
        }

        self._health_history.append(health)
        return health

    def get_completion_rate(self) -> float:
        """Tamamlanma oranini getirir.

        Returns:
            Tamamlanma orani.
        """
        total = self._stats["loops_tracked"]
        if total == 0:
            return 0.0
        return round(
            self._stats["completed"] / total, 3,
        )

    def record_velocity(
        self,
        learnings_per_hour: float,
    ) -> dict[str, Any]:
        """Ogrenme hizini kaydeder.

        Args:
            learnings_per_hour: Saat basina ogrenme.

        Returns:
            Kayit bilgisi.
        """
        self._velocity_samples.append(
            learnings_per_hour,
        )

        return {
            "velocity": learnings_per_hour,
            "avg_velocity": round(
                self._compute_velocity(), 3,
            ),
            "recorded": True,
        }

    def record_quality(
        self,
        quality_score: float,
    ) -> dict[str, Any]:
        """Geri bildirim kalitesini kaydeder.

        Args:
            quality_score: Kalite puani (0.0-1.0).

        Returns:
            Kayit bilgisi.
        """
        quality_score = max(
            0.0, min(1.0, quality_score),
        )
        self._quality_samples.append(quality_score)

        return {
            "quality": quality_score,
            "avg_quality": round(
                self._compute_quality(), 3,
            ),
            "recorded": True,
        }

    def detect_gap(
        self,
        action_id: str,
        missing_stage: str,
        severity: str = "medium",
    ) -> dict[str, Any]:
        """Bosluk tespit eder.

        Args:
            action_id: Aksiyon ID.
            missing_stage: Eksik asama.
            severity: Ciddiyet.

        Returns:
            Bosluk bilgisi.
        """
        gap = {
            "action_id": action_id,
            "missing_stage": missing_stage,
            "severity": severity,
            "detected_at": time.time(),
        }

        self._gaps.append(gap)
        self._stats["gaps_detected"] += 1

        return {
            "action_id": action_id,
            "missing_stage": missing_stage,
            "severity": severity,
            "detected": True,
        }

    def get_gaps(
        self,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Bosluklari getirir.

        Args:
            limit: Limit.

        Returns:
            Bosluk listesi.
        """
        return list(self._gaps[-limit:])

    def get_health_history(
        self,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Saglik gecmisini getirir.

        Args:
            limit: Limit.

        Returns:
            Saglik gecmisi.
        """
        return list(
            self._health_history[-limit:],
        )

    def _compute_velocity(self) -> float:
        """Ogrenme hizini hesaplar.

        Returns:
            Normalize edilmis hiz (0.0-1.0).
        """
        if not self._velocity_samples:
            return 0.0
        recent = self._velocity_samples[-10:]
        avg = sum(recent) / len(recent)
        # 10+ per hour = max velocity
        return min(1.0, avg / 10.0)

    def _compute_quality(self) -> float:
        """Geri bildirim kalitesini hesaplar.

        Returns:
            Ortalama kalite (0.0-1.0).
        """
        if not self._quality_samples:
            return 0.0
        recent = self._quality_samples[-10:]
        return sum(recent) / len(recent)

    @property
    def loop_count(self) -> int:
        """Dongu sayisi."""
        return len(self._loop_records)

    @property
    def gap_count(self) -> int:
        """Bosluk sayisi."""
        return len(self._gaps)
