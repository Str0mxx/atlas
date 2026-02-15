"""ATLAS Contextual Availability & Priority testleri.

Müsaitlik öğrenme, öncelik puanlama,
mesaj tamponlama, kesme kararı,
rutin tespiti, sessiz saat yönetimi,
aciliyet geçersiz kılma, özet derleme,
orkestrasyon testleri.
"""

import pytest

from app.models.availability_models import (
    AvailabilityState,
    PriorityLevel,
    InterruptAction,
    RoutineType,
    DigestFrequency,
    OverrideReason,
    AvailabilityRecord,
    BufferedMessage,
    RoutineRecord,
    AvailabilitySnapshot,
)
from app.core.availability.availability_learner import (
    AvailabilityLearner,
)
from app.core.availability.priority_scorer import (
    ContextualPriorityScorer,
)
from app.core.availability.message_buffer import (
    MessageBuffer,
)
from app.core.availability.interrupt_decider import (
    InterruptDecider,
)
from app.core.availability.routine_detector import (
    RoutineDetector,
)
from app.core.availability.quiet_hours_manager import (
    QuietHoursManager,
)
from app.core.availability.urgency_override import (
    UrgencyOverride,
)
from app.core.availability.digest_compiler import (
    DigestCompiler,
)
from app.core.availability.availability_orchestrator import (
    AvailabilityOrchestrator,
)


# ========== Model Testleri ==========


class TestAvailabilityModels:
    """Model testleri."""

    def test_availability_state_enum(self):
        assert AvailabilityState.available == "available"
        assert AvailabilityState.busy == "busy"
        assert AvailabilityState.away == "away"
        assert AvailabilityState.dnd == "dnd"
        assert AvailabilityState.sleeping == "sleeping"
        assert AvailabilityState.offline == "offline"

    def test_priority_level_enum(self):
        assert PriorityLevel.critical == "critical"
        assert PriorityLevel.high == "high"
        assert PriorityLevel.medium == "medium"
        assert PriorityLevel.low == "low"
        assert PriorityLevel.informational == "informational"
        assert PriorityLevel.deferred == "deferred"

    def test_interrupt_action_enum(self):
        assert InterruptAction.deliver_now == "deliver_now"
        assert InterruptAction.buffer == "buffer"
        assert InterruptAction.digest == "digest"
        assert InterruptAction.escalate == "escalate"
        assert InterruptAction.discard == "discard"
        assert InterruptAction.schedule == "schedule"

    def test_routine_type_enum(self):
        assert RoutineType.daily == "daily"
        assert RoutineType.weekly == "weekly"
        assert RoutineType.workday == "workday"
        assert RoutineType.weekend == "weekend"
        assert RoutineType.custom == "custom"
        assert RoutineType.exception == "exception"

    def test_digest_frequency_enum(self):
        assert DigestFrequency.hourly == "hourly"
        assert DigestFrequency.every_4h == "every_4h"
        assert DigestFrequency.daily == "daily"
        assert DigestFrequency.twice_daily == "twice_daily"
        assert DigestFrequency.weekly == "weekly"
        assert DigestFrequency.on_available == "on_available"

    def test_override_reason_enum(self):
        assert OverrideReason.emergency == "emergency"
        assert OverrideReason.security == "security"
        assert OverrideReason.financial == "financial"
        assert OverrideReason.deadline == "deadline"
        assert OverrideReason.user_request == "user_request"
        assert OverrideReason.system_critical == "system_critical"

    def test_availability_record_model(self):
        record = AvailabilityRecord(
            user_id="u1",
            state=AvailabilityState.busy,
        )
        assert record.user_id == "u1"
        assert record.state == AvailabilityState.busy
        assert record.record_id
        assert record.confidence == 0.5
        assert record.created_at

    def test_buffered_message_model(self):
        msg = BufferedMessage(
            content="test",
            priority=PriorityLevel.high,
        )
        assert msg.content == "test"
        assert msg.priority == PriorityLevel.high
        assert msg.message_id
        assert msg.action == InterruptAction.buffer

    def test_routine_record_model(self):
        record = RoutineRecord(
            name="morning",
            routine_type=RoutineType.daily,
            start_hour=8,
            end_hour=12,
        )
        assert record.name == "morning"
        assert record.routine_type == RoutineType.daily
        assert record.start_hour == 8
        assert record.end_hour == 12

    def test_availability_snapshot_model(self):
        snap = AvailabilitySnapshot(
            current_state=AvailabilityState.dnd,
            buffered_count=5,
        )
        assert snap.current_state == AvailabilityState.dnd
        assert snap.buffered_count == 5
        assert snap.snapshot_id
        assert snap.quiet_hours_active is False


# ========== AvailabilityLearner Testleri ==========


