"""Intelligent Heartbeat Engine test suite."""

import time
import pytest

from app.models.heartbeat_models import (
    DigestEntry, HeartbeatConfig, HeartbeatResult, HeartbeatStatus,
    HeartbeatTemplate, ImportanceLevel, QuietHoursConfig,
)
from app.core.heartbeat.heartbeat_engine import HeartbeatEngine
from app.core.heartbeat.importance_scorer import ImportanceScorer
from app.core.heartbeat.quiet_hours import HeartbeatQuietHours
from app.core.heartbeat.digest_accumulator import DigestAccumulator


class TestHeartbeatModels:
    def test_heartbeat_status_values(self) -> None:
        assert HeartbeatStatus.OK == "ok"
        assert HeartbeatStatus.CRITICAL == "critical"

    def test_importance_level_values(self) -> None:
        assert ImportanceLevel.NONE == "none"
        assert ImportanceLevel.CRITICAL == "critical"

    def test_heartbeat_result_defaults(self) -> None:
        r = HeartbeatResult()
        assert r.heartbeat_id == ""
        assert r.status == HeartbeatStatus.OK
        assert r.findings == []
        assert r.should_notify is False

    def test_template_defaults(self) -> None:
        t = HeartbeatTemplate()
        assert t.interval_minutes == 15
        assert t.enabled is True

    def test_quiet_hours_defaults(self) -> None:
        c = QuietHoursConfig()
        assert c.enabled is False
        assert len(c.days) == 7

    def test_config_defaults(self) -> None:
        c = HeartbeatConfig()
        assert c.default_interval == 15
        assert "OK" in c.ok_responses

    def test_digest_entry_defaults(self) -> None:
        e = DigestEntry()
        assert e.importance == ImportanceLevel.LOW


class TestHeartbeatEngine:
    def test_init_defaults(self) -> None:
        engine = HeartbeatEngine()
        assert engine.get_stats()["total_templates"] == 0

    def test_save_load_template(self) -> None:
        e = HeartbeatEngine()
        t = HeartbeatTemplate(template_id="t1", name="Test", content="HEARTBEAT_OK")
        assert e.save_template(t) is True
        assert e.load_template("t1").name == "Test"

    def test_save_template_auto_id(self) -> None:
        e = HeartbeatEngine()
        t = HeartbeatTemplate(name="Auto")
        e.save_template(t)
        assert t.template_id != ""

    def test_list_templates(self) -> None:
        e = HeartbeatEngine()
        e.save_template(HeartbeatTemplate(template_id="a"))
        e.save_template(HeartbeatTemplate(template_id="b"))
        assert len(e.list_templates()) == 2

    def test_run_missing(self) -> None:
        assert HeartbeatEngine().run_heartbeat("x").status == HeartbeatStatus.SKIPPED

    def test_run_disabled(self) -> None:
        e = HeartbeatEngine()
        e.save_template(HeartbeatTemplate(template_id="t1", content="OK", enabled=False))
        assert e.run_heartbeat("t1").status == HeartbeatStatus.SKIPPED

    def test_run_ok(self) -> None:
        e = HeartbeatEngine()
        e.save_template(HeartbeatTemplate(template_id="t1", content="HEARTBEAT_OK"))
        r = e.run_heartbeat("t1")
        assert r.status == HeartbeatStatus.OK
        assert r.heartbeat_id != ""

    def test_run_warning(self) -> None:
        e = HeartbeatEngine()
        e.save_template(HeartbeatTemplate(template_id="t1", content="WARNING: disk high"))
        assert e.run_heartbeat("t1").status == HeartbeatStatus.WARNING

    def test_run_critical(self) -> None:
        e = HeartbeatEngine()
        e.save_template(HeartbeatTemplate(template_id="t1", content="CRITICAL: down"))
        assert e.run_heartbeat("t1").status == HeartbeatStatus.CRITICAL

    def test_process_empty(self) -> None:
        assert HeartbeatEngine().process_response("").status == HeartbeatStatus.SILENT

    def test_process_strip_prefix(self) -> None:
        assert HeartbeatEngine().process_response("Status: ALL_CLEAR").status == HeartbeatStatus.OK

    def test_schedule_cancel(self) -> None:
        e = HeartbeatEngine()
        e.save_template(HeartbeatTemplate(template_id="t1"))
        assert e.schedule_heartbeat("t1", 5) is True
        assert e.cancel_heartbeat("t1") is True

    def test_schedule_missing(self) -> None:
        assert HeartbeatEngine().schedule_heartbeat("x") is False

    def test_inject_metadata(self) -> None:
        t = HeartbeatTemplate(template_id="t1")
        HeartbeatEngine().inject_metadata(t, {"host": "srv1"})
        assert t.metadata["host"] == "srv1"

    def test_last_result(self) -> None:
        e = HeartbeatEngine()
        e.save_template(HeartbeatTemplate(template_id="t1", content="OK"))
        e.run_heartbeat("t1")
        assert e.get_last_result("t1") is not None

    def test_is_healthy_empty(self) -> None:
        assert HeartbeatEngine().is_healthy() is True

    def test_is_healthy_critical(self) -> None:
        e = HeartbeatEngine()
        e.save_template(HeartbeatTemplate(template_id="t1", content="CRITICAL err"))
        e.run_heartbeat("t1")
        assert e.is_healthy() is False

    def test_sender_metadata(self) -> None:
        e = HeartbeatEngine(config=HeartbeatConfig(sender_metadata={"env": "prod"}))
        e.save_template(HeartbeatTemplate(template_id="t1", content="OK"))
        assert e.run_heartbeat("t1").metrics.get("env") == "prod"

    def test_history(self) -> None:
        e = HeartbeatEngine()
        e.save_template(HeartbeatTemplate(template_id="t1", content="OK"))
        e.run_heartbeat("t1")
        assert len(e.get_history()) >= 2


