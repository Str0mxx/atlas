"""MemoryConsolidator testleri.

Hafiza pekistirme sistemi: tam dongu, tekrar oynatma, oruntu cikarma,
sema olusturma, catisma cozumu, guclendirme, zayiflatma ve istatistik testleri.
"""

from datetime import datetime, timedelta, timezone

from app.core.memory_palace.episodic_memory import EpisodicMemory
from app.core.memory_palace.forgetting_curve import ForgettingCurve
from app.core.memory_palace.memory_consolidator import MemoryConsolidator
from app.models.memory_palace import (
    ConsolidationPhase,
    MemoryStrength,
    MemoryType,
    SchemaType,
)


# === Yardimci fonksiyonlar ===


def _make_episodic(**kwargs) -> EpisodicMemory:
    """EpisodicMemory olusturur."""
    return EpisodicMemory(**kwargs)


def _make_curve(**kwargs) -> ForgettingCurve:
    """ForgettingCurve olusturur."""
    return ForgettingCurve(**kwargs)


def _make_consolidator(
    episodic: EpisodicMemory | None = None,
    forgetting_curve: ForgettingCurve | None = None,
) -> MemoryConsolidator:
    """MemoryConsolidator olusturur, varsayilan alt sistemlerle."""
    ep = episodic if episodic is not None else _make_episodic()
    fc = forgetting_curve if forgetting_curve is not None else _make_curve()
    return MemoryConsolidator(episodic=ep, forgetting_curve=fc)


# === Init Testleri ===


class TestInit:
    """MemoryConsolidator initialization testleri."""

    def test_defaults(self) -> None:
        """Varsayilan degerlerle baslatma testi."""
        mc = _make_consolidator()
        assert mc._cycles == []
        assert mc._schemas == {}

    def test_all_subsystems_none(self) -> None:
        """Tum alt sistemler None iken baslatma testi."""
        mc = MemoryConsolidator()
        assert mc._episodic is None
        assert mc._forgetting_curve is None
        assert mc._emotional is None
        assert mc._associative is None
        assert mc._cycles == []
        assert mc._schemas == {}


# === ConsolidationCycle Testleri ===


class TestConsolidationCycle:
    """MemoryConsolidator.run_consolidation_cycle testleri."""

    def test_runs_full_cycle(self) -> None:
        """Tam pekistirme dongusu calistirma testi."""
        ep = _make_episodic()
        fc = _make_curve()
        mc = _make_consolidator(episodic=ep, forgetting_curve=fc)
        ep.store("olay 1", importance=0.8, tags=["a", "b"])
        fc.register_memory(ep._timeline[0], importance=0.8)

        cycle = mc.run_consolidation_cycle()

        assert cycle is not None
        assert cycle.phase == ConsolidationPhase.CONSOLIDATION

    def test_returns_consolidation_cycle_with_stats(self) -> None:
        """Dongu istatistikleri iceren ConsolidationCycle donmesi testi."""
        ep = _make_episodic()
        fc = _make_curve()
        mc = _make_consolidator(episodic=ep, forgetting_curve=fc)

        # Onemli hafizalar
        e1 = ep.store("olay 1", importance=0.8, tags=["a"])
        fc.register_memory(e1.id, importance=0.8)

        # Onemsiz hafiza
        e2 = ep.store("olay 2", importance=0.1, tags=["z"])

        cycle = mc.run_consolidation_cycle()

        assert cycle.memories_processed >= 1
        assert cycle.memories_strengthened >= 0
        assert cycle.memories_weakened >= 0
        assert isinstance(cycle.patterns_found, int)

    def test_completed_at_set(self) -> None:
        """Dongu tamamlanma zamani ayarlanmasi testi."""
        mc = _make_consolidator()
        cycle = mc.run_consolidation_cycle()
        assert cycle.completed_at is not None

    def test_cycle_appended(self) -> None:
        """Dongu listeye eklenmesi testi."""
        mc = _make_consolidator()
        mc.run_consolidation_cycle()
        assert len(mc.get_cycles()) == 1