class TestAvailabilityLearner:
    """Müsaitlik öğrenici testleri."""

    def test_init(self):
        learner = AvailabilityLearner()
        assert learner.observation_count == 0
        assert learner.pattern_count == 0

    def test_observe(self):
        learner = AvailabilityLearner()
        result = learner.observe(
            state="available", hour=9, day_of_week=1,
        )
        assert result["recorded"] is True
        assert result["state"] == "available"
        assert learner.observation_count == 1

    def test_observe_multiple(self):
        learner = AvailabilityLearner(min_observations=3)
        for _ in range(5):
            learner.observe(state="available", hour=9)
        assert learner.observation_count == 5
        assert learner.pattern_count > 0

    def test_pattern_learning(self):
        learner = AvailabilityLearner(min_observations=3)
        for _ in range(5):
            learner.observe(state="busy", hour=14, day_of_week=2)
        result = learner.predict(hour=14, day_of_week=2)
        assert result["predicted_state"] == "busy"
        assert result["confidence"] > 0

    def test_predict_unknown(self):
        learner = AvailabilityLearner()
        result = learner.predict(hour=3, day_of_week=5)
        assert result["predicted_state"] == "unknown"
        assert result["confidence"] == 0.0

    def test_detect_schedule(self):
        learner = AvailabilityLearner(min_observations=3)
        for _ in range(5):
            learner.observe(state="available", hour=9)
            learner.observe(state="busy", hour=14)
        result = learner.detect_schedule()
        assert result["schedule_detected"] is True
        assert 9 in result["active_hours"]

    def test_detect_schedule_insufficient_data(self):
        learner = AvailabilityLearner()
        result = learner.detect_schedule()
        assert result["schedule_detected"] is False

    def test_analyze_behavior(self):
        learner = AvailabilityLearner()
        learner.observe(state="available", hour=9)
        learner.observe(state="available", hour=10)
        learner.observe(state="busy", hour=14)
        result = learner.analyze_behavior()
        assert result["analyzed"] is True
        assert result["total_observations"] == 3
        assert result["dominant_state"] == "available"
        assert result["availability_rate"] > 0

    def test_analyze_behavior_empty(self):
        learner = AvailabilityLearner()
        result = learner.analyze_behavior()
        assert result["analyzed"] is False

    def test_anomaly_detection(self):
        learner = AvailabilityLearner(min_observations=3)
        # Kalıp oluştur
        for _ in range(5):
            learner.observe(state="available", hour=9, day_of_week=0)
        # Anomali gözlemleri — kalıp öğrenildikten sonra
        learner.observe(state="busy", hour=9, day_of_week=0)
        assert learner.anomaly_count >= 1

    def test_get_anomalies(self):
        learner = AvailabilityLearner(min_observations=3)
        for _ in range(5):
            learner.observe(state="available", hour=10, day_of_week=1)
        learner.observe(state="dnd", hour=10, day_of_week=1)
        anomalies = learner.get_anomalies()
        assert isinstance(anomalies, list)

    def test_observe_with_context(self):
        learner = AvailabilityLearner()
        result = learner.observe(
            state="busy", hour=15,
            context={"meeting": True},
        )
        assert result["recorded"] is True


# ========== ContextualPriorityScorer Testleri ==========


class TestContextualPriorityScorer:
    """Öncelik puanlayıcı testleri."""

    def test_init(self):
        scorer = ContextualPriorityScorer()
        assert scorer.scores_calculated == 0

    def test_score_basic(self):
        scorer = ContextualPriorityScorer()
        result = scorer.score(
            message="test message",
            source="user",
            urgency=0.5,
            impact=0.5,
        )
        assert "total_score" in result
        assert "level" in result
        assert "factors" in result
        assert 0 <= result["total_score"] <= 1
        assert scorer.scores_calculated == 1

    def test_score_high_urgency(self):
        scorer = ContextualPriorityScorer()
        result = scorer.score(
            message="urgent",
            source="security",
            urgency=1.0,
            impact=0.9,
        )
        assert result["total_score"] > 0.5
        assert result["level"] in ("critical", "high")

    def test_score_low_priority(self):
        scorer = ContextualPriorityScorer()
        result = scorer.score(
            message="info",
            source="notification",
            urgency=0.1,
            impact=0.1,
        )
        assert result["total_score"] < 0.5

    def test_score_with_context(self):
        scorer = ContextualPriorityScorer()
        r1 = scorer.score(
            message="task", urgency=0.5, impact=0.5,
        )
        r2 = scorer.score(
            message="task", urgency=0.5, impact=0.5,
            context={"deadline": True, "financial": True},
        )
        assert r2["total_score"] >= r1["total_score"]

    def test_calculate_urgency_deadline(self):
        scorer = ContextualPriorityScorer()
        result = scorer.calculate_urgency(
            deadline_hours=0.5,
        )
        assert result["urgency"] == 1.0

    def test_calculate_urgency_no_deadline(self):
        scorer = ContextualPriorityScorer()
        result = scorer.calculate_urgency(
            severity="high",
        )
        assert result["urgency"] == 0.7  # 0.5 + 0.2

    def test_calculate_urgency_with_dependencies(self):
        scorer = ContextualPriorityScorer()
        result = scorer.calculate_urgency(
            deadline_hours=24, dependencies=3,
        )
        assert result["urgency"] > 0.6

    def test_assess_impact_organization(self):
        scorer = ContextualPriorityScorer()
        result = scorer.assess_impact(
            scope="organization",
            reversible=False,
        )
        assert result["impact"] >= 1.0

    def test_assess_impact_individual(self):
        scorer = ContextualPriorityScorer()
        result = scorer.assess_impact(
            scope="individual", reversible=True,
        )
        assert result["impact"] == 0.3

    def test_assess_impact_financial(self):
        scorer = ContextualPriorityScorer()
        result = scorer.assess_impact(
            scope="project",
            financial_impact=15000,
        )
        assert result["impact"] > 0.5

    def test_adjust_weight(self):
        scorer = ContextualPriorityScorer()
        result = scorer.adjust_weight("urgency", 0.5)
        assert result["adjusted"] is True
        assert result["new_weight"] == 0.5
        assert scorer.adjustments_made == 1

    def test_adjust_weight_invalid(self):
        scorer = ContextualPriorityScorer()
        result = scorer.adjust_weight("invalid", 0.5)
        assert "error" in result

    def test_set_source_priority(self):
        scorer = ContextualPriorityScorer()
        result = scorer.set_source_priority("custom", 0.7)
        assert result["set"] is True
        assert result["priority"] == 0.7

    def test_get_scores(self):
        scorer = ContextualPriorityScorer()
        scorer.score(message="a", urgency=0.3)
        scorer.score(message="b", urgency=0.7)
        scores = scorer.get_scores()
        assert len(scores) == 2

    def test_get_scores_min_filter(self):
        scorer = ContextualPriorityScorer()
        scorer.score(message="low", urgency=0.1, impact=0.1)
        scorer.score(message="high", urgency=0.9, impact=0.9)
        scores = scorer.get_scores(min_score=0.5)
        assert len(scores) >= 1


