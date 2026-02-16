"""ATLAS Onboarding & Training Assistant testleri."""

import pytest

from app.core.onboarding.skill_assessor import (
    SkillAssessor,
)
from app.core.onboarding.learning_path_builder import (
    LearningPathBuilder,
)
from app.core.onboarding.tutorial_generator import (
    TutorialGenerator,
)
from app.core.onboarding.onboarding_progress_tracker import (
    OnboardingProgressTracker,
)
from app.core.onboarding.quiz_builder import (
    QuizBuilder,
)
from app.core.onboarding.certification_manager import (
    CertificationManager,
)
from app.core.onboarding.adaptive_difficulty import (
    AdaptiveDifficulty,
)
from app.core.onboarding.mentor_matcher import (
    MentorMatcher,
)
from app.core.onboarding.onboarding_orchestrator import (
    OnboardingOrchestrator,
)
from app.models.onboarding_models import (
    SkillLevel,
    LearningStatus,
    QuestionFormat,
    CertificationStatus,
    DifficultyLevel,
    TutorialType,
    SkillAssessmentRecord,
    LearningPathRecord,
    CertificationRecord,
    MentorAssignmentRecord,
)


# --- SkillAssessor ---

class TestEvaluateSkill:
    def test_expert(self):
        sa = SkillAssessor()
        r = sa.evaluate_skill(
            "u1", "python",
            answers=[
                {"correct": True},
                {"correct": True},
                {"correct": True},
                {"correct": True},
                {"correct": True},
            ],
        )
        assert r["evaluated"]
        assert r["score"] == 100.0
        assert r["level"] == "expert"

    def test_beginner(self):
        sa = SkillAssessor()
        r = sa.evaluate_skill(
            "u1", "python",
            answers=[
                {"correct": False},
                {"correct": False},
                {"correct": True},
            ],
        )
        assert r["level"] == "beginner"

    def test_empty(self):
        sa = SkillAssessor()
        r = sa.evaluate_skill("u1", "py")
        assert r["evaluated"]


class TestTestKnowledge:
    def test_passed(self):
        sa = SkillAssessor()
        r = sa.test_knowledge(
            "u1", "python",
            questions=[
                {"correct": True},
                {"correct": True},
                {"correct": True},
                {"correct": False},
            ],
        )
        assert r["tested"]
        assert r["passed"]

    def test_failed(self):
        sa = SkillAssessor()
        r = sa.test_knowledge(
            "u1", "python",
            questions=[
                {"correct": False},
                {"correct": False},
                {"correct": True},
            ],
        )
        assert not r["passed"]


class TestIdentifyGaps:
    def test_gaps(self):
        sa = SkillAssessor()
        sa.evaluate_skill(
            "u1", "python",
            answers=[{"correct": True}],
        )
        r = sa.identify_gaps(
            "u1",
            required_skills=[
                "python", "docker", "sql",
            ],
        )
        assert r["identified"]
        assert "docker" in r["missing_skills"]
        assert "sql" in r["missing_skills"]

    def test_weak(self):
        sa = SkillAssessor()
        sa.evaluate_skill(
            "u1", "python",
            answers=[
                {"correct": False},
                {"correct": False},
                {"correct": False},
            ],
        )
        r = sa.identify_gaps(
            "u1",
            required_skills=["python"],
        )
        assert "python" in r["weak_skills"]


class TestDetermineLevel:
    def test_with_data(self):
        sa = SkillAssessor()
        sa.evaluate_skill(
            "u1", "python",
            answers=[
                {"correct": True},
                {"correct": True},
            ],
        )
        r = sa.determine_level("u1")
        assert r["determined"]
        assert r["level"] == "expert"

    def test_no_data(self):
        sa = SkillAssessor()
        r = sa.determine_level("u1")
        assert r["level"] == "beginner"


class TestCompareBenchmark:
    def test_above(self):
        sa = SkillAssessor()
        sa.evaluate_skill(
            "u1", "python",
            answers=[{"correct": True}],
        )
        r = sa.compare_benchmark(
            "u1", "python", 50.0,
        )
        assert r["compared"]
        assert r["above_benchmark"]

    def test_below(self):
        sa = SkillAssessor()
        r = sa.compare_benchmark(
            "u1", "python", 70.0,
        )
        assert not r["above_benchmark"]


# --- LearningPathBuilder ---

