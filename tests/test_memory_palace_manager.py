"""MemoryPalaceManager testleri.

Memory Palace orkestrator sistemi: baslatma, kodlama, getirme, arama,
iliskilendirme, pekistirme, istatistik ve calisma bellegi testleri.
"""

from datetime import datetime, timedelta, timezone

from app.core.memory_palace.memory_palace_manager import MemoryPalaceManager
from app.models.memory_palace import (
    AssociationType,
    EmotionType,
    MemoryPalaceStats,
    MemorySearchQuery,
    MemoryType,
)


# === Yardimci fonksiyonlar ===


def _make_palace(**kwargs) -> MemoryPalaceManager:
    """MemoryPalaceManager olusturur."""
    return MemoryPalaceManager(**kwargs)


# === Init Testleri ===


class TestInit:
    """MemoryPalaceManager initialization testleri."""

    def test_defaults(self) -> None:
        """Varsayilan degerlerle baslatma testi."""
        mp = _make_palace()
        assert mp._consolidation_interval == 3600
        assert mp._last_consolidation is None

    def test_custom_parameters(self) -> None:
        """Ozel parametrelerle baslatma testi."""
        mp = _make_palace(
            max_working_memory=5,
            forgetting_rate=0.2,
            emotional_weight=0.5,
            consolidation_interval=1800,
        )
        assert mp._consolidation_interval == 1800
        assert mp.working_memory._capacity == 5

    def test_all_subsystems_initialized(self) -> None:
        """Tum alt sistemlerin baslatilmasi testi."""
        mp = _make_palace()
        assert mp.episodic is not None
        assert mp.procedural is not None
        assert mp.emotional is not None
        assert mp.forgetting_curve is not None
        assert mp.associative is not None
        assert mp.working_memory is not None
        assert mp.consolidator is not None
        assert mp.autobiographical is not None


# === Encode Testleri ===


class TestEncode:
    """MemoryPalaceManager.encode testleri."""

    def test_episodic_encoding(self) -> None:
        """Epizodik hafiza kodlama testi."""
        mp = _make_palace()
        memory_id = mp.encode(
            "sunucu coktu",
            memory_type=MemoryType.EPISODIC,
            importance=0.8,
        )

        assert memory_id != ""
        assert mp.episodic.count() == 1

    def test_procedural_encoding(self) -> None:
        """Prosedurel hafiza kodlama testi."""
        mp = _make_palace()
        memory_id = mp.encode(
            "deployment becerisi",
            memory_type=MemoryType.PROCEDURAL,
            context={"domain": "devops", "steps": []},
        )

        assert memory_id != ""
        assert mp.procedural.count() == 1

    def test_with_emotion_tagging(self) -> None:
        """Duygusal etiketleme ile kodlama testi."""
        mp = _make_palace()
        memory_id = mp.encode(
            "basarili is",
            memory_type=MemoryType.EPISODIC,
            emotion=EmotionType.JOY,
            emotion_intensity=0.9,
        )

        emotions = mp.emotional.get_emotions(memory_id)
        assert len(emotions) == 1
        assert emotions[0].emotion == EmotionType.JOY
        assert emotions[0].intensity == 0.9

    def test_forgetting_curve_registered(self) -> None:
        """Unutma egrisi kaydinin olusturulmasi testi."""
        mp = _make_palace()
        memory_id = mp.encode(
            "kayitli olay",
            memory_type=MemoryType.EPISODIC,
            importance=0.6,
        )

        trace = mp.forgetting_curve.get_trace(memory_id)
        assert trace is not None
        assert trace.memory_id == memory_id


# === Retrieve Testleri ===


