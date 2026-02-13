"""EmotionalMemory testleri.

Duygusal hafiza sistemi: etiketleme, tercih guncelleme, kacinma,
ruh hali yonetimi, mood-congruent recall ve duygu dagilimi testleri.
"""

import pytest

from app.core.memory_palace.emotional_memory import EmotionalMemory
from app.models.memory_palace import EmotionType, Sentiment


# === Yardimci fonksiyonlar ===


def _make_emotional(**kwargs) -> EmotionalMemory:
    """EmotionalMemory olusturur."""
    return EmotionalMemory(**kwargs)


# === Init Testleri ===


class TestInit:
    """EmotionalMemory initialization testleri."""

    def test_defaults(self) -> None:
        """Varsayilan degerlerle baslatma testi."""
        em = _make_emotional()
        assert em._emotional_weight == 0.3
        assert em._associations == {}
        assert em._preferences == {}
        assert em._aversions == {}
        assert em._current_mood is None

    def test_custom_emotional_weight(self) -> None:
        """Ozel duygusal agirlik katsayisi testi."""
        em = _make_emotional(emotional_weight=0.7)
        assert em._emotional_weight == 0.7


# === TagMemory Testleri ===


class TestTagMemory:
    """EmotionalMemory.tag_memory testleri."""

    def test_basic_tag(self) -> None:
        """Temel duygusal etiketleme testi."""
        em = _make_emotional()
        assoc = em.tag_memory("mem1", EmotionType.JOY)
        assert assoc.memory_id == "mem1"
        assert assoc.emotion == EmotionType.JOY
        assert assoc.intensity == 0.5  # varsayilan yogunluk

    def test_custom_intensity(self) -> None:
        """Ozel yogunluk degeri testi."""
        em = _make_emotional()
        assoc = em.tag_memory("mem1", EmotionType.ANGER, intensity=0.9)
        assert assoc.intensity == 0.9

    def test_intensity_clamped_high(self) -> None:
        """Yogunluk ust siniri testi."""
        em = _make_emotional()
        assoc = em.tag_memory("mem1", EmotionType.FEAR, intensity=5.0)
        assert assoc.intensity == 1.0

    def test_intensity_clamped_low(self) -> None:
        """Yogunluk alt siniri testi."""
        em = _make_emotional()
        assoc = em.tag_memory("mem1", EmotionType.TRUST, intensity=-2.0)
        assert assoc.intensity == 0.0

    def test_multiple_tags_same_memory(self) -> None:
        """Ayni hafizaya birden fazla etiket ekleme testi."""
        em = _make_emotional()
        em.tag_memory("mem1", EmotionType.JOY, intensity=0.8)
        em.tag_memory("mem1", EmotionType.SURPRISE, intensity=0.3)
        associations = em.get_emotions("mem1")
        assert len(associations) == 2
        emotions = {a.emotion for a in associations}
        assert EmotionType.JOY in emotions
        assert EmotionType.SURPRISE in emotions


# === GetEmotions Testleri ===


class TestGetEmotions:
    """EmotionalMemory.get_emotions testleri."""

    def test_existing_memory(self) -> None:
        """Mevcut hafiza icin duygu listesi testi."""
        em = _make_emotional()
        em.tag_memory("mem1", EmotionType.SADNESS, intensity=0.6)
        result = em.get_emotions("mem1")
        assert len(result) == 1
        assert result[0].emotion == EmotionType.SADNESS

    def test_empty_for_unknown(self) -> None:
        """Bilinmeyen hafiza icin bos liste testi."""
        em = _make_emotional()
        result = em.get_emotions("unknown")
        assert result == []

    def test_returns_copy(self) -> None:
        """get_emotions sonucunun kopya oldugunu dogrulama testi."""
        em = _make_emotional()
        em.tag_memory("mem1", EmotionType.JOY)
        result = em.get_emotions("mem1")
        result.clear()
        assert len(em.get_emotions("mem1")) == 1


# === Preference Testleri ===


