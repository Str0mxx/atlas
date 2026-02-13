"""EpisodicMemory testleri.

Olay bazli hafiza sistemi: kayit, geri cagirma, zaman filtreli sorgulama,
kronolojik zaman cizgisi, flashbulb hafiza ve konsolidasyon testleri.
"""

from datetime import datetime, timedelta, timezone

from app.core.memory_palace.episodic_memory import EpisodicMemory
from app.models.memory_palace import EpisodeQuery, MemoryStrength


# === Yardimci fonksiyonlar ===


def _make_episodic(**kwargs) -> EpisodicMemory:
    """EpisodicMemory olusturur."""
    return EpisodicMemory(**kwargs)


# === Init Testleri ===


class TestInit:
    """EpisodicMemory initialization testleri."""

    def test_defaults(self) -> None:
        """Varsayilan degerlerle baslatma testi."""
        em = _make_episodic()
        assert em._episodes == {}
        assert em._timeline == []
        assert em._flashbulb_threshold == 0.9

    def test_custom_flashbulb_threshold(self) -> None:
        """Ozel flashbulb esigi testi."""
        em = _make_episodic(flashbulb_threshold=0.7)
        assert em._flashbulb_threshold == 0.7


# === Store Testleri ===


class TestStore:
    """EpisodicMemory.store testleri."""

    def test_basic_store(self) -> None:
        """Temel olay kaydetme testi."""
        em = _make_episodic()
        episode = em.store("test olayi")
        assert episode.what == "test olayi"
        assert episode.id in em._episodes

    def test_flashbulb_detection_at_threshold(self) -> None:
        """Onem esiginde flashbulb isaretleme testi."""
        em = _make_episodic(flashbulb_threshold=0.9)
        episode = em.store("onemli olay", importance=0.9)
        assert episode.is_flashbulb is True
        assert episode.memory_strength == MemoryStrength.FLASHBULB

    def test_flashbulb_detection_above_threshold(self) -> None:
        """Onem esiginin uzerinde flashbulb isaretleme testi."""
        em = _make_episodic(flashbulb_threshold=0.9)
        episode = em.store("cok onemli olay", importance=1.0)
        assert episode.is_flashbulb is True
        assert episode.memory_strength == MemoryStrength.FLASHBULB

    def test_no_flashbulb_below_threshold(self) -> None:
        """Onem esiginin altinda flashbulb olmamasi testi."""
        em = _make_episodic(flashbulb_threshold=0.9)
        episode = em.store("normal olay", importance=0.5)
        assert episode.is_flashbulb is False

    def test_strong_memory_strength(self) -> None:
        """Guclu hafiza seviyesi testi (0.7 <= importance < threshold)."""
        em = _make_episodic(flashbulb_threshold=0.9)
        episode = em.store("guclu olay", importance=0.75)
        assert episode.memory_strength == MemoryStrength.STRONG

    def test_moderate_memory_strength(self) -> None:
        """Orta hafiza seviyesi testi (0.4 <= importance < 0.7)."""
        em = _make_episodic()
        episode = em.store("orta olay", importance=0.5)
        assert episode.memory_strength == MemoryStrength.MODERATE

    def test_weak_memory_strength(self) -> None:
        """Zayif hafiza seviyesi testi (importance < 0.4)."""
        em = _make_episodic()
        episode = em.store("zayif olay", importance=0.2)
        assert episode.memory_strength == MemoryStrength.WEAK

    def test_store_with_tags(self) -> None:
        """Etiketlerle kaydetme testi."""
        em = _make_episodic()
        episode = em.store("etiketli olay", tags=["is", "toplanti"])
        assert episode.tags == ["is", "toplanti"]

    def test_store_with_who(self) -> None:
        """Katilimcilerle kaydetme testi."""
        em = _make_episodic()
        episode = em.store("toplanti", who=["Fatih", "Ali"])
        assert episode.who == ["Fatih", "Ali"]

    def test_store_with_where(self) -> None:
        """Konumla kaydetme testi."""
        em = _make_episodic()
        episode = em.store("toplanti", where="Istanbul Ofis")
        assert episode.where == "Istanbul Ofis"

    def test_store_with_context(self) -> None:
        """Baglamsal bilgiyle kaydetme testi."""
        em = _make_episodic()
        ctx = {"project": "ATLAS", "sprint": 3}
        episode = em.store("sprint toplantisi", context=ctx)
        assert episode.context == {"project": "ATLAS", "sprint": 3}

    def test_store_defaults_empty_lists(self) -> None:
        """Varsayilan bos listeler testi."""
        em = _make_episodic()
        episode = em.store("basit olay")
        assert episode.who == []
        assert episode.tags == []
        assert episode.context == {}
        assert episode.where == ""


# === Recall Testleri ===