# ========== MessageBuffer Testleri ==========


class TestMessageBuffer:
    """Mesaj tamponu testleri."""

    def test_init(self):
        buffer = MessageBuffer()
        assert buffer.size == 0
        assert buffer.queued_count == 0

    def test_enqueue(self):
        buffer = MessageBuffer()
        result = buffer.enqueue(
            content="test message",
            priority="high",
        )
        assert result["queued"] is True
        assert buffer.size == 1
        assert buffer.queued_count == 1

    def test_enqueue_dedup(self):
        buffer = MessageBuffer()
        buffer.enqueue(
            content="msg1", dedup_key="key1",
        )
        result = buffer.enqueue(
            content="msg1 copy", dedup_key="key1",
        )
        assert result["queued"] is False
        assert result["reason"] == "duplicate"
        assert buffer.size == 1

    def test_enqueue_max_size(self):
        buffer = MessageBuffer(max_size=3)
        buffer.enqueue(content="a", priority="low")
        buffer.enqueue(content="b", priority="medium")
        buffer.enqueue(content="c", priority="high")
        # Tam dolu, yenisini ekle: en düşük çıkarılır
        buffer.enqueue(content="d", priority="critical")
        assert buffer.size == 3

    def test_dequeue(self):
        buffer = MessageBuffer()
        buffer.enqueue(content="msg1", priority="high")
        buffer.enqueue(content="msg2", priority="low")
        results = buffer.dequeue(count=1)
        assert len(results) == 1
        assert results[0]["priority"] == "high"
        assert buffer.size == 1

    def test_dequeue_multiple(self):
        buffer = MessageBuffer()
        buffer.enqueue(content="a")
        buffer.enqueue(content="b")
        buffer.enqueue(content="c")
        results = buffer.dequeue(count=2)
        assert len(results) == 2
        assert buffer.delivered_count == 2

    def test_batch_collect(self):
        buffer = MessageBuffer()
        buffer.enqueue(content="a", priority="high")
        buffer.enqueue(content="b", priority="low")
        buffer.enqueue(content="c", priority="informational")
        collected = buffer.batch_collect(min_priority="medium")
        # high >= medium
        assert len(collected) == 1

    def test_batch_collect_all(self):
        buffer = MessageBuffer()
        buffer.enqueue(content="a", priority="high")
        buffer.enqueue(content="b", priority="low")
        collected = buffer.batch_collect(min_priority="low")
        assert len(collected) == 2

    def test_peek(self):
        buffer = MessageBuffer()
        buffer.enqueue(content="a", priority="low")
        buffer.enqueue(content="b", priority="high")
        peeked = buffer.peek(count=2)
        assert len(peeked) == 2
        assert peeked[0]["priority"] == "high"
        assert buffer.size == 2  # Peek kaldırmaz

    def test_get_stats(self):
        buffer = MessageBuffer()
        buffer.enqueue(content="a")
        buffer.enqueue(content="b")
        buffer.dequeue(count=1)
        stats = buffer.get_stats()
        assert stats["buffer_size"] == 1
        assert stats["total_queued"] == 2
        assert stats["total_delivered"] == 1

    def test_clear(self):
        buffer = MessageBuffer()
        buffer.enqueue(content="a")
        buffer.enqueue(content="b")
        result = buffer.clear()
        assert result["cleared"] is True
        assert result["messages_removed"] == 2
        assert buffer.size == 0

    def test_ttl(self):
        buffer = MessageBuffer(default_ttl=1)
        buffer.enqueue(content="quick", ttl=0)
        # TTL 0 saniye - hemen expire olacak
        import time
        time.sleep(0.01)
        buffer._cleanup_expired()
        assert buffer.size == 0


