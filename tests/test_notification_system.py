"""Notification & Alert System testleri.

NotificationManager, ChannelDispatcher,
AlertEngine, PreferenceManager,
TemplateEngine, DeliveryTracker,
DigestBuilder, EscalationManager,
NotificationOrchestrator testleri.
"""

import time

import pytest

from app.models.notification_system import (
    AlertRecord,
    AlertType,
    DeliveryRecord,
    DigestFrequency,
    EscalationLevel,
    NotificationChannel,
    NotificationPriority,
    NotificationRecord,
    NotificationSnapshot,
    NotificationStatus,
)

from app.core.notification.notification_manager import (
    NotificationManager,
)
from app.core.notification.channel_dispatcher import (
    ChannelDispatcher,
)
from app.core.notification.alert_engine import AlertEngine
from app.core.notification.preference_manager import (
    NotificationPreferenceManager,
)
from app.core.notification.template_engine import (
    NotificationTemplateEngine,
)
from app.core.notification.delivery_tracker import (
    DeliveryTracker,
)
from app.core.notification.digest_builder import DigestBuilder
from app.core.notification.escalation_manager import (
    EscalationManager,
)
from app.core.notification.notification_orchestrator import (
    NotificationOrchestrator,
)


# ===================== Models =====================


class TestNotificationModels:
    """Model testleri."""

    def test_notification_priority_values(self) -> None:
        assert NotificationPriority.LOW == "low"
        assert NotificationPriority.MEDIUM == "medium"
        assert NotificationPriority.HIGH == "high"
        assert NotificationPriority.CRITICAL == "critical"

    def test_notification_status_values(self) -> None:
        assert NotificationStatus.PENDING == "pending"
        assert NotificationStatus.SENT == "sent"
        assert NotificationStatus.DELIVERED == "delivered"
        assert NotificationStatus.READ == "read"
        assert NotificationStatus.FAILED == "failed"
        assert NotificationStatus.SUPPRESSED == "suppressed"

    def test_notification_channel_values(self) -> None:
        assert NotificationChannel.TELEGRAM == "telegram"
        assert NotificationChannel.EMAIL == "email"
        assert NotificationChannel.LOG == "log"

    def test_alert_type_values(self) -> None:
        assert AlertType.THRESHOLD == "threshold"
        assert AlertType.PATTERN == "pattern"
        assert AlertType.ANOMALY == "anomaly"

    def test_escalation_level_values(self) -> None:
        assert EscalationLevel.L1 == "l1"
        assert EscalationLevel.L2 == "l2"
        assert EscalationLevel.L3 == "l3"
        assert EscalationLevel.MANAGEMENT == "management"
        assert EscalationLevel.EMERGENCY == "emergency"

    def test_digest_frequency_values(self) -> None:
        assert DigestFrequency.HOURLY == "hourly"
        assert DigestFrequency.DAILY == "daily"
        assert DigestFrequency.WEEKLY == "weekly"

    def test_notification_record_defaults(self) -> None:
        rec = NotificationRecord()
        assert rec.notification_id
        assert rec.title == ""
        assert rec.priority == NotificationPriority.MEDIUM
        assert rec.status == NotificationStatus.PENDING
        assert rec.channel == NotificationChannel.LOG

    def test_notification_record_custom(self) -> None:
        rec = NotificationRecord(
            title="Test",
            message="Hello",
            priority=NotificationPriority.HIGH,
            channel=NotificationChannel.TELEGRAM,
            recipient="user1",
        )
        assert rec.title == "Test"
        assert rec.message == "Hello"
        assert rec.priority == NotificationPriority.HIGH
        assert rec.recipient == "user1"

    def test_alert_record_defaults(self) -> None:
        rec = AlertRecord()
        assert rec.alert_id
        assert rec.alert_type == AlertType.THRESHOLD
        assert rec.severity == NotificationPriority.MEDIUM
        assert not rec.acknowledged
        assert not rec.suppressed

    def test_delivery_record_defaults(self) -> None:
        rec = DeliveryRecord()
        assert rec.delivery_id
        assert rec.attempts == 0
        assert rec.status == NotificationStatus.PENDING

    def test_notification_snapshot(self) -> None:
        snap = NotificationSnapshot(
            total_notifications=10,
            pending=3,
            sent=5,
            failed=2,
            active_alerts=1,
            delivery_rate=0.833,
        )
        assert snap.total_notifications == 10
        assert snap.delivery_rate == 0.833


# =========== NotificationManager ===========


