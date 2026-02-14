"""Context-Aware Assistant sistemi testleri."""

from datetime import datetime, timedelta, timezone

import pytest

from app.models.assistant import (
    AssistantSnapshot,
    ChannelType,
    ContextSnapshot,
    ContextType,
    ConversationEntry,
    IntentCategory,
    IntentPrediction,
    PreferenceType,
    ProactiveAction,
    ProactiveType,
    ResponseFormat,
    SmartResponse,
    UserPreference,
)


# ── Model Testleri ──────────────────────────────────────────


class TestAssistantModels:
    """Model testleri."""

    def test_context_snapshot_defaults(self):
        s = ContextSnapshot()
        assert s.context_type == ContextType.USER
        assert s.relevance == 0.5
        assert s.data == {}
        assert s.context_id

    def test_context_snapshot_custom(self):
        s = ContextSnapshot(
            context_type=ContextType.TASK,
            data={"task_id": "t1"},
            relevance=0.9,
        )
        assert s.context_type == ContextType.TASK
        assert s.data["task_id"] == "t1"
        assert s.relevance == 0.9

    def test_intent_prediction_defaults(self):
        p = IntentPrediction()
        assert p.category == IntentCategory.QUERY
        assert p.confidence == 0.5
        assert p.predicted_action == ""

    def test_smart_response_defaults(self):
        r = SmartResponse()
        assert r.format == ResponseFormat.TEXT
        assert r.tone == "neutral"
        assert r.channel == ChannelType.TELEGRAM

    def test_user_preference_defaults(self):
        p = UserPreference()
        assert p.preference_type == PreferenceType.COMMUNICATION
        assert p.learned_from == 0

    def test_conversation_entry_defaults(self):
        e = ConversationEntry()
        assert e.role == "user"
        assert e.content == ""
        assert e.references == []

    def test_proactive_action_defaults(self):
        a = ProactiveAction()
        assert a.action_type == ProactiveType.SUGGESTION
        assert a.urgency == 0.5

    def test_assistant_snapshot_defaults(self):
        s = AssistantSnapshot()
        assert s.total_conversations == 0
        assert s.prediction_accuracy == 0.0

    def test_enum_values(self):
        assert ContextType.USER == "user"
        assert IntentCategory.COMMAND == "command"
        assert ResponseFormat.LIST == "list"
        assert ChannelType.TELEGRAM == "telegram"
        assert PreferenceType.STYLE == "style"
        assert ProactiveType.REMINDER == "reminder"

    def test_context_snapshot_unique_ids(self):
        s1 = ContextSnapshot()
        s2 = ContextSnapshot()
        assert s1.context_id != s2.context_id

    def test_smart_response_custom(self):
        r = SmartResponse(
            content="test",
            format=ResponseFormat.LIST,
            tone="friendly",
            detail_level=0.8,
            channel=ChannelType.EMAIL,
        )
        assert r.content == "test"
        assert r.format == ResponseFormat.LIST
        assert r.channel == ChannelType.EMAIL

    def test_proactive_action_custom(self):
        a = ProactiveAction(
            action_type=ProactiveType.ALERT,
            title="Deadline",
            urgency=0.9,
            relevance=0.95,
        )
        assert a.action_type == ProactiveType.ALERT
        assert a.urgency == 0.9


# ── ContextBuilder Testleri ──────────────────────────────────


