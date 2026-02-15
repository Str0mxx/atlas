"""ATLAS Voice Call Interface testleri."""

import time

import pytest

from app.core.voicecall.call_initiator import (
    CallInitiator,
)
from app.core.voicecall.call_recorder import (
    CallRecorder,
)
from app.core.voicecall.call_scheduler import (
    CallScheduler,
)
from app.core.voicecall.speech_to_text import (
    SpeechToText,
)
from app.core.voicecall.text_to_speech import (
    TextToSpeech,
)
from app.core.voicecall.urgency_classifier import (
    UrgencyClassifier,
)
from app.core.voicecall.voice_authenticator import (
    VoiceAuthenticator,
)
from app.core.voicecall.voice_conversation_manager import (
    VoiceConversationManager,
)
from app.core.voicecall.voicecall_orchestrator import (
    VoiceCallOrchestrator,
)
from app.models.voicecall_models import (
    AuthMethod,
    CallDirection,
    CallRecord,
    CallStatus,
    RecordingConsent,
    TranscriptionRecord,
    UrgencyLevel,
    VoiceCallSnapshot,
    VoiceProfile,
    VoiceProvider,
)


# ==================== Models ====================

class TestVoiceCallModels:
    """VoiceCall model testleri."""

    def test_call_direction_enum(self):
        assert CallDirection.INBOUND == "inbound"
        assert CallDirection.OUTBOUND == "outbound"
        assert CallDirection.INTERNAL == "internal"
        assert CallDirection.EMERGENCY == "emergency"
        assert CallDirection.SCHEDULED == "scheduled"

    def test_call_status_enum(self):
        assert CallStatus.RINGING == "ringing"
        assert CallStatus.ACTIVE == "active"
        assert CallStatus.ON_HOLD == "on_hold"
        assert CallStatus.COMPLETED == "completed"
        assert CallStatus.FAILED == "failed"

    def test_voice_provider_enum(self):
        assert VoiceProvider.TWILIO == "twilio"
        assert VoiceProvider.VONAGE == "vonage"
        assert VoiceProvider.LOCAL == "local"
        assert VoiceProvider.ELEVENLABS == "elevenlabs"
        assert VoiceProvider.AZURE == "azure"

    def test_auth_method_enum(self):
        assert AuthMethod.VOICE_BIOMETRIC == "voice_biometric"
        assert AuthMethod.PIN == "pin"
        assert AuthMethod.CHALLENGE == "challenge"
        assert AuthMethod.PASSPHRASE == "passphrase"
        assert AuthMethod.NONE == "none"

    def test_urgency_level_enum(self):
        assert UrgencyLevel.CRITICAL == "critical"
        assert UrgencyLevel.HIGH == "high"
        assert UrgencyLevel.MEDIUM == "medium"
        assert UrgencyLevel.LOW == "low"
        assert UrgencyLevel.ROUTINE == "routine"

    def test_recording_consent_enum(self):
        assert RecordingConsent.GRANTED == "granted"
        assert RecordingConsent.DENIED == "denied"
        assert RecordingConsent.PENDING == "pending"
        assert RecordingConsent.NOT_REQUIRED == "not_required"
        assert RecordingConsent.REVOKED == "revoked"

    def test_call_record_model(self):
        cr = CallRecord(caller="sys", callee="+90555")
        assert cr.call_id
        assert cr.direction == CallDirection.OUTBOUND
        assert cr.status == CallStatus.RINGING
        assert cr.caller == "sys"

    def test_transcription_record_model(self):
        tr = TranscriptionRecord(text="Hello")
        assert tr.transcription_id
        assert tr.text == "Hello"
        assert tr.language == "en"
        assert tr.confidence == 0.0

    def test_voice_profile_model(self):
        vp = VoiceProfile(user_id="u1")
        assert vp.profile_id
        assert vp.user_id == "u1"
        assert vp.auth_method == AuthMethod.NONE
        assert vp.enrolled is False

    def test_voicecall_snapshot_model(self):
        snap = VoiceCallSnapshot()
        assert snap.snapshot_id
        assert snap.total_calls == 0
        assert snap.total_recordings == 0