class TestBuildPath:
    def test_basic(self):
        lpb = LearningPathBuilder()
        r = lpb.build_personalized_path(
            "u1",
            target_skills=["python", "sql"],
        )
        assert r["built"]
        assert r["module_count"] == 2

    def test_empty(self):
        lpb = LearningPathBuilder()
        r = lpb.build_personalized_path("u1")
        assert r["module_count"] == 0


class TestHandlePrereqs:
    def test_ready(self):
        lpb = LearningPathBuilder()
        lpb.build_personalized_path(
            "u1",
            target_skills=["python"],
        )
        pid = "path_1"
        r = lpb.handle_prerequisites(
            pid, "sql",
        )
        assert r["handled"]
        assert r["ready"]

    def test_not_found(self):
        lpb = LearningPathBuilder()
        r = lpb.handle_prerequisites(
            "x", "sql",
        )
        assert not r["found"]


class TestEstimateDuration:
    def test_basic(self):
        lpb = LearningPathBuilder()
        lpb.build_personalized_path(
            "u1",
            target_skills=["a", "b", "c"],
        )
        r = lpb.estimate_duration("path_1")
        assert r["estimated"]
        assert r["estimated_hours"] == 6.0

    def test_not_found(self):
        lpb = LearningPathBuilder()
        r = lpb.estimate_duration("x")
        assert not r["found"]


class TestSetMilestones:
    def test_basic(self):
        lpb = LearningPathBuilder()
        lpb.build_personalized_path("u1")
        r = lpb.set_milestones(
            "path_1",
            milestones=[{"name": "m1"}],
        )
        assert r["set"]
        assert r["milestone_count"] == 1


class TestAdaptSequence:
    def test_reorder(self):
        lpb = LearningPathBuilder()
        lpb.build_personalized_path(
            "u1",
            target_skills=["python", "sql"],
        )
        r = lpb.adapt_sequence(
            "path_1",
            performance_scores={
                "python": 30,
            },
        )
        assert r["adapted"]
        assert r["reordered"]

    def test_no_change(self):
        lpb = LearningPathBuilder()
        lpb.build_personalized_path("u1")
        r = lpb.adapt_sequence("path_1")
        assert not r["reordered"]


# --- TutorialGenerator ---

class TestStepByStep:
    def test_basic(self):
        tg = TutorialGenerator()
        r = tg.generate_step_by_step(
            "python",
            steps=["install", "run"],
        )
        assert r["generated"]
        assert r["step_count"] == 2


class TestInteractive:
    def test_basic(self):
        tg = TutorialGenerator()
        r = tg.generate_interactive(
            "python",
            interactions=[
                {"type": "click"},
            ],
        )
        assert r["generated"]
        assert r["interaction_count"] == 1


class TestVideoScript:
    def test_basic(self):
        tg = TutorialGenerator()
        r = tg.generate_video_script(
            "python",
            duration_minutes=15,
        )
        assert r["generated"]
        assert r["duration_minutes"] == 15


class TestCodeExample:
    def test_basic(self):
        tg = TutorialGenerator()
        r = tg.generate_code_example(
            "python",
            code="print('hello')",
        )
        assert r["generated"]
        assert r["language"] == "python"


class TestCreateExercise:
    def test_basic(self):
        tg = TutorialGenerator()
        r = tg.create_exercise(
            "python",
            instructions="Write a loop",
        )
        assert r["created"]


# --- OnboardingProgressTracker ---

class TestTrackCompletion:
    def test_basic(self):
        pt = OnboardingProgressTracker()
        r = pt.track_completion(
            "u1", "module1", completed=True,
        )
        assert r["tracked"]
        assert r["completed_modules"] == 1

    def test_incomplete(self):
        pt = OnboardingProgressTracker()
        r = pt.track_completion(
            "u1", "module1",
        )
        assert r["completed_modules"] == 0


class TestRecordTime:
    def test_basic(self):
        pt = OnboardingProgressTracker()
        r = pt.record_time_spent(
            "u1", "module1", minutes=30,
        )
        assert r["recorded"]
        assert r["total_minutes"] == 30


class TestTrackScore:
    def test_basic(self):
        pt = OnboardingProgressTracker()
        r = pt.track_score(
            "u1", "module1", score=85,
        )
        assert r["tracked"]
        assert r["avg_score"] == 85