class TestContextBuilder:
    """ContextBuilder testleri."""

    def setup_method(self):
        from app.core.assistant.context_builder import ContextBuilder
        self.builder = ContextBuilder(context_window=20)

    def test_init(self):
        assert self.builder.context_count == 0
        assert self.builder.conversation_length == 0

    def test_load_user_profile(self):
        snap = self.builder.load_user_profile({"name": "Fatih", "role": "admin"})
        assert snap.context_type == ContextType.USER
        assert self.builder.user_profile["name"] == "Fatih"

    def test_add_conversation_turn(self):
        snap = self.builder.add_conversation_turn("user", "Merhaba")
        assert snap.context_type == ContextType.CONVERSATION
        assert self.builder.conversation_length == 1

    def test_conversation_window_limit(self):
        builder = __import__(
            "app.core.assistant.context_builder", fromlist=["ContextBuilder"]
        ).ContextBuilder(context_window=3)
        for i in range(5):
            builder.add_conversation_turn("user", f"msg {i}")
        assert builder.conversation_length == 3

    def test_set_task_context(self):
        snap = self.builder.set_task_context("t1", {"type": "deploy"})
        assert snap.context_type == ContextType.TASK
        assert self.builder.has_task_context

    def test_clear_task_context(self):
        self.builder.set_task_context("t1", {"type": "deploy"})
        self.builder.clear_task_context()
        assert not self.builder.has_task_context

    def test_update_environment(self):
        snap = self.builder.update_environment({"platform": "linux"})
        assert snap.context_type == ContextType.ENVIRONMENT

    def test_get_temporal_context(self):
        snap = self.builder.get_temporal_context()
        assert snap.context_type == ContextType.TEMPORAL
        assert "hour" in snap.data

    def test_build_full_context(self):
        self.builder.load_user_profile({"name": "Test"})
        self.builder.add_conversation_turn("user", "Hello")
        ctx = self.builder.build_full_context()
        assert "user_profile" in ctx
        assert "conversation_history" in ctx
        assert "temporal" in ctx
        assert ctx["total_turns"] == 1

    def test_get_relevant_context(self):
        self.builder.load_user_profile({"name": "Fatih"})
        self.builder.add_conversation_turn("user", "deploy server")
        results = self.builder.get_relevant_context("deploy", top_k=3)
        assert len(results) > 0

    def test_get_contexts_by_type(self):
        self.builder.load_user_profile({"name": "Test"})
        self.builder.update_environment({"os": "linux"})
        user_ctxs = self.builder.get_contexts_by_type(ContextType.USER)
        assert len(user_ctxs) == 1

    def test_context_count(self):
        self.builder.load_user_profile({"a": 1})
        self.builder.add_conversation_turn("user", "hi")
        assert self.builder.context_count == 2


# ── IntentPredictor Testleri ─────────────────────────────────


class TestIntentPredictor:
    """IntentPredictor testleri."""

    def setup_method(self):
        from app.core.assistant.intent_predictor import IntentPredictor
        self.predictor = IntentPredictor()

    def test_init(self):
        assert self.predictor.prediction_count == 0
        assert self.predictor.sequence_count == 0

    def test_record_action(self):
        self.predictor.record_action("deploy")
        assert self.predictor.sequence_count == 1

    def test_predict_next_no_data(self):
        pred = self.predictor.predict_next("unknown")
        assert pred.predicted_action == "unknown"
        assert pred.confidence == 0.1

    def test_predict_next_with_data(self):
        self.predictor.record_action("deploy")
        self.predictor.record_action("monitor")
        self.predictor.record_action("deploy")
        self.predictor.record_action("monitor")
        pred = self.predictor.predict_next("deploy")
        assert pred.predicted_action == "monitor"
        assert pred.confidence > 0.5

    def test_suggest_proactively(self):
        self.predictor.record_action("deploy")
        self.predictor.record_action("monitor")
        self.predictor.record_action("deploy")
        self.predictor.record_action("test")
        suggestions = self.predictor.suggest_proactively(["deploy"])
        assert len(suggestions) > 0

    def test_add_pattern(self):
        self.predictor.add_pattern("ci_cd", ["build", "test", "deploy"])
        assert self.predictor.pattern_count == 1

    def test_recognize_pattern(self):
        self.predictor.add_pattern("ci_cd", ["build", "test", "deploy"])
        result = self.predictor.recognize_pattern(["build", "test"])
        assert result["matched"]
        assert result["pattern"] == "ci_cd"

    def test_recognize_pattern_no_match(self):
        self.predictor.add_pattern("ci_cd", ["build", "test", "deploy"])
        result = self.predictor.recognize_pattern(["eat", "sleep"])
        assert not result["matched"]

    def test_verify_prediction_correct(self):
        self.predictor.record_action("a")
        self.predictor.record_action("b")
        pred = self.predictor.predict_next("a")
        result = self.predictor.verify_prediction(pred.prediction_id, "b")
        assert result["verified"]
        assert result["correct"]

    def test_verify_prediction_wrong(self):
        self.predictor.record_action("a")
        self.predictor.record_action("b")
        pred = self.predictor.predict_next("a")
        result = self.predictor.verify_prediction(pred.prediction_id, "c")
        assert result["verified"]
        assert not result["correct"]

    def test_verify_prediction_not_found(self):
        result = self.predictor.verify_prediction("nonexistent", "x")
        assert not result["verified"]

    def test_accuracy(self):
        self.predictor.record_action("a")
        self.predictor.record_action("b")
        pred = self.predictor.predict_next("a")
        self.predictor.verify_prediction(pred.prediction_id, "b")
        assert self.predictor.accuracy == 1.0

    def test_get_behavior_model(self):
        self.predictor.record_action("x")
        self.predictor.record_action("y")
        model = self.predictor.get_behavior_model()
        assert "x" in model
        assert model["x"]["y"] == 1


# ── SmartResponder Testleri ──────────────────────────────────


