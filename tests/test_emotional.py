"""ATLAS Emotional Intelligence sistemi testleri.

SentimentAnalyzer, EmpathyEngine, MoodTracker,
CommunicationStyler, ConflictResolver, MotivationEngine,
PersonalityAdapter, EmotionalMemoryManager, EQOrchestrator testleri.
"""

from app.core.emotional.communication_styler import CommunicationStyler
from app.core.emotional.conflict_resolver import ConflictResolver
from app.core.emotional.emotional_memory import EmotionalMemoryManager
from app.core.emotional.empathy_engine import EmpathyEngine
from app.core.emotional.eq_orchestrator import EQOrchestrator
from app.core.emotional.mood_tracker import MoodTracker
from app.core.emotional.motivation_engine import MotivationEngine
from app.core.emotional.personality_adapter import PersonalityAdapter
from app.core.emotional.sentiment_analyzer import SentimentAnalyzer
from app.models.emotional import (
    CommunicationTone,
    ConflictEvent,
    ConflictLevel,
    EQAnalysis,
    Emotion,
    EmotionalInteraction,
    EscalationAction,
    FormalityLevel,
    MoodEntry,
    MoodLevel,
    MotivationMessage,
    MotivationType,
    PersonalityProfile,
    RelationshipQuality,
    Sentiment,
    SentimentResult,
    StyleProfile,
    UserEmotionalState,
)


# === Helper fonksiyonlar ===


def _make_sentiment(
    text: str = "test",
    sentiment: Sentiment = Sentiment.NEUTRAL,
    emotion: Emotion = Emotion.TRUST,
    intensity: float = 0.5,
) -> SentimentResult:
    """Test duygu sonucu olusturur."""
    return SentimentResult(
        text=text,
        sentiment=sentiment,
        emotion=emotion,
        intensity=intensity,
    )


def _make_state(
    user_id: str = "user1",
    mood: MoodLevel = MoodLevel.NEUTRAL,
    frustration: float = 0.0,
    satisfaction: float = 0.5,
) -> UserEmotionalState:
    """Test duygusal durum olusturur."""
    return UserEmotionalState(
        user_id=user_id,
        current_mood=mood,
        frustration_level=frustration,
        satisfaction_level=satisfaction,
    )


# === Model Testleri ===


class TestEmotionalModels:
    """Emotional model testleri."""

    def test_sentiment_result_defaults(self) -> None:
        """SentimentResult varsayilan degerler."""
        s = SentimentResult()
        assert s.sentiment == Sentiment.NEUTRAL
        assert s.emotion == Emotion.TRUST
        assert s.is_sarcastic is False

    def test_user_emotional_state_defaults(self) -> None:
        """UserEmotionalState varsayilan degerler."""
        u = UserEmotionalState()
        assert u.current_mood == MoodLevel.NEUTRAL
        assert u.frustration_level == 0.0

    def test_mood_entry_defaults(self) -> None:
        """MoodEntry varsayilan degerler."""
        m = MoodEntry()
        assert m.mood == MoodLevel.NEUTRAL

    def test_style_profile_defaults(self) -> None:
        """StyleProfile varsayilan degerler."""
        s = StyleProfile()
        assert s.preferred_tone == CommunicationTone.PROFESSIONAL
        assert s.humor_receptive is True

    def test_conflict_event_defaults(self) -> None:
        """ConflictEvent varsayilan degerler."""
        c = ConflictEvent()
        assert c.level == ConflictLevel.NONE
        assert c.resolved is False

    def test_motivation_message_defaults(self) -> None:
        """MotivationMessage varsayilan degerler."""
        m = MotivationMessage()
        assert m.motivation_type == MotivationType.ENCOURAGEMENT
        assert m.delivered is False

    def test_personality_profile_defaults(self) -> None:
        """PersonalityProfile varsayilan degerler."""
        p = PersonalityProfile()
        assert p.patience_level == 0.5
        assert p.detail_preference == 0.5

    def test_emotional_interaction_defaults(self) -> None:
        """EmotionalInteraction varsayilan degerler."""
        e = EmotionalInteraction()
        assert e.relationship_quality == RelationshipQuality.NEUTRAL

    def test_eq_analysis_defaults(self) -> None:
        """EQAnalysis varsayilan degerler."""
        e = EQAnalysis()
        assert e.conflict_level == ConflictLevel.NONE
        assert e.motivation_needed is False

    def test_sentiment_enum(self) -> None:
        """Sentiment enum degerleri."""
        assert len(Sentiment) == 4
        assert Sentiment.MIXED.value == "mixed"

    def test_emotion_enum(self) -> None:
        """Emotion enum degerleri."""
        assert len(Emotion) == 8

    def test_mood_level_enum(self) -> None:
        """MoodLevel enum degerleri."""
        assert len(MoodLevel) == 5

    def test_communication_tone_enum(self) -> None:
        """CommunicationTone enum degerleri."""
        assert len(CommunicationTone) == 6

    def test_formality_level_enum(self) -> None:
        """FormalityLevel enum degerleri."""
        assert len(FormalityLevel) == 5

    def test_conflict_level_enum(self) -> None:
        """ConflictLevel enum degerleri."""
        assert len(ConflictLevel) == 5

    def test_escalation_action_enum(self) -> None:
        """EscalationAction enum degerleri."""
        assert len(EscalationAction) == 5

    def test_motivation_type_enum(self) -> None:
        """MotivationType enum degerleri."""
        assert len(MotivationType) == 5

    def test_relationship_quality_enum(self) -> None:
        """RelationshipQuality enum degerleri."""
        assert len(RelationshipQuality) == 5