# ========== InterruptDecider Testleri ==========


class TestInterruptDecider:
    """Kesme kararıcı testleri."""

    def test_init(self):
        decider = InterruptDecider()
        assert decider.decisions_made == 0

    def test_decide_available_high_priority(self):
        decider = InterruptDecider()
        result = decider.decide(
            priority_score=0.8,
            user_state="available",
        )
        assert result["should_interrupt"] is True
        assert result["action"] == "deliver_now"
        assert decider.decisions_made == 1

    def test_decide_available_low_priority(self):
        decider = InterruptDecider()
        result = decider.decide(
            priority_score=0.1,
            user_state="available",
        )
        assert result["should_interrupt"] is False

    def test_decide_busy(self):
        decider = InterruptDecider()
        result = decider.decide(
            priority_score=0.5,
            user_state="busy",
        )
        # busy threshold 0.8, 0.5 < 0.8
        assert result["should_interrupt"] is False

    def test_decide_dnd(self):
        decider = InterruptDecider()
        result = decider.decide(
            priority_score=0.9,
            user_state="dnd",
        )
        # dnd threshold 0.95, 0.9 < 0.95
        assert result["should_interrupt"] is False

    def test_decide_quiet_hours(self):
        decider = InterruptDecider()
        result = decider.decide(
            priority_score=0.7,
            is_quiet_hours=True,
        )
        # quiet threshold 0.9, 0.7 < 0.9
        assert result["should_interrupt"] is False
        assert result["action"] in ("buffer", "digest")

    def test_decide_emergency_override(self):
        decider = InterruptDecider()
        result = decider.decide(
            priority_score=0.5,
            user_state="dnd",
            context={"emergency": True},
        )
        assert result["should_interrupt"] is True
        assert result["override_applied"] is True

    def test_decide_force_deliver(self):
        decider = InterruptDecider()
        result = decider.decide(
            priority_score=0.3,
            user_state="busy",
            context={"force_deliver": True},
        )
        assert result["should_interrupt"] is True

    def test_benefit_cost_analysis(self):
        decider = InterruptDecider()
        result = decider.decide(
            priority_score=0.6,
            user_state="busy",
        )
        assert "benefit" in result
        assert "cost" in result
        assert "net_value" in result

    def test_set_threshold(self):
        decider = InterruptDecider()
        result = decider.set_threshold("busy", 0.5)
        assert result["set"] is True
        assert result["new_threshold"] == 0.5

    def test_add_override(self):
        decider = InterruptDecider()
        result = decider.add_override(
            name="vip", condition="source:vip",
        )
        assert result["added"] is True

    def test_get_decisions(self):
        decider = InterruptDecider()
        decider.decide(priority_score=0.5)
        decider.decide(priority_score=0.9)
        decisions = decider.get_decisions()
        assert len(decisions) == 2

    def test_interrupt_rate(self):
        decider = InterruptDecider()
        decider.decide(priority_score=0.9, user_state="available")
        decider.decide(priority_score=0.1, user_state="available")
        rate = decider.interrupt_rate
        assert rate == 50.0


# ========== RoutineDetector Testleri ==========