class TestSmartResponder:
    """SmartResponder testleri."""

    def setup_method(self):
        from app.core.assistant.smart_responder import SmartResponder
        self.responder = SmartResponder()

    def test_init(self):
        assert self.responder.response_count == 0

    def test_generate_response(self):
        resp = self.responder.generate_response("Hello world")
        assert resp.content
        assert resp.format == ResponseFormat.TEXT
        assert self.responder.response_count == 1

    def test_generate_response_with_context(self):
        resp = self.responder.generate_response(
            "Error occurred",
            context={"error": True},
        )
        assert resp.tone == "empathetic"

    def test_generate_response_email_channel(self):
        resp = self.responder.generate_response(
            "Report ready",
            channel=ChannelType.EMAIL,
        )
        assert resp.channel == ChannelType.EMAIL
        assert "Saygilarimla" in resp.content

    def test_adapt_tone_formal(self):
        result = self.responder.adapt_tone("hey there!", "formal")
        assert "merhaba" in result

    def test_adapt_tone_friendly(self):
        result = self.responder.adapt_tone("Hello", "friendly")
        assert result.endswith("!")

    def test_adapt_tone_direct(self):
        result = self.responder.adapt_tone(
            "First sentence. Second sentence. Third sentence. Fourth sentence.",
            "direct",
        )
        # Direct should be shorter
        assert len(result) <= len(
            "First sentence. Second sentence. Third sentence. Fourth sentence."
        )

    def test_adjust_detail_low(self):
        content = "First. Second. Third. Fourth."
        result = self.responder.adjust_detail(content, 0.1)
        assert "Fourth" not in result

    def test_adjust_detail_high(self):
        content = "First. Second. Third."
        result = self.responder.adjust_detail(content, 0.9)
        assert result == content

    def test_optimize_format_list(self):
        result = self.responder.optimize_format(
            "Item one. Item two. Item three.",
            ResponseFormat.LIST,
        )
        assert result.startswith("- ")

    def test_optimize_format_summary(self):
        result = self.responder.optimize_format(
            "First sentence. Second sentence. Third sentence.",
            ResponseFormat.SUMMARY,
        )
        assert "Third" not in result

    def test_add_template(self):
        self.responder.add_template("greeting", "Merhaba {name}!")
        assert self.responder.template_count == 1

    def test_render_template(self):
        self.responder.add_template("greeting", "Merhaba {name}!")
        result = self.responder.render_template("greeting", {"name": "Fatih"})
        assert result == "Merhaba Fatih!"

    def test_render_template_not_found(self):
        result = self.responder.render_template("missing", {})
        assert result is None

    def test_format_for_channel_voice(self):
        result = self.responder.format_for_channel(
            "One. Two. Three. Four. Five.",
            ChannelType.VOICE,
        )
        assert len(result.split(". ")) <= 4

    def test_add_tone_rule(self):
        self.responder.add_tone_rule("warning", "cautious")
        assert self.responder.tone_rule_count > 5

    def test_generate_with_list_format(self):
        resp = self.responder.generate_response(
            "Item A. Item B.",
            context={"list_request": True},
        )
        assert resp.format == ResponseFormat.LIST


# ── TaskInferrer Testleri ────────────────────────────────────


