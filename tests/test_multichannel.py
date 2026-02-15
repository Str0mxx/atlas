"""ATLAS Multi-Channel Command Center testleri."""

import time

import pytest

from app.core.multichannel.availability_tracker import (
    AvailabilityTracker,
)
from app.core.multichannel.channel_preference_engine import (
    ChannelPreferenceEngine,
)
from app.core.multichannel.channel_router import (
    ChannelRouter,
)
from app.core.multichannel.command_interpreter import (
    CommandInterpreter,
)
from app.core.multichannel.context_carrier import (
    ContextCarrier,
)
from app.core.multichannel.escalation_path_manager import (
    EscalationPathManager,
)
from app.core.multichannel.multichannel_orchestrator import (
    MultiChannelOrchestrator,
)
from app.core.multichannel.response_formatter import (
    ResponseFormatter,
)
from app.core.multichannel.unified_inbox import (
    UnifiedInbox,
)
from app.models.multichannel_models import (
    ChannelMessage,
    ChannelType,
    CommandType,
    EscalationLevel,
    EscalationRecord,
    FormatType,
    MessageDirection,
    MultiChannelSnapshot,
    PresenceStatus,
    SessionRecord,
)


# ==================== Models ====================

class TestMultiChannelModels:
    """MultiChannel model testleri."""

    def test_channel_type_enum(self):
        assert ChannelType.TELEGRAM == "telegram"
        assert ChannelType.WHATSAPP == "whatsapp"
        assert ChannelType.EMAIL == "email"
        assert ChannelType.VOICE == "voice"
        assert ChannelType.SMS == "sms"

    def test_message_direction_enum(self):
        assert MessageDirection.INBOUND == "inbound"
        assert MessageDirection.OUTBOUND == "outbound"
        assert MessageDirection.INTERNAL == "internal"
        assert MessageDirection.BROADCAST == "broadcast"
        assert MessageDirection.SYSTEM == "system"

    def test_escalation_level_enum(self):
        assert EscalationLevel.NONE == "none"
        assert EscalationLevel.LOW == "low"
        assert EscalationLevel.MEDIUM == "medium"
        assert EscalationLevel.HIGH == "high"
        assert EscalationLevel.CRITICAL == "critical"

    def test_presence_status_enum(self):
        assert PresenceStatus.ONLINE == "online"
        assert PresenceStatus.AWAY == "away"
        assert PresenceStatus.BUSY == "busy"
        assert PresenceStatus.OFFLINE == "offline"
        assert PresenceStatus.DND == "dnd"

    def test_command_type_enum(self):
        assert CommandType.QUERY == "query"
        assert CommandType.ACTION == "action"
        assert CommandType.REPORT == "report"
        assert CommandType.CONFIG == "config"
        assert CommandType.HELP == "help"

    def test_format_type_enum(self):
        assert FormatType.PLAIN == "plain"
        assert FormatType.MARKDOWN == "markdown"
        assert FormatType.HTML == "html"
        assert FormatType.RICH == "rich"
        assert FormatType.MINIMAL == "minimal"

    def test_channel_message_model(self):
        cm = ChannelMessage(content="Hello", sender="u1")
        assert cm.message_id
        assert cm.channel == ChannelType.TELEGRAM
        assert cm.direction == MessageDirection.INBOUND
        assert cm.content == "Hello"
        assert cm.sender == "u1"

    def test_session_record_model(self):
        sr = SessionRecord(user_id="u1")
        assert sr.session_id
        assert sr.user_id == "u1"
        assert sr.channel == ChannelType.TELEGRAM
        assert sr.active is True
        assert sr.context == {}

    def test_escalation_record_model(self):
        er = EscalationRecord(
            from_channel="telegram",
            to_channel="email",
            reason="timeout",
        )
        assert er.escalation_id
        assert er.from_channel == "telegram"
        assert er.to_channel == "email"
        assert er.level == EscalationLevel.LOW
        assert er.reason == "timeout"

    def test_multichannel_snapshot_model(self):
        snap = MultiChannelSnapshot()
        assert snap.snapshot_id
        assert snap.total_messages == 0
        assert snap.total_sessions == 0
        assert snap.total_escalations == 0
        assert snap.active_channels == 0


# ==================== ChannelRouter ====================

