"""ATLAS Sesli Arama Orkestratörü modülü.

Tam sesli arama pipeline, gelen/giden arama,
konuşma entegrasyonu, analitik, kalite izleme.
"""

import logging
from typing import Any

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

logger = logging.getLogger(__name__)


class VoiceCallOrchestrator:
    """Sesli arama orkestratörü.

    Tüm sesli arama bileşenlerini koordine eder.

    Attributes:
        initiator: Arama başlatıcı.
        stt: Konuşmadan metne.
        tts: Metinden konuşmaya.
        conversation: Konuşma yöneticisi.
        urgency: Aciliyet sınıflandırıcı.
        scheduler: Arama zamanlayıcı.
        authenticator: Ses doğrulayıcı.
        recorder: Arama kaydedici.
    """

    def __init__(
        self,
        default_voice: str = "atlas_default",
        recording_enabled: bool = True,
        max_call_duration: int = 1800,
    ) -> None:
        """Orkestratörü başlatır.

        Args:
            default_voice: Varsayılan ses.
            recording_enabled: Kayıt etkin mi.
            max_call_duration: Maks arama süresi.
        """
        self.initiator = CallInitiator()
        self.stt = SpeechToText()
        self.tts = TextToSpeech(
            default_voice=default_voice,
        )
        self.conversation = (
            VoiceConversationManager()
        )
        self.urgency = UrgencyClassifier()
        self.scheduler = CallScheduler()
        self.authenticator = (
            VoiceAuthenticator()
        )
        self.recorder = CallRecorder(
            recording_enabled=recording_enabled,
        )

        self._max_call_duration = max_call_duration
        self._stats = {
            "total_calls": 0,
            "inbound_calls": 0,
            "outbound_calls": 0,
        }

        logger.info(
            "VoiceCallOrchestrator baslatildi",
        )

    def make_call(
        self,
        callee: str,
        message: str,
        voice: str | None = None,
        record: bool = True,
    ) -> dict[str, Any]:
        """Giden arama yapar.

        Args:
            callee: Aranan.
            message: Söylenecek mesaj.
            voice: Ses.
            record: Kayıt yap.

        Returns:
            Arama bilgisi.
        """
        # 1) Arama başlat
        call = self.initiator.initiate_call(
            callee=callee,
        )
        call_id = call["call_id"]

        # 2) Konuşma başlat
        conv = self.conversation.start_conversation(
            call_id=call_id,
            participants=["system", callee],
        )

        # 3) TTS ile mesaj sentezle
        synthesis = self.tts.synthesize(
            message, voice=voice,
        )

        # 4) Kayıt başlat
        recording = None
        if record:
            recording = self.recorder.start_recording(
                call_id=call_id,
                consent_status="granted",
            )

        self._stats["total_calls"] += 1
        self._stats["outbound_calls"] += 1

        return {
            "call_id": call_id,
            "conversation_id": conv[
                "conversation_id"
            ],
            "synthesis_id": synthesis[
                "synthesis_id"
            ],
            "recording_id": (
                recording["recording_id"]
                if recording
                and "recording_id" in recording
                else None
            ),
            "status": "active",
        }

    def handle_inbound(
        self,
        caller: str,
        audio_data: str | None = None,
    ) -> dict[str, Any]:
        """Gelen arama yönetir.

        Args:
            caller: Arayan.
            audio_data: Ses verisi.

        Returns:
            Arama bilgisi.
        """
        # 1) Arama kaydı
        call = self.initiator.initiate_call(
            callee="system",
            caller=caller,
        )
        call["direction"] = "inbound"
        call_id = call["call_id"]

        # 2) Konuşma başlat
        conv = self.conversation.start_conversation(
            call_id=call_id,
            participants=[caller, "system"],
        )

        # 3) STT
        transcription = None
        if audio_data:
            transcription = self.stt.transcribe(
                audio_data, call_id=call_id,
            )

            # 4) Aciliyet kontrolü
            urgency_result = (
                self.urgency.classify(
                    transcription.get("text", ""),
                )
            )
        else:
            urgency_result = None

        self._stats["total_calls"] += 1
        self._stats["inbound_calls"] += 1

        return {
            "call_id": call_id,
            "conversation_id": conv[
                "conversation_id"
            ],
            "transcription": transcription,
            "urgency": urgency_result,
            "status": "active",
        }

    def process_speech(
        self,
        call_id: str,
        audio_data: str,
    ) -> dict[str, Any]:
        """Konuşma işler.

        Args:
            call_id: Arama ID.
            audio_data: Ses verisi.

        Returns:
            İşleme bilgisi.
        """
        # STT
        transcription = self.stt.transcribe(
            audio_data, call_id=call_id,
        )
        text = transcription.get("text", "")

        # Aciliyet kontrolü
        urgency_result = self.urgency.classify(
            text,
        )

        return {
            "call_id": call_id,
            "text": text,
            "confidence": transcription.get(
                "confidence", 0,
            ),
            "urgency": urgency_result["urgency"],
            "is_emergency": urgency_result.get(
                "is_emergency", False,
            ),
        }

    def respond(
        self,
        call_id: str,
        conversation_id: str,
        response_text: str,
        voice: str | None = None,
    ) -> dict[str, Any]:
        """Yanıt verir.

        Args:
            call_id: Arama ID.
            conversation_id: Konuşma ID.
            response_text: Yanıt metni.
            voice: Ses.

        Returns:
            Yanıt bilgisi.
        """
        # TTS ile sentezle
        synthesis = self.tts.synthesize(
            response_text, voice=voice,
        )

        # Konuşmaya sıra ekle
        turn = self.conversation.add_turn(
            conversation_id,
            speaker="system",
            text=response_text,
        )

        return {
            "call_id": call_id,
            "synthesis_id": synthesis[
                "synthesis_id"
            ],
            "turn": turn,
            "response": response_text,
        }

    def end_call(
        self,
        call_id: str,
        conversation_id: str | None = None,
        duration: int = 0,
    ) -> dict[str, Any]:
        """Aramayı bitirir.

        Args:
            call_id: Arama ID.
            conversation_id: Konuşma ID.
            duration: Süre (saniye).

        Returns:
            Bitiş bilgisi.
        """
        # Aramayı tamamla
        self.initiator.complete_call(
            call_id, duration,
        )

        # Konuşmayı bitir
        conv_result = None
        if conversation_id:
            conv_result = (
                self.conversation.end_conversation(
                    conversation_id,
                )
            )

        # Aktif kayıtları durdur
        for rec in self.recorder.get_recordings(
            call_id=call_id,
        ):
            if rec["status"] == "recording":
                self.recorder.stop_recording(
                    rec["recording_id"],
                    duration,
                )

        return {
            "call_id": call_id,
            "status": "completed",
            "duration": duration,
            "conversation": conv_result,
        }

    def get_analytics(self) -> dict[str, Any]:
        """Analitik raporu.

        Returns:
            Rapor.
        """
        return {
            "total_calls": self._stats[
                "total_calls"
            ],
            "inbound_calls": self._stats[
                "inbound_calls"
            ],
            "outbound_calls": self._stats[
                "outbound_calls"
            ],
            "transcriptions": (
                self.stt.transcription_count
            ),
            "syntheses": (
                self.tts.synthesis_count
            ),
            "conversations": (
                self.conversation
                .conversation_count
            ),
            "recordings": (
                self.recorder.recording_count
            ),
            "authentications": (
                self.authenticator
                .verification_count
            ),
            "scheduled_calls": (
                self.scheduler.schedule_count
            ),
            "urgency_classifications": (
                self.urgency
                .classification_count
            ),
        }

    def get_status(self) -> dict[str, Any]:
        """Durum bilgisi.

        Returns:
            Durum.
        """
        return {
            "total_calls": self._stats[
                "total_calls"
            ],
            "active_calls": (
                self.initiator.active_call_count
            ),
            "active_conversations": (
                self.conversation
                .active_conversation_count
            ),
            "active_recordings": (
                self.recorder
                .active_recording_count
            ),
        }

    def get_quality_metrics(
        self,
    ) -> dict[str, Any]:
        """Kalite metrikleri getirir.

        Returns:
            Kalite bilgisi.
        """
        total = self._stats["total_calls"]
        completed = (
            self.initiator._stats[
                "calls_completed"
            ]
        )
        failed = self.initiator._stats[
            "calls_failed"
        ]

        success_rate = (
            round(completed / total, 3)
            if total > 0
            else 0.0
        )

        return {
            "total_calls": total,
            "completed": completed,
            "failed": failed,
            "success_rate": success_rate,
            "avg_stt_confidence": (
                self.stt._stats["avg_confidence"]
            ),
        }

    @property
    def total_calls(self) -> int:
        """Toplam arama sayısı."""
        return self._stats["total_calls"]
