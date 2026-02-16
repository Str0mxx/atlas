"""Learning & Self-Development Coach testleri."""

import pytest

from app.core.selfdev import (
    CertificationPath,
    CourseRecommender,
    DailyLearningPlanner,
    PodcastCurator,
    ReadingListBuilder,
    SelfDevMentorFinder,
    SelfDevOrchestrator,
    SelfDevProgressTracker,
    SelfDevSkillGapAnalyzer,
)
from app.models.selfdev_models import (
    CertDifficulty,
    CertificationRecord,
    ContentType,
    CourseRecord,
    LearningStyle,
    MentorStatus,
    ProgressStatus,
    ReadingRecord,
    SkillLevel,
    SkillRecord,
)


# ── Models ──────────────────────────────────────


class TestSelfDevModels:
    """SelfDev model testleri."""

    def test_skill_level_values(self):
        assert SkillLevel.novice == "novice"
        assert SkillLevel.beginner == "beginner"
        assert SkillLevel.intermediate == "intermediate"
        assert SkillLevel.advanced == "advanced"
        assert SkillLevel.expert == "expert"
        assert SkillLevel.master == "master"

    def test_content_type_values(self):
        assert ContentType.course == "course"
        assert ContentType.book == "book"
        assert ContentType.podcast == "podcast"
        assert ContentType.article == "article"
        assert ContentType.video == "video"
        assert ContentType.workshop == "workshop"

    def test_learning_style_values(self):
        assert LearningStyle.visual == "visual"
        assert LearningStyle.auditory == "auditory"
        assert LearningStyle.reading == "reading"
        assert LearningStyle.kinesthetic == "kinesthetic"
        assert LearningStyle.mixed == "mixed"

    def test_cert_difficulty_values(self):
        assert CertDifficulty.entry == "entry"
        assert CertDifficulty.associate == "associate"
        assert CertDifficulty.professional == "professional"
        assert CertDifficulty.expert == "expert"
        assert CertDifficulty.architect == "architect"

    def test_mentor_status_values(self):
        assert MentorStatus.available == "available"
        assert MentorStatus.busy == "busy"
        assert MentorStatus.matched == "matched"

    def test_progress_status_values(self):
        assert ProgressStatus.not_started == "not_started"
        assert ProgressStatus.in_progress == "in_progress"
        assert ProgressStatus.completed == "completed"
        assert ProgressStatus.certified == "certified"

    def test_skill_record(self):
        r = SkillRecord(name="python", level="intermediate")
        assert r.name == "python"
        assert r.level == "intermediate"
        assert len(r.skill_id) == 8

    def test_course_record(self):
        r = CourseRecord(title="ML Course", platform="udemy")
        assert r.title == "ML Course"
        assert r.platform == "udemy"

    def test_reading_record(self):
        r = ReadingRecord(title="Clean Code", author="Martin")
        assert r.title == "Clean Code"
        assert r.status == "not_started"

    def test_certification_record(self):
        r = CertificationRecord(
            name="AWS SAA", provider="Amazon"
        )
        assert r.name == "AWS SAA"
        assert r.difficulty == "associate"
        assert r.status == "planned"


# ── SelfDevSkillGapAnalyzer ────────────────────