class TestEngagementMetrics:
    def test_basic(self):
        pt = OnboardingProgressTracker()
        pt.track_completion(
            "u1", "m1", completed=True,
        )
        pt.record_time_spent(
            "u1", "m1", minutes=20,
        )
        r = pt.get_engagement_metrics("u1")
        assert r["engaged"]
        assert r["total_time_min"] == 20

    def test_not_found(self):
        pt = OnboardingProgressTracker()
        r = pt.get_engagement_metrics("x")
        assert not r["found"]


class TestDetectDropout:
    def test_no_sessions(self):
        pt = OnboardingProgressTracker()
        r = pt.detect_dropout("u1")
        assert r["at_risk"]
        assert r["reason"] == "no_sessions"

    def test_active(self):
        pt = OnboardingProgressTracker()
        pt.record_time_spent(
            "u1", "m1", minutes=10,
        )
        r = pt.detect_dropout(
            "u1", inactive_days=7,
        )
        assert not r["at_risk"]


# --- QuizBuilder ---

class TestGenerateQuestions:
    def test_basic(self):
        qb = QuizBuilder()
        r = qb.generate_questions(
            "python", count=3,
        )
        assert r["generated"]
        assert r["question_count"] == 3


class TestMultiFormat:
    def test_basic(self):
        qb = QuizBuilder()
        r = qb.create_multi_format(
            "python",
        )
        assert r["created"]
        assert r["format_count"] == 3


class TestSetDifficulty:
    def test_basic(self):
        qb = QuizBuilder()
        qb.generate_questions("python")
        r = qb.set_difficulty(
            "quiz_1", "hard",
        )
        assert r["set"]

    def test_not_found(self):
        qb = QuizBuilder()
        r = qb.set_difficulty("x", "hard")
        assert not r["found"]


class TestRandomize:
    def test_basic(self):
        qb = QuizBuilder()
        qb.generate_questions(
            "python", count=5,
        )
        r = qb.randomize(
            "quiz_1", seed=42,
        )
        assert r["randomized"]

    def test_not_found(self):
        qb = QuizBuilder()
        r = qb.randomize("x")
        assert not r["found"]


class TestScoreQuiz:
    def test_perfect(self):
        qb = QuizBuilder()
        qb.generate_questions(
            "python", count=3,
        )
        r = qb.score_quiz(
            "quiz_1",
            answers={
                "q_1": "A",
                "q_2": "A",
                "q_3": "A",
            },
        )
        assert r["scored"]
        assert r["score"] == 100.0
        assert r["passed"]

    def test_failed(self):
        qb = QuizBuilder()
        qb.generate_questions(
            "python", count=3,
        )
        r = qb.score_quiz(
            "quiz_1",
            answers={
                "q_1": "B",
                "q_2": "B",
                "q_3": "B",
            },
        )
        assert r["score"] == 0.0
        assert not r["passed"]

    def test_not_found(self):
        qb = QuizBuilder()
        r = qb.score_quiz("x")
        assert not r["found"]


# --- CertificationManager ---

class TestDefineCriteria:
    def test_basic(self):
        cm = CertificationManager()
        r = cm.define_criteria(
            "Python Cert",
            required_score=80,
            required_modules=["py1"],
        )
        assert r["defined"]
        assert r["module_count"] == 1


class TestManageExam:
    def test_passed(self):
        cm = CertificationManager()
        cm.define_criteria("Cert")
        r = cm.manage_exam(
            "Cert", "u1", score=90,
        )
        assert r["managed"]
        assert r["passed"]

    def test_failed(self):
        cm = CertificationManager()
        cm.define_criteria(
            "Cert", required_score=80,
        )
        r = cm.manage_exam(
            "Cert", "u1", score=50,
        )
        assert not r["passed"]

    def test_not_found(self):
        cm = CertificationManager()
        r = cm.manage_exam("X", "u1")
        assert not r["found"]


class TestGenerateCertificate:
    def test_basic(self):
        cm = CertificationManager()
        cm.define_criteria("Cert")
        cm.manage_exam(
            "Cert", "u1", score=90,
        )
        r = cm.generate_certificate(
            "Cert", "u1",
        )
        assert r["generated"]
        assert r["status"] == "active"

    def test_not_eligible(self):
        cm = CertificationManager()
        cm.define_criteria("Cert")
        cm.manage_exam(
            "Cert", "u1", score=30,
        )
        r = cm.generate_certificate(
            "Cert", "u1",
        )
        assert not r["eligible"]

    def test_cert_not_found(self):
        cm = CertificationManager()
        r = cm.generate_certificate(
            "X", "u1",
        )
        assert not r["found"]


