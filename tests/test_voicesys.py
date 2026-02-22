"""
Voice Call System testleri.

VoiceCallManager, TalkModeManager, TTSManager ve
TranscriptionManager icin kapsamli birim testleri.
"""

import os
import time
import pytest

from app.models.voicesys_models import (
    CallDirection,
    CallStatus,
    StaleCallConfig,
    TalkModeConfig,
    TTSProvider,
    TTSRequest,
    TTSResult,
    TranscriptionResult,
    VoiceCall,
    VoiceConfig,
)
from app.core.voice.voice_call import VoiceCallManager
from app.core.voice.talk_mode import TalkModeManager
from app.core.voice.tts_manager import TTSManager
from app.core.voice.transcription import TranscriptionManager


# ===== Model Testleri =====

class TestVoiceModels:
    """Ses sistemi model testleri."""

    def test_call_direction_values(self):
        """Arama yonu enum degerlerini dogrula."""
        assert CallDirection.INBOUND == "inbound"
        assert CallDirection.OUTBOUND == "outbound"

    def test_call_status_values(self):
        """Arama durumu enum degerlerini dogrula."""
        assert CallStatus.INITIATING == "initiating"
        assert CallStatus.ACTIVE == "active"
        assert CallStatus.ENDED == "ended"
        assert CallStatus.STALE == "stale"

    def test_tts_provider_values(self):
        """TTS saglayici enum degerlerini dogrula."""
        assert TTSProvider.ELEVENLABS == "elevenlabs"
        assert TTSProvider.EDGE_TTS == "edge_tts"
        assert TTSProvider.GOOGLE_TTS == "google_tts"

    def test_voice_call_defaults(self):
        """VoiceCall varsayilan degerlerini dogrula."""
        call = VoiceCall()
        assert call.call_id == ""
        assert call.direction == CallDirection.OUTBOUND
        assert call.status == CallStatus.INITIATING
        assert call.transcript == []
        assert call.turn_lock is False

    def test_talk_mode_config_defaults(self):
        """TalkModeConfig varsayilan degerlerini dogrula."""
        config = TalkModeConfig()
        assert config.enabled is False
        assert config.barge_in_enabled is True
        assert config.auto_end_on_silence == 30
        assert config.wake_word == ""

    def test_tts_request_defaults(self):
        """TTSRequest varsayilan degerlerini dogrula."""
        req = TTSRequest()
        assert req.provider == TTSProvider.ELEVENLABS
        assert req.language == "tr"
        assert req.speed == 1.0

    def test_transcription_result_defaults(self):
        """TranscriptionResult varsayilan degerlerini dogrula."""
        result = TranscriptionResult()
        assert result.source == "whisper"
        assert result.is_duplicate is False
        assert result.confidence == 0.0

    def test_voice_config_defaults(self):
        """VoiceConfig varsayilan degerlerini dogrula."""
        config = VoiceConfig()
        assert config.max_concurrent_calls == 5
        assert config.secure_temp_files is True
        assert config.pre_cache_greeting is True


# ===== VoiceCallManager Testleri =====