# === ReplayMemories Testleri ===


class TestReplayMemories:
    """MemoryConsolidator.replay_memories testleri."""

    def test_replays_recent_episodes(self) -> None:
        """Son olaylari tekrar oynatma testi."""
        ep = _make_episodic()
        mc = _make_consolidator(episodic=ep)
        ep.store("yeni olay", importance=0.5)

        replayed = mc.replay_memories(recent_hours=24)

        assert len(replayed) == 1
        assert replayed[0].what == "yeni olay"

    def test_empty_when_no_episodic(self) -> None:
        """Epizodik hafiza yokken bos liste donmesi testi."""
        mc = MemoryConsolidator()
        replayed = mc.replay_memories()
        assert replayed == []

    def test_access_count_bumps(self) -> None:
        """Tekrar oynatmada erisim sayisi artmasi testi."""
        ep = _make_episodic()
        mc = _make_consolidator(episodic=ep)
        e = ep.store("olay", importance=0.5)
        initial_count = e.access_count

        mc.replay_memories(recent_hours=24)

        updated = ep._episodes[e.id]
        assert updated.access_count > initial_count

    def test_old_episodes_excluded(self) -> None:
        """Eski olaylarin tekrar oynatmadan haric tutulmasi testi."""
        ep = _make_episodic()
        mc = _make_consolidator(episodic=ep)

        e = ep.store("eski olay", importance=0.5)
        # Olayi 48 saat oncesine tasi
        e.when = datetime.now(timezone.utc) - timedelta(hours=48)

        replayed = mc.replay_memories(recent_hours=24)
        assert len(replayed) == 0


# === ExtractPatterns Testleri ===


class TestExtractPatterns:
    """MemoryConsolidator.extract_patterns testleri."""

    def test_finds_patterns_from_overlapping_tags(self) -> None:
        """Ortusuen etiketlerden oruntu bulma testi."""
        ep = _make_episodic()
        mc = _make_consolidator(episodic=ep)

        # 3+ olay ayni etiketlerle
        e1 = ep.store("olay 1", tags=["server", "alert"])
        e2 = ep.store("olay 2", tags=["server", "alert"])
        e3 = ep.store("olay 3", tags=["server", "alert"])

        patterns = mc.extract_patterns([e1, e2, e3])

        assert len(patterns) >= 1
        assert patterns[0].schema_type == SchemaType.EVENT_SCRIPT

    def test_no_pattern_for_dissimilar_episodes(self) -> None:
        """Benzer olmayan olaylardan oruntu cikmamasi testi."""
        ep = _make_episodic()
        mc = _make_consolidator(episodic=ep)

        e1 = ep.store("olay 1", tags=["a"])
        e2 = ep.store("olay 2", tags=["b"])
        e3 = ep.store("olay 3", tags=["c"])

        patterns = mc.extract_patterns([e1, e2, e3])
        assert len(patterns) == 0

    def test_groups_three_plus_into_schema(self) -> None:
        """3+ uyeli grubun sema olusturmasi testi."""
        ep = _make_episodic()
        mc = _make_consolidator(episodic=ep)

        episodes = [
            ep.store(f"olay {i}", tags=["common", "shared"])
            for i in range(4)
        ]

        patterns = mc.extract_patterns(episodes)

        assert len(patterns) == 1
        assert len(patterns[0].source_memory_ids) == 4

    def test_less_than_two_episodes_returns_empty(self) -> None:
        """Ikiden az olayla bos sonuc donmesi testi."""
        ep = _make_episodic()
        mc = _make_consolidator(episodic=ep)

        e1 = ep.store("tek olay", tags=["a"])
        patterns = mc.extract_patterns([e1])
        assert patterns == []

    def test_two_episodes_not_enough_for_schema(self) -> None:
        """Iki olaylik grubun sema olusturmamasi testi (3 gerekli)."""
        ep = _make_episodic()
        mc = _make_consolidator(episodic=ep)

        e1 = ep.store("olay 1", tags=["x", "y"])
        e2 = ep.store("olay 2", tags=["x", "y"])

        patterns = mc.extract_patterns([e1, e2])
        assert len(patterns) == 0


