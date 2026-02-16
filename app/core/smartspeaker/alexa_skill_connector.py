"""
Alexa Skill Connector - Amazon Alexa entegrasyonu için skill ve intent yönetimi.

Bu modül Alexa skill kayıt, intent işleme ve session yönetimi sağlar.
"""

import logging
import time
from typing import Any, Optional

logger = logging.getLogger(__name__)


class AlexaSkillConnector:
    """Amazon Alexa skill ve intent yönetimi için connector sınıfı."""

    def __init__(self) -> None:
        """AlexaSkillConnector başlatıcı."""
        self._skills: dict[str, dict] = {}
        self._sessions: dict[str, dict] = {}
        self._counter: int = 0
        self._stats = {"skills_registered": 0, "intents_handled": 0}
        logger.info("AlexaSkillConnector başlatıldı")

    @property
    def skill_count(self) -> int:
        """Kayıtlı skill sayısını döndürür."""
        return self._stats["skills_registered"]

    @property
    def intent_count(self) -> int:
        """İşlenen intent sayısını döndürür."""
        return self._stats["intents_handled"]

    def register_skill(
        self,
        skill_id: str,
        name: str,
        intents: Optional[list] = None
    ) -> dict[str, Any]:
        """
        Yeni bir Alexa skill kaydeder.

        Args:
            skill_id: Skill benzersiz kimliği
            name: Skill adı
            intents: Desteklenen intent listesi

        Returns:
            Skill kayıt sonucu
        """
        if intents is None:
            intents = []

        self._skills[skill_id] = {
            "name": name,
            "intents": intents,
            "registered_at": time.time()
        }
        self._counter += 1
        self._stats["skills_registered"] += 1

        logger.info(
            f"Alexa skill kaydedildi: {skill_id} - {name} "
            f"({len(intents)} intent)"
        )

        return {
            "skill_id": skill_id,
            "name": name,
            "intents_count": len(intents),
            "registered": True
        }

    def handle_intent(
        self,
        skill_id: str,
        intent_name: str,
        slots: Optional[dict] = None
    ) -> dict[str, Any]:
        """
        Bir intent işler.

        Args:
            skill_id: Skill kimliği
            intent_name: Intent adı
            slots: Intent slot parametreleri

        Returns:
            Intent işleme sonucu
        """
        if skill_id not in self._skills:
            logger.warning(f"Skill bulunamadı: {skill_id}")
            return {"found": False}

        if slots is None:
            slots = {}

        self._stats["intents_handled"] += 1

        logger.info(
            f"Intent işlendi: {intent_name} (skill: {skill_id}, "
            f"{len(slots)} slot)"
        )

        return {
            "skill_id": skill_id,
            "intent_name": intent_name,
            "slots_processed": len(slots),
            "handled": True
        }

    def process_slots(self, slots: dict) -> dict[str, Any]:
        """
        Intent slot'larını işler.

        Args:
            slots: Slot dictionary'si

        Returns:
            İşlenmiş slot bilgileri
        """
        resolved = []
        for name, value in slots.items():
            resolved.append({
                "name": name,
                "value": value,
                "resolved": True
            })

        logger.debug(f"{len(slots)} slot işlendi")

        return {
            "slots_count": len(slots),
            "resolved": resolved,
            "processed": True
        }

    def build_response(
        self,
        speech_text: str,
        card_title: str = "",
        card_content: str = "",
        should_end: bool = True
    ) -> dict[str, Any]:
        """
        Alexa yanıtı oluşturur.

        Args:
            speech_text: Sesli yanıt metni
            card_title: Card başlığı (opsiyonel)
            card_content: Card içeriği (opsiyonel)
            should_end: Session sonlandırılsın mı

        Returns:
            Oluşturulan yanıt
        """
        card = None
        if card_title:
            card = {"title": card_title, "content": card_content}

        logger.debug(
            f"Alexa yanıtı oluşturuldu (card: {bool(card)}, "
            f"end: {should_end})"
        )

        return {
            "speech": speech_text,
            "card": card,
            "should_end_session": should_end,
            "built": True
        }

    def manage_session(
        self,
        session_id: str,
        action: str = "start",
        attributes: Optional[dict] = None
    ) -> dict[str, Any]:
        """
        Alexa session yönetimi.

        Args:
            session_id: Session kimliği
            action: İşlem tipi (start/end)
            attributes: Session özellikleri

        Returns:
            Session yönetim sonucu
        """
        active = False

        if action == "start":
            if attributes is None:
                attributes = {}
            self._sessions[session_id] = {
                "attributes": attributes,
                "started_at": time.time()
            }
            active = True
            logger.info(f"Alexa session başlatıldı: {session_id}")

        elif action == "end":
            if session_id in self._sessions:
                self._sessions.pop(session_id)
            logger.info(f"Alexa session sonlandırıldı: {session_id}")

        return {
            "session_id": session_id,
            "action": action,
            "active": active,
            "managed": True
        }
