"""
Smart Speaker Orchestrator - Tüm smart speaker bileşenlerini orkestre eder.

Bu modül tüm smart speaker sistemini koordine eder ve end-to-end voice
pipeline sağlar.
"""

import logging
from typing import Any, Optional

from app.core.smartspeaker.alexa_skill_connector import (
    AlexaSkillConnector
)
from app.core.smartspeaker.google_assistant_bridge import (
    GoogleAssistantBridge
)
from app.core.smartspeaker.siri_shortcuts import SiriShortcuts
from app.core.smartspeaker.voice_command_parser import VoiceCommandParser
from app.core.smartspeaker.smart_speaker_response_formatter import (
    SmartSpeakerResponseFormatter
)
from app.core.smartspeaker.multi_device_sync import MultiDeviceSync
from app.core.smartspeaker.wake_word_handler import WakeWordHandler
from app.core.smartspeaker.conversation_context import (
    SpeakerConversationContext
)

logger = logging.getLogger(__name__)


class SmartSpeakerOrchestrator:
    """Smart speaker sistemini orkestre eden ana sınıf."""

    def __init__(self) -> None:
        """SmartSpeakerOrchestrator başlatıcı."""
        self.alexa = AlexaSkillConnector()
        self.google = GoogleAssistantBridge()
        self.siri = SiriShortcuts()
        self.parser = VoiceCommandParser()
        self.formatter = SmartSpeakerResponseFormatter()
        self.sync = MultiDeviceSync()
        self.wake = WakeWordHandler()
        self.context = SpeakerConversationContext()

        self._stats = {"pipelines_run": 0, "commands_processed": 0}

        logger.info("SmartSpeakerOrchestrator başlatıldı")

    @property
    def pipeline_count(self) -> int:
        """Çalıştırılan pipeline sayısını döndürür."""
        return self._stats["pipelines_run"]

    @property
    def command_count(self) -> int:
        """İşlenen komut sayısını döndürür."""
        return self._stats["commands_processed"]

    def process_voice_command(
        self,
        raw_text: str,
        platform: str = "alexa",
        session_id: str = "",
        device_id: str = ""
    ) -> dict[str, Any]:
        """
        Sesli komutu end-to-end işler.

        Args:
            raw_text: Ham komut metni
            platform: Platform (alexa, google, siri)
            session_id: Session kimliği
            device_id: Cihaz kimliği

        Returns:
            İşlenmiş komut sonucu
        """
        # 1. Komutu parse et
        parsed = self.parser.parse_command(raw_text)
        intent = parsed["intent"]

        # 2. Session yönetimi
        if session_id:
            if session_id not in self.context._sessions:
                self.context.start_session(session_id, platform)
            self.context.add_turn(session_id, "user", raw_text)

        # 3. Yanıt formatla (SSML)
        ssml_result = self.formatter.generate_ssml(
            f"Processing {intent} command"
        )

        # 4. Platforma adapte et
        response = {"text": raw_text, "speech": ssml_result["ssml"]}
        adapted = self.formatter.adapt_platform(response, platform)

        self._stats["pipelines_run"] += 1
        self._stats["commands_processed"] += 1

        logger.info(
            f"Voice command işlendi: '{raw_text}' -> {intent} "
            f"({platform})"
        )

        return {
            "raw_text": raw_text,
            "intent": intent,
            "platform": platform,
            "response_text": ssml_result["ssml"],
            "pipeline_complete": True
        }

    def setup_platform(
        self,
        platform: str,
        config: Optional[dict] = None
    ) -> dict[str, Any]:
        """
        Platform yapılandırması yapar.

        Args:
            platform: Platform adı (alexa, google, siri)
            config: Yapılandırma parametreleri

        Returns:
            Yapılandırma sonucu
        """
        if config is None:
            config = {}

        if platform == "alexa":
            skill_name = config.get("skill_name", "ATLAS")
            self.alexa.register_skill(
                "atlas_skill",
                skill_name,
                ["ControlIntent", "QueryIntent"]
            )

        elif platform == "google":
            action_name = config.get("action_name", "ATLAS Assistant")
            self.google.register_action(
                "atlas_action",
                action_name,
                ["talk to atlas", "ask atlas"]
            )

        elif platform == "siri":
            shortcut_name = config.get("shortcut_name", "ATLAS Command")
            self.siri.create_shortcut(
                shortcut_name,
                "process_command"
            )

        logger.info(f"Platform yapılandırıldı: {platform}")

        return {
            "platform": platform,
            "configured": True
        }

    def get_analytics(self) -> dict[str, Any]:
        """
        Tüm bileşenlerden analitik verileri toplar.

        Returns:
            Toplanan analitik veriler
        """
        analytics = {
            "orchestrator": {
                "pipelines_run": self._stats["pipelines_run"],
                "commands_processed": self._stats["commands_processed"]
            },
            "alexa": {
                "skills_registered": self.alexa._stats["skills_registered"],
                "intents_handled": self.alexa._stats["intents_handled"]
            },
            "google": {
                "actions_registered": (
                    self.google._stats["actions_registered"]
                ),
                "fulfillments_handled": (
                    self.google._stats["fulfillments_handled"]
                )
            },
            "siri": {
                "shortcuts_created": self.siri._stats["shortcuts_created"],
                "intents_donated": self.siri._stats["intents_donated"]
            },
            "parser": {
                "commands_parsed": self.parser._stats["commands_parsed"],
                "entities_extracted": (
                    self.parser._stats["entities_extracted"]
                )
            },
            "formatter": {
                "responses_formatted": (
                    self.formatter._stats["responses_formatted"]
                ),
                "ssml_generated": self.formatter._stats["ssml_generated"]
            },
            "sync": {
                "devices_registered": self.sync._stats["devices_registered"],
                "syncs_done": self.sync._stats["syncs_done"]
            },
            "wake": {
                "activations_handled": (
                    self.wake._stats["activations_handled"]
                ),
                "words_registered": self.wake._stats["words_registered"]
            },
            "context": {
                "sessions_created": (
                    self.context._stats["sessions_created"]
                ),
                "turns_processed": self.context._stats["turns_processed"]
            }
        }

        logger.debug("Analitik veriler toplandı")

        return analytics