class TestVoiceCallManager:
    """VoiceCallManager birim testleri."""

    def test_initiate_call(self):
        """Arama baslatma islemini dogrula."""
        mgr = VoiceCallManager(max_concurrent=3)
        call = mgr.initiate_call("user1", "atlas")
        assert call.call_id != ""
        assert call.direction == CallDirection.OUTBOUND
        assert call.status == CallStatus.RINGING
        assert call.caller == "atlas"
        assert call.callee == "user1"
        assert call.started_at > 0

    def test_accept_and_end_call(self):
        """Arama kabul etme ve sonlandirma islemlerini dogrula."""
        mgr = VoiceCallManager()
        call = mgr.initiate_call("user1")
        accepted = mgr.accept_call(call.call_id)
        assert accepted.status == CallStatus.ACTIVE
        ended = mgr.end_call(call.call_id)
        assert ended.status == CallStatus.ENDED
        assert ended.duration > 0

    def test_hold_and_resume(self):
        """Beklemeye alma ve devam ettirme islemlerini dogrula."""
        mgr = VoiceCallManager()
        call = mgr.initiate_call("user1")
        mgr.accept_call(call.call_id)
        assert mgr.hold_call(call.call_id) is True
        assert mgr.get_call(call.call_id).status == CallStatus.ON_HOLD
        assert mgr.resume_call(call.call_id) is True
        assert mgr.get_call(call.call_id).status == CallStatus.ACTIVE

    def test_max_concurrent_limit(self):
        """Maksimum esanli arama limitini dogrula."""
        mgr = VoiceCallManager(max_concurrent=2)
        mgr.initiate_call("user1")
        mgr.initiate_call("user2")
        with pytest.raises(RuntimeError):
            mgr.initiate_call("user3")

    def test_transcript_management(self):
        """Transkript yonetimini dogrula."""
        mgr = VoiceCallManager()
        call = mgr.initiate_call("user1")
        mgr.accept_call(call.call_id)
        mgr.add_transcript_entry(call.call_id, "atlas", "Merhaba")
        mgr.add_transcript_entry(call.call_id, "user1", "Selam")
        transcript = mgr.get_transcript(call.call_id)
        assert len(transcript) == 2
        assert transcript[0]["speaker"] == "atlas"
        assert transcript[1]["text"] == "Selam"

    def test_turn_lock(self):
        """Sira kilidi islemlerini dogrula."""
        mgr = VoiceCallManager()
        call = mgr.initiate_call("user1")
        assert mgr.acquire_turn_lock(call.call_id) is True
        assert mgr.acquire_turn_lock(call.call_id) is False
        assert mgr.release_turn_lock(call.call_id) is True
        assert mgr.release_turn_lock(call.call_id) is False

    def test_stale_call_reaping(self):
        """Bayat arama temizligi islemini dogrula."""
        stale_config = StaleCallConfig(reaper_enabled=True, stale_seconds=0, max_idle_seconds=0)
        mgr = VoiceCallManager(stale_config=stale_config)
        call = mgr.initiate_call("user1")
        call_id = call.call_id
        time.sleep(0.01)
        reaped = mgr.reap_stale_calls()
        assert call_id in reaped
        assert mgr.get_call(call_id).status == CallStatus.STALE

    def test_stats_and_history(self):
        """Istatistik ve gecmis kayit islemlerini dogrula."""
        mgr = VoiceCallManager()
        call = mgr.initiate_call("user1")
        mgr.accept_call(call.call_id)
        mgr.end_call(call.call_id)
        stats = mgr.get_stats()
        assert stats["total_calls"] == 1
        assert stats["ended_calls"] == 1
        assert stats["history_count"] > 0
        history = mgr.get_history()
        assert len(history) > 0
        actions = [h["action"] for h in history]
        assert "initiate_call" in actions
        assert "end_call" in actions


# ===== TalkModeManager Testleri =====

class TestTalkModeManager:
    """TalkModeManager birim testleri."""

    def test_enable_disable(self):
        """Etkinlestirme ve devre disi birakma islemlerini dogrula."""
        mgr = TalkModeManager()
        assert mgr.is_active() is False
        config = mgr.enable()
        assert mgr.is_active() is True
        assert config.enabled is True
        mgr.disable()
        assert mgr.is_active() is False

    def test_enable_with_custom_config(self):
        """Ozel yapilandirma ile etkinlestirmeyi dogrula."""
        mgr = TalkModeManager()
        custom = TalkModeConfig(barge_in_enabled=False, auto_end_on_silence=60)
        config = mgr.enable(custom)
        assert config.barge_in_enabled is False
        assert config.auto_end_on_silence == 60
        assert config.enabled is True

    def test_toggle_background_listening(self):
        """Arka plan dinleme acma/kapama islemini dogrula."""
        mgr = TalkModeManager()
        assert mgr.get_config().background_listening is False
        result = mgr.toggle_background_listening()
        assert result is True
        assert mgr.get_config().background_listening is True
        result = mgr.toggle_background_listening()
        assert result is False

    def test_set_barge_in(self):
        """Araya girme ayarlarini dogrula."""
        mgr = TalkModeManager()
        mgr.set_barge_in(enabled=True, speaker_disable=True, receiver_disable=False)
        config = mgr.get_config()
        assert config.barge_in_enabled is True
        assert config.barge_in_speaker_disable is True
        assert config.barge_in_receiver_disable is False

    def test_wake_word_and_token_saving(self):
        """Uyandirma kelimesi ve token tasarrufu islemlerini dogrula."""
        mgr = TalkModeManager()
        mgr.set_wake_word("atlas")
        assert mgr.get_config().wake_word == "atlas"
        mgr.enable_token_saving()
        assert mgr.get_config().token_saving_mode is True

    def test_process_audio_input(self):
        """Ses girisi isleme islemini dogrula."""
        mgr = TalkModeManager()
        assert mgr.process_audio_input(b"data") is None
        mgr.enable()
        result = mgr.process_audio_input(b"test audio data")
        assert result is not None
        assert "[audio:" in result
        assert mgr.process_audio_input(b"") is None


# ===== TTSManager Testleri =====

