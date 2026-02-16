"""ATLAS Voice Command & Smart Speaker Bridge testleri."""

import pytest

from app.core.smartspeaker import (
    AlexaSkillConnector,
    GoogleAssistantBridge,
    MultiDeviceSync,
    SiriShortcuts,
    SmartSpeakerOrchestrator,
    SmartSpeakerResponseFormatter,
    SpeakerConversationContext,
    VoiceCommandParser,
    WakeWordHandler,
)
from app.models.smartspeaker_models import (
    CommandIntent,
    ConversationRecord,
    ConversationState,
    DeviceSyncStatus,
    ResponseRecord,
    ResponseType,
    SpeakerDeviceRecord,
    SpeakerPlatform,
    VoiceCommandRecord,
    WakeWordState,
)


# ── Model Testleri ──


class TestSpeakerPlatform:
    """SpeakerPlatform enum testleri."""

    def test_values(self) -> None:
        assert SpeakerPlatform.ALEXA == "alexa"
        assert SpeakerPlatform.GOOGLE == "google"
        assert SpeakerPlatform.SIRI == "siri"
        assert SpeakerPlatform.CUSTOM == "custom"

    def test_member_count(self) -> None:
        assert len(SpeakerPlatform) == 4


class TestCommandIntent:
    """CommandIntent enum testleri."""

    def test_values(self) -> None:
        assert CommandIntent.CONTROL == "control"
        assert CommandIntent.QUERY == "query"
        assert CommandIntent.AUTOMATION == "automation"
        assert CommandIntent.MEDIA == "media"
        assert CommandIntent.COMMUNICATION == "communication"

    def test_member_count(self) -> None:
        assert len(CommandIntent) == 5


class TestResponseType:
    """ResponseType enum testleri."""

    def test_values(self) -> None:
        assert ResponseType.SPEECH == "speech"
        assert ResponseType.CARD == "card"
        assert ResponseType.SSML == "ssml"

    def test_member_count(self) -> None:
        assert len(ResponseType) == 5


class TestDeviceSyncStatus:
    """DeviceSyncStatus enum testleri."""

    def test_values(self) -> None:
        assert DeviceSyncStatus.SYNCED == "synced"
        assert DeviceSyncStatus.PENDING == "pending"
        assert DeviceSyncStatus.CONFLICT == "conflict"
        assert DeviceSyncStatus.OFFLINE == "offline"

    def test_member_count(self) -> None:
        assert len(DeviceSyncStatus) == 4


class TestWakeWordState:
    """WakeWordState enum testleri."""

    def test_values(self) -> None:
        assert WakeWordState.LISTENING == "listening"
        assert WakeWordState.ACTIVATED == "activated"
        assert WakeWordState.IDLE == "idle"
        assert WakeWordState.DISABLED == "disabled"

    def test_member_count(self) -> None:
        assert len(WakeWordState) == 4


class TestConversationState:
    """ConversationState enum testleri."""

    def test_values(self) -> None:
        assert ConversationState.ACTIVE == "active"
        assert ConversationState.WAITING == "waiting"
        assert ConversationState.ENDED == "ended"
        assert ConversationState.TIMEOUT == "timeout"

    def test_member_count(self) -> None:
        assert len(ConversationState) == 4


class TestVoiceCommandRecord:
    """VoiceCommandRecord model testleri."""

    def test_defaults(self) -> None:
        r = VoiceCommandRecord()
        assert r.platform == "alexa"
        assert r.raw_text == ""
        assert r.intent == ""
        assert r.confidence == 0.0
        assert r.record_id
        assert r.created_at

    def test_custom(self) -> None:
        r = VoiceCommandRecord(
            platform="google",
            raw_text="turn on lights",
            intent="control",
            confidence=0.95,
        )
        assert r.platform == "google"
        assert r.raw_text == "turn on lights"
        assert r.confidence == 0.95


class TestSpeakerDeviceRecord:
    """SpeakerDeviceRecord model testleri."""

    def test_defaults(self) -> None:
        r = SpeakerDeviceRecord()
        assert r.device_name == ""
        assert r.platform == "alexa"
        assert r.status == "synced"

    def test_custom(self) -> None:
        r = SpeakerDeviceRecord(
            device_name="Kitchen Echo",
            platform="alexa",
            location="kitchen",
        )
        assert r.device_name == "Kitchen Echo"
        assert r.location == "kitchen"