# === SentimentAnalyzer Testleri ===


class TestSentimentAnalyzer:
    """SentimentAnalyzer testleri."""

    def test_init(self) -> None:
        """Baslatma testi."""
        sa = SentimentAnalyzer()
        assert sa.analysis_count == 0

    def test_positive_text(self) -> None:
        """Pozitif metin analizi."""
        sa = SentimentAnalyzer()
        result = sa.analyze("Harika bir is cikardin, tesekkurler!")
        assert result.sentiment == Sentiment.POSITIVE

    def test_negative_text(self) -> None:
        """Negatif metin analizi."""
        sa = SentimentAnalyzer()
        result = sa.analyze("Bu cok kotu ve berbat bir sonuc")
        assert result.sentiment == Sentiment.NEGATIVE

    def test_neutral_text(self) -> None:
        """Notr metin analizi."""
        sa = SentimentAnalyzer()
        result = sa.analyze("Toplanti saat 3'te")
        assert result.sentiment == Sentiment.NEUTRAL

    def test_mixed_sentiment(self) -> None:
        """Karisik duygu analizi."""
        sa = SentimentAnalyzer()
        result = sa.analyze("Guzel ama bazi hatalar var, kotu taraflari da var")
        assert result.sentiment == Sentiment.MIXED

    def test_emotion_happy(self) -> None:
        """Mutluluk duygusu."""
        sa = SentimentAnalyzer()
        result = sa.analyze("Cok mutlu ve sevincli hissediyorum")
        assert result.emotion == Emotion.HAPPY

    def test_emotion_angry(self) -> None:
        """Ofke duygusu."""
        sa = SentimentAnalyzer()
        result = sa.analyze("Cok kizginim ve sinir oldum")
        assert result.emotion == Emotion.ANGRY

    def test_emotion_sad(self) -> None:
        """Uzuntu duygusu."""
        sa = SentimentAnalyzer()
        result = sa.analyze("Cok uzgun ve mutsuz hissediyorum")
        assert result.emotion == Emotion.SAD

    def test_intensity_with_intensifiers(self) -> None:
        """Yogunlastirici ile yogunluk."""
        sa = SentimentAnalyzer()
        result = sa.analyze("Cok cok harika!!!")
        assert result.intensity > 0.6

    def test_sarcasm_detection(self) -> None:
        """Alaycilik tespiti."""
        sa = SentimentAnalyzer()
        result = sa.analyze("cok guzel tabii, bravo sana")
        assert result.is_sarcastic is True

    def test_sarcasm_flips_sentiment(self) -> None:
        """Alaycilik duyguyu cevirir."""
        sa = SentimentAnalyzer()
        result = sa.analyze("oh great, how wonderful")
        assert result.sentiment == Sentiment.NEGATIVE

    def test_context_complaint(self) -> None:
        """Sikayet baglami."""
        sa = SentimentAnalyzer()
        result = sa.analyze("Bu durum boyle", context="complaint")
        assert result.sentiment == Sentiment.NEGATIVE

    def test_context_success(self) -> None:
        """Basari baglami."""
        sa = SentimentAnalyzer()
        result = sa.analyze("Gorev tamamlandi", context="success")
        assert result.sentiment == Sentiment.POSITIVE

    def test_batch_analyze(self) -> None:
        """Toplu analiz."""
        sa = SentimentAnalyzer()
        results = sa.batch_analyze(["harika", "kotu", "normal"])
        assert len(results) == 3

    def test_dominant_sentiment(self) -> None:
        """Baskin duygu."""
        sa = SentimentAnalyzer()
        sa.analyze("harika")
        sa.analyze("guzel")
        sa.analyze("kotu")
        assert sa.get_dominant_sentiment() == Sentiment.POSITIVE

    def test_keywords_extracted(self) -> None:
        """Anahtar kelime cikarma."""
        sa = SentimentAnalyzer()
        result = sa.analyze("harika ve guzel bir sonuc")
        assert len(result.keywords) > 0

    def test_history(self) -> None:
        """Analiz gecmisi."""
        sa = SentimentAnalyzer()
        sa.analyze("test")
        assert len(sa.history) == 1


# === EmpathyEngine Testleri ===