class TestRetrieve:
    """MemoryPalaceManager.retrieve testleri."""

    def test_episodic_retrieval(self) -> None:
        """Epizodik hafiza getirme testi."""
        mp = _make_palace()
        memory_id = mp.encode(
            "test olayi", memory_type=MemoryType.EPISODIC
        )

        result = mp.retrieve(memory_id, MemoryType.EPISODIC)

        assert result is not None
        assert result["what"] == "test olayi"

    def test_procedural_retrieval(self) -> None:
        """Prosedurel hafiza getirme testi."""
        mp = _make_palace()
        memory_id = mp.encode(
            "python becerisi",
            memory_type=MemoryType.PROCEDURAL,
            context={"domain": "programlama"},
        )

        result = mp.retrieve(memory_id, MemoryType.PROCEDURAL)

        assert result is not None
        assert result["name"] == "python becerisi"

    def test_not_found_returns_none(self) -> None:
        """Bulunamayan hafiza icin None donmesi testi."""
        mp = _make_palace()
        result = mp.retrieve("nonexistent-id", MemoryType.EPISODIC)
        assert result is None

    def test_includes_retention(self) -> None:
        """Getirme sonucunda _retention alaninin bulunmasi testi."""
        mp = _make_palace()
        memory_id = mp.encode(
            "unutma testi", memory_type=MemoryType.EPISODIC
        )

        result = mp.retrieve(memory_id, MemoryType.EPISODIC)

        assert result is not None
        assert "_retention" in result
        assert 0.0 <= result["_retention"] <= 1.0


# === Search Testleri ===


class TestSearch:
    """MemoryPalaceManager.search testleri."""

    def test_finds_by_keywords(self) -> None:
        """Anahtar kelime ile arama testi."""
        mp = _make_palace()
        mp.encode(
            "sunucu sorununu cozdum",
            memory_type=MemoryType.EPISODIC,
            context={"tags": ["sunucu"]},
        )
        mp.encode(
            "kahve mola verdim",
            memory_type=MemoryType.EPISODIC,
        )

        query = MemorySearchQuery(
            query="sunucu",
            memory_types=[MemoryType.EPISODIC],
        )
        results = mp.search(query)

        assert len(results) >= 1
        assert any("sunucu" in r.content.get("what", "") for r in results)

    def test_respects_limit(self) -> None:
        """Sonuc siniri testi."""
        mp = _make_palace()
        for i in range(5):
            mp.encode(
                f"olay {i} server",
                memory_type=MemoryType.EPISODIC,
            )

        query = MemorySearchQuery(
            query="server", limit=2,
            memory_types=[MemoryType.EPISODIC],
        )
        results = mp.search(query)

        assert len(results) <= 2

    def test_respects_min_relevance(self) -> None:
        """Minimum ilgi esigi testi."""
        mp = _make_palace()
        mp.encode("tamamen alakasiz icerik", memory_type=MemoryType.EPISODIC)

        query = MemorySearchQuery(
            query="sunucu monitor",
            min_relevance=0.8,
            memory_types=[MemoryType.EPISODIC],
        )
        results = mp.search(query)

        assert all(r.relevance >= 0.8 for r in results)

    def test_empty_results(self) -> None:
        """Sonucsuz arama testi."""
        mp = _make_palace()

        query = MemorySearchQuery(
            query="varolmayan kelime",
            memory_types=[MemoryType.EPISODIC],
        )
        results = mp.search(query)

        assert results == []


# === Associate Testleri ===


class TestAssociate:
    """MemoryPalaceManager.associate testleri."""

    def test_creates_link_between_memories(self) -> None:
        """Iki hafiza arasinda baglanti kurma testi."""
        mp = _make_palace()
        id_a = mp.encode("olay A", memory_type=MemoryType.EPISODIC)
        id_b = mp.encode("olay B", memory_type=MemoryType.EPISODIC)

        link = mp.associate(id_a, id_b, weight=0.7)

        assert link is not None
        assert link.weight == 0.7

    def test_auto_creates_concept_nodes(self) -> None:
        """Otomatik kavram dugumu olusturma testi."""
        mp = _make_palace()

        # Henuz kavram olarak eklenmemis ID'ler
        link = mp.associate("new_id_1", "new_id_2", weight=0.5)

        assert link is not None
        node_a = mp.associative.get_concept(
            mp.associative.get_concept_by_name("new_id_1").id
        )
        node_b = mp.associative.get_concept(
            mp.associative.get_concept_by_name("new_id_2").id
        )
        assert node_a is not None
        assert node_b is not None