# ==================== CallInitiator ====================

class TestCallInitiator:
    """CallInitiator testleri."""

    def test_init(self):
        ci = CallInitiator()
        assert ci.call_count == 0
        assert ci.provider_count == 2

    def test_initiate_call(self):
        ci = CallInitiator()
        result = ci.initiate_call("+90555", "system")
        assert "call_id" in result
        assert result["status"] == "ringing"
        assert ci.call_count == 1

    def test_complete_call(self):
        ci = CallInitiator()
        call = ci.initiate_call("+90555")
        result = ci.complete_call(call["call_id"], 120)
        assert result["status"] == "completed"
        assert result["duration"] == 120

    def test_complete_call_not_found(self):
        ci = CallInitiator()
        result = ci.complete_call("bad_id")
        assert result.get("error") == "call_not_found"

    def test_fail_call(self):
        ci = CallInitiator()
        call = ci.initiate_call("+90555")
        result = ci.fail_call(call["call_id"], "no answer")
        assert result["status"] == "failed"

    def test_retry_call(self):
        ci = CallInitiator()
        call = ci.initiate_call("+90555")
        ci.fail_call(call["call_id"])
        result = ci.retry_call(call["call_id"])
        assert result["retry_count"] == 1

    def test_retry_max_exceeded(self):
        ci = CallInitiator(max_retries=1)
        call = ci.initiate_call("+90555")
        ci.retry_call(call["call_id"])
        result = ci.retry_call(call["call_id"])
        assert result.get("error") == "max_retries_exceeded"

    def test_emergency_call(self):
        ci = CallInitiator()
        result = ci.emergency_call("+90555", "server down")
        assert result["emergency"] is True
        assert result["priority"] == 10

    def test_configure_provider(self):
        ci = CallInitiator()
        result = ci.configure_provider("local", enabled=True)
        assert result["configured"] is True
        assert ci.provider_count == 3

    def test_get_active_calls(self):
        ci = CallInitiator()
        ci.initiate_call("+90555")
        ci.initiate_call("+90666")
        assert len(ci.get_active_calls()) == 2

    def test_get_call(self):
        ci = CallInitiator()
        call = ci.initiate_call("+90555")
        result = ci.get_call(call["call_id"])
        assert result["callee"] == "+90555"

    def test_get_call_history(self):
        ci = CallInitiator()
        ci.initiate_call("+90555")
        history = ci.get_call_history()
        assert len(history) == 1


# ==================== SpeechToText ====================

class TestSpeechToText:
    """SpeechToText testleri."""

    def test_init(self):
        stt = SpeechToText()
        assert stt.transcription_count == 0
        assert stt.language_count == 5

    def test_transcribe(self):
        stt = SpeechToText()
        result = stt.transcribe("Hello world")
        assert result["text"] == "Hello world"
        assert result["confidence"] > 0
        assert stt.transcription_count == 1

    def test_transcribe_with_language(self):
        stt = SpeechToText()
        result = stt.transcribe("Merhaba", language="tr")
        assert result["language"] == "tr"

    def test_transcribe_unsupported_language(self):
        stt = SpeechToText()
        result = stt.transcribe("test", language="zz")
        assert result.get("error") == "unsupported_language"

    def test_transcribe_realtime(self):
        stt = SpeechToText()
        chunks = ["Hello", "world", "test"]
        result = stt.transcribe_realtime(chunks, call_id="c1")
        assert result["chunks"] == 3
        assert "Hello" in result["full_text"]

    def test_diarize(self):
        stt = SpeechToText()
        tr = stt.transcribe("Hello world test")
        result = stt.diarize(tr["transcription_id"])
        assert result["speakers_detected"] == 2

    def test_diarize_not_found(self):
        stt = SpeechToText()
        result = stt.diarize("bad_id")
        assert result.get("error") == "transcription_not_found"

    def test_filter_noise(self):
        stt = SpeechToText()
        result = stt.filter_noise("audio data", aggressiveness=3)
        assert result["filtered"] is True
        assert result["aggressiveness"] == 3

    def test_confidence_score(self):
        stt = SpeechToText()
        tr = stt.transcribe("test")
        result = stt.get_confidence_score(tr["transcription_id"])
        assert result["quality"] in ("low", "medium", "high")

    def test_confidence_not_found(self):
        stt = SpeechToText()
        result = stt.get_confidence_score("bad_id")
        assert result.get("error") == "transcription_not_found"

    def test_add_language(self):
        stt = SpeechToText()
        result = stt.add_language("ja", "Japanese")
        assert result["added"] is True
        assert stt.language_count == 6

    def test_get_transcriptions_by_call(self):
        stt = SpeechToText()
        stt.transcribe("a", call_id="c1")
        stt.transcribe("b", call_id="c2")
        results = stt.get_transcriptions(call_id="c1")
        assert len(results) == 1