class TestSelfDevSkillGapAnalyzer:
    """SelfDevSkillGapAnalyzer testleri."""

    def setup_method(self):
        self.sga = SelfDevSkillGapAnalyzer()

    def test_init(self):
        assert self.sga.skill_count == 0

    def test_assess_current_skills(self):
        skills = [
            {"name": "python", "level": "intermediate"},
            {"name": "sql", "level": "beginner"},
        ]
        r = self.sga.assess_current_skills(skills)
        assert r["assessed"] is True
        assert r["skills_assessed"] == 2
        assert r["total_skills"] == 2

    def test_assess_empty(self):
        r = self.sga.assess_current_skills()
        assert r["assessed"] is True
        assert r["skills_assessed"] == 0

    def test_map_target_skills(self):
        self.sga.assess_current_skills([
            {"name": "python", "level": "beginner"},
        ])
        r = self.sga.map_target_skills(
            role="data_scientist"
        )
        assert r["mapped"] is True
        assert "python" in r["existing"]
        assert len(r["new_skills_needed"]) > 0

    def test_map_custom_targets(self):
        r = self.sga.map_target_skills(
            target_skills=["go", "rust"]
        )
        assert r["coverage_pct"] == 0.0

    def test_identify_gaps(self):
        self.sga.assess_current_skills([
            {"name": "python", "level": "novice"},
            {"name": "sql", "level": "advanced"},
        ])
        r = self.sga.identify_gaps("intermediate")
        assert r["identified"] is True
        assert r["gap_count"] == 1
        assert r["on_target_count"] == 1

    def test_identify_gaps_all_on_target(self):
        self.sga.assess_current_skills([
            {"name": "python", "level": "expert"},
        ])
        r = self.sga.identify_gaps("intermediate")
        assert r["gap_count"] == 0

    def test_rank_priorities(self):
        gaps = [
            {"name": "sql", "gap": 1},
            {"name": "ml", "gap": 3},
            {"name": "stats", "gap": 2},
        ]
        r = self.sga.rank_priorities(gaps)
        assert r["ranked"] is True
        assert r["priorities"][0]["name"] == "ml"
        assert r["priorities"][0]["priority"] == "critical"

    def test_rank_empty(self):
        r = self.sga.rank_priorities([])
        assert r["count"] == 0

    def test_create_roadmap(self):
        gaps = [
            {"name": "python"},
            {"name": "sql"},
            {"name": "ml"},
        ]
        r = self.sga.create_roadmap(
            gaps, weeks_available=12
        )
        assert r["created"] is True
        assert r["phase_count"] == 3

    def test_create_roadmap_empty(self):
        r = self.sga.create_roadmap([])
        assert r["total_weeks"] == 0


# ── CourseRecommender ──────────────────────────


class TestCourseRecommender:
    """CourseRecommender testleri."""

    def setup_method(self):
        self.cr = CourseRecommender()

    def test_init(self):
        assert self.cr.course_count == 0

    def test_discover_courses(self):
        r = self.cr.discover_courses(
            topic="Python", level="beginner"
        )
        assert r["discovered"] is True
        assert r["count"] == 3

    def test_discover_limited(self):
        r = self.cr.discover_courses(
            topic="AI", max_results=2
        )
        assert r["count"] == 2

    def test_aggregate_platforms(self):
        r = self.cr.aggregate_platforms("Python")
        assert r["aggregated"] is True
        assert r["platform_count"] == 4
        assert r["best_value"] == "edx"

    def test_score_quality_excellent(self):
        r = self.cr.score_quality(
            rating=4.8, reviews=1000,
            completion_rate=80.0,
            instructor_rating=4.9,
        )
        assert r["scored"] is True
        assert r["grade"] == "excellent"

    def test_score_quality_below(self):
        r = self.cr.score_quality(
            rating=2.0, reviews=10,
        )
        assert r["grade"] == "below_average"

    def test_compare_prices(self):
        courses = [
            {"title": "A", "price": 0},
            {"title": "B", "price": 99.99},
            {"title": "C", "price": 49.99},
        ]
        r = self.cr.compare_prices(courses)
        assert r["compared"] is True
        assert r["cheapest"]["price"] == 0
        assert r["free_courses"] == 1

    def test_compare_prices_empty(self):
        r = self.cr.compare_prices([])
        assert r["cheapest"] is None

    def test_personalize_visual(self):
        r = self.cr.personalize(
            learning_style="visual",
            available_hours=25,
            budget=300.0,
        )
        assert r["personalized"] is True
        assert r["format_preference"] == "video_heavy"
        assert r["pace"] == "intensive"
        assert r["budget_tier"] == "premium"

    def test_personalize_casual(self):
        r = self.cr.personalize(
            available_hours=5, budget=20.0
        )
        assert r["pace"] == "casual"
        assert r["budget_tier"] == "free_only"


