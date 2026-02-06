"""VoiceAgent unit testleri.

API call'lar mock'lanarak voice agent davranislari test edilir.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.base_agent import TaskResult
from app.agents.voice_agent import VoiceAgent
from app.core.decision_matrix import ActionType, RiskLevel, UrgencyLevel
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


# === Fixtures ===


@pytest.fixture
def config() -> VoiceConfig:
    """Ornek voice yapilandirmasi."""
    return VoiceConfig(
        whisper_model="whisper-1",
        default_language=VoiceLanguage.TURKISH,
    )


@pytest.fixture
def agent(config: VoiceConfig) -> VoiceAgent:
    """Yapilandirilmis VoiceAgent."""
    return VoiceAgent(config=config)


# === Agent olusturma testleri ===


class TestVoiceAgentInit:
    """Agent baslangic testleri."""

    def test_default_init(self) -> None:
        agent = VoiceAgent()
        assert agent.name == "voice"
        assert agent.config.whisper_model == "whisper-1"
        assert agent.config.default_language == VoiceLanguage.TURKISH

    def test_custom_config(self, config: VoiceConfig) -> None:
        agent = VoiceAgent(config=config)
        assert agent.config == config

    def test_get_info(self, agent: VoiceAgent) -> None:
        info = agent.get_info()
        assert info["name"] == "voice"
        assert info["status"] == "idle"
        assert info["task_count"] == 0


# === Intent-agent eslestirme testleri ===


class TestIntentToAgent:
    """Komut niyetinden agent eslestirme testleri."""

    def test_server_check(self) -> None:
        assert VoiceAgent._intent_to_agent(CommandIntent.SERVER_CHECK) == "server_monitor"

    def test_security_scan(self) -> None:
        assert VoiceAgent._intent_to_agent(CommandIntent.SECURITY_SCAN) == "security"

    def test_send_email(self) -> None:
        assert VoiceAgent._intent_to_agent(CommandIntent.SEND_EMAIL) == "communication"

    def test_research(self) -> None:
        assert VoiceAgent._intent_to_agent(CommandIntent.RESEARCH) == "research"

    def test_marketing(self) -> None:
        assert VoiceAgent._intent_to_agent(CommandIntent.MARKETING) == "marketing"

    def test_code_review(self) -> None:
        assert VoiceAgent._intent_to_agent(CommandIntent.CODE_REVIEW) == "coding"

    def test_unknown_returns_empty(self) -> None:
        assert VoiceAgent._intent_to_agent(CommandIntent.UNKNOWN) == ""

    def test_general_question_returns_empty(self) -> None:
        assert VoiceAgent._intent_to_agent(CommandIntent.GENERAL_QUESTION) == ""


# === LLM parse testleri ===


class TestParseLlmResponse:
    """LLM yanit parse testleri."""

    def test_plain_json(self) -> None:
        text = '{"intent": "server_check", "confidence": 0.9}'
        result = VoiceAgent._parse_llm_response(text)
        assert result["intent"] == "server_check"
        assert result["confidence"] == 0.9

    def test_json_in_code_block(self) -> None:
        text = '```json\n{"intent": "research", "confidence": 0.8}\n```'
        result = VoiceAgent._parse_llm_response(text)
        assert result["intent"] == "research"

    def test_json_with_surrounding_text(self) -> None:
        text = 'Analiz sonucu: {"intent": "unknown", "confidence": 0.3} bitti.'
        result = VoiceAgent._parse_llm_response(text)
        assert result["intent"] == "unknown"

    def test_invalid_json_returns_raw(self) -> None:
        text = "Bu JSON degil"
        result = VoiceAgent._parse_llm_response(text)
        assert "raw_text" in result


# === Risk/aciliyet eslestirme testleri ===


class TestRiskUrgencyMapping:
    """Karar matrisi eslestirme testleri."""

    def test_normal_command(self) -> None:
        result = VoiceAnalysisResult(
            command=CommandAnalysis(
                original_text="test",
                intent=CommandIntent.GENERAL_QUESTION,
                confidence=0.9,
            ),
        )
        risk, urgency = VoiceAgent._map_to_risk_urgency(result)
        assert risk == RiskLevel.LOW
        assert urgency == UrgencyLevel.LOW

    def test_unknown_command(self) -> None:
        result = VoiceAnalysisResult(
            command=CommandAnalysis(
                original_text="garbled",
                intent=CommandIntent.UNKNOWN,
                confidence=0.1,
            ),
        )
        risk, urgency = VoiceAgent._map_to_risk_urgency(result)
        assert risk == RiskLevel.LOW
        assert urgency == UrgencyLevel.MEDIUM

    def test_security_command(self) -> None:
        result = VoiceAnalysisResult(
            command=CommandAnalysis(
                original_text="guvenlik taramas",
                intent=CommandIntent.SECURITY_SCAN,
                confidence=0.85,
            ),
        )
        risk, urgency = VoiceAgent._map_to_risk_urgency(result)
        assert urgency == UrgencyLevel.MEDIUM

    def test_server_check_command(self) -> None:
        result = VoiceAnalysisResult(
            command=CommandAnalysis(
                original_text="sunucu durumu",
                intent=CommandIntent.SERVER_CHECK,
                confidence=0.9,
            ),
        )
        risk, urgency = VoiceAgent._map_to_risk_urgency(result)
        assert urgency == UrgencyLevel.MEDIUM

    def test_no_command(self) -> None:
        result = VoiceAnalysisResult(task_type=VoiceTaskType.TRANSCRIBE)
        risk, urgency = VoiceAgent._map_to_risk_urgency(result)
        assert risk == RiskLevel.LOW
        assert urgency == UrgencyLevel.LOW

    def test_determine_action(self) -> None:
        action = VoiceAgent._determine_action(RiskLevel.LOW, UrgencyLevel.LOW)
        assert action == ActionType.LOG

        action = VoiceAgent._determine_action(RiskLevel.LOW, UrgencyLevel.MEDIUM)
        assert action == ActionType.LOG

        action = VoiceAgent._determine_action(RiskLevel.HIGH, UrgencyLevel.HIGH)
        assert action == ActionType.IMMEDIATE


# === Analyze methodu testleri ===


class TestAnalyze:
    """VoiceAgent.analyze testleri."""

    @pytest.mark.asyncio
    async def test_analyze_with_command(self, agent: VoiceAgent) -> None:
        data = {
            "result": VoiceAnalysisResult(
                task_type=VoiceTaskType.COMMAND,
                command=CommandAnalysis(
                    original_text="sunucu kontrol",
                    intent=CommandIntent.SERVER_CHECK,
                    target_agent="server_monitor",
                    confidence=0.9,
                ),
                summary="Test ozeti",
            ).model_dump(),
        }
        result = await agent.analyze(data)
        assert result["task_type"] == "command"
        assert result["risk"] == "low"
        assert result["urgency"] == "medium"
        assert result["stats"]["command_intent"] == "server_check"
        assert result["stats"]["target_agent"] == "server_monitor"

    @pytest.mark.asyncio
    async def test_analyze_low_confidence_issue(self, agent: VoiceAgent) -> None:
        data = {
            "result": VoiceAnalysisResult(
                command=CommandAnalysis(
                    original_text="mmmm",
                    intent=CommandIntent.UNKNOWN,
                    confidence=0.2,
                ),
            ).model_dump(),
        }
        result = await agent.analyze(data)
        assert len(result["issues"]) >= 2  # unknown + low confidence

    @pytest.mark.asyncio
    async def test_analyze_empty_transcription_issue(self, agent: VoiceAgent) -> None:
        data = {
            "result": VoiceAnalysisResult(
                task_type=VoiceTaskType.TRANSCRIBE,
                transcription=TranscriptionResult(text="", language="tr"),
            ).model_dump(),
        }
        result = await agent.analyze(data)
        assert any("bos" in i.lower() for i in result["issues"])


# === Report methodu testleri ===


class TestReport:
    """VoiceAgent.report testleri."""

    @pytest.mark.asyncio
    async def test_report_format(self, agent: VoiceAgent) -> None:
        task_result = TaskResult(
            success=True,
            data={
                "analysis": {
                    "task_type": "command",
                    "risk": "low",
                    "urgency": "medium",
                    "action": "log",
                    "summary": "Test ozeti",
                    "issues": [],
                    "stats": {
                        "has_command": True,
                        "command_intent": "server_check",
                        "target_agent": "server_monitor",
                        "command_confidence": 0.9,
                    },
                },
            },
            message="Test",
        )
        report = await agent.report(task_result)
        assert "SESLI ASISTAN RAPORU" in report
        assert "server_check" in report
        assert "server_monitor" in report

    @pytest.mark.asyncio
    async def test_report_with_errors(self, agent: VoiceAgent) -> None:
        task_result = TaskResult(
            success=False,
            data={"analysis": {"task_type": "command", "risk": "low",
                               "urgency": "low", "action": "log",
                               "summary": "", "issues": [], "stats": {}}},
            message="Hata",
            errors=["API baglanti hatasi"],
        )
        report = await agent.report(task_result)
        assert "HATALAR" in report
        assert "API baglanti hatasi" in report


# === Summary builder testleri ===


class TestBuildSummary:
    """VoiceAgent._build_summary testleri."""

    def test_empty_result(self, agent: VoiceAgent) -> None:
        result = VoiceAnalysisResult()
        summary = agent._build_summary(result)
        assert summary == "Ses gorevi tamamlandi."

    def test_transcription_summary(self, agent: VoiceAgent) -> None:
        result = VoiceAnalysisResult(
            transcription=TranscriptionResult(text="merhaba dunya test"),
        )
        summary = agent._build_summary(result)
        assert "Transkripsiyon" in summary

    def test_command_summary(self, agent: VoiceAgent) -> None:
        result = VoiceAnalysisResult(
            command=CommandAnalysis(
                original_text="sunucu kontrol",
                intent=CommandIntent.SERVER_CHECK,
                target_agent="server_monitor",
                confidence=0.9,
            ),
        )
        summary = agent._build_summary(result)
        assert "server_check" in summary
        assert "server_monitor" in summary

    def test_synthesis_summary(self, agent: VoiceAgent) -> None:
        result = VoiceAnalysisResult(
            synthesis=SynthesisResult(
                audio_path="/tmp/test.mp3",
                text="test",
                duration=2.5,
            ),
        )
        summary = agent._build_summary(result)
        assert "Sentez" in summary
        assert "2.5s" in summary


# === Execute testleri (API mock) ===


class TestExecute:
    """VoiceAgent.execute testleri (API mock'lu)."""

    @pytest.mark.asyncio
    async def test_invalid_task_type(self, agent: VoiceAgent) -> None:
        result = await agent.execute({"task_type": "invalid_type"})
        assert not result.success
        assert "Gecersiz gorev tipi" in result.message

    @pytest.mark.asyncio
    async def test_transcribe_no_audio(self, agent: VoiceAgent) -> None:
        result = await agent.execute({"task_type": "transcribe"})
        assert not result.success

    @pytest.mark.asyncio
    async def test_synthesize_no_text(self, agent: VoiceAgent) -> None:
        result = await agent.execute({"task_type": "synthesize"})
        assert not result.success

    @pytest.mark.asyncio
    async def test_command_with_text(self, agent: VoiceAgent) -> None:
        """Metin tabanli komut testi (Whisper atlanir, LLM mock'lanir)."""
        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(
                text='{"intent": "server_check", "target_agent": "server_monitor", '
                '"parameters": {}, "confidence": 0.9, '
                '"response_text": "Sunucu kontrolu baslatiliyor."}'
            )
        ]

        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)

        # ElevenLabs mock (sentez)
        mock_http = AsyncMock()
        mock_http_response = MagicMock()
        mock_http_response.content = b"fake_audio_data"
        mock_http_response.raise_for_status = MagicMock()
        mock_http.post = AsyncMock(return_value=mock_http_response)
        mock_http.is_closed = False

        agent._anthropic_client = mock_client
        agent._http_client = mock_http

        with patch.object(agent, "_get_audio_duration", return_value=1.5), \
             patch("app.agents.voice_agent.settings") as mock_settings:
            mock_settings.anthropic_api_key.get_secret_value.return_value = "test-key"
            mock_settings.elevenlabs_api_key.get_secret_value.return_value = "test-key"

            result = await agent.execute({
                "task_type": "command",
                "text": "sunucu durumunu kontrol et",
                "synthesize_response": False,
            })

        assert result.success
        analysis = result.data.get("analysis_result", {})
        assert analysis["command"]["intent"] == "server_check"
        assert analysis["command"]["target_agent"] == "server_monitor"

    @pytest.mark.asyncio
    async def test_run_wraps_execute(self, agent: VoiceAgent) -> None:
        """BaseAgent.run hata yakalama testi.

        execute() icinde try/except hatalar yakalandigi icin
        run()'a exception ulasmaz, status idle kalir.
        """
        result = await agent.run({"task_type": "transcribe"})
        assert not result.success
        assert agent.status.value == "idle"