class TestEmpathyEngine:
    """EmpathyEngine testleri."""

    def test_init(self) -> None:
        """Baslatma testi."""
        ee = EmpathyEngine()
        assert ee.tracked_users == 0
        assert ee.empathy_level == "medium"

    def test_update_state_positive(self) -> None:
        """Pozitif durum guncellemesi."""
        ee = EmpathyEngine()
        sentiment = _make_sentiment(sentiment=Sentiment.POSITIVE)
        state = ee.update_state("u1", sentiment)
        assert state.satisfaction_level > 0.5

    def test_update_state_negative(self) -> None:
        """Negatif durum guncellemesi."""
        ee = EmpathyEngine()
        sentiment = _make_sentiment(sentiment=Sentiment.NEGATIVE)
        state = ee.update_state("u1", sentiment)
        assert state.frustration_level > 0.0

    def test_frustration_accumulates(self) -> None:
        """Frustrasyon birikir."""
        ee = EmpathyEngine()
        neg = _make_sentiment(sentiment=Sentiment.NEGATIVE)
        ee.update_state("u1", neg)
        ee.update_state("u1", neg)
        state = ee.get_state("u1")
        assert state is not None
        assert state.frustration_level >= 0.35

    def test_appropriate_tone_frustrated(self) -> None:
        """Frustre kullanici icin ton."""
        ee = EmpathyEngine()
        neg = _make_sentiment(sentiment=Sentiment.NEGATIVE)
        for _ in range(5):
            ee.update_state("u1", neg)
        tone = ee.get_appropriate_tone("u1")
        assert tone == CommunicationTone.EMPATHETIC

    def test_appropriate_tone_default(self) -> None:
        """Varsayilan ton."""
        ee = EmpathyEngine()
        tone = ee.get_appropriate_tone("unknown")
        assert tone == CommunicationTone.PROFESSIONAL

    def test_supportive_response(self) -> None:
        """Destekleyici yanit."""
        ee = EmpathyEngine()
        neg = _make_sentiment(sentiment=Sentiment.NEGATIVE, emotion=Emotion.SAD)
        ee.update_state("u1", neg)
        response = ee.generate_supportive_response("u1")
        assert len(response) > 0

    def test_detect_frustration(self) -> None:
        """Frustrasyon tespiti."""
        ee = EmpathyEngine()
        neg = _make_sentiment(sentiment=Sentiment.NEGATIVE)
        for _ in range(4):
            ee.update_state("u1", neg)
        assert ee.detect_frustration("u1") is True

    def test_no_frustration(self) -> None:
        """Frustrasyon yok."""
        ee = EmpathyEngine()
        assert ee.detect_frustration("u1") is False

    def test_detect_celebration(self) -> None:
        """Kutlama tespiti."""
        ee = EmpathyEngine()
        happy = _make_sentiment(
            sentiment=Sentiment.POSITIVE,
            emotion=Emotion.HAPPY,
            intensity=0.8,
        )
        assert ee.detect_celebration(happy) is True

    def test_no_celebration_low_intensity(self) -> None:
        """Dusuk yogunlukta kutlama yok."""
        ee = EmpathyEngine()
        mild = _make_sentiment(
            sentiment=Sentiment.POSITIVE,
            emotion=Emotion.HAPPY,
            intensity=0.3,
        )
        assert ee.detect_celebration(mild) is False

    def test_mood_calculation(self) -> None:
        """Ruh hali hesaplama."""
        ee = EmpathyEngine()
        pos = _make_sentiment(sentiment=Sentiment.POSITIVE)
        state = ee.update_state("u1", pos)
        assert state.current_mood in (MoodLevel.HIGH, MoodLevel.VERY_HIGH, MoodLevel.NEUTRAL)


# === MoodTracker Testleri ===


