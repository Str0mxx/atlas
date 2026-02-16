"""
Wellness orkestratör modülü.

Tam wellness yönetimi, Track→Remind→Suggest→Report,
bütünsel sağlık ve analitik.
"""

import logging
from typing import Any

from app.core.wellness.exercise_suggester import (
    ExerciseSuggester,
)
from app.core.wellness.health_report_generator import (
    HealthReportGenerator,
)
from app.core.wellness.meal_planner import (
    MealPlanner,
)
from app.core.wellness.medical_appointment_tracker import (
    MedicalAppointmentTracker,
)
from app.core.wellness.medication_tracker import (
    MedicationTracker,
)
from app.core.wellness.sleep_analyzer import (
    SleepAnalyzer,
)
from app.core.wellness.stress_estimator import (
    StressEstimator,
)
from app.core.wellness.wellness_reminder import (
    WellnessReminder,
)

logger = logging.getLogger(__name__)


class WellnessOrchestrator:
    """Wellness orkestratör.

    Attributes:
        _reminder: Hatırlatıcı.
        _exercise: Egzersiz öneri.
        _sleep: Uyku analiz.
        _meal: Öğün planlama.
        _appointment: Randevu takip.
        _stress: Stres tahmin.
        _report: Rapor üretici.
        _medication: İlaç takip.
    """

    def __init__(self) -> None:
        """Orkestratörü başlatır."""
        self._reminder = WellnessReminder()
        self._exercise = ExerciseSuggester()
        self._sleep = SleepAnalyzer()
        self._meal = MealPlanner()
        self._appointment = (
            MedicalAppointmentTracker()
        )
        self._stress = StressEstimator()
        self._report = HealthReportGenerator()
        self._medication = MedicationTracker()
        logger.info(
            "WellnessOrchestrator baslatildi"
        )

    def full_wellness_check(
        self,
        sleep_hours: float = 7.0,
        exercise_min: int = 30,
        stress_score: float = 40.0,
        water_glasses: int = 8,
        calories: int = 2000,
    ) -> dict[str, Any]:
        """Tam wellness kontrolü yapar.

        Track → Remind → Suggest → Report.

        Args:
            sleep_hours: Uyku süresi.
            exercise_min: Egzersiz dakikası.
            stress_score: Stres puanı.
            water_glasses: Su bardak sayısı.
            calories: Günlük kalori.

        Returns:
            Tam wellness raporu.
        """
        try:
            sleep = self._sleep.log_sleep(
                hours=sleep_hours,
                deep_sleep_pct=20.0,
            )

            exercise = (
                self._exercise.suggest_workout(
                    duration_min=exercise_min,
                )
            )

            stress = (
                self._stress.calculate_stress_score(
                    sleep_hours=sleep_hours,
                    exercise_min=exercise_min,
                    workload_score=stress_score,
                )
            )

            nutrition = (
                self._meal.count_calories(
                    consumed=calories,
                )
            )

            report = (
                self._report.generate_weekly_summary(
                    sleep_avg=sleep_hours,
                    exercise_min=exercise_min,
                    calories_avg=calories,
                    stress_avg=stress_score,
                    water_glasses=water_glasses,
                )
            )

            return {
                "sleep": sleep,
                "exercise": exercise,
                "stress": stress,
                "nutrition": nutrition,
                "report": report,
                "completed": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "completed": False,
                "error": str(e),
            }

    def daily_briefing(
        self,
    ) -> dict[str, Any]:
        """Günlük wellness brifingi.

        Returns:
            Günlük özet.
        """
        try:
            reminders = (
                self._reminder.reminder_count
            )
            sleep_patterns = (
                self._sleep.analyze_patterns()
            )
            stress_patterns = (
                self._stress.detect_patterns()
            )
            medications = (
                self._medication.check_refill()
            )

            return {
                "active_reminders": reminders,
                "sleep": sleep_patterns,
                "stress": stress_patterns,
                "medications": medications,
                "briefed": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "briefed": False,
                "error": str(e),
            }

    def get_analytics(
        self,
    ) -> dict[str, Any]:
        """Wellness analitiklerini getirir.

        Returns:
            Analitik verileri.
        """
        try:
            return {
                "reminders": (
                    self._reminder.reminder_count
                ),
                "exercises": (
                    self._exercise.exercise_count
                ),
                "sleep_records": (
                    self._sleep.record_count
                ),
                "meals": (
                    self._meal.meal_count
                ),
                "appointments": (
                    self._appointment.appointment_count
                ),
                "stress_readings": (
                    self._stress.reading_count
                ),
                "reports": (
                    self._report.report_count
                ),
                "medications": (
                    self._medication.medication_count
                ),
                "components": 8,
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }
