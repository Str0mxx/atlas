"""Health & Wellness Tracker testleri."""

import pytest

from app.core.wellness import (
    ExerciseSuggester,
    HealthReportGenerator,
    MealPlanner,
    MedicalAppointmentTracker,
    MedicationTracker,
    SleepAnalyzer,
    StressEstimator,
    WellnessOrchestrator,
    WellnessReminder,
)
from app.models.wellness_models import (
    AppointmentRecord,
    ExerciseLevel,
    MealType,
    MedicationFrequency,
    MedicationRecord,
    ReminderType,
    SleepQuality,
    SleepRecord,
    StressLevel,
    WellnessReminderRecord,
)


# ── Models ──────────────────────────────────────


class TestWellnessModels:
    """Wellness model testleri."""

    def test_reminder_type_values(self):
        assert ReminderType.hydration == "hydration"
        assert ReminderType.posture == "posture"
        assert ReminderType.break_time == "break_time"
        assert ReminderType.stretch == "stretch"
        assert ReminderType.medication == "medication"
        assert ReminderType.custom == "custom"

    def test_exercise_level_values(self):
        assert ExerciseLevel.beginner == "beginner"
        assert ExerciseLevel.intermediate == "intermediate"
        assert ExerciseLevel.advanced == "advanced"
        assert ExerciseLevel.expert == "expert"

    def test_sleep_quality_values(self):
        assert SleepQuality.excellent == "excellent"
        assert SleepQuality.good == "good"
        assert SleepQuality.fair == "fair"
        assert SleepQuality.poor == "poor"
        assert SleepQuality.very_poor == "very_poor"

    def test_meal_type_values(self):
        assert MealType.breakfast == "breakfast"
        assert MealType.lunch == "lunch"
        assert MealType.dinner == "dinner"
        assert MealType.snack == "snack"
        assert MealType.pre_workout == "pre_workout"
        assert MealType.post_workout == "post_workout"

    def test_stress_level_values(self):
        assert StressLevel.minimal == "minimal"
        assert StressLevel.low == "low"
        assert StressLevel.moderate == "moderate"
        assert StressLevel.high == "high"
        assert StressLevel.severe == "severe"

    def test_medication_frequency_values(self):
        assert MedicationFrequency.once_daily == "once_daily"
        assert MedicationFrequency.twice_daily == "twice_daily"
        assert MedicationFrequency.weekly == "weekly"
        assert MedicationFrequency.as_needed == "as_needed"
        assert MedicationFrequency.monthly == "monthly"

    def test_wellness_reminder_record(self):
        r = WellnessReminderRecord()
        assert r.reminder_type == "hydration"
        assert r.interval_minutes == 60
        assert r.active is True
        assert len(r.reminder_id) == 8

    def test_sleep_record(self):
        r = SleepRecord(hours=7.5, quality="good")
        assert r.hours == 7.5
        assert r.quality == "good"
        assert len(r.sleep_id) == 8

    def test_appointment_record(self):
        r = AppointmentRecord(
            doctor="Dr. Smith",
            specialty="cardiology",
        )
        assert r.doctor == "Dr. Smith"
        assert r.specialty == "cardiology"
        assert r.status == "scheduled"

    def test_medication_record(self):
        r = MedicationRecord(
            name="Aspirin",
            dosage="100mg",
        )
        assert r.name == "Aspirin"
        assert r.dosage == "100mg"
        assert r.frequency == "once_daily"
        assert r.active is True


# ── WellnessReminder ───────────────────────────


class TestWellnessReminder:
    """WellnessReminder testleri."""

    def setup_method(self):
        self.wr = WellnessReminder()

    def test_init(self):
        assert self.wr.reminder_count == 0

    def test_add_hydration(self):
        r = self.wr.add_hydration()
        assert r["added"] is True
        assert r["type"] == "hydration"
        assert r["interval_min"] == 60
        assert r["daily_glasses"] == 10
        assert self.wr.reminder_count == 1

    def test_add_hydration_custom(self):
        r = self.wr.add_hydration(
            interval_min=45, daily_goal_ml=2000
        )
        assert r["daily_glasses"] == 8

    def test_add_posture_check(self):
        r = self.wr.add_posture_check()
        assert r["added"] is True
        assert r["type"] == "posture"
        assert len(r["tips"]) == 3

    def test_add_break_reminder(self):
        r = self.wr.add_break_reminder()
        assert r["added"] is True
        assert r["type"] == "break_time"
        assert r["daily_breaks"] == 8

    def test_add_stretch_prompt(self):
        r = self.wr.add_stretch_prompt()
        assert r["added"] is True
        assert r["type"] == "stretch"
        assert r["stretch_count"] == 4

    def test_add_custom_reminder(self):
        r = self.wr.add_custom_reminder(
            name="Vitamins", message="Take vitamins"
        )
        assert r["added"] is True
        assert r["type"] == "custom"
        assert r["name"] == "Vitamins"

    def test_multiple_reminders(self):
        self.wr.add_hydration()
        self.wr.add_posture_check()
        self.wr.add_break_reminder()
        assert self.wr.reminder_count == 3


# ── ExerciseSuggester ──────────────────────────


class TestExerciseSuggester:
    """ExerciseSuggester testleri."""

    def setup_method(self):
        self.es = ExerciseSuggester()

    def test_init(self):
        assert self.es.exercise_count == 0

    def test_suggest_workout(self):
        r = self.es.suggest_workout()
        assert r["suggested"] is True
        assert r["level"] == "beginner"
        assert r["focus"] == "full_body"
        assert r["sets"] == 2
        assert len(r["exercises"]) == 4

    def test_suggest_cardio(self):
        r = self.es.suggest_workout(
            level="advanced", focus="cardio"
        )
        assert r["sets"] == 4
        assert "burpees" in r["exercises"]

    def test_estimated_calories(self):
        r = self.es.suggest_workout(
            duration_min=30
        )
        assert r["estimated_calories"] == 30 * 2 * 3

    def test_adapt_difficulty_level_up(self):
        r = self.es.adapt_difficulty(
            "beginner", 95.0
        )
        assert r["adapted"] is True
        assert r["new_level"] == "intermediate"
        assert r["action"] == "level_up"

    def test_adapt_difficulty_level_down(self):
        r = self.es.adapt_difficulty(
            "intermediate", 30.0
        )
        assert r["new_level"] == "beginner"
        assert r["action"] == "level_down"

    def test_adapt_difficulty_maintain(self):
        r = self.es.adapt_difficulty(
            "advanced", 70.0
        )
        assert r["new_level"] == "advanced"
        assert r["action"] == "maintain"

    def test_adapt_expert_cap(self):
        r = self.es.adapt_difficulty(
            "expert", 95.0
        )
        assert r["new_level"] == "expert"

    def test_time_based_5min(self):
        r = self.es.time_based_options(5)
        assert r["generated"] is True
        assert r["option_count"] == 1

    def test_time_based_60min(self):
        r = self.es.time_based_options(60)
        assert r["option_count"] == 4

    def test_check_equipment_none(self):
        r = self.es.check_equipment()
        assert r["checked"] is True
        assert r["equipment_level"] == "bodyweight_only"

    def test_check_equipment_full(self):
        r = self.es.check_equipment([
            "dumbbells", "resistance_band",
            "yoga_mat", "pull_up_bar",
            "kettlebell", "jump_rope",
        ])
        assert r["equipment_level"] == "well_equipped"
        assert r["coverage_pct"] == 100.0

    def test_check_equipment_basic(self):
        r = self.es.check_equipment(
            ["yoga_mat", "dumbbells"]
        )
        assert r["equipment_level"] == "basic"

    def test_track_progress_starter(self):
        r = self.es.track_progress(
            exercises_done=3, streak_days=2
        )
        assert r["tracked"] is True
        assert r["badge"] == "starter"

    def test_track_progress_gold(self):
        r = self.es.track_progress(
            streak_days=30, total_minutes=150
        )
        assert r["badge"] == "gold"
        assert r["weekly_progress_pct"] == 100.0

    def test_track_progress_silver(self):
        r = self.es.track_progress(streak_days=14)
        assert r["badge"] == "silver"

    def test_track_progress_bronze(self):
        r = self.es.track_progress(streak_days=7)
        assert r["badge"] == "bronze"


# ── SleepAnalyzer ──────────────────────────────


class TestSleepAnalyzer:
    """SleepAnalyzer testleri."""

    def setup_method(self):
        self.sa = SleepAnalyzer()

    def test_init(self):
        assert self.sa.record_count == 0

    def test_log_sleep_excellent(self):
        r = self.sa.log_sleep(
            hours=8.0, deep_sleep_pct=25.0, interruptions=0
        )
        assert r["logged"] is True
        assert r["quality"] == "excellent"
        assert r["score"] >= 85

    def test_log_sleep_poor(self):
        r = self.sa.log_sleep(
            hours=4.0, deep_sleep_pct=10.0, interruptions=3
        )
        assert r["quality"] == "poor"

    def test_log_sleep_very_poor(self):
        r = self.sa.log_sleep(
            hours=2.0, deep_sleep_pct=5.0, interruptions=3
        )
        assert r["quality"] == "very_poor"

    def test_analyze_patterns_no_data(self):
        r = self.sa.analyze_patterns()
        assert r["analyzed"] is True
        assert r["pattern"] == "no_data"

    def test_analyze_patterns_healthy(self):
        for _ in range(3):
            self.sa.log_sleep(
                hours=8.0, deep_sleep_pct=25.0
            )
        r = self.sa.analyze_patterns()
        assert r["pattern"] == "healthy"

    def test_analyze_patterns_insufficient(self):
        for _ in range(3):
            self.sa.log_sleep(
                hours=4.5, deep_sleep_pct=10.0,
                interruptions=2,
            )
        r = self.sa.analyze_patterns()
        assert r["pattern"] == "insufficient"

    def test_score_quality(self):
        r = self.sa.score_quality(hours=5.0)
        assert r["scored"] is True
        assert "short_duration" in r["factors"]

    def test_score_quality_oversleeping(self):
        r = self.sa.score_quality(hours=10.0)
        assert "oversleeping" in r["factors"]

    def test_score_low_deep(self):
        r = self.sa.score_quality(
            deep_sleep_pct=10.0
        )
        assert "low_deep_sleep" in r["factors"]

    def test_score_frequent_interruptions(self):
        r = self.sa.score_quality(
            interruptions=5
        )
        assert "frequent_interruptions" in r["factors"]

    def test_get_recommendations_short(self):
        r = self.sa.get_recommendations(
            avg_hours=5.0, avg_score=40.0
        )
        assert r["generated"] is True
        assert "increase_sleep_duration" in r["recommendations"]
        assert "improve_sleep_hygiene" in r["recommendations"]

    def test_get_recommendations_good(self):
        r = self.sa.get_recommendations(
            avg_hours=8.0, avg_score=85.0
        )
        assert "increase_sleep_duration" not in r["recommendations"]

    def test_detect_trends_insufficient(self):
        r = self.sa.detect_trends()
        assert r["trend"] == "insufficient_data"

    def test_detect_trends_improving(self):
        self.sa.log_sleep(hours=5.0, deep_sleep_pct=10.0)
        self.sa.log_sleep(hours=5.5, deep_sleep_pct=12.0)
        self.sa.log_sleep(hours=8.0, deep_sleep_pct=25.0)
        self.sa.log_sleep(hours=8.0, deep_sleep_pct=25.0)
        r = self.sa.detect_trends()
        assert r["trend"] == "improving"

    def test_detect_trends_declining(self):
        self.sa.log_sleep(hours=8.0, deep_sleep_pct=25.0)
        self.sa.log_sleep(hours=8.0, deep_sleep_pct=25.0)
        self.sa.log_sleep(hours=4.0, deep_sleep_pct=5.0, interruptions=3)
        self.sa.log_sleep(hours=4.0, deep_sleep_pct=5.0, interruptions=3)
        r = self.sa.detect_trends()
        assert r["trend"] == "declining"


# ── MealPlanner ────────────────────────────────


class TestMealPlanner:
    """MealPlanner testleri."""

    def setup_method(self):
        self.mp = MealPlanner()

    def test_init(self):
        assert self.mp.meal_count == 0

    def test_suggest_meal(self):
        r = self.mp.suggest_meal()
        assert r["suggested"] is True
        assert r["meal_type"] == "lunch"
        assert r["option_count"] == 3

    def test_suggest_breakfast(self):
        r = self.mp.suggest_meal(
            meal_type="breakfast"
        )
        assert "oatmeal_fruit" in r["options"]

    def test_suggest_snack(self):
        r = self.mp.suggest_meal(
            meal_type="snack"
        )
        assert "fresh_fruit" in r["options"]

    def test_track_nutrition_optimal(self):
        r = self.mp.track_nutrition(
            calories=500,
            protein_g=30.0,
            carbs_g=50.0,
            fat_g=20.0,
        )
        assert r["tracked"] is True
        assert r["balance"] == "optimal"

    def test_track_nutrition_high_protein(self):
        r = self.mp.track_nutrition(
            protein_g=60.0, carbs_g=20.0, fat_g=10.0
        )
        assert r["balance"] == "high_protein"

    def test_track_nutrition_high_carb(self):
        r = self.mp.track_nutrition(
            protein_g=10.0, carbs_g=80.0, fat_g=10.0
        )
        assert r["balance"] == "high_carb"

    def test_track_nutrition_high_fat(self):
        r = self.mp.track_nutrition(
            protein_g=10.0, carbs_g=10.0, fat_g=50.0
        )
        assert r["balance"] == "high_fat"

    def test_track_nutrition_zero(self):
        r = self.mp.track_nutrition()
        assert r["protein_pct"] == 0.0

    def test_count_calories_on_track(self):
        r = self.mp.count_calories(
            daily_target=2000, consumed=1200
        )
        assert r["counted"] is True
        assert r["status"] == "on_track"
        assert r["remaining"] == 800

    def test_count_calories_over(self):
        r = self.mp.count_calories(
            daily_target=2000, consumed=2200
        )
        assert r["status"] == "over_limit"

    def test_count_calories_near(self):
        r = self.mp.count_calories(
            daily_target=2000, consumed=1700
        )
        assert r["status"] == "near_limit"

    def test_count_calories_under(self):
        r = self.mp.count_calories(
            daily_target=2000, consumed=500
        )
        assert r["status"] == "under_target"

    def test_set_diet_goal_maintain(self):
        r = self.mp.set_diet_goal()
        assert r["set"] is True
        assert r["daily_calories"] == 2000
        assert r["adjustment"] == 0

    def test_set_diet_goal_lose(self):
        r = self.mp.set_diet_goal(
            goal_type="lose_weight"
        )
        assert r["daily_calories"] == 1500

    def test_set_diet_goal_gain(self):
        r = self.mp.set_diet_goal(
            goal_type="gain_weight"
        )
        assert r["daily_calories"] == 2500

    def test_get_recipe_ideas_short(self):
        r = self.mp.get_recipe_ideas(max_time_min=10)
        assert r["generated"] is True
        assert r["recipe_count"] == 1

    def test_get_recipe_ideas_long(self):
        r = self.mp.get_recipe_ideas(max_time_min=45)
        assert r["recipe_count"] == 4


# ── MedicalAppointmentTracker ──────────────────


class TestMedicalAppointmentTracker:
    """MedicalAppointmentTracker testleri."""

    def setup_method(self):
        self.mat = MedicalAppointmentTracker()

    def test_init(self):
        assert self.mat.appointment_count == 0

    def test_schedule_appointment(self):
        r = self.mat.schedule_appointment(
            doctor="Dr. Smith",
            specialty="cardiology",
            date="2026-03-01",
        )
        assert r["scheduled"] is True
        assert r["doctor"] == "Dr. Smith"
        assert r["status"] == "scheduled"

    def test_set_reminder(self):
        a = self.mat.schedule_appointment(
            doctor="Dr. A"
        )
        r = self.mat.set_reminder(
            appointment_id=a["appointment_id"],
            days_before=3,
        )
        assert r["set"] is True
        assert r["days_before"] == 3

    def test_set_reminder_not_found(self):
        r = self.mat.set_reminder(
            appointment_id="invalid"
        )
        assert r["set"] is False

    def test_add_doctor(self):
        r = self.mat.add_doctor(
            name="Dr. Brown",
            specialty="dermatology",
            hospital="City Hospital",
        )
        assert r["added"] is True
        assert r["name"] == "Dr. Brown"

    def test_get_history_empty(self):
        r = self.mat.get_history()
        assert r["retrieved"] is True
        assert r["total"] == 0

    def test_get_history_filtered(self):
        self.mat.schedule_appointment(
            specialty="cardiology"
        )
        self.mat.schedule_appointment(
            specialty="dermatology"
        )
        r = self.mat.get_history(
            specialty="cardiology"
        )
        assert r["total"] == 1

    def test_manage_documents(self):
        a = self.mat.schedule_appointment(
            doctor="Dr. X"
        )
        r = self.mat.manage_documents(
            appointment_id=a["appointment_id"],
            document_type="lab_result",
            document_name="blood_test.pdf",
        )
        assert r["managed"] is True
        assert r["total_docs"] == 1

    def test_manage_documents_not_found(self):
        r = self.mat.manage_documents(
            appointment_id="invalid"
        )
        assert r["managed"] is False


# ── StressEstimator ────────────────────────────


class TestStressEstimator:
    """StressEstimator testleri."""

    def setup_method(self):
        self.se = StressEstimator()

    def test_init(self):
        assert self.se.reading_count == 0

    def test_analyze_workload_minimal(self):
        r = self.se.analyze_workload(
            tasks_count=1, hours_worked=2.0
        )
        assert r["analyzed"] is True
        assert r["level"] == "minimal"

    def test_analyze_workload_overloaded(self):
        r = self.se.analyze_workload(
            tasks_count=10, hours_worked=12.0,
            deadlines_soon=3,
        )
        assert r["level"] == "overloaded"

    def test_detect_patterns_no_data(self):
        r = self.se.detect_patterns()
        assert r["pattern"] == "no_data"

    def test_detect_patterns_chronic(self):
        for _ in range(5):
            self.se.analyze_workload(
                tasks_count=10, hours_worked=12.0,
                deadlines_soon=3,
            )
        r = self.se.detect_patterns()
        assert r["pattern"] == "chronic_high"

    def test_detect_patterns_low(self):
        for _ in range(5):
            self.se.analyze_workload(
                tasks_count=1, hours_worked=2.0,
            )
        r = self.se.detect_patterns()
        assert r["pattern"] == "consistently_low"

    def test_calculate_stress_low(self):
        r = self.se.calculate_stress_score(
            sleep_hours=8.0, exercise_min=30,
            social_score=7, workload_score=20.0,
        )
        assert r["calculated"] is True
        assert r["level"] == "minimal" or r["level"] == "low"

    def test_calculate_stress_high(self):
        r = self.se.calculate_stress_score(
            sleep_hours=4.0, exercise_min=0,
            social_score=1, workload_score=90.0,
        )
        assert r["level"] in ("high", "severe")

    def test_check_warnings_green(self):
        r = self.se.check_warnings(
            stress_score=30.0
        )
        assert r["checked"] is True
        assert r["alert_level"] == "green"
        assert r["warning_count"] == 0

    def test_check_warnings_critical(self):
        r = self.se.check_warnings(
            stress_score=85.0, consecutive_high=8
        )
        assert r["alert_level"] == "red"
        assert r["warning_count"] >= 2

    def test_check_warnings_yellow(self):
        r = self.se.check_warnings(
            stress_score=65.0
        )
        assert r["alert_level"] == "yellow"

    def test_suggest_coping_minimal(self):
        r = self.se.suggest_coping("minimal")
        assert r["suggested"] is True
        assert r["urgent"] is False
        assert r["suggestion_count"] == 2

    def test_suggest_coping_severe(self):
        r = self.se.suggest_coping("severe")
        assert r["urgent"] is True
        assert "professional_help" in r["suggestions"]


# ── HealthReportGenerator ──────────────────────


class TestHealthReportGenerator:
    """HealthReportGenerator testleri."""

    def setup_method(self):
        self.hrg = HealthReportGenerator()

    def test_init(self):
        assert self.hrg.report_count == 0

    def test_weekly_summary_excellent(self):
        r = self.hrg.generate_weekly_summary(
            sleep_avg=8.0,
            exercise_min=200,
            calories_avg=2000,
            stress_avg=20.0,
            water_glasses=10,
        )
        assert r["generated"] is True
        assert r["grade"] == "excellent"
        assert r["overall_score"] >= 80

    def test_weekly_summary_needs_improvement(self):
        r = self.hrg.generate_weekly_summary(
            sleep_avg=4.0,
            exercise_min=30,
            calories_avg=3000,
            stress_avg=80.0,
            water_glasses=2,
        )
        assert r["grade"] == "needs_improvement"

    def test_trend_report_insufficient(self):
        r = self.hrg.generate_trend_report([])
        assert r["trend"] == "insufficient_data"

    def test_trend_report_improving(self):
        points = [
            {"value": 50}, {"value": 55},
            {"value": 80}, {"value": 85},
        ]
        r = self.hrg.generate_trend_report(points)
        assert r["trend"] == "improving"

    def test_trend_report_declining(self):
        points = [
            {"value": 80}, {"value": 85},
            {"value": 50}, {"value": 45},
        ]
        r = self.hrg.generate_trend_report(points)
        assert r["trend"] == "declining"

    def test_track_goal_progress_empty(self):
        r = self.hrg.track_goal_progress()
        assert r["tracked"] is True
        assert r["goals"] == 0

    def test_track_goal_progress(self):
        goals = [
            {"name": "sleep", "progress": 100},
            {"name": "exercise", "progress": 50},
            {"name": "weight", "progress": 0},
        ]
        r = self.hrg.track_goal_progress(goals)
        assert r["completed"] == 1
        assert r["in_progress"] == 1
        assert r["not_started"] == 1
        assert r["avg_progress"] == 50.0

    def test_get_recommendations_low_score(self):
        r = self.hrg.get_recommendations(
            overall_score=40.0,
            weak_areas=["sleep", "exercise"],
        )
        assert r["generated"] is True
        assert "consult_healthcare_provider" in r["recommendations"]
        assert r["priority"] == "high"

    def test_get_recommendations_good(self):
        r = self.hrg.get_recommendations(
            overall_score=80.0,
        )
        assert r["priority"] == "low"

    def test_export_report(self):
        self.hrg.generate_weekly_summary()
        rid = self.hrg._reports[0]["report_id"]
        r = self.hrg.export_report(
            report_id=rid, format_type="pdf"
        )
        assert r["exported"] is True
        assert r["format"] == "pdf"

    def test_export_report_not_found(self):
        r = self.hrg.export_report(
            report_id="invalid"
        )
        assert r["exported"] is False


# ── MedicationTracker ──────────────────────────