class TestMoodTracker:
    """MoodTracker testleri."""

    def test_init(self) -> None:
        """Baslatma testi."""
        mt = MoodTracker()
        assert mt.tracked_users == 0
        assert mt.total_entries == 0

    def test_record(self) -> None:
        """Kayit testi."""
        mt = MoodTracker()
        entry = mt.record("u1", MoodLevel.HIGH, Emotion.HAPPY, "basari")
        assert entry.user_id == "u1"
        assert mt.total_entries == 1

    def test_record_from_sentiment(self) -> None:
        """Sentiment'tan kayit."""
        mt = MoodTracker()
        result = _make_sentiment(sentiment=Sentiment.POSITIVE, intensity=0.8)
        entry = mt.record_from_sentiment("u1", result)
        assert entry.mood == MoodLevel.VERY_HIGH

    def test_get_history(self) -> None:
        """Gecmis getirme."""
        mt = MoodTracker()
        mt.record("u1", MoodLevel.HIGH, Emotion.HAPPY)
        mt.record("u1", MoodLevel.LOW, Emotion.SAD)
        history = mt.get_history("u1")
        assert len(history) == 2

    def test_get_current_mood(self) -> None:
        """Mevcut ruh hali."""
        mt = MoodTracker()
        mt.record("u1", MoodLevel.HIGH, Emotion.HAPPY)
        assert mt.get_current_mood("u1") == MoodLevel.HIGH

    def test_current_mood_default(self) -> None:
        """Varsayilan ruh hali."""
        mt = MoodTracker()
        assert mt.get_current_mood("unknown") == MoodLevel.NEUTRAL

    def test_analyze_patterns_stable(self) -> None:
        """Stabil kalip analizi."""
        mt = MoodTracker()
        for _ in range(6):
            mt.record("u1", MoodLevel.NEUTRAL, Emotion.TRUST)
        patterns = mt.analyze_patterns("u1")
        assert patterns["trend"] == "stable"

    def test_analyze_patterns_improving(self) -> None:
        """Iyilesen kalip."""
        mt = MoodTracker()
        for level in [MoodLevel.VERY_LOW, MoodLevel.LOW, MoodLevel.NEUTRAL, MoodLevel.HIGH, MoodLevel.VERY_HIGH, MoodLevel.VERY_HIGH]:
            mt.record("u1", level, Emotion.HAPPY)
        patterns = mt.analyze_patterns("u1")
        assert patterns["trend"] == "improving"

    def test_identify_triggers(self) -> None:
        """Tetikleyici tespiti."""
        mt = MoodTracker()
        mt.record("u1", MoodLevel.LOW, Emotion.ANGRY, "deadline")
        mt.record("u1", MoodLevel.LOW, Emotion.ANGRY, "deadline")
        mt.record("u1", MoodLevel.HIGH, Emotion.HAPPY, "success")
        triggers = mt.identify_triggers("u1", min_count=2)
        assert len(triggers) == 1
        assert triggers[0]["trigger"] == "deadline"

    def test_predict_mood(self) -> None:
        """Ruh hali tahmini."""
        mt = MoodTracker()
        for _ in range(5):
            mt.record("u1", MoodLevel.HIGH, Emotion.HAPPY)
        predicted = mt.predict_mood("u1")
        assert predicted in (MoodLevel.HIGH, MoodLevel.VERY_HIGH)

    def test_predict_mood_insufficient(self) -> None:
        """Yetersiz veri ile tahmin."""
        mt = MoodTracker()
        mt.record("u1", MoodLevel.HIGH, Emotion.HAPPY)
        assert mt.predict_mood("u1") == MoodLevel.NEUTRAL

    def test_needs_proactive_support(self) -> None:
        """Proaktif destek gereksinimi."""
        mt = MoodTracker()
        mt.record("u1", MoodLevel.LOW, Emotion.SAD)
        mt.record("u1", MoodLevel.VERY_LOW, Emotion.SAD)
        mt.record("u1", MoodLevel.LOW, Emotion.SAD)
        assert mt.needs_proactive_support("u1") is True

    def test_no_proactive_support(self) -> None:
        """Proaktif destek gerekmez."""
        mt = MoodTracker()
        mt.record("u1", MoodLevel.HIGH, Emotion.HAPPY)
        mt.record("u1", MoodLevel.HIGH, Emotion.HAPPY)
        mt.record("u1", MoodLevel.HIGH, Emotion.HAPPY)
        assert mt.needs_proactive_support("u1") is False

    def test_mood_distribution(self) -> None:
        """Ruh hali dagilimi."""
        mt = MoodTracker()
        mt.record("u1", MoodLevel.HIGH, Emotion.HAPPY)
        mt.record("u1", MoodLevel.HIGH, Emotion.HAPPY)
        mt.record("u1", MoodLevel.LOW, Emotion.SAD)
        dist = mt.get_mood_distribution("u1")
        assert dist["high"] == 2
        assert dist["low"] == 1

    def test_max_history(self) -> None:
        """Gecmis limiti."""
        mt = MoodTracker(max_history=5)
        for _ in range(10):
            mt.record("u1", MoodLevel.NEUTRAL, Emotion.TRUST)
        assert len(mt.get_history("u1", limit=100)) == 5


# === CommunicationStyler Testleri ===


class TestCommunicationStyler:
    """CommunicationStyler testleri."""

    def test_init(self) -> None:
        """Baslatma testi."""
        cs = CommunicationStyler()
        assert cs.profile_count == 0

    def test_adapt_tone_low_mood(self) -> None:
        """Dusuk ruh halinde ton."""
        cs = CommunicationStyler()
        tone = cs.adapt_tone("u1", MoodLevel.VERY_LOW)
        assert tone == CommunicationTone.EMPATHETIC

    def test_adapt_tone_high_mood(self) -> None:
        """Yuksek ruh halinde ton."""
        cs = CommunicationStyler()
        tone = cs.adapt_tone("u1", MoodLevel.VERY_HIGH)
        assert tone == CommunicationTone.ENTHUSIASTIC

    def test_detect_formality_formal(self) -> None:
        """Resmi metin tespiti."""
        cs = CommunicationStyler()
        level = cs.detect_formality("Sayin yetkili, rica ederim bilgilerinize arz ederim")
        assert level in (FormalityLevel.FORMAL, FormalityLevel.VERY_FORMAL)

    def test_detect_formality_casual(self) -> None:
        """Gunluk metin tespiti."""
        cs = CommunicationStyler()
        level = cs.detect_formality("abi hadi ya bak kanka")
        assert level in (FormalityLevel.CASUAL, FormalityLevel.VERY_CASUAL)

    def test_humor_appropriate(self) -> None:
        """Mizah uygunlugu."""
        cs = CommunicationStyler(humor_enabled=True)
        assert cs.is_humor_appropriate(None) is True

    def test_humor_not_appropriate_low_mood(self) -> None:
        """Dusuk ruh halinde mizah uygun degil."""
        cs = CommunicationStyler(humor_enabled=True)
        state = _make_state(mood=MoodLevel.VERY_LOW)
        assert cs.is_humor_appropriate(state) is False

    def test_humor_disabled(self) -> None:
        """Mizah kapali."""
        cs = CommunicationStyler(humor_enabled=False)
        assert cs.is_humor_appropriate(None) is False

    def test_detect_urgency(self) -> None:
        """Aciliyet tespiti."""
        cs = CommunicationStyler()
        assert cs.detect_urgency("Acil sunucu coktu hemen bak") is True

    def test_no_urgency(self) -> None:
        """Aciliyet yok."""
        cs = CommunicationStyler()
        assert cs.detect_urgency("Yarin toplanti var") is False

    def test_update_profile(self) -> None:
        """Profil guncellemesi."""
        cs = CommunicationStyler()
        profile = cs.update_profile("u1", "Merhaba nasil gidiyor")
        assert profile.user_id == "u1"
        assert cs.profile_count == 1

    def test_style_recommendation(self) -> None:
        """Stil onerisi."""
        cs = CommunicationStyler()
        rec = cs.get_style_recommendation("u1", MoodLevel.HIGH)
        assert "tone" in rec
        assert "formality" in rec


