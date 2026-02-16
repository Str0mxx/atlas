"""
Stres tahmin modülü.

İş yükü analizi, patern tespiti, stres
puanlama, uyarı alarmları, başa çıkma önerileri.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class StressEstimator:
    """Stres tahmin motoru.

    Attributes:
        _readings: Stres okumaları.
        _stats: İstatistikler.
    """

    def __init__(self) -> None:
        """Tahmin motorunu başlatır."""
        self._readings: list[dict] = []
        self._stats: dict[str, int] = {
            "readings_taken": 0,
        }
        logger.info(
            "StressEstimator baslatildi"
        )

    @property
    def reading_count(self) -> int:
        """Okuma sayısı."""
        return len(self._readings)

    def analyze_workload(
        self,
        tasks_count: int = 0,
        hours_worked: float = 8.0,
        deadlines_soon: int = 0,
    ) -> dict[str, Any]:
        """İş yükü analizi yapar.

        Args:
            tasks_count: Görev sayısı.
            hours_worked: Çalışılan saat.
            deadlines_soon: Yaklaşan son teslim.

        Returns:
            İş yükü analizi.
        """
        try:
            workload_score = min(
                tasks_count * 5
                + hours_worked * 3
                + deadlines_soon * 15,
                100.0,
            )

            if workload_score >= 80:
                level = "overloaded"
            elif workload_score >= 60:
                level = "heavy"
            elif workload_score >= 40:
                level = "moderate"
            elif workload_score >= 20:
                level = "light"
            else:
                level = "minimal"

            reading = {
                "type": "workload",
                "score": workload_score,
                "level": level,
            }
            self._readings.append(reading)
            self._stats["readings_taken"] += 1

            return {
                "tasks_count": tasks_count,
                "hours_worked": hours_worked,
                "deadlines_soon": deadlines_soon,
                "workload_score": workload_score,
                "level": level,
                "analyzed": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "analyzed": False,
                "error": str(e),
            }

    def detect_patterns(
        self,
    ) -> dict[str, Any]:
        """Stres paternlerini tespit eder.

        Returns:
            Patern bilgisi.
        """
        try:
            if not self._readings:
                return {
                    "pattern": "no_data",
                    "readings": 0,
                    "detected": True,
                }

            scores = [
                r["score"]
                for r in self._readings
            ]
            avg = sum(scores) / len(scores)
            high_count = sum(
                1 for s in scores if s >= 60
            )

            if high_count > len(scores) * 0.7:
                pattern = "chronic_high"
            elif high_count > len(scores) * 0.3:
                pattern = "intermittent"
            elif avg < 30:
                pattern = "consistently_low"
            else:
                pattern = "variable"

            return {
                "avg_score": round(avg, 1),
                "high_stress_count": high_count,
                "total_readings": len(scores),
                "pattern": pattern,
                "detected": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "detected": False,
                "error": str(e),
            }

    def calculate_stress_score(
        self,
        sleep_hours: float = 7.0,
        exercise_min: int = 30,
        social_score: int = 5,
        workload_score: float = 50.0,
    ) -> dict[str, Any]:
        """Stres puanı hesaplar.

        Args:
            sleep_hours: Uyku süresi.
            exercise_min: Egzersiz dakikası.
            social_score: Sosyal puan (1-10).
            workload_score: İş yükü puanı.

        Returns:
            Stres puanı.
        """
        try:
            sleep_factor = max(
                0, (8 - sleep_hours) * 8
            )
            exercise_factor = max(
                0, (30 - exercise_min) * 0.5
            )
            social_factor = max(
                0, (5 - social_score) * 5
            )
            work_factor = workload_score * 0.4

            stress = min(
                sleep_factor
                + exercise_factor
                + work_factor
                + social_factor,
                100.0,
            )

            if stress >= 80:
                level = "severe"
            elif stress >= 60:
                level = "high"
            elif stress >= 40:
                level = "moderate"
            elif stress >= 20:
                level = "low"
            else:
                level = "minimal"

            reading = {
                "type": "composite",
                "score": stress,
                "level": level,
            }
            self._readings.append(reading)
            self._stats["readings_taken"] += 1

            return {
                "stress_score": round(
                    stress, 1
                ),
                "level": level,
                "factors": {
                    "sleep": round(
                        sleep_factor, 1
                    ),
                    "exercise": round(
                        exercise_factor, 1
                    ),
                    "social": round(
                        social_factor, 1
                    ),
                    "workload": round(
                        work_factor, 1
                    ),
                },
                "calculated": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "calculated": False,
                "error": str(e),
            }

    def check_warnings(
        self,
        stress_score: float = 0.0,
        consecutive_high: int = 0,
    ) -> dict[str, Any]:
        """Stres uyarılarını kontrol eder.

        Args:
            stress_score: Stres puanı.
            consecutive_high: Ardışık yüksek gün.

        Returns:
            Uyarı bilgisi.
        """
        try:
            warnings = []

            if stress_score >= 80:
                warnings.append({
                    "type": "critical_stress",
                    "severity": "critical",
                })
            elif stress_score >= 60:
                warnings.append({
                    "type": "high_stress",
                    "severity": "warning",
                })

            if consecutive_high >= 7:
                warnings.append({
                    "type": "chronic_stress",
                    "severity": "critical",
                })
            elif consecutive_high >= 3:
                warnings.append({
                    "type": "sustained_stress",
                    "severity": "warning",
                })

            if warnings:
                alert_level = "red" if any(
                    w["severity"] == "critical"
                    for w in warnings
                ) else "yellow"
            else:
                alert_level = "green"

            return {
                "stress_score": stress_score,
                "consecutive_high": (
                    consecutive_high
                ),
                "warnings": warnings,
                "warning_count": len(warnings),
                "alert_level": alert_level,
                "checked": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "checked": False,
                "error": str(e),
            }

    def suggest_coping(
        self,
        stress_level: str = "moderate",
    ) -> dict[str, Any]:
        """Başa çıkma önerileri verir.

        Args:
            stress_level: Stres seviyesi.

        Returns:
            Öneri listesi.
        """
        try:
            base_suggestions = [
                "deep_breathing",
                "short_walk",
            ]

            level_suggestions = {
                "minimal": [],
                "low": ["mindfulness"],
                "moderate": [
                    "mindfulness",
                    "exercise",
                ],
                "high": [
                    "mindfulness",
                    "exercise",
                    "talk_to_someone",
                    "take_break",
                ],
                "severe": [
                    "mindfulness",
                    "exercise",
                    "professional_help",
                    "immediate_break",
                    "reduce_workload",
                ],
            }

            extras = level_suggestions.get(
                stress_level, []
            )
            all_suggestions = (
                base_suggestions + extras
            )

            return {
                "stress_level": stress_level,
                "suggestions": all_suggestions,
                "suggestion_count": len(
                    all_suggestions
                ),
                "urgent": stress_level in (
                    "high",
                    "severe",
                ),
                "suggested": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "suggested": False,
                "error": str(e),
            }