class TestRecall:
    """EpisodicMemory.recall testleri."""

    def test_existing_episode(self) -> None:
        """Mevcut olayi geri cagirma testi."""
        em = _make_episodic()
        episode = em.store("hatirlanan olay")
        recalled = em.recall(episode.id)
        assert recalled is not None
        assert recalled.what == "hatirlanan olay"

    def test_nonexistent_returns_none(self) -> None:
        """Olmayan olay icin None donmesi testi."""
        em = _make_episodic()
        assert em.recall("yok-id") is None

    def test_access_count_increments(self) -> None:
        """Erisim sayacinin artmasi testi."""
        em = _make_episodic()
        episode = em.store("sayac testi")
        assert episode.access_count == 0
        em.recall(episode.id)
        assert episode.access_count == 1
        em.recall(episode.id)
        assert episode.access_count == 2

    def test_last_accessed_updates(self) -> None:
        """Son erisim zamaninin guncellenmesi testi."""
        em = _make_episodic()
        episode = em.store("zaman testi")
        assert episode.last_accessed is None
        before = datetime.now(timezone.utc)
        em.recall(episode.id)
        assert episode.last_accessed is not None
        assert episode.last_accessed >= before


# === Query Testleri ===


class TestQuery:
    """EpisodicMemory.query testleri."""

    def test_time_start_filter(self) -> None:
        """Baslangic zamani filtresi testi."""
        em = _make_episodic()
        e1 = em.store("eski olay")
        e2 = em.store("yeni olay")
        # e1'in zamanini gecmise cek
        e1.when = datetime.now(timezone.utc) - timedelta(hours=2)
        cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
        query = EpisodeQuery(time_start=cutoff)
        results = em.query(query)
        ids = [e.id for e in results]
        assert e2.id in ids
        assert e1.id not in ids

    def test_time_end_filter(self) -> None:
        """Bitis zamani filtresi testi."""
        em = _make_episodic()
        e1 = em.store("eski olay")
        e2 = em.store("yeni olay")
        e1.when = datetime.now(timezone.utc) - timedelta(hours=2)
        cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
        query = EpisodeQuery(time_end=cutoff)
        results = em.query(query)
        ids = [e.id for e in results]
        assert e1.id in ids
        assert e2.id not in ids

    def test_location_filter(self) -> None:
        """Konum filtresi testi (icerme kontrolu)."""
        em = _make_episodic()
        em.store("istanbul toplanti", where="Istanbul Ofis")
        em.store("ankara toplanti", where="Ankara Merkez")
        query = EpisodeQuery(location="istanbul")
        results = em.query(query)
        assert len(results) == 1
        assert results[0].where == "Istanbul Ofis"

    def test_participant_filter(self) -> None:
        """Katilimci filtresi testi."""
        em = _make_episodic()
        em.store("fatih toplantisi", who=["Fatih", "Ali"])
        em.store("baska toplanti", who=["Mehmet"])
        query = EpisodeQuery(participants=["Fatih"])
        results = em.query(query)
        assert len(results) == 1
        assert "Fatih" in results[0].who

    def test_tag_filter(self) -> None:
        """Etiket filtresi testi."""
        em = _make_episodic()
        em.store("is olayi", tags=["is", "acil"])
        em.store("kisisel olay", tags=["kisisel"])
        query = EpisodeQuery(tags=["is"])
        results = em.query(query)
        assert len(results) == 1
        assert "is" in results[0].tags

    def test_min_importance_filter(self) -> None:
        """Minimum onem filtresi testi."""
        em = _make_episodic()
        em.store("onemli", importance=0.8)
        em.store("onemsiz", importance=0.2)
        query = EpisodeQuery(min_importance=0.5)
        results = em.query(query)
        assert len(results) == 1
        assert results[0].importance == 0.8

    def test_limit(self) -> None:
        """Sonuc limiti testi."""
        em = _make_episodic()
        for i in range(5):
            em.store(f"olay-{i}", importance=i * 0.2)
        query = EpisodeQuery(limit=3)
        results = em.query(query)
        assert len(results) == 3

    def test_combined_filters(self) -> None:
        """Birlesik filtre testi."""
        em = _make_episodic()
        em.store("hedef", where="Istanbul", who=["Fatih"], tags=["acil"], importance=0.8)
        em.store("yanlis konum", where="Ankara", who=["Fatih"], tags=["acil"], importance=0.8)
        em.store("yanlis kisi", where="Istanbul", who=["Mehmet"], tags=["acil"], importance=0.8)
        em.store("dusuk onem", where="Istanbul", who=["Fatih"], tags=["acil"], importance=0.1)
        query = EpisodeQuery(
            location="istanbul",
            participants=["Fatih"],
            tags=["acil"],
            min_importance=0.5,
        )
        results = em.query(query)
        assert len(results) == 1
        assert results[0].what == "hedef"

    def test_results_sorted_by_importance(self) -> None:
        """Sonuclarin oneme gore azalan sirada siralanmasi testi."""
        em = _make_episodic()
        em.store("dusuk", importance=0.3)
        em.store("yuksek", importance=0.9)
        em.store("orta", importance=0.6)
        query = EpisodeQuery()
        results = em.query(query)
        importances = [e.importance for e in results]
        assert importances == sorted(importances, reverse=True)