class TestRoutineDetector:
    """Rutin tespitçisi testleri."""

    def test_init(self):
        detector = RoutineDetector()
        assert detector.event_count == 0
        assert detector.routine_count == 0

    def test_record_event(self):
        detector = RoutineDetector()
        result = detector.record_event(
            event_type="work", hour=9,
        )
        assert result["recorded"] is True
        assert detector.event_count == 1

    def test_detect_daily_patterns(self):
        detector = RoutineDetector(min_occurrences=3)
        for _ in range(5):
            detector.record_event(
                event_type="work", hour=9,
            )
        patterns = detector.detect_daily_patterns()
        assert len(patterns) > 0
        assert patterns[0]["type"] == "daily"
        assert patterns[0]["hour"] == 9

    def test_detect_daily_patterns_insufficient(self):
        detector = RoutineDetector(min_occurrences=5)
        detector.record_event(event_type="work", hour=9)
        patterns = detector.detect_daily_patterns()
        assert len(patterns) == 0

    def test_detect_weekly_patterns(self):
        detector = RoutineDetector(min_occurrences=3)
        for _ in range(5):
            detector.record_event(
                event_type="meeting",
                hour=14, day_of_week=3,
            )
        patterns = detector.detect_weekly_patterns()
        assert len(patterns) > 0
        assert patterns[0]["type"] == "weekly"
        assert patterns[0]["day_of_week"] == 3

    def test_detect_exceptions(self):
        detector = RoutineDetector(min_occurrences=3)
        for _ in range(5):
            detector.record_event(
                event_type="work", hour=9,
            )
        detector.detect_daily_patterns()
        # İstisna olay ekle
        detector.record_event(
            event_type="holiday", hour=9,
        )
        exceptions = detector.detect_exceptions()
        assert isinstance(exceptions, list)

    def test_learn_habit(self):
        detector = RoutineDetector()
        result = detector.learn_habit(
            name="coffee",
            event_type="break",
            hour=10,
        )
        assert result["learned"] is True
        assert detector.habit_count == 1

    def test_predict_from_daily(self):
        detector = RoutineDetector(min_occurrences=3)
        for _ in range(5):
            detector.record_event(
                event_type="work", hour=9,
            )
        detector.detect_daily_patterns()
        result = detector.predict(hour=9)
        assert result["predicted_event"] == "work"
        assert result["source"] == "daily_pattern"

    def test_predict_from_habit(self):
        detector = RoutineDetector()
        detector.learn_habit(
            name="lunch",
            event_type="break",
            hour=12,
            days=[0, 1, 2, 3, 4],
        )
        result = detector.predict(
            hour=12, day_of_week=2,
        )
        assert result["predicted_event"] == "break"
        assert "habit" in result["source"]

    def test_predict_unknown(self):
        detector = RoutineDetector()
        result = detector.predict(hour=3, day_of_week=6)
        assert result["predicted_event"] == "unknown"

    def test_get_routines(self):
        detector = RoutineDetector(min_occurrences=3)
        for _ in range(5):
            detector.record_event(
                event_type="work", hour=9,
            )
        detector.detect_daily_patterns()
        routines = detector.get_routines()
        assert len(routines) > 0

    def test_get_routines_filtered(self):
        detector = RoutineDetector(min_occurrences=3)
        for _ in range(5):
            detector.record_event(event_type="a", hour=9)
            detector.record_event(
                event_type="b", hour=14, day_of_week=2,
            )
        detector.detect_daily_patterns()
        detector.detect_weekly_patterns()
        daily = detector.get_routines(routine_type="daily")
        weekly = detector.get_routines(routine_type="weekly")
        assert all(r["type"] == "daily" for r in daily)
        assert all(r["type"] == "weekly" for r in weekly)


# ========== QuietHoursManager Testleri ==========


class TestQuietHoursManager:
    """Sessiz saat yöneticisi testleri."""

    def test_init(self):
        mgr = QuietHoursManager()
        assert mgr.period_count == 1  # Varsayılan

    def test_define_period(self):
        mgr = QuietHoursManager()
        result = mgr.define_period(
            "lunch", "12:00", "13:00",
        )
        assert result["defined"] is True
        assert mgr.period_count == 2

    def test_is_quiet_hours_yes(self):
        mgr = QuietHoursManager(
            default_start="22:00",
            default_end="08:00",
        )
        result = mgr.is_quiet_hours(hour=23)
        assert result["is_quiet"] is True

    def test_is_quiet_hours_morning(self):
        mgr = QuietHoursManager(
            default_start="22:00",
            default_end="08:00",
        )
        result = mgr.is_quiet_hours(hour=5)
        assert result["is_quiet"] is True

    def test_is_quiet_hours_no(self):
        mgr = QuietHoursManager(
            default_start="22:00",
            default_end="08:00",
        )
        result = mgr.is_quiet_hours(hour=12)
        assert result["is_quiet"] is False

    def test_is_quiet_hours_boundary(self):
        mgr = QuietHoursManager(
            default_start="22:00",
            default_end="08:00",
        )
        # 22:00 tam başlangıç
        result = mgr.is_quiet_hours(hour=22, minute=0)
        assert result["is_quiet"] is True

    def test_is_quiet_hours_day_filter(self):
        mgr = QuietHoursManager()
        mgr.define_period(
            "weekend_quiet", "10:00", "12:00",
            days=[5, 6],
        )
        # Cuma (5) = sessiz
        result = mgr.is_quiet_hours(
            hour=11, day_of_week=5,
        )
        assert result["is_quiet"] is True
        # Pazartesi (0) = değil
        result = mgr.is_quiet_hours(
            hour=11, day_of_week=0,
        )
        # Varsayılan periyod devrede değil bu saatte
        # weekend_quiet da 0. gün yok
        assert result["is_quiet"] is False

    def test_auto_detect(self):
        mgr = QuietHoursManager()
        result = mgr.auto_detect(
            sleep_hours=[23, 0, 1, 2, 3, 4, 5, 6],
        )
        assert result["detected"] is True

    def test_auto_detect_no_data(self):
        mgr = QuietHoursManager()
        result = mgr.auto_detect(sleep_hours=[])
        assert result["detected"] is False

    def test_add_override(self):
        mgr = QuietHoursManager()
        result = mgr.add_override(
            name="critical_alerts",
            condition="priority:critical",
        )
        assert result["added"] is True

    def test_check_override(self):
        mgr = QuietHoursManager()
        mgr.add_override(
            name="critical",
            condition="priority:critical",
        )
        result = mgr.check_override(
            priority="critical",
        )
        assert result["override_active"] is True
        assert result["allow_through"] is True

    def test_check_override_no_match(self):
        mgr = QuietHoursManager()
        result = mgr.check_override(
            priority="low",
        )
        assert result["override_active"] is False

    def test_configure_wakeup(self):
        mgr = QuietHoursManager()
        result = mgr.configure_wakeup(
            gradual_minutes=60,
            stages=["low", "medium", "high", "all"],
        )
        assert result["configured"] is True
        assert result["gradual_minutes"] == 60

    def test_get_wakeup_stage_quiet(self):
        mgr = QuietHoursManager()
        result = mgr.get_wakeup_stage(
            minutes_until_end=60,
        )
        assert result["in_wakeup"] is False
        assert result["stage"] == "quiet"

    def test_get_wakeup_stage_active(self):
        mgr = QuietHoursManager()
        mgr.configure_wakeup(gradual_minutes=30)
        result = mgr.get_wakeup_stage(
            minutes_until_end=10,
        )
        assert result["in_wakeup"] is True

    def test_emergency_bypass(self):
        mgr = QuietHoursManager()
        result = mgr.emergency_bypass(
            reason="server_down",
        )
        assert result["bypassed"] is True
        assert mgr.bypass_count == 1

    def test_get_periods(self):
        mgr = QuietHoursManager()
        periods = mgr.get_periods()
        assert len(periods) >= 1