class TestNotificationManager:
    """NotificationManager testleri."""

    def test_create(self) -> None:
        mgr = NotificationManager()
        rec = mgr.create("Test", "Message")
        assert rec.title == "Test"
        assert rec.message == "Message"
        assert mgr.total_count == 1

    def test_create_with_params(self) -> None:
        mgr = NotificationManager()
        rec = mgr.create(
            "Alert", "Urgent",
            priority=NotificationPriority.CRITICAL,
            channel=NotificationChannel.TELEGRAM,
            category="security",
            recipient="admin",
        )
        assert rec.priority == NotificationPriority.CRITICAL
        assert rec.channel == NotificationChannel.TELEGRAM
        assert rec.category == "security"
        assert rec.recipient == "admin"

    def test_create_batch(self) -> None:
        mgr = NotificationManager()
        items = [
            {"title": "A", "message": "a"},
            {"title": "B", "message": "b"},
            {"title": "C", "message": "c"},
        ]
        records = mgr.create_batch(items)
        assert len(records) == 3
        assert mgr.total_count == 3

    def test_mark_sent(self) -> None:
        mgr = NotificationManager()
        rec = mgr.create("Test", "Msg")
        assert mgr.mark_sent(rec.notification_id)
        assert rec.status == NotificationStatus.SENT

    def test_mark_read(self) -> None:
        mgr = NotificationManager()
        rec = mgr.create("Test", "Msg")
        assert mgr.mark_read(rec.notification_id)
        assert rec.status == NotificationStatus.READ

    def test_mark_failed(self) -> None:
        mgr = NotificationManager()
        rec = mgr.create("Test", "Msg")
        assert mgr.mark_failed(rec.notification_id)
        assert rec.status == NotificationStatus.FAILED

    def test_mark_nonexistent(self) -> None:
        mgr = NotificationManager()
        assert not mgr.mark_sent("invalid")
        assert not mgr.mark_read("invalid")
        assert not mgr.mark_failed("invalid")

    def test_get(self) -> None:
        mgr = NotificationManager()
        rec = mgr.create("Test", "Msg")
        found = mgr.get(rec.notification_id)
        assert found is not None
        assert found.title == "Test"

    def test_get_nonexistent(self) -> None:
        mgr = NotificationManager()
        assert mgr.get("invalid") is None

    def test_get_by_priority(self) -> None:
        mgr = NotificationManager()
        mgr.create("A", "a", priority=NotificationPriority.LOW)
        mgr.create("B", "b", priority=NotificationPriority.HIGH)
        mgr.create("C", "c", priority=NotificationPriority.HIGH)
        high = mgr.get_by_priority(NotificationPriority.HIGH)
        assert len(high) == 2

    def test_get_by_category(self) -> None:
        mgr = NotificationManager()
        mgr.create("A", "a", category="alert")
        mgr.create("B", "b", category="info")
        mgr.create("C", "c", category="alert")
        alerts = mgr.get_by_category("alert")
        assert len(alerts) == 2

    def test_get_pending(self) -> None:
        mgr = NotificationManager()
        r1 = mgr.create("A", "a")
        mgr.create("B", "b")
        mgr.mark_sent(r1.notification_id)
        pending = mgr.get_pending()
        assert len(pending) == 1

    def test_delete(self) -> None:
        mgr = NotificationManager()
        rec = mgr.create("Test", "Msg")
        assert mgr.delete(rec.notification_id)
        assert mgr.total_count == 0

    def test_delete_nonexistent(self) -> None:
        mgr = NotificationManager()
        assert not mgr.delete("invalid")

    def test_pending_count(self) -> None:
        mgr = NotificationManager()
        mgr.create("A", "a")
        mgr.create("B", "b")
        assert mgr.pending_count == 2

    def test_category_count(self) -> None:
        mgr = NotificationManager()
        mgr.create("A", "a", category="alert")
        mgr.create("B", "b", category="info")
        assert mgr.category_count == 2


# =========== ChannelDispatcher ===========


class TestChannelDispatcher:
    """ChannelDispatcher testleri."""

    def test_init_default_channels(self) -> None:
        disp = ChannelDispatcher()
        assert disp.channel_count == len(NotificationChannel)

    def test_dispatch(self) -> None:
        disp = ChannelDispatcher()
        result = disp.dispatch(
            NotificationChannel.LOG, "user1",
            "Title", "Message",
        )
        assert result["status"] == NotificationStatus.SENT.value
        assert result["channel"] == "log"
        assert disp.dispatch_count == 1

    def test_dispatch_disabled_channel(self) -> None:
        disp = ChannelDispatcher()
        disp.disable_channel(NotificationChannel.EMAIL)
        result = disp.dispatch(
            NotificationChannel.EMAIL, "user1",
            "Title", "Message",
        )
        assert result["status"] == NotificationStatus.FAILED.value
        assert result["reason"] == "channel_disabled"

    def test_dispatch_multi(self) -> None:
        disp = ChannelDispatcher()
        results = disp.dispatch_multi(
            [NotificationChannel.LOG, NotificationChannel.EMAIL],
            "user1", "Title", "Message",
        )
        assert len(results) == 2
        assert all(
            r["status"] == NotificationStatus.SENT.value
            for r in results
        )

    def test_enable_disable_channel(self) -> None:
        disp = ChannelDispatcher()
        assert disp.is_enabled(NotificationChannel.LOG)
        disp.disable_channel(NotificationChannel.LOG)
        assert not disp.is_enabled(NotificationChannel.LOG)
        disp.enable_channel(NotificationChannel.LOG)
        assert disp.is_enabled(NotificationChannel.LOG)

    def test_configure_channel(self) -> None:
        disp = ChannelDispatcher()
        disp.configure_channel(
            NotificationChannel.TELEGRAM,
            {"bot_token": "xxx", "chat_id": "123"},
        )
        # Config is stored internally
        ch = disp._channels["telegram"]
        assert ch["config"]["bot_token"] == "xxx"

    def test_get_stats(self) -> None:
        disp = ChannelDispatcher()
        disp.dispatch(
            NotificationChannel.LOG, "", "T", "M",
        )
        disp.dispatch(
            NotificationChannel.LOG, "", "T2", "M2",
        )
        stats = disp.get_stats()
        assert stats["log"]["sent"] == 2

    def test_enabled_count(self) -> None:
        disp = ChannelDispatcher()
        total = disp.enabled_count
        disp.disable_channel(NotificationChannel.SMS)
        assert disp.enabled_count == total - 1


