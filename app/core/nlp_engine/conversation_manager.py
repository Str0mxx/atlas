"""ATLAS Diyalog Yoneticisi modulu.

Baglam surekliligi, referans cozumleme, konu takibi,
hafiza entegrasyonu ve kisilik tutarliligi.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from app.models.nlp_engine import (
    ConversationContext,
    ConversationState,
    DialogueTurn,
    Intent,
    Topic,
    TopicStatus,
)

logger = logging.getLogger(__name__)


class ConversationManager:
    """Diyalog yoneticisi.

    Konusma baglamini surdurir, referanslari cozer,
    konulari takip eder, hafiza ile entegre olur
    ve tutarli bir kisilik saglar.

    Attributes:
        _context: Konusma baglami.
        _max_turns: Maksimum hatirdanan tur sayisi.
        _personality: Kisilik ayarlari.
    """

    def __init__(self, max_turns: int = 50, personality: dict[str, str] | None = None) -> None:
        """Diyalog yoneticisini baslatir.

        Args:
            max_turns: Maksimum hatirdanan tur sayisi.
            personality: Kisilik ayarlari (tone, style, vb).
        """
        self._context = ConversationContext()
        self._max_turns = max_turns
        self._personality = personality or {
            "tone": "professional",
            "style": "concise",
            "language": "tr",
        }

        logger.info(
            "ConversationManager baslatildi (max_turns=%d, personality=%s)",
            max_turns, self._personality.get("tone", "default"),
        )

    def add_user_turn(self, content: str, intent: Intent | None = None) -> DialogueTurn:
        """Kullanici turu ekler.

        Args:
            content: Kullanici mesaji.
            intent: Analiz edilmis niyet.

        Returns:
            Olusturulan DialogueTurn nesnesi.
        """
        turn = DialogueTurn(role="user", content=content, intent=intent)
        self._context.turns.append(turn)
        self._context.state = ConversationState.LISTENING

        # Tur limiti kontrolu
        if len(self._context.turns) > self._max_turns:
            self._context.turns = self._context.turns[-self._max_turns:]

        # Referanslari guncelle
        self._update_references(content)

        # Konuyu guncelle
        self._update_topic(content, turn.id)

        logger.info("Kullanici turu eklendi: %s", content[:30])
        return turn

    def add_system_turn(self, content: str) -> DialogueTurn:
        """Sistem turu ekler.

        Args:
            content: Sistem yaniti.

        Returns:
            Olusturulan DialogueTurn nesnesi.
        """
        turn = DialogueTurn(role="system", content=content)
        self._context.turns.append(turn)
        self._context.state = ConversationState.REPORTING

        if len(self._context.turns) > self._max_turns:
            self._context.turns = self._context.turns[-self._max_turns:]

        # Aktif konuya ekle
        if self._context.active_topic_id:
            for topic in self._context.topics:
                if topic.id == self._context.active_topic_id:
                    topic.turn_ids.append(turn.id)
                    break

        return turn

    def resolve_reference(self, text: str) -> str:
        """Referanslari cozer.

        'o', 'bu', 'onceki' gibi zamirleri gercek degerleri
        ile degistirir.

        Args:
            text: Giris metni.

        Returns:
            Referanslari cozulmus metin.
        """
        resolved = text
        for short_ref, full_ref in self._context.references.items():
            # Kelime sinirlarinda degistir
            import re
            pattern = rf"\b{re.escape(short_ref)}\b"
            resolved = re.sub(pattern, full_ref, resolved, flags=re.IGNORECASE)

        return resolved

    def _update_references(self, text: str) -> None:
        """Referans haritasini gunceller.

        Metindeki onemli kelimeleri referans olarak kaydeder.

        Args:
            text: Giris metni.
        """
        words = text.split()
        # Son bahsedilen varlik isimlerini kaydet
        significant_words = [w for w in words if len(w) > 3 and w[0].isupper()]
        if significant_words:
            last_entity = significant_words[-1]
            self._context.references["o"] = last_entity
            self._context.references["bu"] = last_entity
            self._context.references["it"] = last_entity
            self._context.references["this"] = last_entity

    def start_topic(self, name: str, context: dict[str, Any] | None = None) -> Topic:
        """Yeni konu baslatir.

        Mevcut aktif konuyu duraklattir ve yenisini aktif yapar.

        Args:
            name: Konu adi.
            context: Konu baglami.

        Returns:
            Olusturulan Topic nesnesi.
        """
        # Mevcut konuyu duraklat
        if self._context.active_topic_id:
            for topic in self._context.topics:
                if topic.id == self._context.active_topic_id and topic.status == TopicStatus.ACTIVE:
                    topic.status = TopicStatus.PAUSED

        new_topic = Topic(
            name=name,
            context=context or {},
        )
        self._context.topics.append(new_topic)
        self._context.active_topic_id = new_topic.id

        logger.info("Yeni konu baslatildi: %s", name)
        return new_topic

    def complete_topic(self, topic_id: str | None = None) -> bool:
        """Konuyu tamamlar.

        Args:
            topic_id: Konu ID. None ise aktif konuyu tamamlar.

        Returns:
            Basarili mi.
        """
        target_id = topic_id or self._context.active_topic_id
        if not target_id:
            return False

        for topic in self._context.topics:
            if topic.id == target_id:
                topic.status = TopicStatus.COMPLETED
                topic.ended_at = datetime.now(timezone.utc)

                # Aktif konu tamamlandiysa duraklayanI aktive et
                if target_id == self._context.active_topic_id:
                    self._context.active_topic_id = None
                    for t in reversed(self._context.topics):
                        if t.status == TopicStatus.PAUSED:
                            t.status = TopicStatus.ACTIVE
                            self._context.active_topic_id = t.id
                            break

                logger.info("Konu tamamlandi: %s", topic.name)
                return True

        return False

    def _update_topic(self, content: str, turn_id: str) -> None:
        """Konu takibini gunceller.

        Args:
            content: Mesaj icerigi.
            turn_id: Tur ID.
        """
        if self._context.active_topic_id:
            for topic in self._context.topics:
                if topic.id == self._context.active_topic_id:
                    topic.turn_ids.append(turn_id)
                    return

        # Aktif konu yoksa yeni konu olustur
        topic_name = content[:30] if content else "Genel"
        self.start_topic(topic_name)

    def get_recent_context(self, n: int = 5) -> list[DialogueTurn]:
        """Son n turu getirir.

        Args:
            n: Tur sayisi.

        Returns:
            Son turlar.
        """
        return self._context.turns[-n:]

    def add_memory_key(self, key: str) -> None:
        """Hafiza anahtari ekler.

        Args:
            key: Hafiza anahtari.
        """
        if key not in self._context.memory_keys:
            self._context.memory_keys.append(key)

    def get_active_topic(self) -> Topic | None:
        """Aktif konuyu getirir.

        Returns:
            Aktif Topic nesnesi veya None.
        """
        if not self._context.active_topic_id:
            return None
        for topic in self._context.topics:
            if topic.id == self._context.active_topic_id:
                return topic
        return None

    def set_state(self, state: ConversationState) -> None:
        """Diyalog durumunu ayarlar.

        Args:
            state: Yeni durum.
        """
        self._context.state = state

    def reset(self) -> None:
        """Konusma baglamini sifirlar."""
        self._context = ConversationContext()
        logger.info("Konusma baglami sifirlandi")

    @property
    def state(self) -> ConversationState:
        """Diyalog durumu."""
        return self._context.state

    @property
    def turn_count(self) -> int:
        """Toplam tur sayisi."""
        return len(self._context.turns)

    @property
    def topic_count(self) -> int:
        """Toplam konu sayisi."""
        return len(self._context.topics)

    @property
    def context(self) -> ConversationContext:
        """Konusma baglami."""
        return self._context

    @property
    def personality(self) -> dict[str, str]:
        """Kisilik ayarlari."""
        return dict(self._personality)
