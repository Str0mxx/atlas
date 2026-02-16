"""
Speaker Conversation Context - Konuşma context ve tercih yönetimi modülü.

Bu modül session yönetimi, konuşma geçmişi ve kullanıcı tercihi öğrenme
sağlar.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class SpeakerConversationContext:
    """Konuşma context ve tercih yönetim sınıfı."""

    def __init__(self) -> None:
        """SpeakerConversationContext başlatıcı."""
        self._sessions: dict[str, dict] = {}
        self._preferences: dict[str, dict] = {}
        self._stats = {"sessions_created": 0, "turns_processed": 0}
        logger.info("SpeakerConversationContext başlatıldı")

    @property
    def session_count(self) -> int:
        """Oluşturulan session sayısını döndürür."""
        return self._stats["sessions_created"]

    @property
    def turn_count(self) -> int:
        """İşlenen turn sayısını döndürür."""
        return self._stats["turns_processed"]

    def start_session(
        self,
        session_id: str,
        platform: str = "alexa",
        user_id: str = ""
    ) -> dict[str, Any]:
        """
        Yeni bir konuşma session'ı başlatır.

        Args:
            session_id: Session benzersiz kimliği
            platform: Platform (alexa, google, siri)
            user_id: Kullanıcı kimliği

        Returns:
            Session başlatma sonucu
        """
        self._sessions[session_id] = {
            "platform": platform,
            "user_id": user_id,
            "turns": 0,
            "history": [],
            "state": "active",
            "started_at": time.time()
        }

        self._stats["sessions_created"] += 1

        logger.info(
            f"Session başlatıldı: {session_id} ({platform}, "
            f"user: {user_id})"
        )

        return {
            "session_id": session_id,
            "platform": platform,
            "state": "active",
            "started": True
        }

    def add_turn(
        self,
        session_id: str,
        role: str = "user",
        text: str = ""
    ) -> dict[str, Any]:
        """
        Session'a yeni bir konuşma turn'ü ekler.

        Args:
            session_id: Session kimliği
            role: Konuşan rol (user/assistant)
            text: Konuşma metni

        Returns:
            Turn ekleme sonucu
        """
        if session_id not in self._sessions:
            logger.warning(f"Session bulunamadı: {session_id}")
            return {"found": False}

        session = self._sessions[session_id]
        session["turns"] += 1

        turn_entry = {
            "role": role,
            "text": text,
            "timestamp": time.time()
        }

        session["history"].append(turn_entry)
        self._stats["turns_processed"] += 1

        logger.debug(
            f"Turn eklendi: {session_id} (#{session['turns']}, "
            f"role: {role})"
        )

        return {
            "session_id": session_id,
            "role": role,
            "turn_number": session["turns"],
            "added": True
        }

    def get_context(self, session_id: str) -> dict[str, Any]:
        """
        Session context'ini getirir.

        Args:
            session_id: Session kimliği

        Returns:
            Context bilgileri
        """
        if session_id not in self._sessions:
            logger.warning(f"Session bulunamadı: {session_id}")
            return {"found": False}

        session = self._sessions[session_id]

        # Son 5 turn'ü döndür
        recent_history = session["history"][-5:]

        logger.debug(
            f"Context alındı: {session_id} ({session['turns']} turn)"
        )

        return {
            "session_id": session_id,
            "turns": session["turns"],
            "history": recent_history,
            "state": session["state"],
            "retrieved": True
        }

    def learn_preference(
        self,
        user_id: str,
        key: str,
        value: Any
    ) -> dict[str, Any]:
        """
        Kullanıcı tercihini öğrenir ve kaydeder.

        Args:
            user_id: Kullanıcı kimliği
            key: Tercih anahtarı
            value: Tercih değeri

        Returns:
            Tercih öğrenme sonucu
        """
        if user_id not in self._preferences:
            self._preferences[user_id] = {}

        self._preferences[user_id][key] = value

        logger.info(
            f"Tercih öğrenildi: {user_id} - {key} = {value}"
        )

        return {
            "user_id": user_id,
            "key": key,
            "value": value,
            "learned": True
        }

    def personalize(
        self,
        session_id: str,
        user_id: str
    ) -> dict[str, Any]:
        """
        Session'ı kullanıcı tercihlerine göre kişiselleştirir.

        Args:
            session_id: Session kimliği
            user_id: Kullanıcı kimliği

        Returns:
            Kişiselleştirme sonucu
        """
        if session_id not in self._sessions:
            logger.warning(f"Session bulunamadı: {session_id}")
            return {"found": False}

        prefs = self._preferences.get(user_id, {})

        logger.info(
            f"Session kişiselleştirildi: {session_id} "
            f"({len(prefs)} tercih uygulandı)"
        )

        return {
            "session_id": session_id,
            "user_id": user_id,
            "preferences_applied": len(prefs),
            "personalized": True
        }