# =========== AlertEngine ===========


class TestAlertEngine:
    """AlertEngine testleri."""

    def test_add_threshold(self) -> None:
        engine = AlertEngine()
        rule = engine.add_threshold(
            "cpu_high", "cpu", "gt", 80.0,
        )
        assert rule["name"] == "cpu_high"
        assert engine.threshold_count == 1

    def test_check_threshold_gt(self) -> None:
        engine = AlertEngine()
        engine.add_threshold(
            "cpu_high", "cpu", "gt", 80.0,
            NotificationPriority.HIGH,
        )
        alerts = engine.check_threshold("cpu", 90.0)
        assert len(alerts) == 1
        assert alerts[0].severity == NotificationPriority.HIGH

    def test_check_threshold_not_triggered(self) -> None:
        engine = AlertEngine()
        engine.add_threshold(
            "cpu_high", "cpu", "gt", 80.0,
        )
        alerts = engine.check_threshold("cpu", 50.0)
        assert len(alerts) == 0

    def test_check_threshold_lt(self) -> None:
        engine = AlertEngine()
        engine.add_threshold(
            "disk_low", "disk", "lt", 10.0,
        )
        alerts = engine.check_threshold("disk", 5.0)
        assert len(alerts) == 1

    def test_check_threshold_gte(self) -> None:
        engine = AlertEngine()
        engine.add_threshold(
            "mem_high", "memory", "gte", 90.0,
        )
        alerts = engine.check_threshold("memory", 90.0)
        assert len(alerts) == 1

    def test_check_threshold_lte(self) -> None:
        engine = AlertEngine()
        engine.add_threshold(
            "temp_low", "temp", "lte", 0.0,
        )
        alerts = engine.check_threshold("temp", -5.0)
        assert len(alerts) == 1

    def test_check_threshold_eq(self) -> None:
        engine = AlertEngine()
        engine.add_threshold(
            "exact", "value", "eq", 42.0,
        )
        alerts = engine.check_threshold("value", 42.0)
        assert len(alerts) == 1

    def test_check_threshold_wrong_metric(self) -> None:
        engine = AlertEngine()
        engine.add_threshold(
            "cpu_high", "cpu", "gt", 80.0,
        )
        alerts = engine.check_threshold("memory", 95.0)
        assert len(alerts) == 0

    def test_add_pattern(self) -> None:
        engine = AlertEngine()
        rule = engine.add_pattern(
            "error_detect", "error",
            NotificationPriority.HIGH,
        )
        assert rule["name"] == "error_detect"
        assert engine.pattern_count == 1

    def test_check_pattern_match(self) -> None:
        engine = AlertEngine()
        engine.add_pattern(
            "error_detect", "error",
            NotificationPriority.HIGH,
        )
        alerts = engine.check_pattern(
            "Server Error occurred",
        )
        assert len(alerts) == 1

    def test_check_pattern_no_match(self) -> None:
        engine = AlertEngine()
        engine.add_pattern(
            "error_detect", "error",
        )
        alerts = engine.check_pattern("All good")
        assert len(alerts) == 0

    def test_check_pattern_case_insensitive(self) -> None:
        engine = AlertEngine()
        engine.add_pattern("err", "ERROR")
        alerts = engine.check_pattern("some error here")
        assert len(alerts) == 1

    def test_create_anomaly_alert(self) -> None:
        engine = AlertEngine()
        alert = engine.create_anomaly_alert(
            "cpu", "Unusual spike",
        )
        assert alert.alert_type == AlertType.ANOMALY
        assert alert.source == "cpu"
        assert engine.alert_count == 1

    def test_acknowledge(self) -> None:
        engine = AlertEngine()
        alert = engine.create_anomaly_alert(
            "cpu", "Spike",
        )
        assert engine.acknowledge(alert.alert_id)
        assert alert.acknowledged

    def test_acknowledge_nonexistent(self) -> None:
        engine = AlertEngine()
        assert not engine.acknowledge("invalid")

    def test_suppress(self) -> None:
        engine = AlertEngine()
        engine.add_threshold(
            "cpu_high", "cpu", "gt", 80.0,
        )
        engine.suppress("cpu_high", 3600)
        alerts = engine.check_threshold("cpu", 95.0)
        assert len(alerts) == 0

    def test_get_active(self) -> None:
        engine = AlertEngine()
        a1 = engine.create_anomaly_alert("a", "m1")
        engine.create_anomaly_alert("b", "m2")
        engine.acknowledge(a1.alert_id)
        active = engine.get_active()
        assert len(active) == 1

    def test_active_count(self) -> None:
        engine = AlertEngine()
        engine.create_anomaly_alert("a", "m1")
        engine.create_anomaly_alert("b", "m2")
        assert engine.active_count == 2

    def test_multiple_thresholds(self) -> None:
        engine = AlertEngine()
        engine.add_threshold("high", "cpu", "gt", 80.0)
        engine.add_threshold("critical", "cpu", "gt", 95.0)
        alerts = engine.check_threshold("cpu", 97.0)
        assert len(alerts) == 2