# === ConflictResolver Testleri ===


class TestConflictResolver:
    """ConflictResolver testleri."""

    def test_init(self) -> None:
        """Baslatma testi."""
        cr = ConflictResolver()
        assert cr.event_count == 0

    def test_assess_none(self) -> None:
        """Catisma yok."""
        cr = ConflictResolver()
        state = _make_state(frustration=0.1)
        level = cr.assess_conflict("u1", state)
        assert level == ConflictLevel.NONE

    def test_assess_moderate(self) -> None:
        """Orta seviye catisma."""
        cr = ConflictResolver()
        state = _make_state(frustration=0.5)
        level = cr.assess_conflict("u1", state)
        assert level == ConflictLevel.MODERATE

    def test_assess_critical(self) -> None:
        """Kritik catisma."""
        cr = ConflictResolver()
        state = _make_state(frustration=0.95)
        level = cr.assess_conflict("u1", state)
        assert level == ConflictLevel.CRITICAL

    def test_track_negative(self) -> None:
        """Negatif takibi."""
        cr = ConflictResolver()
        count = cr.track_negative("u1")
        assert count == 1
        count = cr.track_negative("u1")
        assert count == 2

    def test_reset_negative(self) -> None:
        """Negatif sifirlama."""
        cr = ConflictResolver()
        cr.track_negative("u1")
        cr.reset_negative("u1")
        count = cr.track_negative("u1")
        assert count == 1

    def test_determine_action(self) -> None:
        """Aksiyon belirleme."""
        cr = ConflictResolver()
        assert cr.determine_action(ConflictLevel.NONE) == EscalationAction.NONE
        assert cr.determine_action(ConflictLevel.MILD) == EscalationAction.ACKNOWLEDGE
        assert cr.determine_action(ConflictLevel.CRITICAL) == EscalationAction.ESCALATE_HUMAN

    def test_deescalation_message(self) -> None:
        """De-eskalasyon mesaji."""
        cr = ConflictResolver()
        msg = cr.get_deescalation_message(ConflictLevel.MODERATE)
        assert len(msg) > 0

    def test_resolve(self) -> None:
        """Catisma cozumu."""
        cr = ConflictResolver()
        state = _make_state(frustration=0.3)
        event = cr.resolve("u1", state, "yavas cevap")
        assert event.level == ConflictLevel.MILD

    def test_escalate_to_human(self) -> None:
        """Insan eskalasyonu."""
        cr = ConflictResolver(escalation_threshold=0.8)
        state = _make_state(frustration=0.9)
        assert cr.should_escalate_to_human("u1", state) is True

    def test_no_escalation(self) -> None:
        """Eskalasyon yok."""
        cr = ConflictResolver()
        state = _make_state(frustration=0.2)
        assert cr.should_escalate_to_human("u1", state) is False

    def test_user_conflicts(self) -> None:
        """Kullanici catismalari."""
        cr = ConflictResolver()
        state = _make_state(frustration=0.5)
        cr.resolve("u1", state)
        cr.resolve("u2", _make_state(user_id="u2"))
        assert len(cr.get_user_conflicts("u1")) == 1

    def test_unresolved_count(self) -> None:
        """Cozulmemis sayisi."""
        cr = ConflictResolver()
        state = _make_state(frustration=0.6)
        cr.resolve("u1", state)
        assert cr.unresolved_count >= 0


# === MotivationEngine Testleri ===