class TestConversationRecord:
    """ConversationRecord model testleri."""

    def test_defaults(self) -> None:
        r = ConversationRecord()
        assert r.session_id == ""
        assert r.turns == 0
        assert r.state == "active"

    def test_custom(self) -> None:
        r = ConversationRecord(
            session_id="sess_1",
            turns=5,
            state="ended",
        )
        assert r.turns == 5
        assert r.state == "ended"


class TestResponseRecord:
    """ResponseRecord model testleri."""

    def test_defaults(self) -> None:
        r = ResponseRecord()
        assert r.response_type == "speech"
        assert r.content == ""

    def test_custom(self) -> None:
        r = ResponseRecord(
            response_type="ssml",
            content="<speak>Hello</speak>",
        )
        assert r.response_type == "ssml"


# ── AlexaSkillConnector Testleri ──


class TestAlexaRegisterSkill:
    """register_skill testleri."""

    def test_basic(self) -> None:
        c = AlexaSkillConnector()
        r = c.register_skill("s1", "Test Skill", ["Intent1"])
        assert r["registered"] is True
        assert r["skill_id"] == "s1"
        assert r["intents_count"] == 1

    def test_no_intents(self) -> None:
        c = AlexaSkillConnector()
        r = c.register_skill("s2", "Empty")
        assert r["intents_count"] == 0

    def test_count(self) -> None:
        c = AlexaSkillConnector()
        c.register_skill("s1", "A")
        c.register_skill("s2", "B")
        assert c.skill_count == 2


class TestAlexaHandleIntent:
    """handle_intent testleri."""

    def test_valid(self) -> None:
        c = AlexaSkillConnector()
        c.register_skill("s1", "T", ["ControlIntent"])
        r = c.handle_intent("s1", "ControlIntent", {"device": "light"})
        assert r["handled"] is True
        assert r["slots_processed"] == 1

    def test_not_found(self) -> None:
        c = AlexaSkillConnector()
        r = c.handle_intent("missing", "SomeIntent")
        assert r["found"] is False

    def test_count(self) -> None:
        c = AlexaSkillConnector()
        c.register_skill("s1", "T")
        c.handle_intent("s1", "I1")
        c.handle_intent("s1", "I2")
        assert c.intent_count == 2


class TestAlexaProcessSlots:
    """process_slots testleri."""

    def test_basic(self) -> None:
        c = AlexaSkillConnector()
        r = c.process_slots({"color": "red", "room": "living"})
        assert r["processed"] is True
        assert r["slots_count"] == 2
        assert len(r["resolved"]) == 2


class TestAlexaBuildResponse:
    """build_response testleri."""

    def test_speech_only(self) -> None:
        c = AlexaSkillConnector()
        r = c.build_response("Hello world")
        assert r["built"] is True
        assert r["speech"] == "Hello world"
        assert r["card"] is None

    def test_with_card(self) -> None:
        c = AlexaSkillConnector()
        r = c.build_response("Hi", card_title="Title", card_content="Body")
        assert r["card"]["title"] == "Title"


class TestAlexaManageSession:
    """manage_session testleri."""

    def test_start(self) -> None:
        c = AlexaSkillConnector()
        r = c.manage_session("sess_1", "start")
        assert r["managed"] is True
        assert r["active"] is True

    def test_end(self) -> None:
        c = AlexaSkillConnector()
        c.manage_session("sess_1", "start")
        r = c.manage_session("sess_1", "end")
        assert r["active"] is False


# ── GoogleAssistantBridge Testleri ──


class TestGoogleRegisterAction:
    """register_action testleri."""

    def test_basic(self) -> None:
        g = GoogleAssistantBridge()
        r = g.register_action("a1", "Test", ["hey test"])
        assert r["registered"] is True
        assert r["action_id"] == "a1"

    def test_count(self) -> None:
        g = GoogleAssistantBridge()
        g.register_action("a1", "A")
        g.register_action("a2", "B")
        assert g.action_count == 2