# ========= PreferenceManager =========


class TestPreferenceManager:
    """NotificationPreferenceManager testleri."""

    def test_set_get_preference(self) -> None:
        mgr = NotificationPreferenceManager()
        mgr.set_preference("u1", "theme", "dark")
        assert mgr.get_preference("u1", "theme") == "dark"

    def test_get_preference_default(self) -> None:
        mgr = NotificationPreferenceManager()
        val = mgr.get_preference("u1", "x", "default")
        assert val == "default"

    def test_channel_preference(self) -> None:
        mgr = NotificationPreferenceManager()
        mgr.set_channel_preference(
            "u1", NotificationChannel.SMS, False,
        )
        assert not mgr.get_channel_preference(
            "u1", NotificationChannel.SMS,
        )
        assert mgr.get_channel_preference(
            "u1", NotificationChannel.EMAIL,
        )

    def test_quiet_hours_midnight_crossing(self) -> None:
        mgr = NotificationPreferenceManager(
            quiet_start="22:00",
            quiet_end="08:00",
        )
        mgr.set_quiet_hours("u1", "22:00", "08:00")
        assert mgr.is_quiet_hours("u1", 23)
        assert mgr.is_quiet_hours("u1", 0)
        assert mgr.is_quiet_hours("u1", 5)
        assert not mgr.is_quiet_hours("u1", 10)
        assert not mgr.is_quiet_hours("u1", 15)

    def test_quiet_hours_same_day(self) -> None:
        mgr = NotificationPreferenceManager()
        mgr.set_quiet_hours("u1", "12:00", "14:00")
        assert mgr.is_quiet_hours("u1", 13)
        assert not mgr.is_quiet_hours("u1", 10)
        assert not mgr.is_quiet_hours("u1", 15)

    def test_quiet_hours_default(self) -> None:
        mgr = NotificationPreferenceManager(
            quiet_start="22:00",
            quiet_end="08:00",
        )
        assert mgr.is_quiet_hours("new_user", 23)
        assert not mgr.is_quiet_hours("new_user", 12)

    def test_rate_limit(self) -> None:
        mgr = NotificationPreferenceManager()
        mgr.set_rate_limit("u1", max_per_hour=2)
        assert mgr.check_rate_limit("u1")
        mgr.record_sent("u1")
        mgr.record_sent("u1")
        assert not mgr.check_rate_limit("u1")

    def test_rate_limit_no_limit_set(self) -> None:
        mgr = NotificationPreferenceManager()
        assert mgr.check_rate_limit("unknown")

    def test_category_filter(self) -> None:
        mgr = NotificationPreferenceManager()
        mgr.set_category_filter(
            "u1", ["spam", "promo"],
        )
        assert not mgr.is_category_allowed("u1", "spam")
        assert mgr.is_category_allowed("u1", "alert")

    def test_category_no_filter(self) -> None:
        mgr = NotificationPreferenceManager()
        assert mgr.is_category_allowed("u1", "anything")

    def test_user_count(self) -> None:
        mgr = NotificationPreferenceManager()
        mgr.set_preference("u1", "k", "v")
        mgr.set_preference("u2", "k", "v")
        assert mgr.user_count == 2

    def test_rate_limit_count(self) -> None:
        mgr = NotificationPreferenceManager()
        mgr.set_rate_limit("u1")
        mgr.set_rate_limit("u2")
        assert mgr.rate_limit_count == 2


# =========== TemplateEngine ===========


