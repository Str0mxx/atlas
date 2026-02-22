"""
Voice Call System modelleri.

Sesli arama sistemi icin veri modelleri: arama yonetimi,
konusma modu, TTS sentezleme ve transkripsiyon.
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class CallDirection(str, Enum):
    """Arama yonu."""
    INBOUND = "inbound"
    OUTBOUND = "outbound"


class CallStatus(str, Enum):
    """Arama durumu."""
    INITIATING = "initiating"
    RINGING = "ringing"
    ACTIVE = "active"
    ON_HOLD = "on_hold"
    ENDED = "ended"
    FAILED = "failed"
    STALE = "stale"


class TTSProvider(str, Enum):
    """TTS saglayici turleri."""
    ELEVENLABS = "elevenlabs"
    EDGE_TTS = "edge_tts"
    GOOGLE_TTS = "google_tts"
    LOCAL = "local"


class VoiceCall(BaseModel):
    """
    Sesli arama modeli.

    Bir sesli aramanin tum durumunu ve meta verilerini tutar.
    Transkript girisleri, sira kilidi ve aktivite izleme dahil.
    """
    call_id: str = ""
    direction: CallDirection = CallDirection.OUTBOUND
    status: CallStatus = CallStatus.INITIATING
    caller: str = ""
    callee: str = ""
    started_at: float = 0.0
    ended_at: float = 0.0
    duration: float = 0.0
    transcript: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    turn_lock: bool = False
    last_activity: float = 0.0


class TalkModeConfig(BaseModel):
    """
    Konusma modu yapilandirmasi.

    Arka plan dinleme, araya girme (barge-in), uyandirma kelimesi
    ve token tasarrufu gibi ozellikler icin ayarlar.
    """
    enabled: bool = False
    background_listening: bool = False
    voice_directive_hints: bool = True
    barge_in_enabled: bool = True
    barge_in_speaker_disable: bool = False
    barge_in_receiver_disable: bool = False
    token_saving_mode: bool = False
    auto_end_on_silence: int = 30
    wake_word: str = ""


class TTSRequest(BaseModel):
    """
    TTS istegi modeli.

    Metin-konusma sentezleme icin gerekli parametreleri icerir.
    """
    text: str = ""
    provider: TTSProvider = TTSProvider.ELEVENLABS
    voice_id: str = "default"
    language: str = "tr"
    speed: float = 1.0
    pitch: float = 1.0
    cache_key: str = ""
    is_greeting: bool = False


class TTSResult(BaseModel):
    """
    TTS sonuc modeli.

    Sentezleme sonucunu, ses dosyasi yolunu ve hata bilgilerini icerir.
    """
    request_id: str = ""
    provider: TTSProvider = TTSProvider.ELEVENLABS
    audio_path: str = ""
    duration: float = 0.0
    cached: bool = False
    error: str = ""
    size_bytes: int = 0


class TranscriptionResult(BaseModel):
    """
    Transkripsiyon sonuc modeli.

    Ses-metin donusum sonucunu, guven puanini ve
    tekillestirme parmak izini icerir.
    """
    transcription_id: str = ""
    call_id: str = ""
    text: str = ""
    language: str = ""
    confidence: float = 0.0
    timestamp: float = 0.0
    source: str = "whisper"
    fingerprint: str = ""
    is_duplicate: bool = False


class StaleCallConfig(BaseModel):
    """
    Bayat arama yapilandirmasi.

    Bayat arama temizleyicisi (reaper) icin zamanlama ayarlari.
    """
    reaper_enabled: bool = True
    stale_seconds: int = 300
    check_interval: int = 60
    max_idle_seconds: int = 120


class VoiceConfig(BaseModel):
    """
    Genel ses sistemi yapilandirmasi.

    TTS saglayici, Whisper modeli, kayit dizini ve
    guvenlik ayarlarini icerir.
    """
    default_tts_provider: TTSProvider = TTSProvider.ELEVENLABS
    elevenlabs_api_key: str = ""
    elevenlabs_voice_id: str = ""
    whisper_model: str = "base"
    pre_cache_greeting: bool = True
    greeting_text: str = "Merhaba, ATLAS burada. Size nasil yardimci olabilirim?"
    stale_call_reaper_seconds: int = 300
    max_concurrent_calls: int = 5
    recording_enabled: bool = True
    recording_dir: str = "workspace/voice/recordings"
    temp_dir: str = "workspace/voice/temp"
    secure_temp_files: bool = True
    owner_only_permissions: bool = True