# === Timeline Testleri ===


class TestTimeline:
    """EpisodicMemory.get_timeline testleri."""

    def test_chronological_order(self) -> None:
        """Kronolojik siralama testi."""
        em = _make_episodic()
        e1 = em.store("birinci")
        e2 = em.store("ikinci")
        e3 = em.store("ucuncu")
        timeline = em.get_timeline()
        ids = [e.id for e in timeline]
        assert ids == [e1.id, e2.id, e3.id]

    def test_time_range_filtering(self) -> None:
        """Zaman araligi filtreleme testi."""
        em = _make_episodic()
        now = datetime.now(timezone.utc)
        e1 = em.store("gecmis")
        e1.when = now - timedelta(hours=3)
        e2 = em.store("simdi")
        e2.when = now
        e3 = em.store("gelecek")
        e3.when = now + timedelta(hours=3)
        # _timeline sirayi kayip edebilir, direkt sonuc kontrolu yapalim
        start = now - timedelta(hours=1)
        end = now + timedelta(hours=1)
        timeline = em.get_timeline(start=start, end=end)
        ids = [e.id for e in timeline]
        assert e2.id in ids
        assert e1.id not in ids
        assert e3.id not in ids


# === Flashbulb Testleri ===


class TestFlashbulb:
    """EpisodicMemory.get_flashbulb_memories testleri."""

    def test_flashbulb_memories_returned(self) -> None:
        """Flashbulb hafizalarin dondurulmesi testi."""
        em = _make_episodic(flashbulb_threshold=0.9)
        em.store("cok onemli", importance=0.95)
        em.store("normal", importance=0.5)
        flashbulbs = em.get_flashbulb_memories()
        assert len(flashbulbs) == 1
        assert flashbulbs[0].what == "cok onemli"

    def test_non_flashbulb_excluded(self) -> None:
        """Flashbulb olmayan hafizalarin haric tutulmasi testi."""
        em = _make_episodic(flashbulb_threshold=0.9)
        em.store("dusuk onem", importance=0.3)
        em.store("orta onem", importance=0.6)
        flashbulbs = em.get_flashbulb_memories()
        assert len(flashbulbs) == 0

    def test_multiple_flashbulbs(self) -> None:
        """Birden fazla flashbulb hafiza testi."""
        em = _make_episodic(flashbulb_threshold=0.8)
        em.store("birinci flashbulb", importance=0.85)
        em.store("ikinci flashbulb", importance=0.95)
        em.store("normal", importance=0.5)
        flashbulbs = em.get_flashbulb_memories()
        assert len(flashbulbs) == 2


# === Consolidate Testleri ===


class TestConsolidate:
    """EpisodicMemory.consolidate testleri."""

    def test_removes_low_importance_unaccessed(self) -> None:
        """Dusuk onemli ve hic erisilmemis olaylarin silinmesi testi."""
        em = _make_episodic()
        em.store("silinecek", importance=0.1)
        removed = em.consolidate(importance_threshold=0.3)
        assert removed == 1
        assert em.count() == 0

    def test_keeps_accessed_episodes(self) -> None:
        """Erisilen olaylarin tutulmasi testi."""
        em = _make_episodic()
        episode = em.store("erisilen", importance=0.1)
        em.recall(episode.id)  # access_count = 1
        removed = em.consolidate(importance_threshold=0.3)
        assert removed == 0
        assert em.count() == 1

    def test_keeps_high_importance(self) -> None:
        """Yuksek onemli olaylarin tutulmasi testi."""
        em = _make_episodic()
        em.store("onemli", importance=0.8)
        removed = em.consolidate(importance_threshold=0.3)
        assert removed == 0
        assert em.count() == 1

    def test_consolidate_removes_from_timeline(self) -> None:
        """Konsolidasyonun zaman cizgisinden de silmesi testi."""
        em = _make_episodic()
        episode = em.store("silinecek", importance=0.1)
        eid = episode.id
        em.consolidate(importance_threshold=0.3)
        assert eid not in em._timeline

    def test_consolidate_mixed(self) -> None:
        """Karisik senaryoda konsolidasyon testi."""
        em = _make_episodic()
        em.store("sil-1", importance=0.1)
        em.store("sil-2", importance=0.2)
        em.store("tut-onemli", importance=0.5)
        keep = em.store("tut-erisilen", importance=0.1)
        em.recall(keep.id)
        removed = em.consolidate(importance_threshold=0.3)
        assert removed == 2
        assert em.count() == 2


# === Count Testleri ===


class TestCount:
    """EpisodicMemory.count testleri."""

    def test_empty(self) -> None:
        """Bos hafizada sifir sayisi testi."""
        em = _make_episodic()
        assert em.count() == 0

    def test_after_stores(self) -> None:
        """Kayitlardan sonra dogru sayim testi."""
        em = _make_episodic()
        em.store("birinci")
        em.store("ikinci")
        em.store("ucuncu")
        assert em.count() == 3