class TestTemplateEngine:
    """NotificationTemplateEngine testleri."""

    def test_register_template(self) -> None:
        eng = NotificationTemplateEngine()
        t = eng.register_template(
            "welcome", "Welcome {name}",
            "Hello {name}, welcome!",
        )
        assert t["name"] == "welcome"
        assert eng.template_count == 1

    def test_render(self) -> None:
        eng = NotificationTemplateEngine()
        eng.register_template(
            "alert", "Alert: {metric}",
            "{metric} is {value}",
        )
        result = eng.render(
            "alert", {"metric": "CPU", "value": "95%"},
        )
        assert result["subject"] == "Alert: CPU"
        assert result["body"] == "CPU is 95%"

    def test_render_no_variables(self) -> None:
        eng = NotificationTemplateEngine()
        eng.register_template(
            "simple", "Hello", "World",
        )
        result = eng.render("simple")
        assert result["subject"] == "Hello"
        assert result["body"] == "World"

    def test_render_missing_template(self) -> None:
        eng = NotificationTemplateEngine()
        result = eng.render("nonexistent")
        assert result["subject"] == "nonexistent"
        assert result["body"] == "nonexistent"

    def test_render_multi_language(self) -> None:
        eng = NotificationTemplateEngine()
        eng.register_template(
            "welcome", "Welcome", "Hello",
            lang="en",
        )
        eng.register_template(
            "welcome", "Hosgeldin", "Merhaba",
            lang="tr",
        )
        en = eng.render("welcome", lang="en")
        tr = eng.render("welcome", lang="tr")
        assert en["subject"] == "Welcome"
        assert tr["subject"] == "Hosgeldin"

    def test_render_fallback_to_english(self) -> None:
        eng = NotificationTemplateEngine()
        eng.register_template(
            "greet", "Hi", "Hello",
            lang="en",
        )
        result = eng.render("greet", lang="fr")
        assert result["subject"] == "Hi"

    def test_preview(self) -> None:
        eng = NotificationTemplateEngine()
        eng.register_template(
            "alert", "Alert: {metric}",
            "Value: {value}",
        )
        preview = eng.preview("alert")
        assert "[metric]" in preview["subject"]
        assert "[value]" in preview["body"]

    def test_preview_missing(self) -> None:
        eng = NotificationTemplateEngine()
        result = eng.preview("missing")
        assert result["subject"] == ""

    def test_register_partial(self) -> None:
        eng = NotificationTemplateEngine()
        eng.register_partial("header", "=== HEADER ===")
        assert eng.partial_count == 1

    def test_render_with_partials(self) -> None:
        eng = NotificationTemplateEngine()
        eng.register_partial("sig", "-- ATLAS Bot")
        result = eng.render_with_partials(
            "Hello {name}\n{{> sig}}",
            {"name": "Fatih"},
        )
        assert "Hello Fatih" in result
        assert "-- ATLAS Bot" in result

    def test_list_templates(self) -> None:
        eng = NotificationTemplateEngine()
        eng.register_template("a", "A", "a", lang="en")
        eng.register_template("b", "B", "b", lang="tr")
        all_t = eng.list_templates()
        assert len(all_t) == 2
        en_only = eng.list_templates(lang="en")
        assert len(en_only) == 1

    def test_delete_template(self) -> None:
        eng = NotificationTemplateEngine()
        eng.register_template("test", "T", "t")
        assert eng.delete_template("test")
        assert eng.template_count == 0

    def test_delete_nonexistent(self) -> None:
        eng = NotificationTemplateEngine()
        assert not eng.delete_template("nope")

    def test_format_type(self) -> None:
        eng = NotificationTemplateEngine()
        eng.register_template(
            "html_alert", "<h1>{title}</h1>",
            "<p>{body}</p>",
            format_type="html",
        )
        result = eng.render(
            "html_alert",
            {"title": "Alert", "body": "Details"},
        )
        assert result["format"] == "html"


# =========== DeliveryTracker ===========


class TestDeliveryTracker:
    """DeliveryTracker testleri."""

    def test_track(self) -> None:
        tracker = DeliveryTracker()
        rec = tracker.track(
            "n1", NotificationChannel.LOG,
        )
        assert rec.notification_id == "n1"
        assert rec.status == NotificationStatus.PENDING
        assert tracker.delivery_count == 1

    def test_mark_sent(self) -> None:
        tracker = DeliveryTracker()
        rec = tracker.track(
            "n1", NotificationChannel.LOG,
        )
        assert tracker.mark_sent(rec.delivery_id)
        assert rec.status == NotificationStatus.SENT
        assert rec.attempts == 1

    def test_mark_delivered(self) -> None:
        tracker = DeliveryTracker()
        rec = tracker.track(
            "n1", NotificationChannel.LOG,
        )
        assert tracker.mark_delivered(rec.delivery_id)
        assert rec.status == NotificationStatus.DELIVERED

    def test_mark_read(self) -> None:
        tracker = DeliveryTracker()
        rec = tracker.track(
            "n1", NotificationChannel.LOG,
        )
        assert tracker.mark_read(rec.delivery_id)
        assert rec.status == NotificationStatus.READ
        assert tracker.read_count == 1

    def test_mark_failed(self) -> None:
        tracker = DeliveryTracker()
        rec = tracker.track(
            "n1", NotificationChannel.LOG,
        )
        assert tracker.mark_failed(
            rec.delivery_id, "connection_error",
        )
        assert rec.status == NotificationStatus.FAILED
        assert rec.last_error == "connection_error"
        assert rec.attempts == 1

    def test_mark_nonexistent(self) -> None:
        tracker = DeliveryTracker()
        assert not tracker.mark_sent("invalid")
        assert not tracker.mark_delivered("invalid")
        assert not tracker.mark_read("invalid")
        assert not tracker.mark_failed("invalid")

    def test_should_retry(self) -> None:
        tracker = DeliveryTracker(max_retries=3)
        rec = tracker.track(
            "n1", NotificationChannel.LOG,
        )
        tracker.mark_failed(rec.delivery_id, "err")
        assert tracker.should_retry(rec.delivery_id)

    def test_should_not_retry_max(self) -> None:
        tracker = DeliveryTracker(max_retries=2)
        rec = tracker.track(
            "n1", NotificationChannel.LOG,
        )
        tracker.mark_failed(rec.delivery_id, "e1")
        tracker.mark_failed(rec.delivery_id, "e2")
        assert not tracker.should_retry(rec.delivery_id)

    def test_should_retry_nonexistent(self) -> None:
        tracker = DeliveryTracker()
        assert not tracker.should_retry("invalid")

    def test_get_failed(self) -> None:
        tracker = DeliveryTracker()
        r1 = tracker.track("n1", NotificationChannel.LOG)
        tracker.track("n2", NotificationChannel.LOG)
        tracker.mark_failed(r1.delivery_id, "err")
        failed = tracker.get_failed()
        assert len(failed) == 1

    def test_get_retryable(self) -> None:
        tracker = DeliveryTracker(max_retries=2)
        r1 = tracker.track("n1", NotificationChannel.LOG)
        r2 = tracker.track("n2", NotificationChannel.LOG)
        tracker.mark_failed(r1.delivery_id, "e1")
        tracker.mark_failed(r2.delivery_id, "e1")
        tracker.mark_failed(r2.delivery_id, "e2")
        retryable = tracker.get_retryable()
        assert len(retryable) == 1

    def test_analytics(self) -> None:
        tracker = DeliveryTracker()
        r1 = tracker.track("n1", NotificationChannel.LOG)
        r2 = tracker.track("n2", NotificationChannel.LOG)
        tracker.mark_sent(r1.delivery_id)
        tracker.mark_failed(r2.delivery_id, "err")
        analytics = tracker.get_analytics()
        assert analytics["total"] == 2
        assert analytics["sent"] == 1
        assert analytics["failed"] == 1
        assert analytics["delivery_rate"] == 0.5