class TestChannelRouter:
    """ChannelRouter testleri."""

    def test_init(self):
        r = ChannelRouter()
        assert r.channel_count == 5
        assert r.active_channel_count == 5
        assert r.routed_count == 0

    def test_route_message_basic(self):
        r = ChannelRouter()
        result = r.route_message(
            content="hello",
            target_channel="telegram",
        )
        assert result["route_id"] == "route_1"
        assert result["channel"] == "telegram"
        assert result["status"] == "routed"
        assert r.routed_count == 1

    def test_route_message_with_priority(self):
        r = ChannelRouter()
        result = r.route_message(
            content="test", priority=9,
        )
        assert result["channel"] == "voice"

    def test_route_message_high_priority(self):
        r = ChannelRouter()
        result = r.route_message(
            content="test", priority=7,
        )
        assert result["channel"] == "telegram"

    def test_route_message_unknown_channel(self):
        r = ChannelRouter()
        result = r.route_message(
            content="test",
            target_channel="unknown_ch",
        )
        assert result.get("error") == "channel_not_found"

    def test_route_message_disabled_channel_failover(self):
        r = ChannelRouter()
        r.configure_channel(
            "telegram", enabled=False,
        )
        result = r.route_message(
            content="test",
            target_channel="telegram",
        )
        assert result["channel"] != "telegram"
        assert result["status"] == "routed"

    def test_detect_channel_telegram(self):
        r = ChannelRouter()
        result = r.detect_channel("t_12345")
        assert result["detected_channel"] == "telegram"

    def test_detect_channel_whatsapp(self):
        r = ChannelRouter()
        result = r.detect_channel("wa_user")
        assert result["detected_channel"] == "whatsapp"

    def test_detect_channel_email(self):
        r = ChannelRouter()
        result = r.detect_channel("user@example.com")
        assert result["detected_channel"] == "email"

    def test_detect_channel_sms(self):
        r = ChannelRouter()
        result = r.detect_channel("+905551234567")
        assert result["detected_channel"] == "sms"

    def test_detect_channel_voice(self):
        r = ChannelRouter()
        result = r.detect_channel("voice_session_1")
        assert result["detected_channel"] == "voice"

    def test_detect_channel_default(self):
        r = ChannelRouter()
        result = r.detect_channel("random_source")
        assert result["detected_channel"] == "telegram"

    def test_configure_channel(self):
        r = ChannelRouter()
        result = r.configure_channel(
            "webchat", priority=6,
            protocol="websocket",
        )
        assert result["configured"] is True
        assert r.channel_count == 6

    def test_set_failover(self):
        r = ChannelRouter()
        result = r.set_failover(
            "telegram", ["sms", "email"],
        )
        assert result["alternatives"] == ["sms", "email"]

    def test_get_channel_status(self):
        r = ChannelRouter()
        status = r.get_channel_status()
        assert "telegram" in status
        assert status["telegram"]["enabled"] is True

    def test_get_routes_empty(self):
        r = ChannelRouter()
        assert r.get_routes() == []

    def test_get_routes_with_filter(self):
        r = ChannelRouter()
        r.route_message("a", target_channel="telegram")
        r.route_message("b", target_channel="email")
        r.route_message("c", target_channel="telegram")
        tg = r.get_routes(channel="telegram")
        assert len(tg) == 2

    def test_failover_all_disabled(self):
        r = ChannelRouter()
        for ch in ["telegram", "whatsapp", "email",
                    "voice", "sms"]:
            r.configure_channel(ch, enabled=False)
        result = r.route_message(
            content="test",
            target_channel="telegram",
        )
        assert result.get("error") == "no_available_channel"


# ==================== ContextCarrier ====================

class TestContextCarrier:
    """ContextCarrier testleri."""

    def test_init(self):
        c = ContextCarrier()
        assert c.session_count == 0
        assert c.active_session_count == 0
        assert c.transfer_count == 0

    def test_create_session(self):
        c = ContextCarrier()
        s = c.create_session("u1", "telegram")
        assert s["session_id"] == "sess_1"
        assert s["user_id"] == "u1"
        assert s["channel"] == "telegram"
        assert s["active"] is True
        assert c.session_count == 1

    def test_create_session_with_context(self):
        c = ContextCarrier()
        s = c.create_session(
            "u1", "telegram",
            {"lang": "tr"},
        )
        assert s["context"]["lang"] == "tr"

    def test_transfer_context(self):
        c = ContextCarrier()
        c.create_session(
            "u1", "telegram",
            {"topic": "support"},
        )
        result = c.transfer_context(
            "u1", "telegram", "email",
        )
        assert result["transferred"] is True
        assert result["from_channel"] == "telegram"
        assert result["to_channel"] == "email"
        assert c.transfer_count == 1

    def test_transfer_context_without_source(self):
        c = ContextCarrier()
        result = c.transfer_context(
            "u1", "telegram", "email",
        )
        assert result["transferred"] is True

    def test_sync_state(self):
        c = ContextCarrier()
        c.create_session("u1", "telegram")
        c.create_session("u1", "email")
        result = c.sync_state(
            "u1", {"mood": "happy"},
        )
        assert result["synced_sessions"] == 2
        assert "mood" in result["keys_updated"]

    def test_sync_state_new_user(self):
        c = ContextCarrier()
        result = c.sync_state(
            "new_user", {"key": "val"},
        )
        assert result["synced_sessions"] == 0

    def test_merge_history(self):
        c = ContextCarrier()
        result = c.merge_history(
            "u1", "telegram",
            [{"content": "hi"}, {"content": "bye"}],
        )
        assert result["messages_merged"] == 2

    def test_restore_context(self):
        c = ContextCarrier()
        c.create_session(
            "u1", "telegram",
            {"topic": "billing"},
        )
        result = c.restore_context("u1")
        assert result["restored"] is True
        assert result["context"]["topic"] == "billing"

    def test_restore_context_with_channel(self):
        c = ContextCarrier()
        c.create_session(
            "u1", "telegram",
            {"a": 1},
        )
        c.create_session(
            "u1", "email",
            {"b": 2},
        )
        result = c.restore_context("u1", "email")
        assert result["restored"] is True

    def test_restore_context_unknown_user(self):
        c = ContextCarrier()
        result = c.restore_context("unknown")
        assert result["restored"] is False

    def test_get_session(self):
        c = ContextCarrier()
        s = c.create_session("u1", "telegram")
        got = c.get_session(s["session_id"])
        assert got["user_id"] == "u1"

    def test_get_session_not_found(self):
        c = ContextCarrier()
        result = c.get_session("nonexistent")
        assert result.get("error") == "session_not_found"

    def test_close_session(self):
        c = ContextCarrier()
        s = c.create_session("u1", "telegram")
        result = c.close_session(s["session_id"])
        assert result["closed"] is True
        assert c.active_session_count == 0

    def test_close_session_not_found(self):
        c = ContextCarrier()
        result = c.close_session("nonexistent")
        assert result.get("error") == "session_not_found"

    def test_cleanup_expired(self):
        c = ContextCarrier(timeout_minutes=0)
        c.create_session("u1", "telegram")
        time.sleep(0.01)
        result = c.cleanup_expired()
        assert result["expired"] >= 1

    def test_get_user_sessions(self):
        c = ContextCarrier()
        c.create_session("u1", "telegram")
        c.create_session("u1", "email")
        c.create_session("u2", "telegram")
        sessions = c.get_user_sessions("u1")
        assert len(sessions) == 2