class TestTTSManager:
    """TTSManager birim testleri."""

    def test_synthesize_default_provider(self):
        """Varsayilan saglayici ile sentezlemeyi dogrula."""
        mgr = TTSManager()
        result = mgr.synthesize("Merhaba dunya")
        assert result.error == ""
        assert result.provider == TTSProvider.ELEVENLABS
        assert result.duration > 0
        assert result.audio_path != ""

    def test_synthesize_with_specific_provider(self):
        """Belirli saglayici ile sentezlemeyi dogrula."""
        mgr = TTSManager()
        result = mgr.synthesize("Test", provider=TTSProvider.EDGE_TTS)
        assert result.provider == TTSProvider.EDGE_TTS
        assert result.error == ""

    def test_cache_hit(self):
        """Onbellek isabetini dogrula."""
        mgr = TTSManager()
        result1 = mgr.synthesize("Ayni metin")
        result2 = mgr.synthesize("Ayni metin")
        assert result2.cached is True

    def test_pre_cache_greeting(self):
        """Karsilama onceden onbellekleme islemini dogrula."""
        mgr = TTSManager()
        result = mgr.pre_cache_greeting("Merhaba ATLAS burada")
        assert result.error == ""
        cached = mgr.get_cached(mgr._make_cache_key("Merhaba ATLAS burada", TTSProvider.ELEVENLABS, "default"))
        assert cached is not None
        assert cached.cached is True

    def test_clear_cache(self):
        """Onbellek temizleme islemini dogrula."""
        mgr = TTSManager()
        mgr.synthesize("Test 1")
        mgr.synthesize("Test 2")
        assert mgr.get_stats()["cache_size"] == 2
        cleared = mgr.clear_cache()
        assert cleared == 2
        assert mgr.get_stats()["cache_size"] == 0

    def test_secure_temp_file(self):
        """Guvenli gecici dosya olusturmayi dogrula."""
        mgr = TTSManager()
        path = mgr._create_secure_temp_file(".mp3")
        assert path.endswith(".mp3")
        assert len(os.path.basename(path)) > 20

    def test_surface_all_errors(self):
        """Hata birlestiricisini dogrula."""
        mgr = TTSManager()
        assert mgr._surface_all_errors([]) == ""
        assert mgr._surface_all_errors(["err1", "err2"]) == "err1 | err2"


# ===== TranscriptionManager Testleri =====

class TestTranscriptionManager:
    """TranscriptionManager birim testleri."""

    def test_transcribe(self):
        """Temel transkripsiyon islemini dogrula."""
        mgr = TranscriptionManager()
        result = mgr.transcribe("/path/to/audio.wav", "tr")
        assert result.transcription_id != ""
        assert result.text != ""
        assert result.language == "tr"
        assert result.source == "whisper"
        assert result.fingerprint != ""
        assert result.confidence > 0

    def test_transcribe_voice_note(self):
        """Sesli not transkripsiyon islemini dogrula."""
        mgr = TranscriptionManager()
        result = mgr.transcribe_voice_note(b"test audio bytes")
        assert result.text != ""
        assert result.source == "voice_note"
        assert "[ses notu:" in result.text

    def test_transcribe_voice_note_fallback(self):
        """Bos ses verisi icin varsayilan degeri dogrula."""
        mgr = TranscriptionManager()
        result = mgr.transcribe_voice_note(b"", fallback="varsayilan metin")
        assert result.text == "varsayilan metin"
        assert result.source == "fallback"
        assert result.confidence == 0.0

    def test_dedupe_transcript(self):
        """Tekillestirme islemini dogrula."""
        mgr = TranscriptionManager()
        result1 = mgr.transcribe("/path/audio1.wav")
        result2 = TranscriptionResult(
            transcription_id="test-id",
            text=result1.text,
            source=result1.source,
            fingerprint=result1.fingerprint,
        )
        is_dupe = mgr.dedupe_transcript(result2, [result1])
        assert is_dupe is True
        assert result2.is_duplicate is True

    def test_dedupe_different_source(self):
        """Farkli kaynaktan tekillestirmenin basarisiz oldugunu dogrula."""
        mgr = TranscriptionManager()
        result1 = mgr.transcribe("/path/audio1.wav")
        result2 = TranscriptionResult(
            transcription_id="test-id",
            text=result1.text,
            source="different_source",
            fingerprint="different_fingerprint",
        )
        is_dupe = mgr.dedupe_transcript(result2, [result1])
        assert is_dupe is False

    def test_replace_media_placeholder(self):
        """Medya yer tutucusu degistirme islemini dogrula."""
        mgr = TranscriptionManager()
        text = "Kullanici soyledi: <media:audio>"
        result = mgr.replace_media_placeholder(text, "merhaba dunya")
        assert result == "Kullanici soyledi: merhaba dunya"
        assert "<media:audio>" not in result

    def test_replace_media_no_placeholder(self):
        """Yer tutucusu olmayan metinde degisiklik olmadigini dogrula."""
        mgr = TranscriptionManager()
        text = "Normal metin"
        result = mgr.replace_media_placeholder(text, "transkript")
        assert result == "Normal metin"

    def test_stats_and_history(self):
        """Istatistik ve gecmis kayit islemlerini dogrula."""
        mgr = TranscriptionManager()
        mgr.transcribe("/path/audio.wav")
        stats = mgr.get_stats()
        assert stats["total_transcriptions"] == 1
        assert stats["whisper_model"] == "base"
        history = mgr.get_history()
        assert len(history) > 0