# =========== DigestBuilder ===========


class TestDigestBuilder:
    """DigestBuilder testleri."""

    def test_add_item(self) -> None:
        builder = DigestBuilder()
        item = builder.add_item(
            "alert", "CPU High", "CPU at 95%",
        )
        assert item["category"] == "alert"
        assert builder.item_count == 1

    def test_subscribe(self) -> None:
        builder = DigestBuilder()
        sub = builder.subscribe(
            "u1", DigestFrequency.DAILY,
        )
        assert sub["user_id"] == "u1"
        assert sub["frequency"] == "daily"
        assert builder.subscription_count == 1

    def test_subscribe_with_categories(self) -> None:
        builder = DigestBuilder()
        sub = builder.subscribe(
            "u1", categories=["alert", "info"],
        )
        assert sub["categories"] == ["alert", "info"]

    def test_unsubscribe(self) -> None:
        builder = DigestBuilder()
        builder.subscribe("u1")
        assert builder.unsubscribe("u1")
        assert builder.subscription_count == 0

    def test_unsubscribe_nonexistent(self) -> None:
        builder = DigestBuilder()
        assert not builder.unsubscribe("invalid")

    def test_build_digest(self) -> None:
        builder = DigestBuilder()
        builder.add_item("alert", "A", "a")
        builder.add_item("info", "B", "b")
        builder.add_item("alert", "C", "c")
        digest = builder.build_digest()
        assert digest["total_items"] == 3
        assert digest["category_count"] == 2
        assert builder.digest_count == 1

    def test_build_digest_category_filter(self) -> None:
        builder = DigestBuilder()
        builder.add_item("alert", "A", "a")
        builder.add_item("info", "B", "b")
        digest = builder.build_digest(
            categories=["alert"],
        )
        assert digest["total_items"] == 1

    def test_build_digest_user_filter(self) -> None:
        builder = DigestBuilder()
        builder.subscribe(
            "u1", categories=["alert"],
        )
        builder.add_item("alert", "A", "a")
        builder.add_item("info", "B", "b")
        digest = builder.build_digest(user_id="u1")
        assert digest["total_items"] == 1

    def test_add_rule(self) -> None:
        builder = DigestBuilder()
        rule = builder.add_rule(
            "high_only",
            min_priority=NotificationPriority.HIGH,
        )
        assert rule["name"] == "high_only"
        assert builder.rule_count == 1

    def test_clear_items(self) -> None:
        builder = DigestBuilder()
        builder.add_item("a", "A", "a")
        builder.add_item("b", "B", "b")
        cleared = builder.clear_items()
        assert cleared == 2
        assert builder.item_count == 0


# ========= EscalationManager =========