# ==================== AvailabilityTracker ====================

class TestAvailabilityTracker:
    """AvailabilityTracker testleri."""

    def test_init(self):
        a = AvailabilityTracker()
        assert a.tracked_user_count == 0
        assert a.online_user_count == 0

    def test_set_presence(self):
        a = AvailabilityTracker()
        result = a.set_presence("u1", "online", "telegram")
        assert result["user_id"] == "u1"
        assert result["status"] == "online"
        assert a.tracked_user_count == 1
        assert a.online_user_count == 1

    def test_set_presence_offline(self):
        a = AvailabilityTracker()
        a.set_presence("u1", "offline")
        assert a.online_user_count == 0

    def test_get_presence(self):
        a = AvailabilityTracker()
        a.set_presence("u1", "busy", "email")
        result = a.get_presence("u1")
        assert result["status"] == "busy"

    def test_get_presence_unknown(self):
        a = AvailabilityTracker()
        result = a.get_presence("unknown")
        assert result["status"] == "unknown"

    def test_set_channel_status(self):
        a = AvailabilityTracker()
        result = a.set_channel_status(
            "telegram", online=True, latency_ms=50.0,
        )
        assert result["online"] is True
        assert result["latency_ms"] == 50.0

    def test_get_channel_status(self):
        a = AvailabilityTracker()
        a.set_channel_status("telegram", online=True)
        result = a.get_channel_status("telegram")
        assert result["online"] is True

    def test_get_channel_status_unknown(self):
        a = AvailabilityTracker()
        result = a.get_channel_status("unknown")
        assert result["online"] is False

    def test_record_response_time(self):
        a = AvailabilityTracker()
        result = a.record_response_time(
            "u1", "telegram", 150.0,
        )
        assert result["response_ms"] == 150.0

    def test_get_avg_response_time(self):
        a = AvailabilityTracker()
        a.record_response_time("u1", "telegram", 100.0)
        a.record_response_time("u1", "telegram", 200.0)
        result = a.get_avg_response_time(user_id="u1")
        assert result["avg_response_ms"] == 150.0
        assert result["count"] == 2

    def test_get_avg_response_time_empty(self):
        a = AvailabilityTracker()
        result = a.get_avg_response_time()
        assert result["avg_response_ms"] == 0.0
        assert result["count"] == 0

    def test_get_avg_response_time_by_channel(self):
        a = AvailabilityTracker()
        a.record_response_time("u1", "telegram", 100.0)
        a.record_response_time("u1", "email", 300.0)
        result = a.get_avg_response_time(channel="email")
        assert result["avg_response_ms"] == 300.0

    def test_set_preferred_channels(self):
        a = AvailabilityTracker()
        result = a.set_preferred_channels(
            "u1", ["telegram", "email"],
        )
        assert result["preferred_channels"] == [
            "telegram", "email",
        ]

    def test_get_preferred_channel(self):
        a = AvailabilityTracker()
        a.set_preferred_channels(
            "u1", ["email", "telegram"],
        )
        result = a.get_preferred_channel("u1")
        assert result["preferred"] == "email"

    def test_get_preferred_channel_default(self):
        a = AvailabilityTracker()
        result = a.get_preferred_channel("unknown")
        assert result["preferred"] == "telegram"

    def test_analyze_patterns(self):
        a = AvailabilityTracker()
        a.set_presence("u1", "online", "telegram")
        a.set_presence("u1", "online", "email")
        a.set_presence("u1", "online", "telegram")
        result = a.analyze_patterns("u1")
        assert result["total_records"] == 3
        assert "channel_usage" in result

    def test_analyze_patterns_empty(self):
        a = AvailabilityTracker()
        result = a.analyze_patterns("unknown")
        assert result["patterns"] == []