class TestTaskInferrer:
    """TaskInferrer testleri."""

    def setup_method(self):
        from app.core.assistant.task_inferrer import TaskInferrer
        self.inferrer = TaskInferrer()

    def test_init(self):
        assert self.inferrer.inferred_count == 0

    def test_detect_implicit_task_deploy(self):
        result = self.inferrer.detect_implicit_task("deploy the server")
        assert result["has_implicit_task"]
        assert result["tasks"][0]["type"] == "deploy"

    def test_detect_implicit_task_question(self):
        result = self.inferrer.detect_implicit_task("How is the server?")
        assert result["has_implicit_task"]
        assert any(t["type"] == "query" for t in result["tasks"])

    def test_detect_implicit_task_no_match(self):
        result = self.inferrer.detect_implicit_task("hello")
        assert not result["has_implicit_task"]

    def test_detect_multiple_tasks(self):
        result = self.inferrer.detect_implicit_task("analiz et ve rapor olustur")
        assert result["tasks_found"] >= 2

    def test_resolve_ambiguity_clear(self):
        result = self.inferrer.resolve_ambiguity("test", [
            {"intent": "deploy", "confidence": 0.9},
            {"intent": "monitor", "confidence": 0.3},
        ])
        assert result["resolved"]
        assert result["selected_intent"]["intent"] == "deploy"

    def test_resolve_ambiguity_unclear(self):
        result = self.inferrer.resolve_ambiguity("test", [
            {"intent": "deploy", "confidence": 0.5},
            {"intent": "monitor", "confidence": 0.45},
        ])
        assert result["needs_clarification"]

    def test_resolve_ambiguity_no_intents(self):
        result = self.inferrer.resolve_ambiguity("test", [])
        assert not result["resolved"]

    def test_predict_follow_up_deploy(self):
        follow_ups = self.inferrer.predict_follow_up("deploy app")
        assert len(follow_ups) > 0

    def test_predict_follow_up_with_errors(self):
        follow_ups = self.inferrer.predict_follow_up(
            "run tests",
            {"has_errors": True},
        )
        assert any("Fix" in f["task"] for f in follow_ups)

    def test_detect_completion_done(self):
        result = self.inferrer.detect_completion(
            "Deploy app",
            {"status": "completed"},
        )
        assert result["is_complete"]

    def test_detect_completion_progress_100(self):
        result = self.inferrer.detect_completion(
            "Build",
            {"progress": 100},
        )
        assert result["is_complete"]

    def test_detect_completion_in_progress(self):
        result = self.inferrer.detect_completion(
            "Build",
            {"progress": 50, "status": "running"},
        )
        assert not result["is_complete"]

    def test_suggest_next_step_completed(self):
        result = self.inferrer.suggest_next_step("deploy app", progress=100)
        assert result["status"] == "completed"

    def test_suggest_next_step_in_progress(self):
        result = self.inferrer.suggest_next_step("build", progress=50)
        assert result["status"] == "in_progress"

    def test_suggest_next_step_starting(self):
        result = self.inferrer.suggest_next_step("build", progress=5)
        assert result["status"] == "starting"

    def test_add_task_keywords(self):
        self.inferrer.add_task_keywords("test", ["test", "dogrula"])
        result = self.inferrer.detect_implicit_task("dogrula bunu")
        assert result["has_implicit_task"]


# ── PreferenceLearner Testleri ───────────────────────────────


class TestPreferenceLearner:
    """PreferenceLearner testleri."""

    def setup_method(self):
        from app.core.assistant.preference_learner import PreferenceLearner
        self.learner = PreferenceLearner(confidence_threshold=0.6)

    def test_init(self):
        assert self.learner.preference_count == 0
        assert self.learner.interaction_count == 0

    def test_observe_interaction(self):
        self.learner.observe_interaction("click", {"element": "button"})
        assert self.learner.interaction_count == 1

    def test_learn_from_feedback_positive(self):
        pref = self.learner.learn_from_feedback(
            "tone", PreferenceType.COMMUNICATION, "formal",
        )
        assert pref.confidence == 0.5
        assert pref.value == "formal"

    def test_learn_from_feedback_reinforced(self):
        self.learner.learn_from_feedback(
            "tone", PreferenceType.COMMUNICATION, "formal",
        )
        pref = self.learner.learn_from_feedback(
            "tone", PreferenceType.COMMUNICATION, "formal",
        )
        assert pref.confidence == 0.6
        assert pref.learned_from == 2

    def test_learn_from_feedback_negative(self):
        self.learner.learn_from_feedback(
            "tone", PreferenceType.COMMUNICATION, "formal",
        )
        pref = self.learner.learn_from_feedback(
            "tone", PreferenceType.COMMUNICATION, "casual",
            is_positive=False,
        )
        assert pref.confidence < 0.5

    def test_learn_style_preference(self):
        pref = self.learner.learn_style_preference("theme", "dark")
        assert pref.preference_type == PreferenceType.STYLE
        assert pref.key == "style_theme"

    def test_learn_communication_preference(self):
        pref = self.learner.learn_communication_preference("language", "tr")
        assert pref.preference_type == PreferenceType.COMMUNICATION

    def test_learn_tool_preference(self):
        pref = self.learner.learn_tool_preference("vim")
        assert pref.preference_type == PreferenceType.TOOL

    def test_learn_time_preference(self):
        pref = self.learner.learn_time_preference("work_hours", "9-18")
        assert pref.preference_type == PreferenceType.TIME

    def test_get_preference(self):
        self.learner.learn_from_feedback(
            "key1", PreferenceType.STYLE, "value1",
        )
        pref = self.learner.get_preference("key1")
        assert pref is not None
        assert pref.value == "value1"

    def test_get_preference_not_found(self):
        assert self.learner.get_preference("nonexistent") is None

    def test_get_preferences_by_type(self):
        self.learner.learn_style_preference("a", "1")
        self.learner.learn_tool_preference("b")
        styles = self.learner.get_preferences_by_type(PreferenceType.STYLE)
        assert len(styles) == 1

    def test_get_confident_preferences(self):
        self.learner.learn_from_feedback("x", PreferenceType.STYLE, "y")
        # confidence=0.5 < threshold=0.6
        assert self.learner.confident_count == 0
        # Reinforce
        self.learner.learn_from_feedback("x", PreferenceType.STYLE, "y")
        # confidence=0.6 == threshold
        assert self.learner.confident_count == 1

    def test_get_preference_summary(self):
        self.learner.learn_style_preference("a", "1")
        summary = self.learner.get_preference_summary()
        assert summary["total"] == 1
        assert "style" in summary["by_type"]

    def test_apply_preferences(self):
        self.learner.learn_from_feedback("x", PreferenceType.STYLE, "dark")
        self.learner.learn_from_feedback("x", PreferenceType.STYLE, "dark")
        result = self.learner.apply_preferences({"key": "val"})
        assert "preferences" in result

    def test_decay_preferences(self):
        self.learner.learn_from_feedback("x", PreferenceType.STYLE, "dark")
        decayed = self.learner.decay_preferences(decay_rate=0.1)
        assert decayed == 1
        pref = self.learner.get_preference("x")
        assert pref is not None
        assert pref.confidence < 0.5

    def test_reset_preference(self):
        self.learner.learn_from_feedback("x", PreferenceType.STYLE, "dark")
        assert self.learner.reset_preference("x")
        assert self.learner.preference_count == 0

    def test_reset_preference_not_found(self):
        assert not self.learner.reset_preference("nonexistent")