# ==================== TextToSpeech ====================

class TestTextToSpeech:
    """TextToSpeech testleri."""

    def test_init(self):
        tts = TextToSpeech()
        assert tts.synthesis_count == 0
        assert tts.voice_count == 3

    def test_synthesize(self):
        tts = TextToSpeech()
        result = tts.synthesize("Hello world")
        assert "synthesis_id" in result
        assert result["text"] == "Hello world"
        assert result["duration_seconds"] > 0
        assert tts.synthesis_count == 1

    def test_synthesize_with_voice(self):
        tts = TextToSpeech()
        result = tts.synthesize("Hi", voice="atlas_warm")
        assert result["voice"] == "atlas_warm"

    def test_synthesize_speed(self):
        tts = TextToSpeech()
        slow = tts.synthesize("test", speed=0.5)
        fast = tts.synthesize("test", speed=2.0)
        assert slow["duration_seconds"] > fast["duration_seconds"]

    def test_synthesize_ssml(self):
        tts = TextToSpeech()
        ssml = "<speak>Hello <break time='500ms'/> world</speak>"
        result = tts.synthesize_ssml(ssml)
        assert result["ssml"] is True
        assert "Hello" in result["text"]

    def test_set_emotion(self):
        tts = TextToSpeech()
        synth = tts.synthesize("Test")
        result = tts.set_emotion(
            synth["synthesis_id"], "happy", 0.8,
        )
        assert result["emotion"] == "happy"
        assert result["intensity"] == 0.8

    def test_set_emotion_not_found(self):
        tts = TextToSpeech()
        result = tts.set_emotion("bad_id", "happy")
        assert result.get("error") == "synthesis_not_found"

    def test_adjust_speed(self):
        tts = TextToSpeech()
        synth = tts.synthesize("Test")
        result = tts.adjust_speed(synth["synthesis_id"], 1.5)
        assert result["speed"] == 1.5

    def test_adjust_speed_clamp(self):
        tts = TextToSpeech()
        synth = tts.synthesize("Test")
        result = tts.adjust_speed(synth["synthesis_id"], 5.0)
        assert result["speed"] == 2.0

    def test_adjust_speed_not_found(self):
        tts = TextToSpeech()
        result = tts.adjust_speed("bad_id", 1.0)
        assert result.get("error") == "synthesis_not_found"

    def test_add_voice(self):
        tts = TextToSpeech()
        result = tts.add_voice("turkish", "female", "tr")
        assert result["added"] is True
        assert tts.voice_count == 4

    def test_list_voices(self):
        tts = TextToSpeech()
        voices = tts.list_voices()
        assert len(voices) == 3

    def test_list_voices_by_language(self):
        tts = TextToSpeech()
        tts.add_voice("tr_voice", language="tr")
        voices = tts.list_voices(language="tr")
        assert len(voices) == 1


# ==================== VoiceConversationManager ====================