# === Consolidate Testleri ===


class TestConsolidate:
    """MemoryPalaceManager.consolidate ve force_consolidate testleri."""

    def test_runs_cycle(self) -> None:
        """Pekistirme dongusu calistirma testi."""
        mp = _make_palace()
        mp.encode("test olayi", memory_type=MemoryType.EPISODIC)

        cycle = mp.consolidate()

        assert cycle is not None
        assert cycle.completed_at is not None

    def test_respects_interval_returns_none(self) -> None:
        """Aralik kontrolu: cok erken cagirilirsa None donmesi testi."""
        mp = _make_palace(consolidation_interval=3600)

        # Ilk cagri: basarili
        cycle1 = mp.consolidate()
        assert cycle1 is not None

        # Ikinci cagri: cok erken
        cycle2 = mp.consolidate()
        assert cycle2 is None

    def test_force_consolidate_always_runs(self) -> None:
        """force_consolidate aralik kontrolu olmadan calistirma testi."""
        mp = _make_palace(consolidation_interval=3600)

        cycle1 = mp.consolidate()
        assert cycle1 is not None

        # Aralik gecmemis olsa bile zorla calistir
        cycle2 = mp.force_consolidate()
        assert cycle2 is not None
        assert cycle2.completed_at is not None


# === Stats Testleri ===


class TestStats:
    """MemoryPalaceManager.get_stats testleri."""

    def test_returns_memory_palace_stats(self) -> None:
        """MemoryPalaceStats donmesi testi."""
        mp = _make_palace()

        stats = mp.get_stats()

        assert isinstance(stats, MemoryPalaceStats)
        assert stats.total_episodes == 0
        assert stats.total_skills == 0

    def test_correct_counts(self) -> None:
        """Dogru sayimlar testi."""
        mp = _make_palace()
        mp.encode("olay 1", memory_type=MemoryType.EPISODIC)
        mp.encode("olay 2", memory_type=MemoryType.EPISODIC)
        mp.encode(
            "beceri 1", memory_type=MemoryType.PROCEDURAL,
            context={"domain": "test"},
        )
        mp.force_consolidate()

        stats = mp.get_stats()

        assert stats.total_episodes == 2
        assert stats.total_skills == 1
        assert stats.consolidation_cycles == 1

    def test_avg_memory_strength(self) -> None:
        """Ortalama hafiza gucu hesaplamasi testi."""
        mp = _make_palace()
        mp.encode("olay", memory_type=MemoryType.EPISODIC, importance=0.5)

        stats = mp.get_stats()

        assert stats.avg_memory_strength >= 0.0
        assert stats.avg_memory_strength <= 1.0


# === LoadToWorkingMemory Testleri ===


class TestLoadToWorkingMemory:
    """MemoryPalaceManager.load_to_working_memory testleri."""

    def test_loads_from_episodic(self) -> None:
        """Epizodik hafizadan calisma bellegine yukleme testi."""
        mp = _make_palace()
        memory_id = mp.encode(
            "yuklenen olay", memory_type=MemoryType.EPISODIC
        )

        item = mp.load_to_working_memory(
            memory_id, MemoryType.EPISODIC, priority=0.8
        )

        assert item is not None
        assert item.priority == 0.8
        assert item.content is not None

    def test_returns_none_for_unknown(self) -> None:
        """Bilinmeyen hafiza icin None donmesi testi."""
        mp = _make_palace()
        item = mp.load_to_working_memory(
            "nonexistent-id", MemoryType.EPISODIC
        )
        assert item is None