# ── ProactiveHelper Testleri ─────────────────────────────────


class TestProactiveHelper:
    """ProactiveHelper testleri."""

    def setup_method(self):
        from app.core.assistant.proactive_helper import ProactiveHelper
        self.helper = ProactiveHelper()

    def test_init(self):
        assert self.helper.action_count == 0

    def test_suggest(self):
        action = self.helper.suggest("Test", "Test oneri", urgency=0.7)
        assert action.action_type == ProactiveType.SUGGESTION
        assert action.urgency == 0.7
        assert self.helper.action_count == 1

    def test_add_reminder(self):
        action = self.helper.add_reminder("Toplanti", "Saat 15:00")
        assert action.action_type == ProactiveType.REMINDER
        assert self.helper.reminder_count == 1

    def test_add_deadline(self):
        deadline = datetime.now(timezone.utc) + timedelta(hours=12)
        action = self.helper.add_deadline("Rapor", deadline)
        assert action.action_type == ProactiveType.ALERT
        assert self.helper.deadline_count == 1

    def test_notify_opportunity(self):
        action = self.helper.notify_opportunity("Firsat", "Yeni musteri")
        assert action.action_type == ProactiveType.OPPORTUNITY

    def test_prevent_problem(self):
        action = self.helper.prevent_problem("Disk dolu", "90% kullanim")
        assert action.action_type == ProactiveType.PREVENTION

    def test_add_rule(self):
        rule = self.helper.add_rule(
            "disk_full", ProactiveType.ALERT, "Disk", "Disk dolu",
        )
        assert self.helper.rule_count == 1
        assert rule["triggered_count"] == 0

    def test_evaluate_rules(self):
        self.helper.add_rule(
            "error", ProactiveType.ALERT, "Hata", "Hata tespit edildi",
        )
        actions = self.helper.evaluate_rules({"message": "error occurred"})
        assert len(actions) == 1

    def test_evaluate_rules_no_match(self):
        self.helper.add_rule(
            "error", ProactiveType.ALERT, "Hata", "Hata",
        )
        actions = self.helper.evaluate_rules({"message": "all good"})
        assert len(actions) == 0

    def test_check_deadlines_approaching(self):
        deadline = datetime.now(timezone.utc) + timedelta(hours=2)
        self.helper.add_deadline("Rapor", deadline, alert_before_hours=24)
        approaching = self.helper.check_deadlines()
        assert len(approaching) == 1

    def test_check_deadlines_not_yet(self):
        deadline = datetime.now(timezone.utc) + timedelta(days=30)
        self.helper.add_deadline("Rapor", deadline, alert_before_hours=24)
        approaching = self.helper.check_deadlines()
        assert len(approaching) == 0

    def test_check_reminders(self):
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        self.helper.add_reminder("Test", "Test", remind_at=past)
        triggered = self.helper.check_reminders()
        assert len(triggered) == 1

    def test_dismiss_action(self):
        action = self.helper.suggest("Test", "Test")
        assert self.helper.dismiss_action(action.action_id)
        assert self.helper.pending_count == 0

    def test_dismiss_action_not_found(self):
        assert not self.helper.dismiss_action("nonexistent")

    def test_get_pending_actions(self):
        self.helper.suggest("Low", "Low", urgency=0.2)
        self.helper.suggest("High", "High", urgency=0.8)
        pending = self.helper.get_pending_actions(min_urgency=0.5)
        assert len(pending) == 1

    def test_get_actions_by_type(self):
        self.helper.suggest("S", "S")
        self.helper.add_reminder("R", "R")
        suggestions = self.helper.get_actions_by_type(ProactiveType.SUGGESTION)
        assert len(suggestions) == 1