# ========== UrgencyOverride Testleri ==========


class TestUrgencyOverride:
    """Aciliyet geçersiz kılma testleri."""

    def test_init(self):
        uo = UrgencyOverride()
        assert uo.override_count == 0
        assert uo.emergency_count == 0

    def test_detect_emergency_by_score(self):
        uo = UrgencyOverride(emergency_threshold=0.9)
        result = uo.detect_emergency(
            message="high priority",
            priority_score=0.95,
        )
        assert result["is_emergency"] is True

    def test_detect_emergency_by_keyword(self):
        uo = UrgencyOverride()
        result = uo.detect_emergency(
            message="Security breach detected",
            priority_score=0.3,
        )
        assert result["is_emergency"] is True
        assert "security_breach" in result["matched_criteria"]

    def test_detect_emergency_no_match(self):
        uo = UrgencyOverride()
        result = uo.detect_emergency(
            message="weekly report ready",
            priority_score=0.3,
        )
        assert result["is_emergency"] is False

    def test_override(self):
        uo = UrgencyOverride()
        result = uo.override(
            reason="emergency",
            source="system",
        )
        assert result["confirmed"] is True
        assert uo.override_count == 1

    def test_override_requires_confirmation(self):
        uo = UrgencyOverride()
        result = uo.override(
            reason="budget_change",
            requires_confirmation=True,
        )
        assert result["confirmed"] is False
        assert result["requires_confirmation"] is True

    def test_confirm(self):
        uo = UrgencyOverride()
        result = uo.override(
            reason="test",
            requires_confirmation=True,
        )
        oid = result["override_id"]
        confirm_result = uo.confirm(oid, approved=True)
        assert confirm_result["approved"] is True

    def test_confirm_not_found(self):
        uo = UrgencyOverride()
        result = uo.confirm("nonexistent")
        assert "error" in result

    def test_add_criterion(self):
        uo = UrgencyOverride()
        result = uo.add_criterion(
            name="custom",
            keywords=["fire", "flood"],
            auto_override=True,
        )
        assert result["added"] is True

    def test_custom_criterion_detection(self):
        uo = UrgencyOverride()
        uo.add_criterion(
            name="natural_disaster",
            keywords=["earthquake", "tsunami"],
            auto_override=True,
        )
        result = uo.detect_emergency(
            message="earthquake detected!",
            priority_score=0.3,
        )
        assert result["is_emergency"] is True

    def test_escalate(self):
        uo = UrgencyOverride()
        result = uo.override(reason="test")
        esc = uo.escalate(
            override_id=result["override_id"],
            target="cto",
            reason="critical_decision",
        )
        assert esc["escalated"] is True
        assert uo.escalation_count == 1

    def test_get_audit_log(self):
        uo = UrgencyOverride()
        uo.detect_emergency(
            message="test", priority_score=0.5,
        )
        uo.override(reason="test")
        log = uo.get_audit_log()
        assert len(log) >= 2

    def test_get_overrides(self):
        uo = UrgencyOverride()
        uo.override(reason="a")
        uo.override(reason="b", requires_confirmation=True)
        all_overrides = uo.get_overrides()
        assert len(all_overrides) == 2
        confirmed = uo.get_overrides(confirmed_only=True)
        assert len(confirmed) == 1


# ========== DigestCompiler Testleri ==========