class TestVoiceConversationManager:
    """VoiceConversationManager testleri."""

    def test_init(self):
        mgr = VoiceConversationManager()
        assert mgr.conversation_count == 0

    def test_start_conversation(self):
        mgr = VoiceConversationManager()
        result = mgr.start_conversation("c1", ["user", "system"])
        assert "conversation_id" in result
        assert result["status"] == "active"
        assert mgr.conversation_count == 1

    def test_end_conversation(self):
        mgr = VoiceConversationManager()
        conv = mgr.start_conversation("c1")
        result = mgr.end_conversation(conv["conversation_id"])
        assert result["status"] == "ended"

    def test_end_conversation_not_found(self):
        mgr = VoiceConversationManager()
        result = mgr.end_conversation("bad_id")
        assert result.get("error") == "conversation_not_found"

    def test_add_turn(self):
        mgr = VoiceConversationManager()
        conv = mgr.start_conversation("c1")
        result = mgr.add_turn(conv["conversation_id"], "user", "Hello")
        assert result["speaker"] == "user"
        assert result["turn_number"] == 1
        assert mgr.turn_count == 1

    def test_add_turn_not_found(self):
        mgr = VoiceConversationManager()
        result = mgr.add_turn("bad_id", "user", "Hi")
        assert result.get("error") == "conversation_not_found"

    def test_handle_interruption(self):
        mgr = VoiceConversationManager()
        conv = mgr.start_conversation("c1")
        mgr.add_turn(conv["conversation_id"], "system", "Hi")
        result = mgr.handle_interruption(
            conv["conversation_id"], "user", "Wait!",
        )
        assert result["interruption"] is True
        assert result["previous_speaker"] == "system"

    def test_detect_silence_short(self):
        mgr = VoiceConversationManager(silence_threshold=3.0)
        conv = mgr.start_conversation("c1")
        result = mgr.detect_silence(conv["conversation_id"], 1.0)
        assert result["is_long_silence"] is False
        assert result["action"] == "continue"

    def test_detect_silence_long(self):
        mgr = VoiceConversationManager(silence_threshold=3.0)
        conv = mgr.start_conversation("c1")
        result = mgr.detect_silence(conv["conversation_id"], 5.0)
        assert result["is_long_silence"] is True
        assert result["action"] == "prompt_user"

    def test_update_context(self):
        mgr = VoiceConversationManager()
        conv = mgr.start_conversation("c1")
        result = mgr.update_context(
            conv["conversation_id"], "topic", "billing",
        )
        assert result["updated"] is True

    def test_get_conversation_flow(self):
        mgr = VoiceConversationManager()
        conv = mgr.start_conversation("c1")
        mgr.add_turn(conv["conversation_id"], "user", "Hi")
        mgr.add_turn(conv["conversation_id"], "system", "Hello")
        result = mgr.get_conversation_flow(conv["conversation_id"])
        assert result["turn_count"] == 2

    def test_active_conversation_count(self):
        mgr = VoiceConversationManager()
        conv1 = mgr.start_conversation("c1")
        mgr.start_conversation("c2")
        mgr.end_conversation(conv1["conversation_id"])
        assert mgr.active_conversation_count == 1


# ==================== UrgencyClassifier ====================