# ── ConversationMemory Testleri ──────────────────────────────


class TestConversationMemory:
    """ConversationMemory testleri."""

    def setup_method(self):
        from app.core.assistant.conversation_memory import ConversationMemory
        self.memory = ConversationMemory(max_entries=50)

    def test_init(self):
        assert self.memory.entry_count == 0
        assert self.memory.topic_count == 0

    def test_add_entry(self):
        entry = self.memory.add_entry("user", "Merhaba")
        assert entry.role == "user"
        assert entry.content == "Merhaba"
        assert self.memory.entry_count == 1

    def test_add_entry_with_topic(self):
        self.memory.add_entry("user", "Deploy", topic="deployment")
        assert self.memory.active_topic == "deployment"
        assert self.memory.topic_count == 1

    def test_set_topic(self):
        self.memory.set_topic("testing")
        assert self.memory.active_topic == "testing"

    def test_get_topic_entries(self):
        self.memory.add_entry("user", "Deploy 1", topic="deploy")
        self.memory.add_entry("user", "Other stuff", topic="other")
        self.memory.add_entry("user", "Deploy 2", topic="deploy")
        entries = self.memory.get_topic_entries("deploy")
        assert len(entries) == 2

    def test_get_recent_entries(self):
        for i in range(10):
            self.memory.add_entry("user", f"msg {i}")
        recent = self.memory.get_recent_entries(limit=3)
        assert len(recent) == 3
        assert "msg 9" in recent[-1].content

    def test_search_entries(self):
        self.memory.add_entry("user", "deploy the server")
        self.memory.add_entry("user", "check the logs")
        self.memory.add_entry("user", "deploy again")
        results = self.memory.search_entries("deploy")
        assert len(results) == 2

    def test_resolve_reference_by_id(self):
        entry = self.memory.add_entry("user", "Test")
        resolved = self.memory.resolve_reference(entry.entry_id)
        assert resolved is not None
        assert resolved.content == "Test"

    def test_resolve_reference_last(self):
        self.memory.add_entry("user", "First")
        self.memory.add_entry("user", "Second")
        resolved = self.memory.resolve_reference("son")
        assert resolved is not None
        assert resolved.content == "Second"

    def test_resolve_reference_by_content(self):
        self.memory.add_entry("user", "deploy production")
        resolved = self.memory.resolve_reference("deploy")
        assert resolved is not None

    def test_resolve_reference_not_found(self):
        assert self.memory.resolve_reference("nonexistent") is None

    def test_recall_topic(self):
        self.memory.add_entry("user", "Build app", topic="ci")
        self.memory.add_entry("user", "Other", topic="other")
        result = self.memory.recall_topic("ci")
        assert result["found"]
        assert result["entry_count"] == 1

    def test_recall_topic_not_found(self):
        result = self.memory.recall_topic("nonexistent")
        assert not result["found"]

    def test_save_and_restore_context(self):
        self.memory.add_entry("user", "Context data", topic="deploy")
        save_result = self.memory.save_context("checkpoint_1")
        assert save_result["saved"]

        restore_result = self.memory.restore_context("checkpoint_1")
        assert restore_result["restored"]

    def test_restore_context_not_found(self):
        result = self.memory.restore_context("nonexistent")
        assert not result["restored"]

    def test_save_context_empty(self):
        result = self.memory.save_context("empty")
        assert not result["saved"]

    def test_get_topic_summary(self):
        self.memory.add_entry("user", "A", topic="t1")
        self.memory.add_entry("user", "B", topic="t2")
        summary = self.memory.get_topic_summary()
        assert summary["total_topics"] == 2

    def test_get_channel_entries(self):
        self.memory.add_entry("user", "A", channel=ChannelType.TELEGRAM)
        self.memory.add_entry("user", "B", channel=ChannelType.EMAIL)
        tg = self.memory.get_channel_entries(ChannelType.TELEGRAM)
        assert len(tg) == 1

    def test_max_entries_limit(self):
        mem = __import__(
            "app.core.assistant.conversation_memory", fromlist=["ConversationMemory"]
        ).ConversationMemory(max_entries=15)
        for i in range(25):
            mem.add_entry("user", f"msg {i}")
        assert mem.entry_count == 15


# ── MultiChannelHandler Testleri ─────────────────────────────