# ==================== CommandInterpreter ====================

class TestCommandInterpreter:
    """CommandInterpreter testleri."""

    def test_init(self):
        ci = CommandInterpreter()
        assert ci.command_count == 0
        assert ci.shortcut_count == 5

    def test_parse_basic(self):
        ci = CommandInterpreter()
        result = ci.parse("show tasks")
        assert result["command_id"] == "cmd_1"
        assert result["intent"] == "query"
        assert ci.command_count == 1

    def test_parse_action_intent(self):
        ci = CommandInterpreter()
        result = ci.parse("run backup")
        assert result["intent"] == "action"

    def test_parse_report_intent(self):
        ci = CommandInterpreter()
        result = ci.parse("generate report")
        assert result["intent"] == "report"

    def test_parse_config_intent(self):
        ci = CommandInterpreter()
        result = ci.parse("set timeout 30")
        assert result["intent"] == "config"

    def test_parse_help_intent(self):
        ci = CommandInterpreter()
        result = ci.parse("help me")
        assert result["intent"] == "help"

    def test_parse_unknown_intent(self):
        ci = CommandInterpreter()
        result = ci.parse("xyz123")
        assert result["intent"] == "unknown"

    def test_parse_with_shortcut(self):
        ci = CommandInterpreter()
        result = ci.parse("st check")
        assert result["expanded"] == "status check"

    def test_parse_with_params_dashes(self):
        ci = CommandInterpreter()
        result = ci.parse(
            "run task --name backup --force",
        )
        assert result["params"]["name"] == "backup"
        assert result["params"]["force"] is True

    def test_parse_with_params_equals(self):
        ci = CommandInterpreter()
        result = ci.parse("run level=5")
        assert result["params"]["level"] == "5"

    def test_extract_intent(self):
        ci = CommandInterpreter()
        result = ci.extract_intent("show me the stats")
        assert result["intent"] == "query"
        assert result["confidence"] > 0

    def test_extract_intent_ambiguous(self):
        ci = CommandInterpreter()
        result = ci.extract_intent(
            "show report stats",
        )
        assert result["ambiguous"] is True
        assert len(result["alternatives"]) > 1

    def test_add_shortcut(self):
        ci = CommandInterpreter()
        result = ci.add_shortcut("q", "query")
        assert result["added"] is True
        assert ci.shortcut_count == 6

    def test_resolve_ambiguity(self):
        ci = CommandInterpreter()
        cmd = ci.parse("show report")
        result = ci.resolve_ambiguity(
            cmd["command_id"], "report",
        )
        assert result["resolved"] is True
        assert result["intent"] == "report"

    def test_resolve_ambiguity_not_found(self):
        ci = CommandInterpreter()
        result = ci.resolve_ambiguity(
            "nonexistent", "query",
        )
        assert result.get("error") == "command_not_found"

    def test_get_commands(self):
        ci = CommandInterpreter()
        ci.parse("show tasks")
        ci.parse("run backup")
        ci.parse("show status")
        all_cmds = ci.get_commands()
        assert len(all_cmds) == 3

    def test_get_commands_by_intent(self):
        ci = CommandInterpreter()
        ci.parse("show tasks")
        ci.parse("run backup")
        ci.parse("find users")
        query_cmds = ci.get_commands(intent="query")
        assert len(query_cmds) == 2

    def test_expand_shortcut_rpt(self):
        ci = CommandInterpreter()
        result = ci.parse("rpt weekly")
        assert "report" in result["expanded"]

    def test_expand_shortcut_hlp(self):
        ci = CommandInterpreter()
        result = ci.parse("hlp commands")
        assert "help" in result["expanded"]


# ==================== ResponseFormatter ====================