class TestMedicationTracker:
    """MedicationTracker testleri."""

    def setup_method(self):
        self.mt = MedicationTracker()

    def test_init(self):
        assert self.mt.medication_count == 0

    def test_add_medication(self):
        r = self.mt.add_medication(
            name="Aspirin", dosage="100mg",
            frequency="once_daily", stock=30,
        )
        assert r["added"] is True
        assert r["name"] == "Aspirin"
        assert r["days_supply"] == 30

    def test_add_medication_twice_daily(self):
        r = self.mt.add_medication(
            name="VitaminC", frequency="twice_daily",
            stock=60,
        )
        assert r["days_supply"] == 30

    def test_record_dose(self):
        a = self.mt.add_medication(
            name="Med1", stock=10
        )
        r = self.mt.record_dose(
            medication_id=a["medication_id"],
            taken=True,
        )
        assert r["recorded"] is True
        assert r["remaining_stock"] == 9

    def test_record_dose_not_found(self):
        r = self.mt.record_dose(
            medication_id="invalid"
        )
        assert r["recorded"] is False

    def test_record_dose_missed(self):
        a = self.mt.add_medication(
            name="Med2", stock=10
        )
        r = self.mt.record_dose(
            medication_id=a["medication_id"],
            taken=False,
        )
        assert r["recorded"] is True
        assert r["remaining_stock"] == 10

    def test_check_refill_needed(self):
        self.mt.add_medication(
            name="LowStock", stock=5,
            frequency="once_daily",
        )
        r = self.mt.check_refill(threshold_days=7)
        assert r["checked"] is True
        assert r["refill_count"] == 1

    def test_check_refill_ok(self):
        self.mt.add_medication(
            name="HighStock", stock=60,
            frequency="once_daily",
        )
        r = self.mt.check_refill(threshold_days=7)
        assert r["refill_count"] == 0

    def test_check_interactions_none(self):
        r = self.mt.check_interactions(
            med_names=["vitamin_c", "zinc"]
        )
        assert r["checked"] is True
        assert r["interaction_count"] == 0
        assert r["risk_level"] == "low"

    def test_check_interactions_found(self):
        r = self.mt.check_interactions(
            med_names=["aspirin", "ibuprofen"]
        )
        assert r["interaction_count"] == 1
        assert r["risk_level"] == "high"

    def test_check_interactions_many_meds(self):
        r = self.mt.check_interactions(
            med_names=["a", "b", "c", "d", "e", "f"]
        )
        assert r["risk_level"] == "moderate"

    def test_get_history_empty(self):
        r = self.mt.get_history()
        assert r["retrieved"] is True
        assert r["total_doses"] == 0
        assert r["adherence_pct"] == 100.0

    def test_get_history_compliance(self):
        a = self.mt.add_medication(
            name="TestMed", stock=30
        )
        mid = a["medication_id"]
        for _ in range(9):
            self.mt.record_dose(mid, taken=True)
        self.mt.record_dose(mid, taken=False)
        r = self.mt.get_history(
            medication_id=mid
        )
        assert r["adherence_pct"] == 90.0
        assert r["compliance"] == "excellent"

    def test_get_history_poor_compliance(self):
        a = self.mt.add_medication(
            name="BadMed", stock=30
        )
        mid = a["medication_id"]
        for _ in range(3):
            self.mt.record_dose(mid, taken=True)
        for _ in range(7):
            self.mt.record_dose(mid, taken=False)
        r = self.mt.get_history(mid)
        assert r["compliance"] == "poor"


# ── WellnessOrchestrator ──────────────────────


class TestWellnessOrchestrator:
    """WellnessOrchestrator testleri."""

    def setup_method(self):
        self.wo = WellnessOrchestrator()

    def test_init(self):
        a = self.wo.get_analytics()
        assert a["retrieved"] is True
        assert a["components"] == 8

    def test_full_wellness_check(self):
        r = self.wo.full_wellness_check()
        assert r["completed"] is True
        assert "sleep" in r
        assert "exercise" in r
        assert "stress" in r
        assert "nutrition" in r
        assert "report" in r

    def test_full_wellness_check_custom(self):
        r = self.wo.full_wellness_check(
            sleep_hours=9.0,
            exercise_min=60,
            stress_score=20.0,
            water_glasses=10,
            calories=1800,
        )
        assert r["completed"] is True

    def test_daily_briefing(self):
        r = self.wo.daily_briefing()
        assert r["briefed"] is True
        assert "sleep" in r
        assert "stress" in r
        assert "medications" in r

    def test_get_analytics(self):
        r = self.wo.get_analytics()
        assert r["reminders"] == 0
        assert r["exercises"] == 0
        assert r["sleep_records"] == 0
        assert r["meals"] == 0

    def test_analytics_after_operations(self):
        self.wo.full_wellness_check()
        r = self.wo.get_analytics()
        assert r["sleep_records"] >= 1
        assert r["exercises"] >= 1
        assert r["reports"] >= 1