class TestGoogleHandleFulfillment:
    """handle_fulfillment testleri."""

    def test_valid(self) -> None:
        g = GoogleAssistantBridge()
        g.register_action("a1", "T")
        r = g.handle_fulfillment("a1", {"key": "val"})
        assert r["fulfilled"] is True
        assert r["parameters_received"] == 1

    def test_not_found(self) -> None:
        g = GoogleAssistantBridge()
        r = g.handle_fulfillment("missing")
        assert r["found"] is False

    def test_count(self) -> None:
        g = GoogleAssistantBridge()
        g.register_action("a1", "T")
        g.handle_fulfillment("a1")
        assert g.fulfillment_count == 1


class TestGoogleManageContext:
    """manage_context testleri."""

    def test_basic(self) -> None:
        g = GoogleAssistantBridge()
        r = g.manage_context("sess_1", "test_ctx", lifespan=3)
        assert r["managed"] is True
        assert r["lifespan"] == 3


class TestGoogleBuildRichResponse:
    """build_rich_response testleri."""

    def test_basic(self) -> None:
        g = GoogleAssistantBridge()
        r = g.build_rich_response("Hello", suggestions=["Yes", "No"])
        assert r["built"] is True
        assert r["text"] == "Hello"
        assert len(r["suggestions"]) == 2

    def test_with_card(self) -> None:
        g = GoogleAssistantBridge()
        r = g.build_rich_response("Hi", card={"title": "Card"})
        assert r["has_card"] is True


class TestGoogleLinkAccount:
    """link_account testleri."""

    def test_with_token(self) -> None:
        g = GoogleAssistantBridge()
        r = g.link_account("user_1", token="abc123")
        assert r["linked"] is True

    def test_without_token(self) -> None:
        g = GoogleAssistantBridge()
        r = g.link_account("user_1")
        assert r["linked"] is False


# ── SiriShortcuts Testleri ──


class TestSiriCreateShortcut:
    """create_shortcut testleri."""

    def test_basic(self) -> None:
        s = SiriShortcuts()
        r = s.create_shortcut("Test", "run_action")
        assert r["created"] is True
        assert r["name"] == "Test"
        assert r["action"] == "run_action"

    def test_count(self) -> None:
        s = SiriShortcuts()
        s.create_shortcut("A", "act_a")
        s.create_shortcut("B", "act_b")
        assert s.shortcut_count == 2


class TestSiriDonateIntent:
    """donate_intent testleri."""

    def test_valid(self) -> None:
        s = SiriShortcuts()
        s.create_shortcut("T", "act")
        r = s.donate_intent("shortcut_0", "user_opened_app")
        assert r["donated"] is True

    def test_not_found(self) -> None:
        s = SiriShortcuts()
        r = s.donate_intent("missing")
        assert r["found"] is False

    def test_count(self) -> None:
        s = SiriShortcuts()
        s.create_shortcut("T", "act")
        s.donate_intent("shortcut_0")
        assert s.donation_count == 1


class TestSiriHandleParameters:
    """handle_parameters testleri."""

    def test_valid(self) -> None:
        s = SiriShortcuts()
        s.create_shortcut("T", "act")
        r = s.handle_parameters("shortcut_0", {"key": "val"})
        assert r["handled"] is True
        assert r["params_set"] == 1

    def test_not_found(self) -> None:
        s = SiriShortcuts()
        r = s.handle_parameters("missing")
        assert r["found"] is False


class TestSiriFormatResponse:
    """format_response testleri."""

    def test_basic(self) -> None:
        s = SiriShortcuts()
        r = s.format_response("Display text")
        assert r["formatted"] is True
        assert r["display_text"] == "Display text"
        assert r["spoken_text"] == "Display text"

    def test_different_spoken(self) -> None:
        s = SiriShortcuts()
        r = s.format_response("Text", spoken_text="Spoken")
        assert r["spoken_text"] == "Spoken"


class TestSiriAddAutomationTrigger:
    """add_automation_trigger testleri."""

    def test_valid(self) -> None:
        s = SiriShortcuts()
        s.create_shortcut("T", "act")
        r = s.add_automation_trigger("shortcut_0", "time", "09:00")
        assert r["added"] is True
        assert r["trigger_type"] == "time"

    def test_not_found(self) -> None:
        s = SiriShortcuts()
        r = s.add_automation_trigger("missing")
        assert r["found"] is False


# ── VoiceCommandParser Testleri ──