# ── ReadingListBuilder ─────────────────────────


class TestReadingListBuilder:
    """ReadingListBuilder testleri."""

    def setup_method(self):
        self.rlb = ReadingListBuilder()

    def test_init(self):
        assert self.rlb.book_count == 0

    def test_recommend_books(self):
        r = self.rlb.recommend_books(
            topic="Python", count=2
        )
        assert r["recommended"] is True
        assert r["count"] == 2

    def test_add_to_list(self):
        r = self.rlb.add_to_list(
            title="Clean Code",
            author="Martin", topic="software",
        )
        assert r["added"] is True
        assert self.rlb.book_count == 1

    def test_cluster_by_topic(self):
        self.rlb.add_to_list(
            title="A", topic="python"
        )
        self.rlb.add_to_list(
            title="B", topic="python"
        )
        self.rlb.add_to_list(
            title="C", topic="ml"
        )
        r = self.rlb.cluster_by_topic()
        assert r["clustered"] is True
        assert r["topic_count"] == 2

    def test_track_progress(self):
        b = self.rlb.add_to_list(
            title="Book", pages=200
        )
        r = self.rlb.track_progress(
            book_id=b["book_id"], pages_read=100
        )
        assert r["tracked"] is True
        assert r["progress_pct"] == 50.0
        assert r["status"] == "in_progress"

    def test_track_progress_completed(self):
        b = self.rlb.add_to_list(
            title="Short", pages=100
        )
        r = self.rlb.track_progress(
            book_id=b["book_id"], pages_read=100
        )
        assert r["status"] == "completed"

    def test_track_progress_not_found(self):
        r = self.rlb.track_progress(
            book_id="invalid"
        )
        assert r["tracked"] is False

    def test_add_note(self):
        b = self.rlb.add_to_list(title="Book")
        r = self.rlb.add_note(
            book_id=b["book_id"],
            note="Great chapter", page=42,
        )
        assert r["added"] is True
        assert r["total_notes"] == 1

    def test_add_note_not_found(self):
        r = self.rlb.add_note(
            book_id="invalid"
        )
        assert r["added"] is False

    def test_aggregate_reviews(self):
        reviews = [
            {"rating": 5}, {"rating": 4},
            {"rating": 3},
        ]
        r = self.rlb.aggregate_reviews(reviews)
        assert r["aggregated"] is True
        assert r["avg_rating"] == 4.0
        assert r["highest"] == 5

    def test_aggregate_reviews_empty(self):
        r = self.rlb.aggregate_reviews()
        assert r["count"] == 0


# ── PodcastCurator ─────────────────────────────


class TestPodcastCurator:
    """PodcastCurator testleri."""

    def setup_method(self):
        self.pc = PodcastCurator()

    def test_init(self):
        assert self.pc.podcast_count == 0
        assert self.pc.queue_size == 0

    def test_discover_podcasts(self):
        r = self.pc.discover_podcasts(
            topic="AI"
        )
        assert r["discovered"] is True
        assert r["count"] == 3

    def test_recommend_episodes(self):
        r = self.pc.recommend_episodes(
            podcast_name="AI Weekly", topic="ML"
        )
        assert r["recommended"] is True
        assert r["count"] == 3

    def test_match_topic(self):
        podcasts = [
            {"name": "P1", "topic": "AI"},
            {"name": "P2", "topic": "Web"},
            {"name": "P3", "topic": "AI"},
        ]
        r = self.pc.match_topic(
            interests=["AI"],
            available_podcasts=podcasts,
        )
        assert r["matched_result"] is True
        assert r["matched_count"] == 2

    def test_filter_by_duration(self):
        episodes = [
            {"title": "A", "duration_min": 15},
            {"title": "B", "duration_min": 45},
            {"title": "C", "duration_min": 30},
        ]
        r = self.pc.filter_by_duration(
            episodes, max_duration_min=30
        )
        assert r["result"] is True
        assert r["filtered_count"] == 2

    def test_manage_queue_add(self):
        r = self.pc.manage_queue(
            action="add",
            episode={"title": "Ep1", "duration_min": 30},
        )
        assert r["managed"] is True
        assert r["queue_size"] == 1

    def test_manage_queue_remove(self):
        self.pc.manage_queue(
            action="add",
            episode={"title": "Ep1", "duration_min": 20},
        )
        r = self.pc.manage_queue(action="remove")
        assert r["queue_size"] == 0

    def test_manage_queue_clear(self):
        self.pc.manage_queue(
            action="add",
            episode={"title": "Ep1", "duration_min": 10},
        )
        self.pc.manage_queue(
            action="add",
            episode={"title": "Ep2", "duration_min": 20},
        )
        r = self.pc.manage_queue(action="clear")
        assert r["queue_size"] == 0