class TestEscalationManager:
    """EscalationManager testleri."""

    def test_add_rule(self) -> None:
        mgr = EscalationManager()
        rule = mgr.add_rule(
            "critical",
            [EscalationLevel.L1, EscalationLevel.L2],
        )
        assert rule["name"] == "critical"
        assert mgr.rule_count == 1

    def test_escalate(self) -> None:
        mgr = EscalationManager()
        mgr.add_rule(
            "critical",
            [EscalationLevel.L1, EscalationLevel.L2],
        )
        result = mgr.escalate("alert1", "critical")
        assert result["escalated"]
        assert result["level"] == "l1"
        assert mgr.active_count == 1

    def test_escalate_next_level(self) -> None:
        mgr = EscalationManager()
        mgr.add_rule(
            "critical",
            [EscalationLevel.L1, EscalationLevel.L2,
             EscalationLevel.L3],
        )
        mgr.escalate("alert1", "critical")
        result = mgr.escalate("alert1", "critical")
        assert result["escalated"]
        assert result["level"] == "l2"

    def test_escalate_max_level(self) -> None:
        mgr = EscalationManager()
        mgr.add_rule(
            "simple", [EscalationLevel.L1],
        )
        mgr.escalate("alert1", "simple")
        result = mgr.escalate("alert1", "simple")
        assert not result["escalated"]
        assert result["reason"] == "max_level_reached"

    def test_escalate_no_rule(self) -> None:
        mgr = EscalationManager()
        result = mgr.escalate("alert1", "nonexistent")
        assert not result["escalated"]
        assert result["reason"] == "rule_not_found"

    def test_acknowledge(self) -> None:
        mgr = EscalationManager()
        mgr.add_rule(
            "rule1", [EscalationLevel.L1],
        )
        mgr.escalate("alert1", "rule1")
        assert mgr.acknowledge("alert1", "admin")
        assert mgr.ack_count == 1
        assert mgr.active_count == 0

    def test_acknowledge_nonexistent(self) -> None:
        mgr = EscalationManager()
        assert not mgr.acknowledge("invalid")

    def test_check_timeouts(self) -> None:
        mgr = EscalationManager()
        mgr.add_rule(
            "fast", [EscalationLevel.L1],
            timeout_seconds=0,
        )
        mgr.escalate("alert1", "fast")
        time.sleep(0.01)
        timed_out = mgr.check_timeouts()
        assert "alert1" in timed_out

    def test_check_timeouts_not_expired(self) -> None:
        mgr = EscalationManager()
        mgr.add_rule(
            "slow", [EscalationLevel.L1],
            timeout_seconds=9999,
        )
        mgr.escalate("alert1", "slow")
        timed_out = mgr.check_timeouts()
        assert len(timed_out) == 0

    def test_add_on_call(self) -> None:
        mgr = EscalationManager()
        entry = mgr.add_on_call(
            "Fatih", EscalationLevel.L1,
            "telegram",
        )
        assert entry["person"] == "Fatih"
        assert mgr.on_call_count == 1

    def test_get_current_on_call(self) -> None:
        mgr = EscalationManager()
        mgr.add_on_call(
            "Fatih", EscalationLevel.L1,
        )
        current = mgr.get_current_on_call()
        assert current is not None
        assert current["person"] == "Fatih"

    def test_get_current_on_call_empty(self) -> None:
        mgr = EscalationManager()
        assert mgr.get_current_on_call() is None

    def test_rotate_on_call(self) -> None:
        mgr = EscalationManager()
        mgr.add_on_call("A", EscalationLevel.L1)
        mgr.add_on_call("B", EscalationLevel.L1)
        current = mgr.get_current_on_call()
        assert current["person"] == "A"
        rotated = mgr.rotate_on_call()
        assert rotated["person"] == "B"

    def test_rotate_on_call_wraps(self) -> None:
        mgr = EscalationManager()
        mgr.add_on_call("A", EscalationLevel.L1)
        mgr.add_on_call("B", EscalationLevel.L1)
        mgr.rotate_on_call()  # B
        rotated = mgr.rotate_on_call()  # wraps to A
        assert rotated["person"] == "A"

    def test_rotate_empty(self) -> None:
        mgr = EscalationManager()
        assert mgr.rotate_on_call() is None

    def test_get_active(self) -> None:
        mgr = EscalationManager()
        mgr.add_rule(
            "r1", [EscalationLevel.L1],
        )
        mgr.escalate("a1", "r1")
        mgr.escalate("a2", "r1")
        mgr.acknowledge("a1")
        active = mgr.get_active()
        assert len(active) == 1

    def test_resolve(self) -> None:
        mgr = EscalationManager()
        mgr.add_rule(
            "r1", [EscalationLevel.L1],
        )
        mgr.escalate("a1", "r1")
        assert mgr.resolve("a1")
        assert mgr.active_count == 0

    def test_resolve_nonexistent(self) -> None:
        mgr = EscalationManager()
        assert not mgr.resolve("invalid")


# ======= NotificationOrchestrator =======


