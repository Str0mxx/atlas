"""Voice modelleri unit testleri."""

from app.models.voice import (
    CommandAnalysis,
    CommandIntent,
    SynthesisResult,
    TranscriptionResult,
    VoiceAnalysisResult,
    VoiceConfig,
    VoiceLanguage,
    VoiceTaskType,
)


class TestVoiceEnums:
    """Enum tanimlari testleri."""

    def test_voice_task_types(self) -> None:
        assert VoiceTaskType.TRANSCRIBE == "transcribe"
        assert VoiceTaskType.SYNTHESIZE == "synthesize"
        assert VoiceTaskType.COMMAND == "command"

    def test_voice_languages(self) -> None:
        assert VoiceLanguage.TURKISH == "tr"
        assert VoiceLanguage.ENGLISH == "en"
        assert VoiceLanguage.ARABIC == "ar"
        assert VoiceLanguage.GERMAN == "de"

    def test_command_intents(self) -> None:
        assert CommandIntent.SERVER_CHECK == "server_check"
        assert CommandIntent.SECURITY_SCAN == "security_scan"
        assert CommandIntent.SEND_EMAIL == "send_email"
        assert CommandIntent.RESEARCH == "research"
        assert CommandIntent.MARKETING == "marketing"
        assert CommandIntent.CODE_REVIEW == "code_review"
        assert CommandIntent.STATUS_REPORT == "status_report"
        assert CommandIntent.GENERAL_QUESTION == "general_question"
        assert CommandIntent.UNKNOWN == "unknown"


class TestVoiceConfig:
    """VoiceConfig testleri."""

    def test_default_config(self) -> None:
        config = VoiceConfig()
        assert config.whisper_model == "whisper-1"
        assert config.elevenlabs_model_id == "eleven_multilingual_v2"
        assert config.default_language == VoiceLanguage.TURKISH
        assert config.max_audio_duration == 300
        assert 0.0 <= config.stability <= 1.0
        assert 0.0 <= config.similarity_boost <= 1.0

    def test_custom_config(self) -> None:
        config = VoiceConfig(
            whisper_model="whisper-2",
            default_language=VoiceLanguage.ENGLISH,
            max_audio_duration=600,
            stability=0.8,
        )
        assert config.whisper_model == "whisper-2"
        assert config.default_language == VoiceLanguage.ENGLISH
        assert config.max_audio_duration == 600
        assert config.stability == 0.8


class TestTranscriptionResult:
    """TranscriptionResult testleri."""

    def test_basic(self) -> None:
        result = TranscriptionResult(text="merhaba dunya", language="tr", duration=2.5)
        assert result.text == "merhaba dunya"
        assert result.language == "tr"
        assert result.duration == 2.5

    def test_defaults(self) -> None:
        result = TranscriptionResult(text="hello")
        assert result.language == ""
        assert result.duration == 0.0


class TestSynthesisResult:
    """SynthesisResult testleri."""

    def test_basic(self) -> None:
        result = SynthesisResult(
            audio_path="/tmp/output.mp3",
            text="test metni",
            duration=3.2,
            voice_id="voice123",
            characters_used=10,
        )
        assert result.audio_path == "/tmp/output.mp3"
        assert result.text == "test metni"
        assert result.duration == 3.2
        assert result.characters_used == 10

    def test_defaults(self) -> None:
        result = SynthesisResult(audio_path="/tmp/out.mp3", text="test")
        assert result.duration == 0.0
        assert result.voice_id == ""
        assert result.characters_used == 0


class TestCommandAnalysis:
    """CommandAnalysis testleri."""

    def test_basic(self) -> None:
        cmd = CommandAnalysis(
            original_text="sunucu durumunu kontrol et",
            intent=CommandIntent.SERVER_CHECK,
            target_agent="server_monitor",
            confidence=0.95,
            response_text="Sunucu kontrolu baslatiliyor.",
        )
        assert cmd.intent == CommandIntent.SERVER_CHECK
        assert cmd.target_agent == "server_monitor"
        assert cmd.confidence == 0.95

    def test_defaults(self) -> None:
        cmd = CommandAnalysis(original_text="test")
        assert cmd.intent == CommandIntent.UNKNOWN
        assert cmd.target_agent == ""
        assert cmd.confidence == 0.0
        assert cmd.parameters == {}

    def test_with_parameters(self) -> None:
        cmd = CommandAnalysis(
            original_text="security scan yap",
            intent=CommandIntent.SECURITY_SCAN,
            target_agent="security",
            parameters={"scan_type": "full", "target": "server1"},
            confidence=0.85,
        )
        assert cmd.parameters["scan_type"] == "full"
        assert cmd.parameters["target"] == "server1"


class TestVoiceAnalysisResult:
    """VoiceAnalysisResult testleri."""

    def test_defaults(self) -> None:
        result = VoiceAnalysisResult()
        assert result.task_type == VoiceTaskType.COMMAND
        assert result.transcription is None
        assert result.synthesis is None
        assert result.command is None
        assert result.summary == ""

    def test_with_transcription(self) -> None:
        result = VoiceAnalysisResult(
            task_type=VoiceTaskType.TRANSCRIBE,
            transcription=TranscriptionResult(text="merhaba", language="tr"),
        )
        assert result.transcription is not None
        assert result.transcription.text == "merhaba"

    def test_with_command(self) -> None:
        result = VoiceAnalysisResult(
            task_type=VoiceTaskType.COMMAND,
            transcription=TranscriptionResult(text="sunucu kontrol"),
            command=CommandAnalysis(
                original_text="sunucu kontrol",
                intent=CommandIntent.SERVER_CHECK,
                target_agent="server_monitor",
                confidence=0.9,
            ),
        )
        assert result.command is not None
        assert result.command.intent == CommandIntent.SERVER_CHECK

    def test_full_pipeline(self) -> None:
        result = VoiceAnalysisResult(
            task_type=VoiceTaskType.COMMAND,
            transcription=TranscriptionResult(text="test", duration=1.0),
            command=CommandAnalysis(
                original_text="test",
                intent=CommandIntent.GENERAL_QUESTION,
                response_text="Yanit metni",
                confidence=0.8,
            ),
            synthesis=SynthesisResult(
                audio_path="/tmp/response.mp3",
                text="Yanit metni",
                duration=2.0,
            ),
            summary="Test ozeti",
        )
        assert result.transcription is not None
        assert result.command is not None
        assert result.synthesis is not None
        assert result.summary == "Test ozeti"

    def test_serialization(self) -> None:
        result = VoiceAnalysisResult(
            task_type=VoiceTaskType.TRANSCRIBE,
            transcription=TranscriptionResult(text="hello", language="en"),
        )
        data = result.model_dump()
        assert data["task_type"] == "transcribe"
        assert data["transcription"]["text"] == "hello"

        restored = VoiceAnalysisResult(**data)
        assert restored.transcription is not None
        assert restored.transcription.text == "hello"