# ── DailyLearningPlanner ──────────────────────


class TestDailyLearningPlanner:
    """DailyLearningPlanner testleri."""

    def setup_method(self):
        self.dlp = DailyLearningPlanner()

    def test_init(self):
        assert self.dlp.plan_count == 0

    def test_set_daily_goals(self):
        r = self.dlp.set_daily_goals(
            learning_minutes=45,
            topics=["python", "ml"],
        )
        assert r["set"] is True
        assert r["learning_minutes"] == 45
        assert r["goal_count"] == 4

    def test_allocate_time(self):
        r = self.dlp.allocate_time(
            total_minutes=60,
            topics=["python", "sql", "ml"],
        )
        assert r["allocated"] is True
        assert r["topic_count"] == 3
        assert sum(
            r["allocation"].values()
        ) == 60

    def test_allocate_single_topic(self):
        r = self.dlp.allocate_time(
            total_minutes=30,
            topics=["python"],
        )
        assert r["allocation"]["python"] == 30

    def test_build_habit(self):
        r = self.dlp.build_habit(
            habit_name="reading",
            trigger="evening",
        )
        assert r["built"] is True
        assert r["current_streak"] == 0

    def test_track_streak_increase(self):
        self.dlp.build_habit("study")
        r = self.dlp.track_streak(
            "study", completed_today=True
        )
        assert r["tracked"] is True
        assert r["streak"] == 1
        assert r["badge"] == "starter"

    def test_track_streak_reset(self):
        self.dlp.build_habit("study")
        self.dlp.track_streak("study", True)
        self.dlp.track_streak("study", True)
        r = self.dlp.track_streak(
            "study", completed_today=False
        )
        assert r["streak"] == 0

    def test_track_streak_gold(self):
        self.dlp.build_habit("study")
        for _ in range(30):
            self.dlp.track_streak("study", True)
        r = self.dlp.track_streak("study", True)
        assert r["badge"] == "gold"

    def test_adjust_flexibility(self):
        p = self.dlp.set_daily_goals(
            learning_minutes=60
        )
        r = self.dlp.adjust_flexibility(
            plan_id=p["plan_id"],
            new_minutes=30,
            reason="busy_day",
        )
        assert r["adjusted"] is True
        assert r["old_minutes"] == 60
        assert r["new_minutes"] == 30

    def test_adjust_not_found(self):
        r = self.dlp.adjust_flexibility(
            plan_id="invalid"
        )
        assert r["adjusted"] is False


# ── SelfDevProgressTracker ─────────────────────