class TestParseCommand:
    """parse_command testleri."""

    def test_control_intent(self) -> None:
        p = VoiceCommandParser()
        r = p.parse_command("turn on the lights")
        assert r["parsed"] is True
        assert r["intent"] == "control"
        assert "turn" in r["tokens"]

    def test_query_intent(self) -> None:
        p = VoiceCommandParser()
        r = p.parse_command("what is the weather")
        assert r["intent"] == "query"

    def test_automation_intent(self) -> None:
        p = VoiceCommandParser()
        r = p.parse_command("every morning play music")
        assert r["intent"] == "automation"

    def test_general_intent(self) -> None:
        p = VoiceCommandParser()
        r = p.parse_command("hello atlas")
        assert r["intent"] == "general"

    def test_count(self) -> None:
        p = VoiceCommandParser()
        p.parse_command("test 1")
        p.parse_command("test 2")
        assert p.parse_count == 2


class TestExtractEntities:
    """extract_entities testleri."""

    def test_number_entity(self) -> None:
        p = VoiceCommandParser()
        r = p.extract_entities("set volume to 50")
        assert r["extracted"] is True
        entities = r["entities"]
        numbers = [e for e in entities if e["type"] == "number"]
        assert len(numbers) == 1
        assert numbers[0]["value"] == "50"

    def test_device_entity(self) -> None:
        p = VoiceCommandParser()
        r = p.extract_entities("turn on the light")
        devices = [e for e in r["entities"] if e["type"] == "device"]
        assert len(devices) == 1

    def test_count(self) -> None:
        p = VoiceCommandParser()
        p.extract_entities("light 42")
        assert p.entity_count == 2


class TestMapIntent:
    """map_intent testleri."""

    def test_control(self) -> None:
        p = VoiceCommandParser()
        r = p.map_intent("turn on switch")
        assert r["mapped"] is True
        assert r["matched_intent"] == "control"
        assert r["score"] > 0

    def test_query(self) -> None:
        p = VoiceCommandParser()
        r = p.map_intent("what is happening")
        assert r["matched_intent"] == "query"

    def test_general_fallback(self) -> None:
        p = VoiceCommandParser()
        r = p.map_intent("hello there")
        assert r["matched_intent"] == "general"


class TestResolveAmbiguity:
    """resolve_ambiguity testleri."""

    def test_single_candidate(self) -> None:
        p = VoiceCommandParser()
        r = p.resolve_ambiguity("test", ["control"])
        assert r["resolved"] is True
        assert r["resolved_intent"] == "control"

    def test_multiple_candidates(self) -> None:
        p = VoiceCommandParser()
        r = p.resolve_ambiguity("test", ["query", "control"])
        assert r["resolved_intent"] == "query"

    def test_no_candidates(self) -> None:
        p = VoiceCommandParser()
        r = p.resolve_ambiguity("test", [])
        assert r["resolved_intent"] == "unknown"


class TestDetectLanguage:
    """detect_language testleri."""

    def test_english(self) -> None:
        p = VoiceCommandParser()
        r = p.detect_language("turn on the lights")
        assert r["detected"] is True
        assert r["detected_language"] == "en"

    def test_turkish(self) -> None:
        p = VoiceCommandParser()
        r = p.detect_language("ışıkları aç")
        assert r["detected_language"] == "tr"

    def test_german(self) -> None:
        p = VoiceCommandParser()
        r = p.detect_language("die Stra\u00dfe ist lang")
        assert r["detected_language"] == "de"


# ── SmartSpeakerResponseFormatter Testleri ──


class TestGenerateSSML:
    """generate_ssml testleri."""

    def test_basic(self) -> None:
        f = SmartSpeakerResponseFormatter()
        r = f.generate_ssml("Hello world")
        assert r["generated"] is True
        assert "<speak>" in r["ssml"]
        assert "Hello world" in r["ssml"]
        assert 'rate="medium"' in r["ssml"]

    def test_custom_rate_pitch(self) -> None:
        f = SmartSpeakerResponseFormatter()
        r = f.generate_ssml("Fast", rate="fast", pitch="high")
        assert 'rate="fast"' in r["ssml"]
        assert 'pitch="high"' in r["ssml"]

    def test_with_voice(self) -> None:
        f = SmartSpeakerResponseFormatter()
        r = f.generate_ssml("Test", voice="en-US-Wavenet")
        assert 'voice name="en-US-Wavenet"' in r["ssml"]

    def test_count(self) -> None:
        f = SmartSpeakerResponseFormatter()
        f.generate_ssml("A")
        f.generate_ssml("B")
        assert f.ssml_count == 2