class TestResponseFormatter:
    """ResponseFormatter testleri."""

    def test_init(self):
        rf = ResponseFormatter()
        assert rf.format_count == 0

    def test_format_response_telegram(self):
        rf = ResponseFormatter()
        result = rf.format_response(
            "**bold** text", "telegram",
        )
        assert result["format_type"] == "markdown"
        assert result["formatted"] == "**bold** text"
        assert rf.format_count == 1

    def test_format_response_email(self):
        rf = ResponseFormatter()
        result = rf.format_response(
            "**bold** text", "email",
        )
        assert result["format_type"] == "html"
        assert "<strong>" in result["formatted"]

    def test_format_response_sms(self):
        rf = ResponseFormatter()
        result = rf.format_response(
            "Hello world", "sms",
        )
        assert result["format_type"] == "minimal"

    def test_format_response_whatsapp(self):
        rf = ResponseFormatter()
        result = rf.format_response(
            "**bold**", "whatsapp",
        )
        assert result["format_type"] == "plain"
        assert "bold" in result["formatted"]

    def test_format_response_voice(self):
        rf = ResponseFormatter()
        result = rf.format_response(
            "Hello **world**", "voice",
        )
        assert result["format_type"] == "plain"

    def test_format_response_truncation(self):
        rf = ResponseFormatter()
        long_text = "A" * 5000
        result = rf.format_response(long_text, "telegram")
        assert result["truncated"] is True
        assert len(result["formatted"]) <= 4096

    def test_format_response_no_truncation(self):
        rf = ResponseFormatter()
        result = rf.format_response(
            "short", "telegram",
        )
        assert result["truncated"] is False

    def test_to_markdown(self):
        rf = ResponseFormatter()
        result = rf.to_markdown("**bold**")
        assert result == "**bold**"

    def test_to_html(self):
        rf = ResponseFormatter()
        result = rf.to_html("**bold** and *italic*")
        assert "<strong>bold</strong>" in result
        assert "<em>italic</em>" in result

    def test_handle_attachment_supported(self):
        rf = ResponseFormatter()
        result = rf.handle_attachment(
            "image", "http://example.com/img.png",
            "telegram",
        )
        assert result["supported"] is True
        assert result["fallback"] is None

    def test_handle_attachment_unsupported(self):
        rf = ResponseFormatter()
        result = rf.handle_attachment(
            "video", "http://example.com/v.mp4",
            "sms",
        )
        assert result["supported"] is False
        assert result["fallback"] == "link"

    def test_handle_attachment_voice_none(self):
        rf = ResponseFormatter()
        result = rf.handle_attachment(
            "image", "http://example.com/img.png",
            "voice",
        )
        assert result["supported"] is False

    def test_set_channel_limit(self):
        rf = ResponseFormatter()
        result = rf.set_channel_limit("telegram", 2048)
        assert result["limit"] == 2048

    def test_format_response_custom_format(self):
        rf = ResponseFormatter()
        result = rf.format_response(
            "text", "telegram", format_type="html",
        )
        assert result["format_type"] == "html"


# ==================== ChannelPreferenceEngine ====================

class TestChannelPreferenceEngine:
    """ChannelPreferenceEngine testleri."""

    def test_init(self):
        cp = ChannelPreferenceEngine()
        assert cp.preference_count == 0
        assert cp.recommendation_count == 0

    def test_learn_preference(self):
        cp = ChannelPreferenceEngine()
        result = cp.learn_preference("u1", "telegram")
        assert result["learned"] is True
        assert cp.preference_count == 1

    def test_learn_preference_multiple(self):
        cp = ChannelPreferenceEngine()
        cp.learn_preference("u1", "telegram")
        cp.learn_preference("u1", "telegram")
        cp.learn_preference("u1", "email")
        assert cp.preference_count == 3

    def test_recommend_channel_urgency(self):
        cp = ChannelPreferenceEngine()
        result = cp.recommend_channel(
            "u1", urgency="critical",
        )
        assert result["recommended"] == "voice"
        assert cp.recommendation_count == 1

    def test_recommend_channel_low(self):
        cp = ChannelPreferenceEngine()
        result = cp.recommend_channel(
            "u1", urgency="low",
        )
        assert result["recommended"] == "email"

    def test_recommend_channel_with_override(self):
        cp = ChannelPreferenceEngine()
        cp.set_override("u1", "sms")
        result = cp.recommend_channel("u1")
        assert result["recommended"] == "sms"
        assert result["reason"] == "user_override"

    def test_recommend_channel_time_rule(self):
        cp = ChannelPreferenceEngine()
        cp.add_time_rule(22, 6, "sms")
        result = cp.recommend_channel(
            "u1", hour=23,
        )
        assert result["recommended"] == "sms"
        assert result["reason"] == "time_based"

    def test_recommend_channel_content_rule(self):
        cp = ChannelPreferenceEngine()
        cp.add_content_rule("document", "email")
        result = cp.recommend_channel(
            "u1", content_type="document",
        )
        assert result["recommended"] == "email"
        assert result["reason"] == "content_based"

    def test_recommend_channel_learned_preference(self):
        cp = ChannelPreferenceEngine()
        cp.learn_preference("u1", "whatsapp")
        cp.learn_preference("u1", "whatsapp")
        cp.learn_preference("u1", "telegram")
        result = cp.recommend_channel(
            "u1", urgency="low",
        )
        assert result["recommended"] == "whatsapp"

    def test_add_time_rule(self):
        cp = ChannelPreferenceEngine()
        result = cp.add_time_rule(9, 18, "telegram")
        assert result["rule_added"] is True

    def test_add_time_rule_midnight_wrap(self):
        cp = ChannelPreferenceEngine()
        cp.add_time_rule(22, 6, "sms")
        result = cp.recommend_channel("u1", hour=2)
        assert result["recommended"] == "sms"

    def test_add_content_rule(self):
        cp = ChannelPreferenceEngine()
        result = cp.add_content_rule("video", "whatsapp")
        assert result["rule_added"] is True

    def test_set_urgency_channel(self):
        cp = ChannelPreferenceEngine()
        cp.set_urgency_channel("routine", "sms")
        result = cp.recommend_channel(
            "u1", urgency="routine",
        )
        assert result["recommended"] == "sms"

    def test_set_override(self):
        cp = ChannelPreferenceEngine()
        result = cp.set_override("u1", "email", 30)
        assert result["override_set"] is True

    def test_clear_override(self):
        cp = ChannelPreferenceEngine()
        cp.set_override("u1", "email")
        result = cp.clear_override("u1")
        assert result["override_cleared"] is True
        rec = cp.recommend_channel("u1")
        assert rec["reason"] != "user_override"

    def test_get_user_preferences(self):
        cp = ChannelPreferenceEngine()
        cp.learn_preference("u1", "telegram")
        result = cp.get_user_preferences("u1")
        assert result["user_id"] == "u1"
        assert "preferences" in result

    def test_get_user_preferences_empty(self):
        cp = ChannelPreferenceEngine()
        result = cp.get_user_preferences("unknown")
        assert result["preferences"] == {}