class TestDigestCompiler:
    """Özet derleyici testleri."""

    def test_init(self):
        compiler = DigestCompiler()
        assert compiler.digest_count == 0

    def test_compile(self):
        compiler = DigestCompiler()
        messages = [
            {"content": "msg1", "priority": "high"},
            {"content": "msg2", "priority": "low"},
            {"content": "msg3", "priority": "critical"},
        ]
        result = compiler.compile(messages)
        assert result["message_count"] == 3
        assert "summary" in result
        assert result["messages"][0]["priority"] == "critical"
        assert compiler.digest_count == 1

    def test_compile_max_items(self):
        compiler = DigestCompiler(max_items_per_digest=2)
        messages = [
            {"content": "a", "priority": "low"},
            {"content": "b", "priority": "high"},
            {"content": "c", "priority": "medium"},
        ]
        result = compiler.compile(messages)
        assert result["message_count"] == 2
        assert result["total_available"] == 3

    def test_compile_summary(self):
        compiler = DigestCompiler()
        messages = [
            {"content": "x", "priority": "critical", "source": "security"},
            {"content": "y", "priority": "high", "source": "system"},
            {"content": "z", "priority": "low", "source": "user"},
        ]
        result = compiler.compile(messages)
        summary = result["summary"]
        assert summary["total_messages"] == 3
        assert summary["high_priority_count"] == 2

    def test_compile_action_extraction(self):
        compiler = DigestCompiler()
        messages = [
            {
                "content": "Please approve the request",
                "priority": "high",
                "message_id": "m1",
            },
            {
                "content": "Regular update",
                "priority": "low",
            },
        ]
        result = compiler.compile(messages)
        assert len(result["actions"]) > 0
        assert compiler.actions_count > 0

    def test_compile_with_explicit_actions(self):
        compiler = DigestCompiler()
        messages = [
            {
                "content": "task",
                "priority": "high",
                "message_id": "m1",
                "actions": ["deploy", "test"],
            },
        ]
        result = compiler.compile(messages)
        assert len(result["actions"]) >= 2

    def test_schedule_delivery(self):
        compiler = DigestCompiler()
        result = compiler.schedule_delivery(
            user_id="u1",
            frequency="daily",
            preferred_hour=9,
        )
        assert result["scheduled"] is True

    def test_should_deliver_matching(self):
        compiler = DigestCompiler()
        compiler.schedule_delivery(
            user_id="u1", preferred_hour=9,
        )
        result = compiler.should_deliver(
            user_id="u1", current_hour=9,
        )
        assert result["should_deliver"] is True

    def test_should_deliver_not_time(self):
        compiler = DigestCompiler()
        compiler.schedule_delivery(
            user_id="u1", preferred_hour=9,
        )
        result = compiler.should_deliver(
            user_id="u1", current_hour=15,
        )
        assert result["should_deliver"] is False

    def test_should_deliver_no_schedule(self):
        compiler = DigestCompiler()
        result = compiler.should_deliver(user_id="x")
        assert result["should_deliver"] is False

    def test_get_digest(self):
        compiler = DigestCompiler()
        messages = [{"content": "x", "priority": "medium"}]
        created = compiler.compile(messages)
        result = compiler.get_digest(created["digest_id"])
        assert result["digest_id"] == created["digest_id"]

    def test_get_digest_not_found(self):
        compiler = DigestCompiler()
        result = compiler.get_digest("nonexistent")
        assert "error" in result

    def test_get_digests(self):
        compiler = DigestCompiler()
        compiler.compile([{"content": "a", "priority": "low"}])
        compiler.compile([{"content": "b", "priority": "high"}])
        digests = compiler.get_digests()
        assert len(digests) == 2


# ========== AvailabilityOrchestrator Testleri ==========