class TestUrgencyClassifier:
    """UrgencyClassifier testleri."""

    def test_init(self):
        uc = UrgencyClassifier()
        assert uc.classification_count == 0

    def test_classify_routine(self):
        uc = UrgencyClassifier()
        result = uc.classify("How are you today?")
        assert result["urgency"] in ("routine", "low")

    def test_classify_emergency(self):
        uc = UrgencyClassifier()
        result = uc.classify(
            "Emergency! Help! Critical danger!",
            voice_features={"pitch": 0.9, "volume": 0.9, "speed": 0.9},
        )
        assert result["urgency"] in ("critical", "high")
        assert result["total_score"] > 0.5

    def test_classify_with_voice_features(self):
        uc = UrgencyClassifier()
        result = uc.classify(
            "normal text",
            voice_features={"pitch": 0.9, "volume": 0.9, "speed": 0.9},
        )
        assert result["tone_score"] > 0

    def test_stress_detection(self):
        uc = UrgencyClassifier()
        result = uc.classify("Please hurry, immediately!")
        assert result["stress_score"] > 0

    def test_escalate(self):
        uc = UrgencyClassifier()
        cls = uc.classify("Normal text")
        result = uc.escalate(
            cls["classification_id"], "critical", "manual override",
        )
        assert result["new_level"] == "critical"

    def test_escalate_not_found(self):
        uc = UrgencyClassifier()
        result = uc.escalate("bad_id", "high")
        assert result.get("error") == "classification_not_found"

    def test_add_emergency_keyword(self):
        uc = UrgencyClassifier()
        result = uc.add_emergency_keyword("mayday")
        assert result["added"] is True

    def test_check_emergency_triggers(self):
        uc = UrgencyClassifier()
        result = uc.check_emergency_triggers("This is an emergency situation")
        assert result["triggered"] is True
        assert "emergency" in result["triggers"]

    def test_check_no_triggers(self):
        uc = UrgencyClassifier()
        result = uc.check_emergency_triggers("Hello world")
        assert result["triggered"] is False

    def test_get_classifications_by_urgency(self):
        uc = UrgencyClassifier()
        uc.classify("Normal")
        uc.classify("Emergency! Help! Danger!")
        results = uc.get_classifications(urgency="routine")
        assert isinstance(results, list)

    def test_emergency_count(self):
        uc = UrgencyClassifier()
        uc.classify(
            "Emergency! Critical! Help! Danger!",
            voice_features={"pitch": 1.0, "volume": 1.0, "speed": 1.0, "stress": 1.0},
        )
        assert uc.classification_count >= 1


# ==================== CallScheduler ====================

class TestCallScheduler:
    """CallScheduler testleri."""

    def test_init(self):
        cs = CallScheduler()
        assert cs.schedule_count == 0

    def test_schedule_call(self):
        cs = CallScheduler()
        result = cs.schedule_call("+90555", purpose="follow-up")
        assert "schedule_id" in result
        assert result["status"] == "pending"
        assert cs.schedule_count == 1

    def test_schedule_with_time(self):
        cs = CallScheduler()
        future = time.time() + 3600
        result = cs.schedule_call("+90555", scheduled_time=future)
        assert result["scheduled_time"] == future

    def test_set_contact_preference(self):
        cs = CallScheduler()
        result = cs.set_contact_preference(
            "+90555", preferred_hour=14, timezone_offset=3,
        )
        assert result["preferences_set"] is True

    def test_check_timezone(self):
        cs = CallScheduler()
        cs.set_contact_preference("+90555", timezone_offset=3)
        result = cs.check_timezone("+90555")
        assert result["timezone_offset"] == 3
        assert "local_hour" in result

    def test_check_timezone_default(self):
        cs = CallScheduler()
        result = cs.check_timezone("unknown")
        assert "local_hour" in result

    def test_schedule_retry(self):
        cs = CallScheduler()
        sched = cs.schedule_call("+90555")
        result = cs.schedule_retry(sched["schedule_id"], 15)
        assert result["retry_of"] == sched["schedule_id"]

    def test_schedule_retry_not_found(self):
        cs = CallScheduler()
        result = cs.schedule_retry("bad_id")
        assert result.get("error") == "schedule_not_found"

    def test_schedule_reminder(self):
        cs = CallScheduler()
        result = cs.schedule_reminder("+90555", "Meeting in 1 hour")
        assert result["reminder_set"] is True
        assert cs.reminder_count == 1

    def test_create_batch(self):
        cs = CallScheduler()
        result = cs.create_batch(
            ["+90555", "+90666", "+90777"], purpose="survey",
        )
        assert result["batch_size"] == 3
        assert cs.schedule_count == 3

    def test_get_pending_schedules(self):
        cs = CallScheduler()
        cs.schedule_call("+90555")
        cs.schedule_call("+90666")
        pending = cs.get_pending_schedules()
        assert len(pending) == 2

    def test_cancel_schedule(self):
        cs = CallScheduler()
        sched = cs.schedule_call("+90555")
        result = cs.cancel_schedule(sched["schedule_id"])
        assert result["cancelled"] is True
        assert cs.pending_count == 0

    def test_cancel_not_found(self):
        cs = CallScheduler()
        result = cs.cancel_schedule("bad_id")
        assert result.get("error") == "schedule_not_found"