class TestCheckExpiration:
    def test_active(self):
        cm = CertificationManager()
        cm.define_criteria("Cert")
        cm.manage_exam(
            "Cert", "u1", score=90,
        )
        cm.generate_certificate(
            "Cert", "u1",
        )
        r = cm.check_expiration("cert_2")
        assert r["checked"]
        assert not r["expired"]

    def test_not_found(self):
        cm = CertificationManager()
        r = cm.check_expiration("x")
        assert not r["found"]


class TestRenewalReminder:
    def test_not_needed(self):
        cm = CertificationManager()
        cm.define_criteria("Cert")
        cm.manage_exam(
            "Cert", "u1", score=90,
        )
        cm.generate_certificate(
            "Cert", "u1",
        )
        r = cm.send_renewal_reminder(
            "cert_2",
        )
        assert not r["needs_renewal"]


# --- AdaptiveDifficulty ---

class TestAnalyzePerformance:
    def test_improving(self):
        ad = AdaptiveDifficulty()
        r = ad.analyze_performance(
            "u1",
            scores=[40, 60, 80, 90],
        )
        assert r["analyzed"]
        assert r["trend"] == "improving"

    def test_declining(self):
        ad = AdaptiveDifficulty()
        r = ad.analyze_performance(
            "u1",
            scores=[90, 70, 50],
        )
        assert r["trend"] == "declining"

    def test_empty(self):
        ad = AdaptiveDifficulty()
        r = ad.analyze_performance("u1")
        assert r["trend"] == "unknown"


class TestAdjustDifficulty:
    def test_increase(self):
        ad = AdaptiveDifficulty()
        r = ad.adjust_difficulty(
            "u1", current_score=95,
        )
        assert r["adjusted"]
        assert r["new_level"] == "hard"

    def test_decrease(self):
        ad = AdaptiveDifficulty()
        ad._profiles["u1"] = {
            "current_difficulty": "hard",
        }
        r = ad.adjust_difficulty(
            "u1", current_score=30,
        )
        assert r["new_level"] == "medium"

    def test_no_change(self):
        ad = AdaptiveDifficulty()
        r = ad.adjust_difficulty(
            "u1", current_score=70,
        )
        assert not r["changed"]


class TestOptimizeChallenge:
    def test_improving(self):
        ad = AdaptiveDifficulty()
        ad._profiles["u1"] = {
            "avg_score": 80,
            "trend": "improving",
        }
        r = ad.optimize_challenge("u1")
        assert r["optimized"]
        assert r["strategy"] == (
            "increase_gradually"
        )


class TestPreventFrustration:
    def test_frustrated(self):
        ad = AdaptiveDifficulty()
        r = ad.prevent_frustration(
            "u1",
            consecutive_failures=5,
        )
        assert r["frustrated"]
        assert len(r["actions"]) > 0

    def test_ok(self):
        ad = AdaptiveDifficulty()
        r = ad.prevent_frustration(
            "u1",
            consecutive_failures=1,
        )
        assert not r["frustrated"]


class TestMaximizeEngagement:
    def test_high_performer(self):
        ad = AdaptiveDifficulty()
        ad._profiles["u1"] = {
            "avg_score": 90,
            "trend": "stable",
        }
        r = ad.maximize_engagement("u1")
        assert r["maximized"]
        assert (
            "introduce_bonus_challenges"
            in r["recommendations"]
        )


# --- MentorMatcher ---

class TestMatchSkills:
    def test_match(self):
        mm = MentorMatcher()
        mm.register_mentor(
            "m1", "Ali",
            skills=["python", "sql"],
        )
        r = mm.match_skills(
            "u1",
            required_skills=["python"],
        )
        assert r["matched"]
        assert r["total_found"] == 1

    def test_no_match(self):
        mm = MentorMatcher()
        r = mm.match_skills(
            "u1",
            required_skills=["rust"],
        )
        assert r["total_found"] == 0