class TestPreference:
    """EmotionalMemory.update_preference testleri."""

    def test_new_preference_created(self) -> None:
        """Yeni tercih olusturma testi."""
        em = _make_emotional()
        pref = em.update_preference("python", Sentiment.POSITIVE, score_delta=0.5)
        assert pref.subject == "python"
        assert pref.sentiment == Sentiment.POSITIVE
        assert pref.score == 0.5
        assert pref.interaction_count == 1

    def test_update_existing_ema(self) -> None:
        """Mevcut tercihi EMA ile guncelleme testi."""
        em = _make_emotional(emotional_weight=0.3)
        em.update_preference("python", Sentiment.POSITIVE, score_delta=0.5)
        pref = em.update_preference("python", Sentiment.POSITIVE, score_delta=1.0)
        # EMA: 0.5 * (1 - 0.3) + 1.0 * 0.3 = 0.35 + 0.30 = 0.65
        assert abs(pref.score - 0.65) < 1e-9

    def test_score_clamped_positive(self) -> None:
        """Puan ust sinir kesimi testi."""
        em = _make_emotional(emotional_weight=1.0)
        em.update_preference("item", Sentiment.POSITIVE, score_delta=0.9)
        pref = em.update_preference("item", Sentiment.POSITIVE, score_delta=5.0)
        assert pref.score <= 1.0

    def test_score_clamped_negative(self) -> None:
        """Puan alt sinir kesimi testi."""
        em = _make_emotional(emotional_weight=1.0)
        em.update_preference("item", Sentiment.NEGATIVE, score_delta=-0.9)
        pref = em.update_preference("item", Sentiment.NEGATIVE, score_delta=-5.0)
        assert pref.score >= -1.0

    def test_interaction_count_increments(self) -> None:
        """Etkilesim sayacinin artmasi testi."""
        em = _make_emotional()
        em.update_preference("topic", Sentiment.NEUTRAL, score_delta=0.1)
        em.update_preference("topic", Sentiment.NEUTRAL, score_delta=0.2)
        em.update_preference("topic", Sentiment.NEUTRAL, score_delta=0.3)
        pref = em.get_preference("topic")
        assert pref is not None
        assert pref.interaction_count == 3

    def test_get_preference_none_for_unknown(self) -> None:
        """Bilinmeyen konu icin None donmesi testi."""
        em = _make_emotional()
        assert em.get_preference("unknown") is None

    def test_new_preference_score_clamped(self) -> None:
        """Yeni tercih puaninin sinirlanmasi testi."""
        em = _make_emotional()
        pref = em.update_preference("extreme", Sentiment.POSITIVE, score_delta=5.0)
        assert pref.score == 1.0


# === Aversion Testleri ===


class TestAversion:
    """EmotionalMemory.record_aversion / get_aversion testleri."""

    def test_new_aversion(self) -> None:
        """Yeni kacinma kaydi testi."""
        em = _make_emotional()
        em.record_aversion("spam", intensity=0.6)
        assert em.get_aversion("spam") == pytest.approx(0.3)  # 0.0 + 0.6 * 0.5

    def test_increases_with_repeated_calls(self) -> None:
        """Tekrarlanan cagrilarda kacinmanin artmasi testi."""
        em = _make_emotional()
        em.record_aversion("spam", intensity=0.4)
        first = em.get_aversion("spam")
        em.record_aversion("spam", intensity=0.4)
        second = em.get_aversion("spam")
        assert second > first

    def test_capped_at_one(self) -> None:
        """Kacinma gucunun 1.0 ile sinirlanmasi testi."""
        em = _make_emotional()
        for _ in range(20):
            em.record_aversion("spam", intensity=1.0)
        assert em.get_aversion("spam") <= 1.0

    def test_unknown_returns_zero(self) -> None:
        """Bilinmeyen konu icin sifir donmesi testi."""
        em = _make_emotional()
        assert em.get_aversion("unknown") == 0.0


# === Mood Testleri ===


