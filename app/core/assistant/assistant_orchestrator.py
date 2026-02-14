"""ATLAS Asistan Orkestratoru modulu.

Tam asistan deneyimi, tum sistemlerin
entegrasyonu, kesintisiz etkilesim,
surekli ogrenme ve kisilik tutarliligi.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from app.models.assistant import (
    AssistantSnapshot,
    ChannelType,
    IntentCategory,
    ProactiveType,
)

from app.core.assistant.context_builder import ContextBuilder
from app.core.assistant.conversation_memory import ConversationMemory
from app.core.assistant.intent_predictor import IntentPredictor
from app.core.assistant.multi_channel_handler import MultiChannelHandler
from app.core.assistant.preference_learner import PreferenceLearner
from app.core.assistant.proactive_helper import ProactiveHelper
from app.core.assistant.smart_responder import SmartResponder
from app.core.assistant.task_inferrer import TaskInferrer

logger = logging.getLogger(__name__)


class AssistantOrchestrator:
    """Asistan orkestratoru.

    Tum asistan alt sistemlerini
    birlestiren merkezi kontrol noktasi.

    Attributes:
        _context: Baglam olusturucu.
        _predictor: Niyet tahmincisi.
        _responder: Akilli yanitlayici.
        _inferrer: Gorev cikarici.
        _learner: Tercih ogrenici.
        _helper: Proaktif yardimci.
        _memory: Konusma hafizasi.
        _channels: Coklu kanal yoneticisi.
    """

    def __init__(
        self,
        context_window: int = 50,
        learning_enabled: bool = True,
        proactive_mode: bool = True,
        multi_channel: bool = True,
    ) -> None:
        """Asistan orkestratoru baslatir.

        Args:
            context_window: Baglam penceresi.
            learning_enabled: Ogrenme aktif mi.
            proactive_mode: Proaktif mod aktif mi.
            multi_channel: Coklu kanal aktif mi.
        """
        self._context = ContextBuilder(context_window=context_window)
        self._predictor = IntentPredictor()
        self._responder = SmartResponder()
        self._inferrer = TaskInferrer()
        self._learner = PreferenceLearner()
        self._helper = ProactiveHelper()
        self._memory = ConversationMemory()
        self._channels = MultiChannelHandler()

        self._learning_enabled = learning_enabled
        self._proactive_mode = proactive_mode
        self._multi_channel = multi_channel
        self._started_at = datetime.now(timezone.utc)
        self._interaction_count = 0

        logger.info(
            "AssistantOrchestrator baslatildi "
            "(learning=%s, proactive=%s, multi_channel=%s)",
            learning_enabled, proactive_mode, multi_channel,
        )

    def handle_message(
        self,
        message: str,
        user_id: str = "default",
        channel: ChannelType = ChannelType.TELEGRAM,
    ) -> dict[str, Any]:
        """Mesaji isle.

        Args:
            message: Kullanici mesaji.
            user_id: Kullanici ID.
            channel: Kanal.

        Returns:
            Islem sonucu.
        """
        self._interaction_count += 1

        # 1. Baglam olustur
        self._context.add_conversation_turn("user", message)
        full_context = self._context.build_full_context()

        # 2. Konusma hafizasina ekle
        entry = self._memory.add_entry(
            role="user",
            content=message,
            channel=channel,
        )

        # 3. Gorev cikar
        task_info = self._inferrer.detect_implicit_task(
            message, full_context,
        )

        # 4. Niyet kaydet
        action_name = (
            task_info["tasks"][0]["type"]
            if task_info["tasks"]
            else "general"
        )
        self._predictor.record_action(action_name)

        # 5. Yanit olustur
        response = self._responder.generate_response(
            content=f"Mesajiniz alindi: {message}",
            context=full_context,
            channel=channel,
        )

        # 6. Tercih ogren
        if self._learning_enabled:
            self._learner.observe_interaction(
                "message", {"user_id": user_id, "channel": channel.value},
            )

        # 7. Yaniti kaydet
        self._context.add_conversation_turn(
            "assistant", response.content,
        )
        self._memory.add_entry(
            role="assistant",
            content=response.content,
            channel=channel,
        )

        return {
            "response": response.content,
            "response_id": response.response_id,
            "tasks_detected": task_info["tasks_found"],
            "channel": channel.value,
            "interaction": self._interaction_count,
        }

    def predict_next_intent(
        self,
        current_action: str,
    ) -> dict[str, Any]:
        """Sonraki niyeti tahmin eder.

        Args:
            current_action: Mevcut aksiyon.

        Returns:
            Tahmin sonucu.
        """
        prediction = self._predictor.predict_next(current_action)

        return {
            "predicted_action": prediction.predicted_action,
            "confidence": prediction.confidence,
            "category": prediction.category.value,
            "prediction_id": prediction.prediction_id,
        }

    def get_proactive_suggestions(
        self,
        context: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Proaktif oneriler getirir.

        Args:
            context: Baglam.

        Returns:
            Oneri listesi.
        """
        if not self._proactive_mode:
            return []

        suggestions: list[dict[str, Any]] = []

        # Kural tabli oneriler
        if context:
            actions = self._helper.evaluate_rules(context)
            for a in actions:
                suggestions.append({
                    "type": a.action_type.value,
                    "title": a.title,
                    "description": a.description,
                    "urgency": a.urgency,
                })

        # Teslim tarihi kontrol
        deadlines = self._helper.check_deadlines()
        for dl in deadlines:
            suggestions.append({
                "type": "deadline",
                "title": dl["title"],
                "remaining_hours": dl["remaining_hours"],
                "urgency": 0.9,
            })

        # Hatirlatma kontrol
        reminders = self._helper.check_reminders()
        for r in reminders:
            suggestions.append({
                "type": "reminder",
                "title": r["title"],
                "urgency": 0.6,
            })

        return suggestions

    def learn_preference(
        self,
        key: str,
        value: Any,
        preference_type: str = "communication",
    ) -> dict[str, Any]:
        """Tercihi ogrenilir.

        Args:
            key: Tercih anahtari.
            value: Deger.
            preference_type: Tercih turu.

        Returns:
            Ogrenme sonucu.
        """
        if not self._learning_enabled:
            return {"learned": False, "reason": "Ogrenme devre disi"}

        from app.models.assistant import PreferenceType
        try:
            ptype = PreferenceType(preference_type)
        except ValueError:
            ptype = PreferenceType.COMMUNICATION

        pref = self._learner.learn_from_feedback(key, ptype, value)

        return {
            "learned": True,
            "key": key,
            "confidence": pref.confidence,
            "total_preferences": self._learner.preference_count,
        }

    def recall_conversation(
        self,
        topic: str,
    ) -> dict[str, Any]:
        """Konusmayi hatirlattir.

        Args:
            topic: Konu.

        Returns:
            Hatirlatma sonucu.
        """
        return self._memory.recall_topic(topic)

    def search_history(
        self,
        query: str,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Gecmisi arar.

        Args:
            query: Arama metni.
            limit: Maks sonuc.

        Returns:
            Arama sonuclari.
        """
        entries = self._memory.search_entries(query, limit)
        return [
            {
                "entry_id": e.entry_id,
                "role": e.role,
                "content": e.content,
                "topic": e.topic,
                "channel": e.channel.value,
            }
            for e in entries
        ]

    def send_to_channel(
        self,
        content: str,
        channel: ChannelType,
    ) -> dict[str, Any]:
        """Kanala mesaj gonderir.

        Args:
            content: Icerik.
            channel: Hedef kanal.

        Returns:
            Gonderim sonucu.
        """
        if not self._multi_channel:
            return {"sent": False, "reason": "Coklu kanal devre disi"}

        return self._channels.send_message(content, channel)

    def broadcast_message(
        self,
        content: str,
    ) -> list[dict[str, Any]]:
        """Tum kanallara yayin yapar.

        Args:
            content: Icerik.

        Returns:
            Gonderim sonuclari.
        """
        if not self._multi_channel:
            return []

        return self._channels.broadcast(content)

    def get_snapshot(self) -> AssistantSnapshot:
        """Asistan goruntusu getirir.

        Returns:
            AssistantSnapshot nesnesi.
        """
        uptime = (
            datetime.now(timezone.utc) - self._started_at
        ).total_seconds()

        return AssistantSnapshot(
            total_conversations=self._memory.entry_count,
            total_predictions=self._predictor.prediction_count,
            prediction_accuracy=self._predictor.accuracy,
            preferences_learned=self._learner.preference_count,
            proactive_actions=self._helper.action_count,
            active_channels=self._channels.active_channel_count,
            context_items=self._context.context_count,
            uptime_seconds=round(uptime, 2),
        )

    # Alt sistem erisimi
    @property
    def context(self) -> ContextBuilder:
        """Baglam olusturucu."""
        return self._context

    @property
    def predictor(self) -> IntentPredictor:
        """Niyet tahmincisi."""
        return self._predictor

    @property
    def responder(self) -> SmartResponder:
        """Akilli yanitlayici."""
        return self._responder

    @property
    def inferrer(self) -> TaskInferrer:
        """Gorev cikarici."""
        return self._inferrer

    @property
    def learner(self) -> PreferenceLearner:
        """Tercih ogrenici."""
        return self._learner

    @property
    def helper(self) -> ProactiveHelper:
        """Proaktif yardimci."""
        return self._helper

    @property
    def memory(self) -> ConversationMemory:
        """Konusma hafizasi."""
        return self._memory

    @property
    def channels(self) -> MultiChannelHandler:
        """Coklu kanal yoneticisi."""
        return self._channels

    @property
    def interaction_count(self) -> int:
        """Etkilesim sayisi."""
        return self._interaction_count
