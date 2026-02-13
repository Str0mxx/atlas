"""ATLAS Duygusal Zeka Orkestratoru modulu.

Tum EQ bilesenlerini entegre eder: gercek zamanli
duygu isleme, yanit zenginlestirme, geri bildirim
dongusu ve surekli ogrenme.
"""

import logging
import time
from typing import Any

from app.core.emotional.communication_styler import CommunicationStyler
from app.core.emotional.conflict_resolver import ConflictResolver
from app.core.emotional.emotional_memory import EmotionalMemoryManager
from app.core.emotional.empathy_engine import EmpathyEngine
from app.core.emotional.mood_tracker import MoodTracker
from app.core.emotional.motivation_engine import MotivationEngine
from app.core.emotional.personality_adapter import PersonalityAdapter
from app.core.emotional.sentiment_analyzer import SentimentAnalyzer
from app.models.emotional import (
    CommunicationTone,
    EQAnalysis,
    Sentiment,
)

logger = logging.getLogger(__name__)


class EQOrchestrator:
    """Duygusal zeka orkestratoru.

    Tum EQ bilesenlerini koordine eder ve
    gercek zamanli duygusal isleme yapar.

    Attributes:
        _analyzer: Duygu analizcisi.
        _empathy: Empati motoru.
        _mood: Ruh hali takipci.
        _styler: Iletisim stilci.
        _conflict: Catisma cozucu.
        _motivation: Motivasyon motoru.
        _personality: Kisilik adaptoru.
        _memory: Duygusal hafiza.
    """

    def __init__(
        self,
        empathy_level: str = "medium",
        humor_enabled: bool = True,
        formality_default: str = "neutral",
    ) -> None:
        """EQ orkestratörunu baslatir.

        Args:
            empathy_level: Empati seviyesi.
            humor_enabled: Mizah aktif mi.
            formality_default: Varsayilan resmiyet.
        """
        self._analyzer = SentimentAnalyzer()
        self._empathy = EmpathyEngine(empathy_level=empathy_level)
        self._mood = MoodTracker()
        self._styler = CommunicationStyler(
            humor_enabled=humor_enabled,
            default_formality=formality_default,
        )
        self._conflict = ConflictResolver()
        self._motivation = MotivationEngine()
        self._personality = PersonalityAdapter()
        self._memory = EmotionalMemoryManager()

        self._analyses: list[EQAnalysis] = []

        logger.info(
            "EQOrchestrator baslatildi (empathy=%s, humor=%s)",
            empathy_level, humor_enabled,
        )

    def process(self, user_id: str, text: str, context: str = "") -> EQAnalysis:
        """Tam EQ pipeline'i calistirir.

        Args:
            user_id: Kullanici ID.
            text: Kullanici metni.
            context: Baglam.

        Returns:
            EQAnalysis nesnesi.
        """
        start = time.monotonic()

        # 1. Duygu analizi
        sentiment = self._analyzer.analyze(text, context)

        # 2. Empati durumu guncelle
        state = self._empathy.update_state(user_id, sentiment)

        # 3. Ruh hali kaydet
        self._mood.record_from_sentiment(user_id, sentiment, context)

        # 4. Kisilik ogren
        formality = self._styler.detect_formality(text)
        self._personality.learn_from_interaction(user_id, text, formality=formality)

        # 5. Stil onerisi
        self._styler.update_profile(user_id, text)

        # 6. Catisma degerlendirmesi
        conflict_level = self._conflict.assess_conflict(user_id, state)

        if sentiment.sentiment == Sentiment.NEGATIVE:
            self._conflict.track_negative(user_id)
        else:
            self._conflict.reset_negative(user_id)

        # 7. Uygun ton
        recommended_tone = self._empathy.get_appropriate_tone(user_id)

        # 8. Motivasyon gerekli mi?
        motivation_needed = self._mood.needs_proactive_support(user_id)

        # 9. Yanit zenginlestir
        enhanced = self._enhance_response(user_id, sentiment.sentiment, recommended_tone, motivation_needed)

        # 10. Hafizaya kaydet
        self._memory.record_interaction(
            user_id=user_id,
            sentiment=sentiment.sentiment,
            emotion=sentiment.emotion,
            event_type="conversation",
            summary=text[:100],
        )

        elapsed = (time.monotonic() - start) * 1000

        analysis = EQAnalysis(
            user_id=user_id,
            input_text=text,
            sentiment=sentiment,
            recommended_tone=recommended_tone,
            conflict_level=conflict_level,
            motivation_needed=motivation_needed,
            enhanced_response=enhanced,
            processing_ms=elapsed,
        )

        self._analyses.append(analysis)
        return analysis

    def get_user_insights(self, user_id: str) -> dict[str, Any]:
        """Kullanici icgorulerini getirir.

        Args:
            user_id: Kullanici ID.

        Returns:
            Icgoru sozlugu.
        """
        mood_patterns = self._mood.analyze_patterns(user_id)
        personality = self._personality.get_adaptation_summary(user_id)
        memory = self._memory.get_user_summary(user_id)
        relationship = self._memory.get_relationship_quality(user_id)

        return {
            "mood": mood_patterns,
            "personality": personality,
            "memory": memory,
            "relationship_quality": relationship.value,
            "needs_support": self._mood.needs_proactive_support(user_id),
        }

    def _enhance_response(
        self,
        user_id: str,
        sentiment: Sentiment,
        tone: CommunicationTone,
        needs_motivation: bool,
    ) -> str:
        """Yaniti zenginlestirir."""
        parts: list[str] = []

        # Catisma varsa de-eskalasyon
        state = self._empathy.get_state(user_id)
        if state and self._conflict.should_escalate_to_human(user_id, state):
            parts.append("[ESKALASYON: Insan desteği gerekli]")
        elif state and state.frustration_level > 0.5:
            conflict_level = self._conflict.assess_conflict(user_id, state)
            msg = self._conflict.get_deescalation_message(conflict_level)
            if msg:
                parts.append(msg)

        # Motivasyon
        if needs_motivation and state:
            motivation = self._motivation.get_appropriate_motivation(user_id, state)
            if motivation:
                parts.append(motivation.message)

        # Kutlama
        last_sentiment = self._analyzer.history[-1] if self._analyzer.history else None
        if last_sentiment and self._empathy.detect_celebration(last_sentiment):
            parts.append("Harika!")

        # Ton ipucu
        if tone == CommunicationTone.EMPATHETIC:
            parts.append("[Ton: empatik]")
        elif tone == CommunicationTone.ENTHUSIASTIC:
            parts.append("[Ton: coskulu]")

        return " ".join(parts) if parts else ""

    @property
    def analyzer(self) -> SentimentAnalyzer:
        """Duygu analizcisi."""
        return self._analyzer

    @property
    def empathy(self) -> EmpathyEngine:
        """Empati motoru."""
        return self._empathy

    @property
    def mood(self) -> MoodTracker:
        """Ruh hali takipci."""
        return self._mood

    @property
    def styler(self) -> CommunicationStyler:
        """Iletisim stilci."""
        return self._styler

    @property
    def conflict(self) -> ConflictResolver:
        """Catisma cozucu."""
        return self._conflict

    @property
    def motivation(self) -> MotivationEngine:
        """Motivasyon motoru."""
        return self._motivation

    @property
    def personality(self) -> PersonalityAdapter:
        """Kisilik adaptoru."""
        return self._personality

    @property
    def memory(self) -> EmotionalMemoryManager:
        """Duygusal hafiza."""
        return self._memory

    @property
    def analysis_count(self) -> int:
        """Analiz sayisi."""
        return len(self._analyses)
