"""ATLAS Sesli Konuşma Yöneticisi modülü.

Sıra yönetimi, bağlam takibi,
kesinti yönetimi, sessizlik tespiti,
konuşma akışı.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class VoiceConversationManager:
    """Sesli konuşma yöneticisi.

    Sesli konuşma akışını yönetir.

    Attributes:
        _conversations: Konuşma kayıtları.
        _turns: Sıra kayıtları.
    """

    def __init__(
        self,
        silence_threshold: float = 3.0,
        max_turn_duration: float = 30.0,
    ) -> None:
        """Yöneticiyi başlatır.

        Args:
            silence_threshold: Sessizlik eşiği (sn).
            max_turn_duration: Maks sıra süresi (sn).
        """
        self._conversations: dict[
            str, dict[str, Any]
        ] = {}
        self._turns: list[dict[str, Any]] = []
        self._silence_threshold = silence_threshold
        self._max_turn_duration = max_turn_duration
        self._counter = 0
        self._stats = {
            "conversations": 0,
            "turns": 0,
            "interruptions": 0,
        }

        logger.info(
            "VoiceConversationManager "
            "baslatildi",
        )

    def start_conversation(
        self,
        call_id: str,
        participants: list[str] | None = None,
    ) -> dict[str, Any]:
        """Konuşma başlatır.

        Args:
            call_id: Arama ID.
            participants: Katılımcılar.

        Returns:
            Konuşma bilgisi.
        """
        self._counter += 1
        conv_id = f"conv_{self._counter}"

        conversation = {
            "conversation_id": conv_id,
            "call_id": call_id,
            "participants": participants or [],
            "status": "active",
            "current_speaker": None,
            "turn_count": 0,
            "context": {},
            "started_at": time.time(),
            "ended_at": None,
        }
        self._conversations[conv_id] = (
            conversation
        )
        self._stats["conversations"] += 1

        return conversation

    def end_conversation(
        self,
        conversation_id: str,
    ) -> dict[str, Any]:
        """Konuşma bitirir.

        Args:
            conversation_id: Konuşma ID.

        Returns:
            Bitiş bilgisi.
        """
        conv = self._conversations.get(
            conversation_id,
        )
        if not conv:
            return {
                "error": "conversation_not_found",
            }

        conv["status"] = "ended"
        conv["ended_at"] = time.time()
        duration = (
            conv["ended_at"]
            - conv["started_at"]
        )

        return {
            "conversation_id": conversation_id,
            "status": "ended",
            "duration": round(duration, 2),
            "total_turns": conv["turn_count"],
        }

    def add_turn(
        self,
        conversation_id: str,
        speaker: str,
        text: str,
        turn_type: str = "statement",
    ) -> dict[str, Any]:
        """Sıra ekler.

        Args:
            conversation_id: Konuşma ID.
            speaker: Konuşmacı.
            text: Metin.
            turn_type: Sıra tipi.

        Returns:
            Sıra bilgisi.
        """
        conv = self._conversations.get(
            conversation_id,
        )
        if not conv:
            return {
                "error": "conversation_not_found",
            }

        turn = {
            "conversation_id": conversation_id,
            "speaker": speaker,
            "text": text,
            "turn_type": turn_type,
            "turn_number": conv["turn_count"] + 1,
            "timestamp": time.time(),
        }
        self._turns.append(turn)
        conv["turn_count"] += 1
        conv["current_speaker"] = speaker
        self._stats["turns"] += 1

        return turn

    def handle_interruption(
        self,
        conversation_id: str,
        interrupter: str,
        text: str = "",
    ) -> dict[str, Any]:
        """Kesinti yönetir.

        Args:
            conversation_id: Konuşma ID.
            interrupter: Kesen kişi.
            text: Kesinti metni.

        Returns:
            Kesinti bilgisi.
        """
        conv = self._conversations.get(
            conversation_id,
        )
        if not conv:
            return {
                "error": "conversation_not_found",
            }

        prev_speaker = conv["current_speaker"]
        turn = self.add_turn(
            conversation_id,
            interrupter,
            text,
            turn_type="interruption",
        )
        self._stats["interruptions"] += 1

        return {
            "interruption": True,
            "previous_speaker": prev_speaker,
            "interrupter": interrupter,
            "turn": turn,
        }

    def detect_silence(
        self,
        conversation_id: str,
        duration_seconds: float,
    ) -> dict[str, Any]:
        """Sessizlik tespit eder.

        Args:
            conversation_id: Konuşma ID.
            duration_seconds: Sessizlik süresi.

        Returns:
            Tespit bilgisi.
        """
        conv = self._conversations.get(
            conversation_id,
        )
        if not conv:
            return {
                "error": "conversation_not_found",
            }

        is_long_silence = (
            duration_seconds
            >= self._silence_threshold
        )

        action = "continue"
        if is_long_silence:
            action = "prompt_user"

        return {
            "conversation_id": conversation_id,
            "silence_seconds": duration_seconds,
            "is_long_silence": is_long_silence,
            "action": action,
            "threshold": self._silence_threshold,
        }

    def update_context(
        self,
        conversation_id: str,
        key: str,
        value: Any,
    ) -> dict[str, Any]:
        """Bağlam günceller.

        Args:
            conversation_id: Konuşma ID.
            key: Anahtar.
            value: Değer.

        Returns:
            Güncelleme bilgisi.
        """
        conv = self._conversations.get(
            conversation_id,
        )
        if not conv:
            return {
                "error": "conversation_not_found",
            }

        conv["context"][key] = value

        return {
            "conversation_id": conversation_id,
            "key": key,
            "updated": True,
        }

    def get_conversation_flow(
        self,
        conversation_id: str,
    ) -> dict[str, Any]:
        """Konuşma akışını getirir.

        Args:
            conversation_id: Konuşma ID.

        Returns:
            Akış bilgisi.
        """
        conv = self._conversations.get(
            conversation_id,
        )
        if not conv:
            return {
                "error": "conversation_not_found",
            }

        turns = [
            t for t in self._turns
            if t["conversation_id"]
            == conversation_id
        ]

        return {
            "conversation_id": conversation_id,
            "turns": turns,
            "turn_count": len(turns),
            "participants": conv["participants"],
            "context": conv["context"],
        }

    def get_conversation(
        self,
        conversation_id: str,
    ) -> dict[str, Any]:
        """Konuşma detayı getirir.

        Args:
            conversation_id: Konuşma ID.

        Returns:
            Konuşma bilgisi.
        """
        conv = self._conversations.get(
            conversation_id,
        )
        if not conv:
            return {
                "error": "conversation_not_found",
            }
        return dict(conv)

    @property
    def conversation_count(self) -> int:
        """Konuşma sayısı."""
        return self._stats["conversations"]

    @property
    def turn_count(self) -> int:
        """Sıra sayısı."""
        return self._stats["turns"]

    @property
    def active_conversation_count(self) -> int:
        """Aktif konuşma sayısı."""
        return sum(
            1 for c in self._conversations.values()
            if c["status"] == "active"
        )