class TestNotificationOrchestrator:
    """NotificationOrchestrator testleri."""

    def test_init(self) -> None:
        orch = NotificationOrchestrator()
        assert orch.daily_count == 0
        assert orch.manager is not None
        assert orch.dispatcher is not None

    def test_send_notification_basic(self) -> None:
        orch = NotificationOrchestrator()
        result = orch.send_notification(
            "Test", "Hello World",
        )
        assert result["sent"]
        assert result["notification_id"]
        assert result["delivery_id"]
        assert orch.daily_count == 1

    def test_send_notification_with_channel(self) -> None:
        orch = NotificationOrchestrator()
        result = orch.send_notification(
            "Test", "Hello",
            channel=NotificationChannel.TELEGRAM,
        )
        assert result["sent"]
        assert result["channel"] == "telegram"

    def test_send_notification_critical(self) -> None:
        orch = NotificationOrchestrator()
        result = orch.send_notification(
            "Critical", "Emergency!",
            priority=NotificationPriority.CRITICAL,
        )
        assert result["sent"]
        assert result["channel"] == "telegram"

    def test_send_daily_limit(self) -> None:
        orch = NotificationOrchestrator(max_daily=2)
        orch.send_notification("A", "a")
        orch.send_notification("B", "b")
        result = orch.send_notification("C", "c")
        assert not result["sent"]
        assert result["reason"] == "daily_limit_reached"

    def test_send_category_blocked(self) -> None:
        orch = NotificationOrchestrator()
        orch.preferences.set_category_filter(
            "user1", ["spam"],
        )
        result = orch.send_notification(
            "Promo", "Buy now!",
            recipient="user1",
            category="spam",
        )
        assert not result["sent"]
        assert result["reason"] == "category_blocked"

    def test_send_rate_limited(self) -> None:
        orch = NotificationOrchestrator()
        orch.preferences.set_rate_limit(
            "user1", max_per_hour=1,
        )
        orch.send_notification(
            "A", "a", recipient="user1",
        )
        result = orch.send_notification(
            "B", "b", recipient="user1",
        )
        assert not result["sent"]
        assert result["reason"] == "rate_limited"

    def test_send_with_template(self) -> None:
        orch = NotificationOrchestrator()
        orch.templates.register_template(
            "alert", "Alert: {metric}",
            "{metric} is {value}",
        )
        result = orch.send_notification(
            "Default Title", "Default Msg",
            template="alert",
            variables={"metric": "CPU", "value": "95%"},
        )
        assert result["sent"]

    def test_check_alerts(self) -> None:
        orch = NotificationOrchestrator()
        orch.alerts.add_threshold(
            "cpu_high", "cpu", "gt", 80.0,
            NotificationPriority.HIGH,
        )
        results = orch.check_alerts("cpu", 95.0)
        assert len(results) == 1
        assert results[0]["sent"]

    def test_check_alerts_no_trigger(self) -> None:
        orch = NotificationOrchestrator()
        orch.alerts.add_threshold(
            "cpu_high", "cpu", "gt", 80.0,
        )
        results = orch.check_alerts("cpu", 50.0)
        assert len(results) == 0

    def test_get_analytics(self) -> None:
        orch = NotificationOrchestrator()
        orch.send_notification("A", "a")
        analytics = orch.get_analytics()
        assert analytics["total_notifications"] == 1
        assert analytics["daily_sent"] == 1
        assert analytics["daily_limit"] == 100
        assert "delivery" in analytics
        assert "channels" in analytics

    def test_get_snapshot(self) -> None:
        orch = NotificationOrchestrator()
        orch.send_notification("A", "a")
        snap = orch.get_snapshot()
        assert isinstance(snap, NotificationSnapshot)
        assert snap.total_notifications == 1

    def test_default_channel_fallback(self) -> None:
        orch = NotificationOrchestrator(
            default_channel="invalid",
        )
        result = orch.send_notification("T", "M")
        assert result["sent"]
        assert result["channel"] == "log"

    def test_send_disabled_channel(self) -> None:
        orch = NotificationOrchestrator(
            default_channel="email",
        )
        orch.dispatcher.disable_channel(
            NotificationChannel.EMAIL,
        )
        result = orch.send_notification("T", "M")
        assert not result["sent"]

    def test_digest_tracking(self) -> None:
        orch = NotificationOrchestrator()
        orch.send_notification(
            "A", "msg1", category="alert",
        )
        orch.send_notification(
            "B", "msg2", category="info",
        )
        assert orch.digests.item_count == 2

    def test_escalation_integration(self) -> None:
        orch = NotificationOrchestrator()
        orch.escalation.add_rule(
            "critical",
            [EscalationLevel.L1, EscalationLevel.L2],
        )
        result = orch.escalation.escalate(
            "alert1", "critical",
        )
        assert result["escalated"]
        assert orch.escalation.active_count == 1


# =========== Config ===========


class TestNotificationConfig:
    """Config testleri."""

    def test_config_defaults(self) -> None:
        from app.config import settings
        assert hasattr(settings, "notification_enabled")
        assert hasattr(settings, "default_channel")
        assert hasattr(settings, "quiet_hours_start")
        assert hasattr(settings, "quiet_hours_end")
        assert hasattr(settings, "max_daily_notifications")

    def test_config_values(self) -> None:
        from app.config import settings
        assert settings.notification_enabled is True
        assert settings.default_channel == "log"
        assert settings.quiet_hours_start == "22:00"
        assert settings.quiet_hours_end == "08:00"
        assert settings.max_daily_notifications == 100


# =========== Imports ===========


class TestNotificationImports:
    """Import testleri."""

    def test_import_all(self) -> None:
        from app.core.notification import (
            AlertEngine,
            ChannelDispatcher,
            DeliveryTracker,
            DigestBuilder,
            EscalationManager,
            NotificationManager,
            NotificationOrchestrator,
            NotificationPreferenceManager,
            NotificationTemplateEngine,
        )
        assert AlertEngine is not None
        assert ChannelDispatcher is not None
        assert DeliveryTracker is not None
        assert DigestBuilder is not None
        assert EscalationManager is not None
        assert NotificationManager is not None
        assert NotificationOrchestrator is not None
        assert NotificationPreferenceManager is not None
        assert NotificationTemplateEngine is not None

    def test_import_models(self) -> None:
        from app.models.notification_system import (
            AlertRecord,
            AlertType,
            DeliveryRecord,
            DigestFrequency,
            EscalationLevel,
            NotificationChannel,
            NotificationPriority,
            NotificationRecord,
            NotificationSnapshot,
            NotificationStatus,
        )
        assert NotificationPriority is not None
        assert NotificationStatus is not None
        assert NotificationChannel is not None
        assert AlertType is not None
        assert EscalationLevel is not None
        assert DigestFrequency is not None
        assert NotificationRecord is not None
        assert AlertRecord is not None
        assert DeliveryRecord is not None
        assert NotificationSnapshot is not None