class TestCheckAvailability:
    def test_available(self):
        mm = MentorMatcher()
        mm.register_mentor("m1", "Ali")
        r = mm.check_availability("m1")
        assert r["checked"]
        assert r["available"]

    def test_not_found(self):
        mm = MentorMatcher()
        r = mm.check_availability("x")
        assert not r["found"]


class TestScoreCompatibility:
    def test_full_match(self):
        mm = MentorMatcher()
        r = mm.score_compatibility(
            "m1", "u1",
            mentor_skills=[
                "python", "sql",
            ],
            mentee_needs=["python"],
        )
        assert r["scored"]
        assert r["score"] == 100.0

    def test_no_needs(self):
        mm = MentorMatcher()
        r = mm.score_compatibility(
            "m1", "u1",
        )
        assert r["score"] == 0.0


class TestAssignMentor:
    def test_basic(self):
        mm = MentorMatcher()
        r = mm.assign_mentor(
            "m1", "u1", "python",
        )
        assert r["assigned"]


class TestCollectFeedback:
    def test_basic(self):
        mm = MentorMatcher()
        mm.assign_mentor("m1", "u1")
        r = mm.collect_feedback(
            "assign_1", rating=5,
        )
        assert r["collected"]

    def test_not_found(self):
        mm = MentorMatcher()
        r = mm.collect_feedback("x")
        assert not r["found"]


# --- OnboardingOrchestrator ---

class TestRunOnboarding:
    def test_basic(self):
        oo = OnboardingOrchestrator()
        r = oo.run_onboarding(
            "u1",
            target_skills=[
                "python", "sql",
            ],
            answers=[
                {"correct": True},
                {"correct": True},
            ],
        )
        assert r["pipeline_complete"]
        assert r["modules_planned"] == 2

    def test_empty(self):
        oo = OnboardingOrchestrator()
        r = oo.run_onboarding("u1")
        assert r["pipeline_complete"]


class TestPersonalizedExperience:
    def test_basic(self):
        oo = OnboardingOrchestrator()
        oo.run_onboarding(
            "u1",
            target_skills=["python"],
            answers=[{"correct": True}],
        )
        r = oo.personalized_experience("u1")
        assert r["personalized"]


class TestOnboardingAnalytics:
    def test_basic(self):
        oo = OnboardingOrchestrator()
        oo.run_onboarding("u1")
        r = oo.get_analytics()
        assert r["pipelines_run"] == 1
        assert r["users_onboarded"] == 1


# --- Models ---

class TestOnboardingModels:
    def test_skill_level(self):
        assert (
            SkillLevel.BEGINNER
            == "beginner"
        )
        assert (
            SkillLevel.EXPERT == "expert"
        )

    def test_learning_status(self):
        assert (
            LearningStatus.IN_PROGRESS
            == "in_progress"
        )
        assert (
            LearningStatus.COMPLETED
            == "completed"
        )

    def test_question_format(self):
        assert (
            QuestionFormat.MULTIPLE_CHOICE
            == "multiple_choice"
        )
        assert (
            QuestionFormat.CODE_EXERCISE
            == "code_exercise"
        )

    def test_certification_status(self):
        assert (
            CertificationStatus.ACTIVE
            == "active"
        )
        assert (
            CertificationStatus.EXPIRED
            == "expired"
        )

    def test_difficulty_level(self):
        assert (
            DifficultyLevel.EASY == "easy"
        )
        assert (
            DifficultyLevel.EXPERT
            == "expert"
        )

    def test_tutorial_type(self):
        assert (
            TutorialType.INTERACTIVE
            == "interactive"
        )
        assert (
            TutorialType.VIDEO_SCRIPT
            == "video_script"
        )

    def test_skill_assessment_record(self):
        r = SkillAssessmentRecord(
            user_id="u1",
            skill_name="python",
        )
        assert r.user_id == "u1"
        assert r.assessment_id

    def test_learning_path_record(self):
        r = LearningPathRecord(
            user_id="u1",
            title="Python Path",
        )
        assert r.title == "Python Path"
        assert r.path_id

    def test_certification_record(self):
        r = CertificationRecord(
            user_id="u1",
            certification_name="Cert",
        )
        assert (
            r.certification_name == "Cert"
        )
        assert r.cert_id

    def test_mentor_assignment_record(self):
        r = MentorAssignmentRecord(
            mentor_id="m1",
            mentee_id="u1",
        )
        assert r.mentor_id == "m1"
        assert r.assignment_id