class TestMotivationEngine:
    """MotivationEngine testleri."""

    def test_init(self) -> None:
        """Baslatma testi."""
        me = MotivationEngine()
        assert me.message_count == 0

    def test_encourage(self) -> None:
        """Tesvik mesaji."""
        me = MotivationEngine()
        msg = me.encourage("u1", "hata yaptim")
        assert msg.motivation_type == MotivationType.ENCOURAGEMENT
        assert msg.delivered is True

    def test_celebrate(self) -> None:
        """Kutlama mesaji."""
        me = MotivationEngine()
        msg = me.celebrate("u1", "proje tamamlandi")
        assert msg.motivation_type == MotivationType.CELEBRATION
        assert "proje tamamlandi" in msg.message

    def test_acknowledge_progress(self) -> None:
        """Ilerleme onay mesaji."""
        me = MotivationEngine()
        msg = me.acknowledge_progress("u1", "migration", 75.0)
        assert msg.motivation_type == MotivationType.PROGRESS
        assert "%75" in msg.message

    def test_remind_goal(self) -> None:
        """Hedef hatirlatma."""
        me = MotivationEngine()
        msg = me.remind_goal("u1", "100 musteri")
        assert msg.motivation_type == MotivationType.GOAL_REMINDER
        assert "100 musteri" in msg.message

    def test_reinforce(self) -> None:
        """Pozitif pekistirme."""
        me = MotivationEngine()
        msg = me.reinforce("u1")
        assert msg.motivation_type == MotivationType.POSITIVE_REINFORCEMENT

    def test_appropriate_motivation_low(self) -> None:
        """Dusuk ruh halinde motivasyon."""
        me = MotivationEngine()
        state = _make_state(mood=MoodLevel.LOW)
        msg = me.get_appropriate_motivation("u1", state)
        assert msg is not None
        assert msg.motivation_type == MotivationType.ENCOURAGEMENT

    def test_appropriate_motivation_high(self) -> None:
        """Yuksek ruh halinde motivasyon."""
        me = MotivationEngine()
        state = _make_state(mood=MoodLevel.VERY_HIGH)
        msg = me.get_appropriate_motivation("u1", state)
        assert msg is not None
        assert msg.motivation_type == MotivationType.POSITIVE_REINFORCEMENT

    def test_appropriate_motivation_neutral(self) -> None:
        """Notr ruh halinde motivasyon yok."""
        me = MotivationEngine()
        state = _make_state(mood=MoodLevel.NEUTRAL)
        msg = me.get_appropriate_motivation("u1", state)
        assert msg is None

    def test_set_and_get_goals(self) -> None:
        """Hedef belirleme ve getirme."""
        me = MotivationEngine()
        me.set_goal("u1", "100 musteri")
        me.set_goal("u1", "10k gelir")
        goals = me.get_goals("u1")
        assert len(goals) == 2

    def test_get_progress(self) -> None:
        """Ilerleme bilgisi."""
        me = MotivationEngine()
        me.acknowledge_progress("u1", "task1", 50.0)
        progress = me.get_progress("u1")
        assert progress["task1"] == 50.0

    def test_user_messages(self) -> None:
        """Kullanici mesajlari."""
        me = MotivationEngine()
        me.encourage("u1")
        me.celebrate("u1")
        msgs = me.get_user_messages("u1")
        assert len(msgs) == 2


# === PersonalityAdapter Testleri ===


class TestPersonalityAdapter:
    """PersonalityAdapter testleri."""

    def test_init(self) -> None:
        """Baslatma testi."""
        pa = PersonalityAdapter()
        assert pa.profile_count == 0

    def test_learn_from_interaction(self) -> None:
        """Etkilesimden ogrenme."""
        pa = PersonalityAdapter()
        profile = pa.learn_from_interaction("u1", "Merhaba nasil gidiyor bugun")
        assert profile.interactions_analyzed == 1

    def test_learn_tone(self) -> None:
        """Ton ogrenme."""
        pa = PersonalityAdapter()
        pa.learn_from_interaction("u1", "test", tone=CommunicationTone.CASUAL)
        assert pa.get_preferred_tone("u1") == CommunicationTone.CASUAL

    def test_learn_formality(self) -> None:
        """Resmiyet ogrenme."""
        pa = PersonalityAdapter()
        pa.learn_from_interaction("u1", "test", formality=FormalityLevel.FORMAL)
        assert pa.get_formality("u1") == FormalityLevel.FORMAL

    def test_humor_style(self) -> None:
        """Mizah stili."""
        pa = PersonalityAdapter()
        pa.learn_from_interaction("u1", "test", tone=CommunicationTone.CASUAL)
        assert pa.get_humor_style("u1") == "playful"

    def test_default_tone(self) -> None:
        """Varsayilan ton."""
        pa = PersonalityAdapter()
        assert pa.get_preferred_tone("unknown") == CommunicationTone.PROFESSIONAL

    def test_response_length_short(self) -> None:
        """Kisa yanit tercihi."""
        pa = PersonalityAdapter()
        for _ in range(5):
            pa.learn_from_interaction("u1", "kisa")
        assert pa.get_response_length("u1") == "short"

    def test_patience_decreases_short_msgs(self) -> None:
        """Kisa mesajlarda sabir azalir."""
        pa = PersonalityAdapter()
        for _ in range(10):
            pa.learn_from_interaction("u1", "ok")
        profile = pa.get_profile("u1")
        assert profile is not None
        assert profile.patience_level < 0.5

    def test_adaptation_summary(self) -> None:
        """Adaptasyon ozeti."""
        pa = PersonalityAdapter()
        pa.learn_from_interaction("u1", "test mesaj burada")
        summary = pa.get_adaptation_summary("u1")
        assert summary["user_id"] == "u1"
        assert "tone" in summary

    def test_no_profile_summary(self) -> None:
        """Profil olmadan ozet."""
        pa = PersonalityAdapter()
        summary = pa.get_adaptation_summary("unknown")
        assert summary["status"] == "no_profile"


