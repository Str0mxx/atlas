"""Sesli asistan veri modelleri.

OpenAI Whisper (STT), ElevenLabs (TTS) ve komut analizi
icin Pydantic schema'lari.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class VoiceTaskType(str, Enum):
    """Ses gorev tanimlari."""

    TRANSCRIBE = "transcribe"
    SYNTHESIZE = "synthesize"
    COMMAND = "command"


class VoiceLanguage(str, Enum):
    """Desteklenen ses dilleri."""

    TURKISH = "tr"
    ENGLISH = "en"
    ARABIC = "ar"
    GERMAN = "de"


class CommandIntent(str, Enum):
    """Ses komutundan cikarilan niyet siniflandirmasi."""

    SERVER_CHECK = "server_check"
    SECURITY_SCAN = "security_scan"
    SEND_EMAIL = "send_email"
    RESEARCH = "research"
    MARKETING = "marketing"
    CODE_REVIEW = "code_review"
    STATUS_REPORT = "status_report"
    GENERAL_QUESTION = "general_question"
    UNKNOWN = "unknown"


class VoiceConfig(BaseModel):
    """Ses agent yapilandirmasi.

    Attributes:
        whisper_model: Whisper transkripsiyon modeli.
        elevenlabs_voice_id: ElevenLabs ses kimlik numarasi.
        elevenlabs_model_id: ElevenLabs TTS modeli.
        default_language: Varsayilan dil.
        anthropic_model: Komut analizi icin Anthropic modeli.
        max_audio_duration: Maksimum ses suresi (saniye).
        stability: ElevenLabs ses kararliligi (0.0-1.0).
        similarity_boost: ElevenLabs ses benzerlik gucu (0.0-1.0).
    """

    whisper_model: str = "whisper-1"
    elevenlabs_voice_id: str = "21m00Tcm4TlvDq8ikWAM"
    elevenlabs_model_id: str = "eleven_multilingual_v2"
    default_language: VoiceLanguage = VoiceLanguage.TURKISH
    anthropic_model: str = "claude-sonnet-4-5-20250929"
    max_audio_duration: int = 300
    stability: float = 0.5
    similarity_boost: float = 0.75


class TranscriptionResult(BaseModel):
    """Whisper transkripsiyon sonucu.

    Attributes:
        text: Transkripsiyonu yapilmis metin.
        language: Algilanan dil.
        duration: Ses dosyasi suresi (saniye).
    """

    text: str
    language: str = ""
    duration: float = 0.0


class SynthesisResult(BaseModel):
    """ElevenLabs sentez sonucu.

    Attributes:
        audio_path: Olusturulan ses dosyasinin yolu.
        text: Sentezlenen metin.
        duration: Olusturulan ses suresi (saniye).
        voice_id: Kullanilan ses kimlik numarasi.
        characters_used: Harcanan karakter sayisi.
    """

    audio_path: str
    text: str
    duration: float = 0.0
    voice_id: str = ""
    characters_used: int = 0


class CommandAnalysis(BaseModel):
    """Ses komutu analiz sonucu.

    Attributes:
        original_text: Orijinal transkripsiyon metni.
        intent: Tespit edilen niyet.
        target_agent: Yonlendirilecek agent adi.
        parameters: Agent'a iletilecek parametreler.
        confidence: Niyet tespit guven skoru (0.0-1.0).
        response_text: Kullaniciya donecek yanit metni.
    """

    original_text: str
    intent: CommandIntent = CommandIntent.UNKNOWN
    target_agent: str = ""
    parameters: dict[str, Any] = Field(default_factory=dict)
    confidence: float = 0.0
    response_text: str = ""


class VoiceAnalysisResult(BaseModel):
    """Ses agent genel analiz sonucu.

    Attributes:
        task_type: Gerceklestirilen gorev tipi.
        transcription: Transkripsiyon sonucu.
        synthesis: Sentez sonucu.
        command: Komut analiz sonucu.
        summary: Ozet metin.
    """

    task_type: VoiceTaskType = VoiceTaskType.COMMAND
    transcription: TranscriptionResult | None = None
    synthesis: SynthesisResult | None = None
    command: CommandAnalysis | None = None
    summary: str = ""
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