# ==================== VoiceAuthenticator ====================

class TestVoiceAuthenticator:
    """VoiceAuthenticator testleri."""

    def test_init(self):
        va = VoiceAuthenticator()
        assert va.enrolled_count == 0

    def test_enroll(self):
        va = VoiceAuthenticator()
        result = va.enroll("user1", "voice_sample_1", pin="1234")
        assert result["enrolled"] is True
        assert result["has_pin"] is True
        assert va.enrolled_count == 1

    def test_verify_voice_match(self):
        va = VoiceAuthenticator()
        va.enroll("user1", "voice_sample_1")
        result = va.verify_voice("user1", "voice_sample_1")
        assert result["verified"] is True
        assert result["confidence"] == 1.0

    def test_verify_voice_mismatch(self):
        va = VoiceAuthenticator()
        va.enroll("user1", "voice_sample_1")
        result = va.verify_voice("user1", "different_sample")
        assert result["verified"] is False

    def test_verify_voice_not_enrolled(self):
        va = VoiceAuthenticator()
        result = va.verify_voice("user1", "sample")
        assert result.get("error") == "user_not_enrolled"

    def test_verify_pin_correct(self):
        va = VoiceAuthenticator()
        va.enroll("user1", "sample", pin="1234")
        result = va.verify_pin("user1", "1234")
        assert result["verified"] is True

    def test_verify_pin_wrong(self):
        va = VoiceAuthenticator()
        va.enroll("user1", "sample", pin="1234")
        result = va.verify_pin("user1", "9999")
        assert result["verified"] is False

    def test_verify_pin_no_pin(self):
        va = VoiceAuthenticator()
        va.enroll("user1", "sample")
        result = va.verify_pin("user1", "1234")
        assert result.get("error") == "no_pin_set"

    def test_create_challenge(self):
        va = VoiceAuthenticator()
        va.enroll("user1", "sample")
        result = va.create_challenge("user1")
        assert "challenge_id" in result
        assert "challenge" in result

    def test_create_challenge_not_enrolled(self):
        va = VoiceAuthenticator()
        result = va.create_challenge("user1")
        assert result.get("error") == "user_not_enrolled"

    def test_answer_challenge(self):
        va = VoiceAuthenticator()
        va.enroll("user1", "sample")
        ch = va.create_challenge("user1")
        result = va.answer_challenge(ch["challenge_id"], "response")
        assert result["verified"] is True

    def test_answer_challenge_not_found(self):
        va = VoiceAuthenticator()
        result = va.answer_challenge("bad_id", "response")
        assert result.get("error") == "challenge_not_found"

    def test_detect_fraud(self):
        va = VoiceAuthenticator()
        va.enroll("user1", "sample")
        # Fail 3 times
        va.verify_voice("user1", "wrong1")
        va.verify_voice("user1", "wrong2")
        va.verify_voice("user1", "wrong3")
        result = va.detect_fraud("user1", "wrong4")
        assert result["is_fraud"] is True

    def test_detect_no_fraud(self):
        va = VoiceAuthenticator()
        va.enroll("user1", "sample")
        result = va.detect_fraud("user1", "sample")
        assert result["is_fraud"] is False

    def test_set_threshold(self):
        va = VoiceAuthenticator()
        result = va.set_threshold(0.9)
        assert result["threshold"] == 0.9

    def test_get_profile(self):
        va = VoiceAuthenticator()
        va.enroll("user1", "sample", pin="1234")
        result = va.get_profile("user1")
        assert result["user_id"] == "user1"
        assert "pin" not in result
        assert "voice_hash" not in result


# ==================== CallRecorder ====================