class TestSelfDevProgressTracker:
    """SelfDevProgressTracker testleri."""

    def setup_method(self):
        self.spt = SelfDevProgressTracker()

    def test_init(self):
        assert self.spt.progress_count == 0

    def test_log_learning(self):
        r = self.spt.log_learning(
            topic="python", minutes=30
        )
        assert r["logged"] is True
        assert r["total_minutes"] == 30

    def test_log_multiple(self):
        self.spt.log_learning("python", 30)
        self.spt.log_learning("python", 45)
        r = self.spt.log_learning("sql", 20)
        assert r["total_minutes"] == 95

    def test_track_skill_improved(self):
        r = self.spt.track_skill_development(
            skill="python",
            old_level="beginner",
            new_level="intermediate",
        )
        assert r["tracked"] is True
        assert r["status"] == "improved"
        assert r["improvement"] == 1

    def test_track_skill_maintained(self):
        r = self.spt.track_skill_development(
            old_level="advanced",
            new_level="advanced",
        )
        assert r["status"] == "maintained"

    def test_add_milestone(self):
        r = self.spt.add_milestone(
            name="100 hours",
            target_value=100.0,
            current_value=60.0,
        )
        assert r["added"] is True
        assert r["progress_pct"] == 60.0
        assert r["reached"] is False

    def test_add_milestone_reached(self):
        r = self.spt.add_milestone(
            target_value=50.0,
            current_value=50.0,
        )
        assert r["reached"] is True

    def test_award_badge_centurion(self):
        r = self.spt.award_badge(
            total_hours=100.0,
            streak_days=30,
            skills_improved=5,
        )
        assert r["awarded"] is True
        assert "centurion" in r["new_badges"]
        assert "streak_master" in r["new_badges"]
        assert "polymath" in r["new_badges"]

    def test_award_badge_basic(self):
        r = self.spt.award_badge(
            total_hours=10.0,
            streak_days=7,
            skills_improved=3,
        )
        assert "committed" in r["new_badges"]
        assert "consistent" in r["new_badges"]
        assert "multi_skilled" in r["new_badges"]

    def test_get_analytics(self):
        self.spt.log_learning("python", 60)
        self.spt.log_learning("sql", 30)
        r = self.spt.get_analytics()
        assert r["retrieved"] is True
        assert r["total_minutes"] == 90
        assert r["total_hours"] == 1.5
        assert r["top_topic"] == "python"


# ── CertificationPath ─────────────────────────


class TestCertificationPath:
    """CertificationPath testleri."""

    def setup_method(self):
        self.cp = CertificationPath()

    def test_init(self):
        assert self.cp.cert_count == 0

    def test_map_certifications_cloud(self):
        r = self.cp.map_certifications("cloud")
        assert r["mapped"] is True
        assert r["count"] == 3

    def test_map_certifications_security(self):
        r = self.cp.map_certifications("security")
        assert r["count"] == 2

    def test_track_requirements_in_progress(self):
        r = self.cp.track_requirements(
            cert_name="AWS SAA",
            total_requirements=5,
            completed=3,
        )
        assert r["tracked"] is True
        assert r["progress_pct"] == 60.0
        assert r["status"] == "halfway"

    def test_track_requirements_ready(self):
        r = self.cp.track_requirements(
            total_requirements=5,
            completed=5,
        )
        assert r["status"] == "ready_for_exam"

    def test_track_requirements_almost(self):
        r = self.cp.track_requirements(
            total_requirements=4,
            completed=3,
        )
        assert r["status"] == "almost_ready"

    def test_plan_study_moderate(self):
        r = self.cp.plan_study(
            cert_name="AWS SAA",
            study_hours=80,
            weeks_available=8,
        )
        assert r["planned"] is True
        assert r["hours_per_week"] == 10.0
        assert r["intensity"] == "moderate"

    def test_plan_study_intensive(self):
        r = self.cp.plan_study(
            study_hours=80,
            weeks_available=4,
        )
        assert r["intensity"] == "very_intensive"

    def test_schedule_exam_ready(self):
        r = self.cp.schedule_exam(
            cert_name="CISSP",
            readiness_pct=85.0,
        )
        assert r["scheduled"] is True
        assert r["recommendation"] == "ready"
        assert r["should_schedule"] is True

    def test_schedule_exam_not_ready(self):
        r = self.cp.schedule_exam(
            readiness_pct=30.0,
        )
        assert r["recommendation"] == "not_ready"
        assert r["should_schedule"] is False

    def test_predict_success_likely(self):
        r = self.cp.predict_success(
            study_hours_completed=60,
            study_hours_target=80,
            practice_score=70.0,
        )
        assert r["predicted"] is True
        assert r["outlook"] == "likely"

    def test_predict_success_unlikely(self):
        r = self.cp.predict_success(
            study_hours_completed=10,
            study_hours_target=80,
            practice_score=20.0,
        )
        assert r["outlook"] == "unlikely"