class TestBuildCard:
    """build_card testleri."""

    def test_basic(self) -> None:
        f = SmartSpeakerResponseFormatter()
        r = f.build_card("Title", "Content")
        assert r["built"] is True
        assert r["card"]["title"] == "Title"
        assert r["has_image"] is False

    def test_with_image(self) -> None:
        f = SmartSpeakerResponseFormatter()
        r = f.build_card("T", "C", image_url="http://img.png")
        assert r["has_image"] is True


class TestBuildAudioResponse:
    """build_audio_response testleri."""

    def test_basic(self) -> None:
        f = SmartSpeakerResponseFormatter()
        r = f.build_audio_response("http://audio.mp3")
        assert r["built"] is True
        assert r["type"] == "audio"
        assert r["fallback_text"] == "Audio playing"

    def test_custom_fallback(self) -> None:
        f = SmartSpeakerResponseFormatter()
        r = f.build_audio_response("http://a.mp3", "Playing music")
        assert r["fallback_text"] == "Playing music"


class TestBuildVisualResponse:
    """build_visual_response testleri."""

    def test_basic(self) -> None:
        f = SmartSpeakerResponseFormatter()
        r = f.build_visual_response("Title", body="Body")
        assert r["built"] is True
        assert r["type"] == "visual"
        assert r["button_count"] == 0

    def test_with_buttons(self) -> None:
        f = SmartSpeakerResponseFormatter()
        r = f.build_visual_response("T", buttons=["Yes", "No"])
        assert r["button_count"] == 2


class TestAdaptPlatform:
    """adapt_platform testleri."""

    def test_alexa(self) -> None:
        f = SmartSpeakerResponseFormatter()
        r = f.adapt_platform({"speech": "Hello"}, "alexa")
        assert r["adapted"] is True
        assert r["adapted_response"]["outputSpeech"] == "Hello"

    def test_google(self) -> None:
        f = SmartSpeakerResponseFormatter()
        r = f.adapt_platform({"text": "Hi"}, "google")
        assert r["adapted_response"]["fulfillmentText"] == "Hi"

    def test_siri(self) -> None:
        f = SmartSpeakerResponseFormatter()
        r = f.adapt_platform({"spoken_text": "Hey"}, "siri")
        assert r["adapted_response"]["spoken"] == "Hey"

    def test_custom_platform(self) -> None:
        f = SmartSpeakerResponseFormatter()
        r = f.adapt_platform({"key": "val"}, "custom")
        assert r["adapted_response"]["key"] == "val"

    def test_count(self) -> None:
        f = SmartSpeakerResponseFormatter()
        f.adapt_platform({}, "alexa")
        f.adapt_platform({}, "google")
        assert f.response_count == 2


# ── MultiDeviceSync Testleri ──


class TestRegisterDevice:
    """register_device testleri."""

    def test_basic(self) -> None:
        m = MultiDeviceSync()
        r = m.register_device("d1", "Kitchen Echo", "alexa", "kitchen")
        assert r["registered"] is True
        assert r["device_id"] == "d1"

    def test_count(self) -> None:
        m = MultiDeviceSync()
        m.register_device("d1", "A")
        m.register_device("d2", "B")
        assert m.device_count == 2


class TestSyncState:
    """sync_state testleri."""

    def test_basic(self) -> None:
        m = MultiDeviceSync()
        m.register_device("d1", "A")
        m.register_device("d2", "B")
        r = m.sync_state("d1", "d2", {"volume": 50})
        assert r["synced"] is True
        assert r["keys_synced"] == 1

    def test_source_not_found(self) -> None:
        m = MultiDeviceSync()
        r = m.sync_state("missing", "d2")
        assert r["found"] is False

    def test_target_not_found(self) -> None:
        m = MultiDeviceSync()
        m.register_device("d1", "A")
        r = m.sync_state("d1", "missing")
        assert r["found"] is False

    def test_count(self) -> None:
        m = MultiDeviceSync()
        m.register_device("d1", "A")
        m.register_device("d2", "B")
        m.sync_state("d1", "d2", {"k": "v"})
        assert m.sync_count == 1