class TestCallRecorder:
    """CallRecorder testleri."""

    def test_init(self):
        cr = CallRecorder()
        assert cr.recording_count == 0

    def test_start_recording(self):
        cr = CallRecorder()
        result = cr.start_recording("c1", "granted")
        assert "recording_id" in result
        assert result["status"] == "recording"
        assert cr.recording_count == 1

    def test_start_recording_disabled(self):
        cr = CallRecorder(recording_enabled=False)
        result = cr.start_recording("c1")
        assert result.get("error") == "recording_disabled"

    def test_start_recording_denied(self):
        cr = CallRecorder()
        result = cr.start_recording("c1", "denied")
        assert result.get("error") == "consent_denied"

    def test_stop_recording(self):
        cr = CallRecorder()
        rec = cr.start_recording("c1", "granted")
        result = cr.stop_recording(rec["recording_id"], 120)
        assert result["status"] == "completed"
        assert result["duration"] == 120

    def test_stop_recording_not_found(self):
        cr = CallRecorder()
        result = cr.stop_recording("bad_id")
        assert result.get("error") == "recording_not_found"

    def test_request_consent(self):
        cr = CallRecorder()
        result = cr.request_consent("c1", "user1")
        assert result["consent_requested"] is True

    def test_grant_consent(self):
        cr = CallRecorder()
        cr.request_consent("c1", "user1")
        result = cr.grant_consent("c1")
        assert result["consent"] == "granted"

    def test_deny_consent(self):
        cr = CallRecorder()
        result = cr.deny_consent("c1")
        assert result["consent"] == "denied"

    def test_link_transcription(self):
        cr = CallRecorder()
        rec = cr.start_recording("c1", "granted")
        result = cr.link_transcription(rec["recording_id"], "tr_1")
        assert result["linked"] is True

    def test_link_not_found(self):
        cr = CallRecorder()
        result = cr.link_transcription("bad_id", "tr_1")
        assert result.get("error") == "recording_not_found"

    def test_apply_retention(self):
        cr = CallRecorder(retention_days=0)
        rec = cr.start_recording("c1", "granted")
        cr.stop_recording(rec["recording_id"], 60)
        # Force old timestamp
        cr._recordings[0]["started_at"] = time.time() - 100000
        result = cr.apply_retention()
        assert result["deleted"] >= 1

    def test_get_storage_status(self):
        cr = CallRecorder()
        rec = cr.start_recording("c1", "granted")
        cr.stop_recording(rec["recording_id"], 100)
        status = cr.get_storage_status()
        assert status["used_mb"] > 0

    def test_delete_recording(self):
        cr = CallRecorder()
        rec = cr.start_recording("c1", "granted")
        result = cr.delete_recording(rec["recording_id"])
        assert result["deleted"] is True

    def test_delete_not_found(self):
        cr = CallRecorder()
        result = cr.delete_recording("bad_id")
        assert result.get("error") == "recording_not_found"

    def test_get_recordings_by_call(self):
        cr = CallRecorder()
        cr.start_recording("c1", "granted")
        cr.start_recording("c2", "granted")
        results = cr.get_recordings(call_id="c1")
        assert len(results) == 1

    def test_active_recording_count(self):
        cr = CallRecorder()
        cr.start_recording("c1", "granted")
        rec2 = cr.start_recording("c2", "granted")
        cr.stop_recording(rec2["recording_id"], 60)
        assert cr.active_recording_count == 1


# ==================== VoiceCallOrchestrator ====================