class TestMood:
    """EmotionalMemory.set_mood / get_mood testleri."""

    def test_initially_none(self) -> None:
        """Baslangicta ruh halinin None olmasi testi."""
        em = _make_emotional()
        assert em.get_mood() is None

    def test_set_and_get_mood(self) -> None:
        """Ruh hali ayarlama ve alma testi."""
        em = _make_emotional()
        em.set_mood(EmotionType.JOY)
        assert em.get_mood() == EmotionType.JOY

    def test_mood_overwrite(self) -> None:
        """Ruh halinin degistirilmesi testi."""
        em = _make_emotional()
        em.set_mood(EmotionType.JOY)
        em.set_mood(EmotionType.SADNESS)
        assert em.get_mood() == EmotionType.SADNESS


# === MoodCongruentRecall Testleri ===


class TestMoodCongruentRecall:
    """EmotionalMemory.mood_congruent_recall testleri."""

    def test_returns_all_if_no_mood_set(self) -> None:
        """Ruh hali ayarlanmamissa tum hatiralarin donmesi testi."""
        em = _make_emotional()
        memories = [{"id": "a"}, {"id": "b"}, {"id": "c"}]
        result = em.mood_congruent_recall(memories)
        assert len(result) == 3

    def test_filters_by_matching_mood_emotion(self) -> None:
        """Ruh haline uyumlu hatiralarin filtrelenmesi testi."""
        em = _make_emotional()
        em.tag_memory("m1", EmotionType.JOY, intensity=0.8)
        em.tag_memory("m2", EmotionType.SADNESS, intensity=0.5)
        em.set_mood(EmotionType.JOY)
        memories = [{"id": "m1"}, {"id": "m2"}]
        result = em.mood_congruent_recall(memories)
        assert len(result) == 1
        assert result[0]["id"] == "m1"

    def test_sorts_by_intensity(self) -> None:
        """Yogunluga gore siralama testi."""
        em = _make_emotional()
        em.tag_memory("low", EmotionType.JOY, intensity=0.2)
        em.tag_memory("high", EmotionType.JOY, intensity=0.9)
        em.tag_memory("mid", EmotionType.JOY, intensity=0.5)
        em.set_mood(EmotionType.JOY)
        memories = [{"id": "low"}, {"id": "high"}, {"id": "mid"}]
        result = em.mood_congruent_recall(memories)
        assert [m["id"] for m in result] == ["high", "mid", "low"]

    def test_empty_result_when_no_match(self) -> None:
        """Eslesen hatira yoksa bos liste testi."""
        em = _make_emotional()
        em.tag_memory("m1", EmotionType.ANGER, intensity=0.7)
        em.set_mood(EmotionType.JOY)
        memories = [{"id": "m1"}]
        result = em.mood_congruent_recall(memories)
        assert result == []


# === SentimentSummary Testleri ===


class TestSentimentSummary:
    """EmotionalMemory.get_sentiment_summary testleri."""

    def test_counts_emotions_correctly(self) -> None:
        """Duygu dagiliminin dogru sayilmasi testi."""
        em = _make_emotional()
        em.tag_memory("m1", EmotionType.JOY)
        em.tag_memory("m2", EmotionType.JOY)
        em.tag_memory("m3", EmotionType.ANGER)
        summary = em.get_sentiment_summary()
        assert summary["joy"] == 2
        assert summary["anger"] == 1

    def test_empty_summary(self) -> None:
        """Bos duygusal hafiza icin bos dagilim testi."""
        em = _make_emotional()
        summary = em.get_sentiment_summary()
        assert summary == {}

    def test_multiple_emotions_on_same_memory(self) -> None:
        """Ayni hafizada birden fazla duygu sayimi testi."""
        em = _make_emotional()
        em.tag_memory("m1", EmotionType.FEAR)
        em.tag_memory("m1", EmotionType.SURPRISE)
        summary = em.get_sentiment_summary()
        assert summary["fear"] == 1
        assert summary["surprise"] == 1