class TestAvailabilityOrchestrator:
    """Orkestratör testleri."""

    def test_init(self):
        orch = AvailabilityOrchestrator()
        assert orch.messages_processed == 0

    def test_process_message_available(self):
        orch = AvailabilityOrchestrator()
        result = orch.process_message(
            content="hello",
            source="user",
            urgency=0.8,
            impact=0.8,
            user_state="available",
            hour=12,
        )
        assert result["action"] in (
            "deliver_now", "buffer", "digest",
        )
        assert orch.messages_processed == 1

    def test_process_message_quiet_hours(self):
        orch = AvailabilityOrchestrator(
            quiet_start="22:00",
            quiet_end="08:00",
        )
        result = orch.process_message(
            content="routine update",
            urgency=0.3,
            impact=0.3,
            hour=23,
            user_state="sleeping",
        )
        assert result["action"] in ("buffer", "digest")
        assert result["is_emergency"] is False

    def test_process_message_emergency(self):
        orch = AvailabilityOrchestrator()
        result = orch.process_message(
            content="Security breach detected!",
            source="security",
            urgency=0.95,
            impact=0.95,
            hour=2,
            user_state="sleeping",
        )
        assert result["action"] == "deliver_now"
        assert result["is_emergency"] is True

    def test_process_message_buffered(self):
        orch = AvailabilityOrchestrator()
        result = orch.process_message(
            content="low priority info",
            urgency=0.1,
            impact=0.1,
            user_state="busy",
            hour=14,
        )
        assert result["action"] in ("buffer", "digest", "deliver_now")

    def test_deliver_digest(self):
        orch = AvailabilityOrchestrator()
        # Tampona mesaj ekle
        orch.buffer.enqueue(
            content="msg1", priority="high",
        )
        orch.buffer.enqueue(
            content="msg2", priority="low",
        )
        result = orch.deliver_digest()
        assert result["delivered"] is True
        assert result["message_count"] == 2

    def test_deliver_digest_empty(self):
        orch = AvailabilityOrchestrator()
        result = orch.deliver_digest()
        assert result["delivered"] is False
        assert result["reason"] == "no_messages"

    def test_deliver_digest_disabled(self):
        orch = AvailabilityOrchestrator(
            digest_enabled=False,
        )
        result = orch.deliver_digest()
        assert result["delivered"] is False
        assert result["reason"] == "digest_disabled"

    def test_get_analytics(self):
        orch = AvailabilityOrchestrator()
        orch.process_message(
            content="test",
            urgency=0.5,
            hour=12,
        )
        analytics = orch.get_analytics()
        assert analytics["messages_processed"] == 1
        assert "buffer_size" in analytics
        assert "patterns_learned" in analytics
        assert "scores_calculated" in analytics

    def test_get_status(self):
        orch = AvailabilityOrchestrator()
        status = orch.get_status()
        assert "messages_processed" in status
        assert "buffer_size" in status
        assert "learning_enabled" in status

    def test_full_pipeline(self):
        orch = AvailabilityOrchestrator()

        # 1) Normal mesaj (gündüz, available)
        r1 = orch.process_message(
            content="normal task",
            urgency=0.7,
            impact=0.6,
            hour=10,
            user_state="available",
        )
        assert r1["action"] in ("deliver_now", "buffer")

        # 2) Düşük öncelik (meşgul)
        r2 = orch.process_message(
            content="newsletter",
            urgency=0.1,
            impact=0.1,
            hour=14,
            user_state="busy",
        )

        # 3) Acil durum (gece)
        r3 = orch.process_message(
            content="Server crash detected!",
            source="security",
            urgency=0.99,
            impact=0.99,
            hour=3,
            user_state="sleeping",
        )
        assert r3["is_emergency"] is True
        assert r3["action"] == "deliver_now"

        assert orch.messages_processed == 3

    def test_learning_integration(self):
        orch = AvailabilityOrchestrator(
            learning_enabled=True,
        )
        for _ in range(6):
            orch.process_message(
                content="work task",
                urgency=0.5,
                hour=9,
                day_of_week=1,
                user_state="available",
            )
        assert orch.learner.observation_count == 6

    def test_multiple_messages(self):
        orch = AvailabilityOrchestrator()
        for i in range(10):
            orch.process_message(
                content=f"message {i}",
                urgency=i * 0.1,
                hour=12,
            )
        assert orch.messages_processed == 10
        analytics = orch.get_analytics()
        assert analytics["scores_calculated"] == 10


# ========== Config Testleri ==========


class TestAvailabilityConfig:
    """Config testleri."""

    def test_config_defaults(self):
        from app.config import Settings
        s = Settings()
        assert s.availability_learning is True
        assert s.default_quiet_start == "22:00"
        assert s.default_quiet_end == "08:00"
        assert s.emergency_override is True
        assert s.digest_enabled is True


# ========== Import Testleri ==========


class TestAvailabilityImports:
    """Import testleri."""

    def test_import_all_from_init(self):
        from app.core.availability import (
            AvailabilityLearner,
            AvailabilityOrchestrator,
            ContextualPriorityScorer,
            DigestCompiler,
            InterruptDecider,
            MessageBuffer,
            QuietHoursManager,
            RoutineDetector,
            UrgencyOverride,
        )
        assert AvailabilityLearner is not None
        assert AvailabilityOrchestrator is not None
        assert ContextualPriorityScorer is not None
        assert DigestCompiler is not None
        assert InterruptDecider is not None
        assert MessageBuffer is not None
        assert QuietHoursManager is not None
        assert RoutineDetector is not None
        assert UrgencyOverride is not None

    def test_import_all_models(self):
        from app.models.availability_models import (
            AvailabilityState,
            PriorityLevel,
            InterruptAction,
            RoutineType,
            DigestFrequency,
            OverrideReason,
            AvailabilityRecord,
            BufferedMessage,
            RoutineRecord,
            AvailabilitySnapshot,
        )
        assert AvailabilityState is not None
        assert PriorityLevel is not None
        assert InterruptAction is not None
        assert RoutineType is not None
        assert DigestFrequency is not None
        assert OverrideReason is not None
        assert AvailabilityRecord is not None
        assert BufferedMessage is not None
        assert RoutineRecord is not None
        assert AvailabilitySnapshot is not None