# === FormSchema Testleri ===


class TestFormSchema:
    """MemoryConsolidator.form_schema testleri."""

    def test_creates_schema_with_correct_fields(self) -> None:
        """Dogru alanlarla sema olusturma testi."""
        mc = _make_consolidator()

        pattern = {"common_tags": ["a", "b"], "common_context_keys": ["c"]}
        source_ids = ["id1", "id2", "id3"]

        schema = mc.form_schema(pattern=pattern, source_ids=source_ids, name="test_schema")

        assert schema.name == "test_schema"
        assert schema.schema_type == SchemaType.EVENT_SCRIPT
        assert schema.pattern == pattern
        assert schema.source_memory_ids == source_ids
        assert schema.instance_count == 3
        assert schema.id in mc._schemas

    def test_auto_generated_name(self) -> None:
        """Isim verilmezse otomatik isim olusturma testi."""
        mc = _make_consolidator()
        schema = mc.form_schema(pattern={}, source_ids=["a"], name="")
        assert schema.name == "schema_0"

    def test_multiple_schemas_unique_ids(self) -> None:
        """Birden fazla sema icin benzersiz ID testi."""
        mc = _make_consolidator()
        s1 = mc.form_schema(pattern={}, source_ids=["a"], name="s1")
        s2 = mc.form_schema(pattern={}, source_ids=["b"], name="s2")
        assert s1.id != s2.id
        assert len(mc._schemas) == 2


# === ResolveInterference Testleri ===


class TestResolveInterference:
    """MemoryConsolidator.resolve_interference testleri."""

    def test_keeps_stronger_memory(self) -> None:
        """Daha guclu hafizayi koruma testi."""
        ep = _make_episodic()
        mc = _make_consolidator(episodic=ep)
        now = datetime.now(timezone.utc)

        e_strong = ep.store("guclu olay", importance=0.9, where="ofis")
        e_weak = ep.store("zayif olay", importance=0.2, where="ofis")

        # Ayni zaman ve ayni yer
        e_strong.when = now
        e_weak.when = now

        kept = mc.resolve_interference([e_strong.id, e_weak.id])

        assert e_strong.id in kept
        assert e_weak.id not in kept

    def test_removes_weaker(self) -> None:
        """Zayif hafizanin cikarilmasi testi."""
        ep = _make_episodic()
        mc = _make_consolidator(episodic=ep)
        now = datetime.now(timezone.utc)

        e1 = ep.store("olay 1", importance=0.8, where="ev")
        e2 = ep.store("olay 2", importance=0.3, where="ev")

        e1.when = now
        e2.when = now

        kept = mc.resolve_interference([e1.id, e2.id])
        assert len(kept) == 1
        assert kept[0] == e1.id

    def test_no_interference_different_location(self) -> None:
        """Farkli konumdaki olaylarin catismamasi testi."""
        ep = _make_episodic()
        mc = _make_consolidator(episodic=ep)
        now = datetime.now(timezone.utc)

        e1 = ep.store("olay 1", importance=0.5, where="ofis")
        e2 = ep.store("olay 2", importance=0.5, where="ev")

        e1.when = now
        e2.when = now

        kept = mc.resolve_interference([e1.id, e2.id])
        assert len(kept) == 2

    def test_no_episodic_returns_all(self) -> None:
        """Epizodik hafiza yokken tum ID'lerin donmesi testi."""
        mc = MemoryConsolidator()
        ids = ["id1", "id2"]
        kept = mc.resolve_interference(ids)
        assert kept == ids


# === Strengthen Testleri ===