# ── SelfDevMentorFinder ────────────────────────


class TestSelfDevMentorFinder:
    """SelfDevMentorFinder testleri."""

    def setup_method(self):
        self.mf = SelfDevMentorFinder()

    def test_init(self):
        assert self.mf.mentor_count == 0

    def test_find_mentors(self):
        r = self.mf.find_mentors(
            expertise="python"
        )
        assert r["found"] is True
        assert r["count"] == 3

    def test_check_alignment_excellent(self):
        r = self.mf.check_alignment(
            learner_goals=["python", "ml"],
            mentor_expertise=["python", "ml", "ai"],
        )
        assert r["checked"] is True
        assert r["fit"] == "excellent"
        assert r["alignment_pct"] == 100.0

    def test_check_alignment_poor(self):
        r = self.mf.check_alignment(
            learner_goals=["python", "ml", "web"],
            mentor_expertise=["java"],
        )
        assert r["fit"] == "poor"

    def test_check_availability_available(self):
        r = self.mf.check_availability(
            mentor_name="Dr. Expert",
            status="available",
        )
        assert r["checked"] is True
        assert r["available"] is True
        assert r["slot_count"] == 2

    def test_check_availability_busy(self):
        r = self.mf.check_availability(
            status="busy"
        )
        assert r["available"] is False
        assert r["slot_count"] == 0

    def test_schedule_session(self):
        r = self.mf.schedule_session(
            mentor_name="Prof. Senior",
            topic="career_growth",
        )
        assert r["scheduled"] is True
        assert r["status"] == "scheduled"

    def test_track_feedback(self):
        s = self.mf.schedule_session(
            mentor_name="Coach"
        )
        r = self.mf.track_feedback(
            session_id=s["session_id"],
            rating=4.8,
            helpful=True,
        )
        assert r["tracked"] is True
        assert r["rating"] == 4.8

    def test_track_feedback_not_found(self):
        r = self.mf.track_feedback(
            session_id="invalid"
        )
        assert r["tracked"] is False


# ── SelfDevOrchestrator ───────────────────────


class TestSelfDevOrchestrator:
    """SelfDevOrchestrator testleri."""

    def setup_method(self):
        self.so = SelfDevOrchestrator()

    def test_init(self):
        a = self.so.get_analytics()
        assert a["retrieved"] is True
        assert a["components"] == 8

    def test_full_learning_cycle(self):
        skills = [
            {"name": "python", "level": "beginner"},
        ]
        r = self.so.full_learning_cycle(
            skills=skills,
            target_level="intermediate",
            daily_minutes=30,
        )
        assert r["completed"] is True
        assert "assessment" in r
        assert "gaps" in r
        assert "plan" in r
        assert "courses" in r

    def test_daily_briefing(self):
        r = self.so.daily_briefing()
        assert r["briefed"] is True
        assert "progress" in r

    def test_get_analytics(self):
        r = self.so.get_analytics()
        assert r["skills"] == 0
        assert r["courses"] == 0
        assert r["certifications"] == 0

    def test_analytics_after_cycle(self):
        self.so.full_learning_cycle(
            skills=[
                {"name": "go", "level": "novice"},
            ],
        )
        r = self.so.get_analytics()
        assert r["skills"] >= 1
        assert r["plans"] >= 1