# ==================== EscalationPathManager ====================

class TestEscalationPathManager:
    """EscalationPathManager testleri."""

    def test_init(self):
        e = EscalationPathManager()
        assert e.escalation_count == 0
        assert e.rule_count == 0
        assert e.path_count == 3

    def test_add_rule(self):
        e = EscalationPathManager()
        result = e.add_rule(
            "timeout_rule", "timeout > 300",
            "voice",
        )
        assert result["added"] is True
        assert e.rule_count == 1

    def test_escalate_basic(self):
        e = EscalationPathManager()
        result = e.escalate(from_channel="telegram")
        assert result["from_channel"] == "telegram"
        assert result["to_channel"] == "whatsapp"
        assert result["status"] == "active"
        assert e.escalation_count == 1

    def test_escalate_next_in_path(self):
        e = EscalationPathManager()
        result = e.escalate(from_channel="whatsapp")
        assert result["to_channel"] == "email"

    def test_escalate_last_in_path_fallback(self):
        e = EscalationPathManager()
        result = e.escalate(from_channel="voice")
        assert result["to_channel"] is not None

    def test_escalate_emergency_path(self):
        e = EscalationPathManager()
        result = e.escalate(
            from_channel="voice",
            path="emergency",
        )
        assert result["to_channel"] == "sms"

    def test_escalate_business_path(self):
        e = EscalationPathManager()
        result = e.escalate(
            from_channel="email",
            path="business",
        )
        assert result["to_channel"] == "telegram"

    def test_handle_timeout_not_expired(self):
        e = EscalationPathManager()
        result = e.handle_timeout("telegram", 100)
        assert result["timed_out"] is False
        assert "escalated_to" not in result

    def test_handle_timeout_expired(self):
        e = EscalationPathManager()
        result = e.handle_timeout("telegram", 300)
        assert result["timed_out"] is True
        assert "escalated_to" in result

    def test_handle_timeout_no_auto(self):
        e = EscalationPathManager(auto_escalate=False)
        result = e.handle_timeout("telegram", 500)
        assert result["timed_out"] is True
        assert "escalated_to" not in result

    def test_get_fallback(self):
        e = EscalationPathManager()
        result = e.get_fallback("telegram")
        assert result["fallback"] == "email"

    def test_get_fallback_unknown(self):
        e = EscalationPathManager()
        result = e.get_fallback("unknown")
        assert result["fallback"] == "telegram"

    def test_set_fallback(self):
        e = EscalationPathManager()
        result = e.set_fallback("telegram", "sms")
        assert result["set"] is True
        fb = e.get_fallback("telegram")
        assert fb["fallback"] == "sms"

    def test_trigger_emergency(self):
        e = EscalationPathManager()
        result = e.trigger_emergency("server_down")
        assert result["emergency"] is True
        assert result["reason"] == "server_down"
        assert "path_channels" in result

    def test_add_path(self):
        e = EscalationPathManager()
        result = e.add_path(
            "custom", ["sms", "voice", "email"],
        )
        assert result["added"] is True
        assert e.path_count == 4

    def test_get_escalations(self):
        e = EscalationPathManager()
        e.escalate(from_channel="telegram")
        e.escalate(
            from_channel="email",
            level="critical",
        )
        all_esc = e.get_escalations()
        assert len(all_esc) == 2

    def test_get_escalations_by_level(self):
        e = EscalationPathManager()
        e.escalate(
            from_channel="telegram",
            level="medium",
        )
        e.escalate(
            from_channel="email",
            level="critical",
        )
        crit = e.get_escalations(level="critical")
        assert len(crit) == 1


# ==================== UnifiedInbox ====================