class TestHandoff:
    """handoff testleri."""

    def test_basic(self) -> None:
        m = MultiDeviceSync()
        m.register_device("d1", "A")
        m.register_device("d2", "B")
        r = m.handoff("d1", "d2", {"session": "s1"})
        assert r["handoff"] is True
        assert r["context_transferred"] is True

    def test_no_context(self) -> None:
        m = MultiDeviceSync()
        m.register_device("d1", "A")
        m.register_device("d2", "B")
        r = m.handoff("d1", "d2")
        assert r["context_transferred"] is False

    def test_not_found(self) -> None:
        m = MultiDeviceSync()
        r = m.handoff("missing1", "missing2")
        assert r["found"] is False


class TestSyncPreferences:
    """sync_preferences testleri."""

    def test_basic(self) -> None:
        m = MultiDeviceSync()
        m.register_device("d1", "A")
        r = m.sync_preferences("d1", {"volume": 80})
        assert r["synced"] is True
        assert r["preferences_synced"] == 1

    def test_not_found(self) -> None:
        m = MultiDeviceSync()
        r = m.sync_preferences("missing")
        assert r["found"] is False


class TestResolveConflict:
    """resolve_conflict testleri."""

    def test_latest_strategy(self) -> None:
        m = MultiDeviceSync()
        r = m.resolve_conflict("d1", "d2", "latest")
        assert r["resolved"] is True
        assert r["winner"] == "d1"

    def test_first_strategy(self) -> None:
        m = MultiDeviceSync()
        r = m.resolve_conflict("d1", "d2", "first")
        assert r["resolved"] is True
        assert r["winner"] == "d2"


# ── WakeWordHandler Testleri ──


class TestRegisterWakeWord:
    """register_wake_word testleri."""

    def test_basic(self) -> None:
        w = WakeWordHandler()
        r = w.register_wake_word("hey atlas", "en", 0.8)
        assert r["registered"] is True
        assert r["word"] == "hey atlas"
        assert r["sensitivity"] == 0.8

    def test_default_word(self) -> None:
        w = WakeWordHandler()
        # Default "atlas" kaydedilir
        assert w.word_count >= 1


class TestHandleDetection:
    """handle_detection testleri."""

    def test_above_threshold(self) -> None:
        w = WakeWordHandler()
        r = w.handle_detection("atlas", "dev_1", 0.9)
        assert r["handled"] is True
        assert r["activated"] is True

    def test_below_threshold(self) -> None:
        w = WakeWordHandler()
        r = w.handle_detection("atlas", "dev_1", 0.3)
        assert r["activated"] is False

    def test_unregistered(self) -> None:
        w = WakeWordHandler()
        r = w.handle_detection("unknown_word", "dev_1", 0.9)
        assert r["activated"] is False

    def test_count(self) -> None:
        w = WakeWordHandler()
        w.handle_detection("atlas", "d1", 0.9)
        w.handle_detection("atlas", "d2", 0.8)
        assert w.activation_count == 2


class TestRouteActivation:
    """route_activation testleri."""

    def test_basic(self) -> None:
        w = WakeWordHandler()
        r = w.route_activation("dev_1", "turn on lights")
        assert r["routed"] is True
        assert r["routed_to"] == "voice_parser"


class TestSetPrivacy:
    """set_privacy testleri."""

    def test_basic(self) -> None:
        w = WakeWordHandler()
        r = w.set_privacy("dev_1", always_listen=True, store_audio=False)
        assert r["privacy_set"] is True
        assert r["always_listen"] is True
        assert r["store_audio"] is False


class TestTrainModel:
    """train_model testleri."""

    def test_enough_samples(self) -> None:
        w = WakeWordHandler()
        r = w.train_model("atlas", 15)
        assert r["trained"] is True
        assert r["accuracy"] == 0.92

    def test_few_samples(self) -> None:
        w = WakeWordHandler()
        r = w.train_model("atlas", 5)
        assert r["accuracy"] == 0.7


# ── SpeakerConversationContext Testleri ──


class TestStartSession:
    """start_session testleri."""

    def test_basic(self) -> None:
        c = SpeakerConversationContext()
        r = c.start_session("sess_1", "alexa", "user_1")
        assert r["started"] is True
        assert r["state"] == "active"

    def test_count(self) -> None:
        c = SpeakerConversationContext()
        c.start_session("s1")
        c.start_session("s2")
        assert c.session_count == 2