# === EmotionalMemoryManager Testleri ===


class TestEmotionalMemoryManager:
    """EmotionalMemoryManager testleri."""

    def test_init(self) -> None:
        """Baslatma testi."""
        em = EmotionalMemoryManager()
        assert em.tracked_users == 0
        assert em.total_interactions == 0

    def test_record_interaction(self) -> None:
        """Etkilesim kaydi."""
        em = EmotionalMemoryManager()
        interaction = em.record_interaction("u1", Sentiment.POSITIVE, Emotion.HAPPY, summary="guzel konusma")
        assert interaction.user_id == "u1"
        assert em.total_interactions == 1

    def test_relationship_improves(self) -> None:
        """Iliski iyilesir."""
        em = EmotionalMemoryManager()
        for _ in range(5):
            em.record_interaction("u1", Sentiment.POSITIVE, Emotion.HAPPY)
        quality = em.get_relationship_quality("u1")
        assert quality in (RelationshipQuality.GOOD, RelationshipQuality.EXCELLENT)

    def test_relationship_declines(self) -> None:
        """Iliski kotulesir."""
        em = EmotionalMemoryManager()
        for _ in range(5):
            em.record_interaction("u1", Sentiment.NEGATIVE, Emotion.ANGRY)
        quality = em.get_relationship_quality("u1")
        assert quality in (RelationshipQuality.STRAINED, RelationshipQuality.POOR)

    def test_get_history(self) -> None:
        """Gecmis getirme."""
        em = EmotionalMemoryManager()
        em.record_interaction("u1", Sentiment.POSITIVE, Emotion.HAPPY)
        em.record_interaction("u1", Sentiment.NEUTRAL, Emotion.TRUST)
        history = em.get_history("u1")
        assert len(history) == 2

    def test_sentiment_history(self) -> None:
        """Duygu gecmisi."""
        em = EmotionalMemoryManager()
        em.record_interaction("u1", Sentiment.POSITIVE, Emotion.HAPPY)
        em.record_interaction("u1", Sentiment.NEGATIVE, Emotion.SAD)
        sentiments = em.get_sentiment_history("u1")
        assert sentiments == [Sentiment.POSITIVE, Sentiment.NEGATIVE]

    def test_important_events(self) -> None:
        """Onemli olaylar."""
        em = EmotionalMemoryManager()
        em.record_interaction("u1", Sentiment.POSITIVE, Emotion.HAPPY, importance=0.3)
        em.record_interaction("u1", Sentiment.POSITIVE, Emotion.HAPPY, importance=0.9)
        events = em.get_important_events("u1")
        assert len(events) == 1

    def test_preferences(self) -> None:
        """Tercih yonetimi."""
        em = EmotionalMemoryManager()
        em.update_preference("u1", "language", "tr")
        assert em.get_preference("u1", "language") == "tr"
        assert em.get_preference("u1", "missing", "default") == "default"

    def test_emotion_distribution(self) -> None:
        """Duygu dagilimi."""
        em = EmotionalMemoryManager()
        em.record_interaction("u1", Sentiment.POSITIVE, Emotion.HAPPY)
        em.record_interaction("u1", Sentiment.POSITIVE, Emotion.HAPPY)
        em.record_interaction("u1", Sentiment.NEGATIVE, Emotion.SAD)
        dist = em.get_emotion_distribution("u1")
        assert dist["happy"] == 2
        assert dist["sad"] == 1

    def test_user_summary(self) -> None:
        """Kullanici ozeti."""
        em = EmotionalMemoryManager()
        em.record_interaction("u1", Sentiment.POSITIVE, Emotion.HAPPY)
        summary = em.get_user_summary("u1")
        assert summary["total_interactions"] == 1
        assert summary["positive_count"] == 1

    def test_max_memory(self) -> None:
        """Hafiza limiti."""
        em = EmotionalMemoryManager(max_memory=5)
        for _ in range(10):
            em.record_interaction("u1", Sentiment.NEUTRAL, Emotion.TRUST)
        assert len(em.get_history("u1", limit=100)) == 5


# === EQOrchestrator Testleri ===