class TestImportanceScorer:
    def test_score_critical(self) -> None:
        s = ImportanceScorer()
        r = HeartbeatResult(status=HeartbeatStatus.CRITICAL)
        assert s.score(r) == ImportanceLevel.CRITICAL

    def test_score_warning(self) -> None:
        s = ImportanceScorer()
        r = HeartbeatResult(status=HeartbeatStatus.WARNING)
        assert s.score(r) == ImportanceLevel.MEDIUM

    def test_score_warning_many_findings(self) -> None:
        s = ImportanceScorer()
        r = HeartbeatResult(status=HeartbeatStatus.WARNING, findings=["a", "b"])
        assert s.score(r) == ImportanceLevel.HIGH

    def test_score_ok_no_findings(self) -> None:
        s = ImportanceScorer()
        r = HeartbeatResult(status=HeartbeatStatus.OK)
        assert s.score(r) == ImportanceLevel.NONE

    def test_score_silent(self) -> None:
        s = ImportanceScorer()
        r = HeartbeatResult(status=HeartbeatStatus.SILENT)
        assert s.score(r) == ImportanceLevel.LOW

    def test_should_notify_critical(self) -> None:
        s = ImportanceScorer()
        r = HeartbeatResult(importance=ImportanceLevel.CRITICAL)
        assert s.should_notify(r) is True

    def test_should_notify_none(self) -> None:
        s = ImportanceScorer()
        r = HeartbeatResult(importance=ImportanceLevel.NONE)
        assert s.should_notify(r) is False

    def test_classify_findings(self) -> None:
        s = ImportanceScorer()
        c = s.classify_findings(["CRITICAL issue", "WARNING low", "info msg"])
        assert len(c["critical"]) == 1
        assert len(c["warning"]) == 1
        assert len(c["info"]) == 1

    def test_compare_first_run(self) -> None:
        s = ImportanceScorer()
        r = HeartbeatResult()
        c = s.compare_with_previous(r, None)
        assert c["first_run"] is True

    def test_compare_changed(self) -> None:
        s = ImportanceScorer()
        prev = HeartbeatResult(status=HeartbeatStatus.OK)
        curr = HeartbeatResult(status=HeartbeatStatus.WARNING)
        c = s.compare_with_previous(curr, prev)
        assert c["changed"] is True

    def test_adjust_threshold(self) -> None:
        s = ImportanceScorer()
        s.adjust_threshold({"warning_weight": 0.8})
        assert s._thresholds["warning_weight"] == 0.8

    def test_scorer_history(self) -> None:
        s = ImportanceScorer()
        s.score(HeartbeatResult(status=HeartbeatStatus.OK))
        assert len(s.get_history()) >= 1

    def test_scorer_stats(self) -> None:
        s = ImportanceScorer()
        stats = s.get_stats()
        assert "total_scores" in stats