class TestUnifiedInbox:
    """UnifiedInbox testleri."""

    def test_init(self):
        inbox = UnifiedInbox()
        assert inbox.message_count == 0
        assert inbox.unread_count == 0
        assert inbox.thread_count == 0

    def test_receive_message(self):
        inbox = UnifiedInbox()
        msg = inbox.receive_message(
            "Hello", "telegram", "u1",
        )
        assert msg["message_id"] == "msg_1"
        assert msg["content"] == "Hello"
        assert msg["read"] is False
        assert inbox.message_count == 1

    def test_receive_message_with_thread(self):
        inbox = UnifiedInbox()
        inbox.receive_message(
            "Hi", "telegram", thread_id="t1",
        )
        inbox.receive_message(
            "Reply", "telegram", thread_id="t1",
        )
        assert inbox.thread_count == 1

    def test_receive_message_priority_clamp(self):
        inbox = UnifiedInbox()
        msg = inbox.receive_message(
            "test", "telegram", priority=15,
        )
        assert msg["priority"] == 10

    def test_get_inbox(self):
        inbox = UnifiedInbox()
        inbox.receive_message("a", "telegram")
        inbox.receive_message("b", "email")
        inbox.receive_message("c", "telegram")
        result = inbox.get_inbox()
        assert len(result) == 3

    def test_get_inbox_by_channel(self):
        inbox = UnifiedInbox()
        inbox.receive_message("a", "telegram")
        inbox.receive_message("b", "email")
        result = inbox.get_inbox(channel="telegram")
        assert len(result) == 1

    def test_get_inbox_unread_only(self):
        inbox = UnifiedInbox()
        m1 = inbox.receive_message("a", "telegram")
        inbox.receive_message("b", "telegram")
        inbox.mark_read(m1["message_id"])
        result = inbox.get_inbox(unread_only=True)
        assert len(result) == 1

    def test_get_inbox_priority_sorted(self):
        inbox = UnifiedInbox()
        inbox.receive_message(
            "low", "telegram", priority=2,
        )
        inbox.receive_message(
            "high", "telegram", priority=9,
        )
        result = inbox.get_inbox()
        assert result[0]["priority"] >= result[1]["priority"]

    def test_mark_read(self):
        inbox = UnifiedInbox()
        msg = inbox.receive_message("a", "telegram")
        result = inbox.mark_read(msg["message_id"])
        assert result["read"] is True
        assert inbox.unread_count == 0

    def test_mark_read_not_found(self):
        inbox = UnifiedInbox()
        result = inbox.mark_read("nonexistent")
        assert result.get("error") == "message_not_found"

    def test_get_thread(self):
        inbox = UnifiedInbox()
        inbox.receive_message(
            "first", "telegram", thread_id="t1",
        )
        inbox.receive_message(
            "second", "telegram", thread_id="t1",
        )
        result = inbox.get_thread("t1")
        assert result["message_count"] == 2

    def test_get_thread_empty(self):
        inbox = UnifiedInbox()
        result = inbox.get_thread("nonexistent")
        assert result["message_count"] == 0

    def test_search(self):
        inbox = UnifiedInbox()
        inbox.receive_message("Hello world", "telegram")
        inbox.receive_message("Goodbye", "email")
        result = inbox.search("hello")
        assert result["total_matches"] == 1

    def test_search_cross_channel(self):
        inbox = UnifiedInbox()
        inbox.receive_message("test msg", "telegram")
        inbox.receive_message("test msg", "email")
        result = inbox.search("test")
        assert result["total_matches"] == 2

    def test_search_with_channel_filter(self):
        inbox = UnifiedInbox()
        inbox.receive_message("test", "telegram")
        inbox.receive_message("test", "email")
        result = inbox.search("test", channel="email")
        assert result["total_matches"] == 1

    def test_search_in_archive(self):
        inbox = UnifiedInbox()
        msg = inbox.receive_message("archived", "telegram")
        inbox.archive_message(msg["message_id"])
        result = inbox.search("archived")
        assert result["total_matches"] >= 1

    def test_archive_message(self):
        inbox = UnifiedInbox()
        msg = inbox.receive_message("old", "telegram")
        result = inbox.archive_message(msg["message_id"])
        assert result["archived"] is True

    def test_archive_message_not_found(self):
        inbox = UnifiedInbox()
        result = inbox.archive_message("nonexistent")
        assert result.get("error") == "message_not_found"

    def test_archived_not_in_inbox(self):
        inbox = UnifiedInbox()
        msg = inbox.receive_message("old", "telegram")
        inbox.archive_message(msg["message_id"])
        result = inbox.get_inbox()
        assert len(result) == 0

    def test_get_archive(self):
        inbox = UnifiedInbox()
        m1 = inbox.receive_message("old1", "telegram")
        m2 = inbox.receive_message("old2", "email")
        inbox.archive_message(m1["message_id"])
        inbox.archive_message(m2["message_id"])
        archive = inbox.get_archive()
        assert len(archive) == 2

    def test_get_stats(self):
        inbox = UnifiedInbox()
        inbox.receive_message("a", "telegram")
        inbox.receive_message("b", "email")
        stats = inbox.get_stats()
        assert stats["total_messages"] == 2
        assert stats["unread"] == 2
        assert "telegram" in stats["by_channel"]
        assert "email" in stats["by_channel"]


# ==================== MultiChannelOrchestrator ====================