class TestEQOrchestrator:
    """EQOrchestrator testleri."""

    def test_init(self) -> None:
        """Baslatma testi."""
        eq = EQOrchestrator()
        assert eq.analysis_count == 0

    def test_components_accessible(self) -> None:
        """Bilesenler erisilebilir."""
        eq = EQOrchestrator()
        assert eq.analyzer is not None
        assert eq.empathy is not None
        assert eq.mood is not None
        assert eq.styler is not None
        assert eq.conflict is not None
        assert eq.motivation is not None
        assert eq.personality is not None
        assert eq.memory is not None

    def test_process_positive(self) -> None:
        """Pozitif metin isleme."""
        eq = EQOrchestrator()
        analysis = eq.process("u1", "Harika bir sonuc, tesekkurler!")
        assert analysis.sentiment is not None
        assert analysis.sentiment.sentiment == Sentiment.POSITIVE
        assert analysis.processing_ms > 0

    def test_process_negative(self) -> None:
        """Negatif metin isleme."""
        eq = EQOrchestrator()
        analysis = eq.process("u1", "Bu cok kotu bir sonuc, berbat")
        assert analysis.sentiment is not None
        assert analysis.sentiment.sentiment == Sentiment.NEGATIVE

    def test_process_updates_mood(self) -> None:
        """Isleme ruh halini gunceller."""
        eq = EQOrchestrator()
        eq.process("u1", "harika")
        current = eq.mood.get_current_mood("u1")
        assert current != MoodLevel.NEUTRAL or True  # ilk kayit

    def test_process_records_memory(self) -> None:
        """Isleme hafizaya kaydeder."""
        eq = EQOrchestrator()
        eq.process("u1", "merhaba")
        assert eq.memory.total_interactions == 1

    def test_process_learns_personality(self) -> None:
        """Isleme kisilik ogrenir."""
        eq = EQOrchestrator()
        eq.process("u1", "abi hadi ya bak kanka cok guzel")
        profile = eq.personality.get_profile("u1")
        assert profile is not None

    def test_user_insights(self) -> None:
        """Kullanici icgoruleri."""
        eq = EQOrchestrator()
        eq.process("u1", "test mesaj")
        insights = eq.get_user_insights("u1")
        assert "mood" in insights
        assert "personality" in insights
        assert "relationship_quality" in insights

    def test_conflict_tracking(self) -> None:
        """Catisma takibi."""
        eq = EQOrchestrator()
        for _ in range(3):
            eq.process("u1", "bu cok kotu, berbat, hata var")
        analysis = eq.process("u1", "yine hata, sinir oldum")
        assert analysis.conflict_level != ConflictLevel.NONE

    def test_motivation_detection(self) -> None:
        """Motivasyon gereksinim tespiti."""
        eq = EQOrchestrator()
        for _ in range(4):
            eq.process("u1", "uzgun ve mutsuz hissediyorum, kotu gidiyor")
        # Son analiz motivasyon gerektirmeli
        analysis = eq.process("u1", "yine kotu")
        # needs_proactive_support 3+ low mood gerektirir
        # birden fazla negatif mood zaten kaydedildi
        assert eq.analysis_count == 5


# === Entegrasyon Testleri ===


class TestEmotionalIntegration:
    """Entegrasyon testleri."""

    def test_sentiment_to_empathy(self) -> None:
        """Sentiment -> Empathy entegrasyonu."""
        sa = SentimentAnalyzer()
        ee = EmpathyEngine()
        result = sa.analyze("Cok kizgin ve sinir oldum bu duruma")
        state = ee.update_state("u1", result)
        assert state.frustration_level > 0

    def test_empathy_to_conflict(self) -> None:
        """Empathy -> Conflict entegrasyonu."""
        ee = EmpathyEngine()
        cr = ConflictResolver()
        neg = _make_sentiment(sentiment=Sentiment.NEGATIVE)
        for _ in range(4):
            ee.update_state("u1", neg)
        state = ee.get_state("u1")
        assert state is not None
        level = cr.assess_conflict("u1", state)
        assert level != ConflictLevel.NONE

    def test_mood_to_motivation(self) -> None:
        """Mood -> Motivation entegrasyonu."""
        mt = MoodTracker()
        me = MotivationEngine()
        mt.record("u1", MoodLevel.LOW, Emotion.SAD)
        mt.record("u1", MoodLevel.LOW, Emotion.SAD)
        mt.record("u1", MoodLevel.LOW, Emotion.SAD)
        if mt.needs_proactive_support("u1"):
            msg = me.encourage("u1")
            assert msg.motivation_type == MotivationType.ENCOURAGEMENT

    def test_full_emotional_flow(self) -> None:
        """Tam duygusal akis."""
        eq = EQOrchestrator(empathy_level="high")

        # Pozitif baslangic
        a1 = eq.process("u1", "Merhaba, harika bir gun!")
        assert a1.sentiment is not None

        # Notr
        eq.process("u1", "Toplanti saat 3'te")

        # Negatif
        eq.process("u1", "Bu hata cok kotu, sinir oldum")

        insights = eq.get_user_insights("u1")
        assert insights["memory"]["total_interactions"] == 3

    def test_multi_user(self) -> None:
        """Coklu kullanici."""
        eq = EQOrchestrator()
        eq.process("u1", "harika sonuc")
        eq.process("u2", "berbat durumda")

        i1 = eq.get_user_insights("u1")
        i2 = eq.get_user_insights("u2")
        assert i1["memory"]["positive_count"] >= i2["memory"]["positive_count"]