class TestVoiceCallOrchestrator:
    """VoiceCallOrchestrator testleri."""

    def test_init(self):
        orch = VoiceCallOrchestrator()
        assert orch.total_calls == 0

    def test_make_call(self):
        orch = VoiceCallOrchestrator()
        result = orch.make_call("+90555", "Hello!")
        assert "call_id" in result
        assert result["status"] == "active"
        assert result["recording_id"] is not None
        assert orch.total_calls == 1

    def test_make_call_no_record(self):
        orch = VoiceCallOrchestrator()
        result = orch.make_call("+90555", "Hi", record=False)
        assert result["recording_id"] is None

    def test_handle_inbound(self):
        orch = VoiceCallOrchestrator()
        result = orch.handle_inbound("+90555", "Hello I need help")
        assert "call_id" in result
        assert result["transcription"] is not None

    def test_handle_inbound_no_audio(self):
        orch = VoiceCallOrchestrator()
        result = orch.handle_inbound("+90555")
        assert result["transcription"] is None

    def test_process_speech(self):
        orch = VoiceCallOrchestrator()
        call = orch.initiator.initiate_call("+90555")
        result = orch.process_speech(call["call_id"], "Emergency help needed")
        assert result["text"] == "Emergency help needed"
        assert "urgency" in result

    def test_respond(self):
        orch = VoiceCallOrchestrator()
        call_result = orch.make_call("+90555", "Hello")
        result = orch.respond(
            call_result["call_id"],
            call_result["conversation_id"],
            "How can I help?",
        )
        assert result["response"] == "How can I help?"

    def test_end_call(self):
        orch = VoiceCallOrchestrator()
        call_result = orch.make_call("+90555", "Test")
        result = orch.end_call(
            call_result["call_id"],
            call_result["conversation_id"],
            duration=60,
        )
        assert result["status"] == "completed"

    def test_get_analytics(self):
        orch = VoiceCallOrchestrator()
        orch.make_call("+90555", "Test")
        analytics = orch.get_analytics()
        assert analytics["total_calls"] == 1
        assert "transcriptions" in analytics
        assert "syntheses" in analytics

    def test_get_status(self):
        orch = VoiceCallOrchestrator()
        status = orch.get_status()
        assert "total_calls" in status
        assert "active_calls" in status

    def test_get_quality_metrics(self):
        orch = VoiceCallOrchestrator()
        call = orch.make_call("+90555", "Test")
        orch.end_call(call["call_id"], duration=30)
        metrics = orch.get_quality_metrics()
        assert "success_rate" in metrics

    def test_full_pipeline(self):
        """Tam pipeline testi."""
        orch = VoiceCallOrchestrator()

        # Giden arama
        call = orch.make_call("+90555", "Merhaba Fatih")

        # Yanıt al
        speech = orch.process_speech(
            call["call_id"], "Hello, what's new?",
        )

        # Cevap ver
        orch.respond(
            call["call_id"],
            call["conversation_id"],
            "Your server needs attention.",
        )

        # Aramayı bitir
        orch.end_call(
            call["call_id"],
            call["conversation_id"],
            duration=120,
        )

        # Analitik kontrol
        analytics = orch.get_analytics()
        assert analytics["total_calls"] == 1
        assert analytics["syntheses"] >= 2


# ==================== Config ====================

class TestVoiceCallConfig:
    """VoiceCall config testleri."""

    def test_config_defaults(self):
        from app.config import Settings
        s = Settings()
        assert s.voicecall_enabled is True
        assert s.default_voice == "atlas_default"
        assert s.max_call_duration == 1800
        assert s.recording_enabled is True
        assert s.emergency_override is True


# ==================== Imports ====================

class TestVoiceCallImports:
    """Import testleri."""

    def test_import_all(self):
        from app.core.voicecall import (
            CallInitiator,
            CallRecorder,
            CallScheduler,
            SpeechToText,
            TextToSpeech,
            UrgencyClassifier,
            VoiceAuthenticator,
            VoiceCallOrchestrator,
            VoiceConversationManager,
        )
        assert CallInitiator is not None
        assert CallRecorder is not None
        assert CallScheduler is not None
        assert SpeechToText is not None
        assert TextToSpeech is not None
        assert UrgencyClassifier is not None
        assert VoiceAuthenticator is not None
        assert VoiceCallOrchestrator is not None
        assert VoiceConversationManager is not None

    def test_import_models(self):
        from app.models.voicecall_models import (
            AuthMethod,
            CallDirection,
            CallRecord,
            CallStatus,
            RecordingConsent,
            TranscriptionRecord,
            UrgencyLevel,
            VoiceCallSnapshot,
            VoiceProfile,
            VoiceProvider,
        )
        assert CallDirection is not None
        assert CallStatus is not None
        assert VoiceProvider is not None
        assert AuthMethod is not None
        assert UrgencyLevel is not None
        assert RecordingConsent is not None
        assert CallRecord is not None
        assert TranscriptionRecord is not None
        assert VoiceProfile is not None
        assert VoiceCallSnapshot is not None