class TestMultiChannelOrchestrator:
    """MultiChannelOrchestrator testleri."""

    def test_init(self):
        o = MultiChannelOrchestrator()
        assert o.messages_processed == 0

    def test_process_message(self):
        o = MultiChannelOrchestrator()
        result = o.process_message(
            "show tasks", "telegram", "u1",
        )
        assert result["channel"] == "telegram"
        assert result["intent"] == "query"
        assert result["user_id"] == "u1"
        assert o.messages_processed == 1

    def test_process_message_with_user_id(self):
        o = MultiChannelOrchestrator()
        result = o.process_message(
            "hello", "email",
            sender="admin",
            user_id="uid_1",
        )
        assert result["user_id"] == "uid_1"

    def test_process_message_sender_as_uid(self):
        o = MultiChannelOrchestrator()
        result = o.process_message(
            "hello", "telegram", "admin",
        )
        assert result["user_id"] == "admin"

    def test_send_response(self):
        o = MultiChannelOrchestrator()
        result = o.send_response(
            "u1", "Hello there!",
            channel="telegram",
        )
        assert result["user_id"] == "u1"
        assert result["channel"] == "telegram"
        assert result["route_id"] is not None

    def test_send_response_auto_channel(self):
        o = MultiChannelOrchestrator()
        result = o.send_response(
            "u1", "test", urgency="critical",
        )
        assert result["channel"] is not None
        assert result["urgency"] == "critical"

    def test_send_response_format(self):
        o = MultiChannelOrchestrator()
        result = o.send_response(
            "u1", "**bold**", channel="email",
        )
        assert "<strong>" in result["formatted_content"]

    def test_switch_channel(self):
        o = MultiChannelOrchestrator()
        result = o.switch_channel(
            "u1", "telegram", "email",
        )
        assert result["from_channel"] == "telegram"
        assert result["to_channel"] == "email"
        assert result["context_transferred"] is True

    def test_escalate_message(self):
        o = MultiChannelOrchestrator()
        result = o.escalate_message(
            "u1", "telegram", "timeout",
        )
        assert result["escalated_from"] == "telegram"
        assert result["escalated_to"] is not None
        assert result["reason"] == "timeout"

    def test_get_analytics(self):
        o = MultiChannelOrchestrator()
        o.process_message("hi", "telegram", "u1")
        o.send_response("u1", "hello", channel="telegram")
        analytics = o.get_analytics()
        assert analytics["messages_processed"] == 1
        assert analytics["responses_sent"] == 1
        assert "active_channels" in analytics
        assert "inbox_messages" in analytics

    def test_get_status(self):
        o = MultiChannelOrchestrator()
        status = o.get_status()
        assert "messages_processed" in status
        assert "active_channels" in status
        assert "active_sessions" in status
        assert "unread_messages" in status

    def test_urgency_to_priority(self):
        o = MultiChannelOrchestrator()
        assert o._urgency_to_priority("critical") == 10
        assert o._urgency_to_priority("high") == 8
        assert o._urgency_to_priority("medium") == 5
        assert o._urgency_to_priority("low") == 3
        assert o._urgency_to_priority("routine") == 1
        assert o._urgency_to_priority("unknown") == 5

    def test_full_pipeline(self):
        o = MultiChannelOrchestrator()
        proc = o.process_message(
            "run backup", "telegram", "u1",
        )
        assert proc["intent"] == "action"

        resp = o.send_response(
            "u1", "Backup started",
            channel="telegram",
        )
        assert resp["route_id"] is not None

        switch = o.switch_channel(
            "u1", "telegram", "email",
        )
        assert switch["context_transferred"] is True

        esc = o.escalate_message(
            "u1", "email", "no_response",
        )
        assert esc["escalated_to"] is not None

        analytics = o.get_analytics()
        assert analytics["messages_processed"] == 1
        assert analytics["responses_sent"] == 1


# ==================== Config ====================

class TestMultiChannelConfig:
    """MultiChannel config testleri."""

    def test_config_defaults(self):
        from app.config import Settings
        s = Settings()
        assert s.multichannel_enabled is True
        assert s.multichannel_default_channel == "telegram"
        assert s.context_timeout_minutes == 30
        assert s.multichannel_auto_escalate is True
        assert s.unified_inbox_enabled is True


# ==================== Imports ====================

class TestMultiChannelImports:
    """MultiChannel import testleri."""

    def test_import_all_from_init(self):
        from app.core.multichannel import (
            AvailabilityTracker,
            ChannelPreferenceEngine,
            ChannelRouter,
            CommandInterpreter,
            ContextCarrier,
            EscalationPathManager,
            MultiChannelOrchestrator,
            ResponseFormatter,
            UnifiedInbox,
        )
        assert AvailabilityTracker is not None
        assert ChannelPreferenceEngine is not None
        assert ChannelRouter is not None
        assert CommandInterpreter is not None
        assert ContextCarrier is not None
        assert EscalationPathManager is not None
        assert MultiChannelOrchestrator is not None
        assert ResponseFormatter is not None
        assert UnifiedInbox is not None

    def test_import_all_models(self):
        from app.models.multichannel_models import (
            ChannelMessage,
            ChannelType,
            CommandType,
            EscalationLevel,
            EscalationRecord,
            FormatType,
            MessageDirection,
            MultiChannelSnapshot,
            PresenceStatus,
            SessionRecord,
        )
        assert ChannelMessage is not None
        assert ChannelType is not None
        assert CommandType is not None
        assert EscalationLevel is not None
        assert EscalationRecord is not None
        assert FormatType is not None
        assert MessageDirection is not None
        assert MultiChannelSnapshot is not None
        assert PresenceStatus is not None
        assert SessionRecord is not None