class TestAddTurn:
    """add_turn testleri."""

    def test_basic(self) -> None:
        c = SpeakerConversationContext()
        c.start_session("s1")
        r = c.add_turn("s1", "user", "Hello")
        assert r["added"] is True
        assert r["turn_number"] == 1

    def test_multiple_turns(self) -> None:
        c = SpeakerConversationContext()
        c.start_session("s1")
        c.add_turn("s1", "user", "Hi")
        r = c.add_turn("s1", "assistant", "Hello!")
        assert r["turn_number"] == 2

    def test_not_found(self) -> None:
        c = SpeakerConversationContext()
        r = c.add_turn("missing", "user", "test")
        assert r["found"] is False

    def test_count(self) -> None:
        c = SpeakerConversationContext()
        c.start_session("s1")
        c.add_turn("s1", "user", "A")
        c.add_turn("s1", "user", "B")
        assert c.turn_count == 2


class TestGetContext:
    """get_context testleri."""

    def test_basic(self) -> None:
        c = SpeakerConversationContext()
        c.start_session("s1")
        c.add_turn("s1", "user", "Hello")
        r = c.get_context("s1")
        assert r["retrieved"] is True
        assert r["turns"] == 1
        assert len(r["history"]) == 1

    def test_not_found(self) -> None:
        c = SpeakerConversationContext()
        r = c.get_context("missing")
        assert r["found"] is False


class TestLearnPreference:
    """learn_preference testleri."""

    def test_basic(self) -> None:
        c = SpeakerConversationContext()
        r = c.learn_preference("u1", "volume", 80)
        assert r["learned"] is True
        assert r["value"] == 80


class TestPersonalize:
    """personalize testleri."""

    def test_basic(self) -> None:
        c = SpeakerConversationContext()
        c.start_session("s1")
        c.learn_preference("u1", "voice", "female")
        r = c.personalize("s1", "u1")
        assert r["personalized"] is True
        assert r["preferences_applied"] == 1

    def test_not_found(self) -> None:
        c = SpeakerConversationContext()
        r = c.personalize("missing", "u1")
        assert r["found"] is False


# ── SmartSpeakerOrchestrator Testleri ──


class TestProcessVoiceCommand:
    """process_voice_command testleri."""

    def test_basic(self) -> None:
        o = SmartSpeakerOrchestrator()
        r = o.process_voice_command("turn on lights", "alexa")
        assert r["pipeline_complete"] is True
        assert r["intent"] == "control"
        assert r["platform"] == "alexa"

    def test_with_session(self) -> None:
        o = SmartSpeakerOrchestrator()
        r = o.process_voice_command(
            "what is the weather",
            "google",
            session_id="sess_1",
        )
        assert r["intent"] == "query"

    def test_count(self) -> None:
        o = SmartSpeakerOrchestrator()
        o.process_voice_command("hello")
        o.process_voice_command("test")
        assert o.pipeline_count == 2
        assert o.command_count == 2


class TestSetupPlatform:
    """setup_platform testleri."""

    def test_alexa(self) -> None:
        o = SmartSpeakerOrchestrator()
        r = o.setup_platform("alexa", {"skill_name": "MySkill"})
        assert r["configured"] is True
        assert r["platform"] == "alexa"

    def test_google(self) -> None:
        o = SmartSpeakerOrchestrator()
        r = o.setup_platform("google")
        assert r["configured"] is True

    def test_siri(self) -> None:
        o = SmartSpeakerOrchestrator()
        r = o.setup_platform("siri")
        assert r["configured"] is True


class TestOrchestratorGetAnalytics:
    """get_analytics testleri."""

    def test_basic(self) -> None:
        o = SmartSpeakerOrchestrator()
        a = o.get_analytics()
        assert "orchestrator" in a
        assert "alexa" in a
        assert "google" in a
        assert "siri" in a
        assert "parser" in a
        assert "formatter" in a
        assert "sync" in a
        assert "wake" in a
        assert "context" in a

    def test_after_operations(self) -> None:
        o = SmartSpeakerOrchestrator()
        o.process_voice_command("test command")
        a = o.get_analytics()
        assert a["orchestrator"]["pipelines_run"] == 1
        assert a["orchestrator"]["commands_processed"] == 1