class TestMultiChannelHandler:
    """MultiChannelHandler testleri."""

    def setup_method(self):
        from app.core.assistant.multi_channel_handler import MultiChannelHandler
        self.handler = MultiChannelHandler()

    def test_init(self):
        assert self.handler.channel_count == 0
        assert self.handler.message_count == 0

    def test_register_channel(self):
        result = self.handler.register_channel(ChannelType.TELEGRAM)
        assert result["active"]
        assert self.handler.channel_count == 1

    def test_unregister_channel(self):
        self.handler.register_channel(ChannelType.TELEGRAM)
        assert self.handler.unregister_channel(ChannelType.TELEGRAM)
        assert self.handler.active_channel_count == 0

    def test_unregister_nonexistent(self):
        assert not self.handler.unregister_channel(ChannelType.API)

    def test_send_message(self):
        result = self.handler.send_message("Hello", ChannelType.TELEGRAM)
        assert result["sent"]
        assert self.handler.message_count == 1

    def test_send_message_email_format(self):
        result = self.handler.send_message("Report", ChannelType.EMAIL)
        assert "Saygilarimla" in result["content"]

    def test_send_message_voice_short(self):
        long_text = ". ".join([f"Sentence {i}" for i in range(10)])
        result = self.handler.send_message(long_text, ChannelType.VOICE)
        assert len(result["content"]) < len(long_text)

    def test_broadcast(self):
        self.handler.register_channel(ChannelType.TELEGRAM)
        self.handler.register_channel(ChannelType.EMAIL)
        results = self.handler.broadcast("Hello all")
        assert len(results) == 2

    def test_sync_context(self):
        result = self.handler.sync_context(
            ChannelType.TELEGRAM,
            ChannelType.EMAIL,
            {"topic": "deploy"},
        )
        assert result["synced"]
        assert self.handler.sync_count == 1

    def test_get_sync_state(self):
        self.handler.sync_context(
            ChannelType.TELEGRAM, ChannelType.EMAIL, {"x": 1},
        )
        state = self.handler.get_sync_state(
            ChannelType.TELEGRAM, ChannelType.EMAIL,
        )
        assert state is not None

    def test_get_sync_state_not_found(self):
        state = self.handler.get_sync_state(
            ChannelType.TELEGRAM, ChannelType.VOICE,
        )
        assert state is None

    def test_get_channel_config(self):
        config = self.handler.get_channel_config(ChannelType.TELEGRAM)
        assert config["max_length"] == 4096

    def test_get_channel_messages(self):
        self.handler.send_message("A", ChannelType.TELEGRAM)
        self.handler.send_message("B", ChannelType.EMAIL)
        self.handler.send_message("C", ChannelType.TELEGRAM)
        msgs = self.handler.get_channel_messages(ChannelType.TELEGRAM)
        assert len(msgs) == 2

    def test_get_active_channels(self):
        self.handler.register_channel(ChannelType.TELEGRAM)
        self.handler.register_channel(ChannelType.EMAIL)
        active = self.handler.get_active_channels()
        assert len(active) == 2

    def test_get_channel_stats(self):
        self.handler.register_channel(ChannelType.TELEGRAM)
        self.handler.send_message("test", ChannelType.TELEGRAM)
        stats = self.handler.get_channel_stats()
        assert stats["total_messages"] == 1


# ── AssistantOrchestrator Testleri ───────────────────────────