class TestQuietHours:
    def test_init_defaults(self) -> None:
        qh = HeartbeatQuietHours()
        assert qh.config.enabled is False

    def test_not_quiet_when_disabled(self) -> None:
        qh = HeartbeatQuietHours()
        assert qh.is_quiet_time() is False

    def test_set_quiet_hours(self) -> None:
        qh = HeartbeatQuietHours()
        qh.set_quiet_hours(22, 6)
        assert qh.config.enabled is True
        assert qh.config.start_hour == 22
        assert qh.config.end_hour == 6

    def test_get_config(self) -> None:
        qh = HeartbeatQuietHours()
        cfg = qh.get_config()
        assert cfg.timezone == "UTC"

    def test_should_override_critical(self) -> None:
        qh = HeartbeatQuietHours(config=QuietHoursConfig(override_critical=True))
        assert qh.should_override(ImportanceLevel.CRITICAL) is True

    def test_should_not_override_low(self) -> None:
        qh = HeartbeatQuietHours()
        assert qh.should_override(ImportanceLevel.LOW) is False

    def test_next_active_time_disabled(self) -> None:
        qh = HeartbeatQuietHours()
        assert qh.next_active_time() is None

    def test_next_active_time_enabled(self) -> None:
        qh = HeartbeatQuietHours(config=QuietHoursConfig(enabled=True, end_hour=8))
        assert qh.next_active_time() == 8

    def test_add_exception(self) -> None:
        qh = HeartbeatQuietHours()
        qh.add_exception("2026-01-01")
        assert "2026-01-01" in qh._exceptions

    def test_quiet_hours_history(self) -> None:
        qh = HeartbeatQuietHours()
        qh.set_quiet_hours(22, 6)
        assert len(qh.get_history()) >= 1

    def test_quiet_hours_stats(self) -> None:
        qh = HeartbeatQuietHours()
        assert "enabled" in qh.get_stats()


class TestDigestAccumulator:
    def test_init_defaults(self) -> None:
        da = DigestAccumulator()
        assert da.get_stats()["pending_entries"] == 0

    def test_add_entry(self) -> None:
        da = DigestAccumulator()
        r = HeartbeatResult(heartbeat_id="hb1", message="test msg", timestamp=time.time())
        assert da.add(r) is True
        assert len(da.get_pending()) == 1

    def test_add_overflow(self) -> None:
        da = DigestAccumulator(config=HeartbeatConfig(max_digest_size=2))
        for i in range(3):
            da.add(HeartbeatResult(heartbeat_id=f"hb{i}", timestamp=time.time()))
        assert len(da.get_pending()) == 2

    def test_compile_digest(self) -> None:
        da = DigestAccumulator()
        da.add(HeartbeatResult(heartbeat_id="hb1", importance=ImportanceLevel.LOW, timestamp=time.time()))
        da.add(HeartbeatResult(heartbeat_id="hb2", importance=ImportanceLevel.CRITICAL, timestamp=time.time()))
        compiled = da.compile_digest()
        assert len(compiled) == 2
        assert compiled[0].importance == ImportanceLevel.CRITICAL

    def test_should_send_empty(self) -> None:
        da = DigestAccumulator()
        assert da.should_send() is False

    def test_should_send_with_entries(self) -> None:
        da = DigestAccumulator(config=HeartbeatConfig(digest_interval_minutes=0))
        da.add(HeartbeatResult(heartbeat_id="hb1", timestamp=time.time()))
        da._last_compile_time = time.time() - 120
        assert da.should_send() is True

    def test_clear(self) -> None:
        da = DigestAccumulator()
        da.add(HeartbeatResult(heartbeat_id="hb1", timestamp=time.time()))
        da.clear()
        assert len(da.get_pending()) == 0

    def test_set_interval(self) -> None:
        da = DigestAccumulator()
        da.set_interval(30)
        assert da.config.digest_interval_minutes == 30

    def test_set_interval_min(self) -> None:
        da = DigestAccumulator()
        da.set_interval(0)
        assert da.config.digest_interval_minutes == 1

    def test_get_summary_empty(self) -> None:
        da = DigestAccumulator()
        s = da.get_summary()
        assert s["total_pending"] == 0
        assert s["oldest"] is None

    def test_get_summary_with_entries(self) -> None:
        da = DigestAccumulator()
        da.add(HeartbeatResult(heartbeat_id="hb1", importance=ImportanceLevel.HIGH, timestamp=time.time()))
        s = da.get_summary()
        assert s["total_pending"] == 1
        assert "high" in s["by_importance"]

    def test_accumulator_history(self) -> None:
        da = DigestAccumulator()
        da.add(HeartbeatResult(heartbeat_id="hb1", timestamp=time.time()))
        assert len(da.get_history()) >= 1

    def test_accumulator_stats(self) -> None:
        da = DigestAccumulator()
        stats = da.get_stats()
        assert "pending_entries" in stats
        assert "max_digest_size" in stats