class TestStrengthen:
    """MemoryConsolidator.strengthen_important testleri."""

    def test_strengthens_important_memories(self) -> None:
        """Onemli hafizalari guclendirme testi (importance >= threshold)."""
        ep = _make_episodic()
        fc = _make_curve()
        mc = _make_consolidator(episodic=ep, forgetting_curve=fc)

        e = ep.store("onemli olay", importance=0.8)
        fc.register_memory(e.id, importance=0.8)

        initial_review_count = fc.get_trace(e.id).review_count
        count = mc.strengthen_important(importance_threshold=0.7)

        assert count >= 1
        assert fc.get_trace(e.id).review_count > initial_review_count

    def test_skips_unimportant(self) -> None:
        """Onemsiz hafizalarin atlanmasi testi."""
        ep = _make_episodic()
        fc = _make_curve()
        mc = _make_consolidator(episodic=ep, forgetting_curve=fc)

        e = ep.store("onemsiz olay", importance=0.2)
        fc.register_memory(e.id, importance=0.2)

        count = mc.strengthen_important(importance_threshold=0.7)
        assert count == 0

    def test_returns_zero_when_no_subsystems(self) -> None:
        """Alt sistemler yokken sifir donmesi testi."""
        mc = MemoryConsolidator()
        count = mc.strengthen_important()
        assert count == 0


# === Weaken Testleri ===


class TestWeaken:
    """MemoryConsolidator.weaken_trivial testleri."""

    def test_weakens_trivial_memories(self) -> None:
        """Onemsiz ve erisilmemis hafizalari zayiflatma testi."""
        ep = _make_episodic()
        mc = _make_consolidator(episodic=ep)

        e = ep.store("onemsiz olay", importance=0.1)
        # access_count varsayilan olarak 0

        count = mc.weaken_trivial(importance_threshold=0.3)

        assert count >= 1
        assert ep._episodes[e.id].memory_strength == MemoryStrength.WEAK

    def test_skips_accessed_memories(self) -> None:
        """Erisilmis hafizalarin atlanmasi testi."""
        ep = _make_episodic()
        mc = _make_consolidator(episodic=ep)

        e = ep.store("olay", importance=0.1)
        ep.recall(e.id)  # access_count = 1

        count = mc.weaken_trivial(importance_threshold=0.3)
        assert count == 0

    def test_skips_important_memories(self) -> None:
        """Onemli hafizalarin atlanmasi testi."""
        ep = _make_episodic()
        mc = _make_consolidator(episodic=ep)

        ep.store("onemli olay", importance=0.8)

        count = mc.weaken_trivial(importance_threshold=0.3)
        assert count == 0

    def test_returns_zero_when_no_episodic(self) -> None:
        """Epizodik hafiza yokken sifir donmesi testi."""
        mc = MemoryConsolidator()
        count = mc.weaken_trivial()
        assert count == 0


# === GetSchemas Testleri ===


class TestGetSchemas:
    """MemoryConsolidator.get_schemas testleri."""

    def test_returns_all_schemas(self) -> None:
        """Tum semalarin donmesi testi."""
        mc = _make_consolidator()
        mc.form_schema(pattern={"a": 1}, source_ids=["x"], name="s1")
        mc.form_schema(pattern={"b": 2}, source_ids=["y"], name="s2")

        schemas = mc.get_schemas()
        assert len(schemas) == 2

    def test_empty_initially(self) -> None:
        """Baslangicta bos liste donmesi testi."""
        mc = _make_consolidator()
        assert mc.get_schemas() == []


# === GetCycles Testleri ===


class TestGetCycles:
    """MemoryConsolidator.get_cycles testleri."""

    def test_returns_all_cycles(self) -> None:
        """Tum dongulerin donmesi testi."""
        mc = _make_consolidator()
        mc.run_consolidation_cycle()
        mc.run_consolidation_cycle()

        cycles = mc.get_cycles()
        assert len(cycles) == 2

    def test_empty_initially(self) -> None:
        """Baslangicta bos liste donmesi testi."""
        mc = _make_consolidator()
        assert mc.get_cycles() == []