class TestAssistantOrchestrator:
    """AssistantOrchestrator testleri."""

    def setup_method(self):
        from app.core.assistant.assistant_orchestrator import AssistantOrchestrator
        self.orch = AssistantOrchestrator(
            context_window=20,
            learning_enabled=True,
            proactive_mode=True,
            multi_channel=True,
        )

    def test_init(self):
        assert self.orch.interaction_count == 0

    def test_handle_message(self):
        result = self.orch.handle_message("Merhaba")
        assert result["response"]
        assert result["interaction"] == 1

    def test_handle_message_with_task(self):
        result = self.orch.handle_message("deploy the server")
        assert result["tasks_detected"] >= 1

    def test_handle_message_channel(self):
        result = self.orch.handle_message(
            "Report", channel=ChannelType.EMAIL,
        )
        assert result["channel"] == "email"

    def test_predict_next_intent(self):
        self.orch.handle_message("deploy app")
        self.orch.handle_message("check status")
        result = self.orch.predict_next_intent("deploy")
        assert "predicted_action" in result

    def test_get_proactive_suggestions(self):
        self.orch.helper.add_rule(
            "error", ProactiveType.ALERT, "Hata", "Hata var",
        )
        suggestions = self.orch.get_proactive_suggestions(
            {"message": "error"},
        )
        assert len(suggestions) >= 1

    def test_learn_preference(self):
        result = self.orch.learn_preference("tone", "formal")
        assert result["learned"]

    def test_learn_preference_disabled(self):
        from app.core.assistant.assistant_orchestrator import AssistantOrchestrator
        orch = AssistantOrchestrator(learning_enabled=False)
        result = orch.learn_preference("tone", "formal")
        assert not result["learned"]

    def test_recall_conversation(self):
        self.orch.memory.add_entry("user", "Deploy app", topic="deploy")
        result = self.orch.recall_conversation("deploy")
        assert result["found"]

    def test_search_history(self):
        self.orch.handle_message("deploy the server")
        results = self.orch.search_history("deploy")
        assert len(results) > 0

    def test_send_to_channel(self):
        result = self.orch.send_to_channel("Hello", ChannelType.TELEGRAM)
        assert result["sent"]

    def test_send_to_channel_disabled(self):
        from app.core.assistant.assistant_orchestrator import AssistantOrchestrator
        orch = AssistantOrchestrator(multi_channel=False)
        result = orch.send_to_channel("Hello", ChannelType.TELEGRAM)
        assert not result["sent"]

    def test_broadcast_message(self):
        self.orch.channels.register_channel(ChannelType.TELEGRAM)
        results = self.orch.broadcast_message("Hello all")
        assert len(results) >= 1

    def test_get_snapshot(self):
        self.orch.handle_message("test")
        snap = self.orch.get_snapshot()
        assert snap.total_conversations > 0
        assert snap.uptime_seconds >= 0

    def test_subsystem_access(self):
        assert self.orch.context is not None
        assert self.orch.predictor is not None
        assert self.orch.responder is not None
        assert self.orch.inferrer is not None
        assert self.orch.learner is not None
        assert self.orch.helper is not None
        assert self.orch.memory is not None
        assert self.orch.channels is not None


# ── Entegrasyon Testleri ─────────────────────────────────────


class TestAssistantIntegration:
    """Entegrasyon testleri."""

    def test_full_conversation_flow(self):
        from app.core.assistant.assistant_orchestrator import AssistantOrchestrator
        orch = AssistantOrchestrator()

        # Profil yukle
        orch.context.load_user_profile({"name": "Fatih"})

        # Mesaj gonder
        r1 = orch.handle_message("deploy the app")
        assert r1["tasks_detected"] >= 1

        # Takip mesaji
        r2 = orch.handle_message("check status")
        assert r2["interaction"] == 2

        # Gecmis ara
        results = orch.search_history("deploy")
        assert len(results) > 0

        # Snapshot al
        snap = orch.get_snapshot()
        assert snap.total_conversations >= 4  # 2 user + 2 assistant

    def test_multi_channel_conversation(self):
        from app.core.assistant.assistant_orchestrator import AssistantOrchestrator
        orch = AssistantOrchestrator()

        orch.channels.register_channel(ChannelType.TELEGRAM)
        orch.channels.register_channel(ChannelType.EMAIL)

        r1 = orch.handle_message("Hello", channel=ChannelType.TELEGRAM)
        r2 = orch.handle_message("Report", channel=ChannelType.EMAIL)

        assert r1["channel"] == "telegram"
        assert r2["channel"] == "email"

    def test_learning_and_prediction(self):
        from app.core.assistant.assistant_orchestrator import AssistantOrchestrator
        orch = AssistantOrchestrator()

        # Kalip olustur
        for _ in range(3):
            orch.handle_message("deploy server")
            orch.handle_message("monitor logs")

        # Tahmin
        result = orch.predict_next_intent("deploy")
        assert result["predicted_action"]

    def test_proactive_with_deadline(self):
        from app.core.assistant.assistant_orchestrator import AssistantOrchestrator
        orch = AssistantOrchestrator()

        deadline = datetime.now(timezone.utc) + timedelta(hours=1)
        orch.helper.add_deadline("Report", deadline, alert_before_hours=24)

        suggestions = orch.get_proactive_suggestions()
        assert any(s.get("type") == "deadline" for s in suggestions)

    def test_context_building_and_response(self):
        from app.core.assistant.assistant_orchestrator import AssistantOrchestrator
        orch = AssistantOrchestrator()

        orch.context.load_user_profile({"role": "admin"})
        orch.context.update_environment({"platform": "linux"})

        result = orch.handle_message("check servers")
        assert result["response"]

    def test_preference_applied_to_response(self):
        from app.core.assistant.assistant_orchestrator import AssistantOrchestrator
        orch = AssistantOrchestrator()

        orch.learn_preference("tone", "formal", "communication")
        result = orch.handle_message("hello")
        assert result["response"]
