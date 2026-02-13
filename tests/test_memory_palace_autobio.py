"""AutobiographicalMemory testleri.

Otobiyografik hafiza sistemi: bolum olusturma/kapatma, olay ekleme,
anlatim olusturma, zaman cizgisi, kimlik yonetimi, hedef iliskili
hafiza arama ve bolum ozeti testleri.
"""

from datetime import datetime, timezone

from app.core.memory_palace.episodic_memory import EpisodicMemory
from app.core.memory_palace.autobiographical import AutobiographicalMemory
from app.models.memory_palace import LifeChapterStatus


# === Yardimci fonksiyonlar ===


def _make_autobio(
    episodic: EpisodicMemory | None = None,
) -> AutobiographicalMemory:
    """AutobiographicalMemory olusturur, varsayilan epizodik alt sistemle."""
    ep = episodic if episodic is not None else EpisodicMemory()
    return AutobiographicalMemory(episodic=ep)


# === Init Testleri ===


class TestInit:
    """AutobiographicalMemory initialization testleri."""

    def test_defaults(self) -> None:
        """Varsayilan degerlerle baslatma testi."""
        ab = _make_autobio()
        assert ab._chapters == {}
        assert ab._identity == {}
        assert ab._active_chapter_id is None

    def test_subsystems_none(self) -> None:
        """Tum alt sistemler None iken baslatma testi."""
        ab = AutobiographicalMemory()
        assert ab._episodic is None
        assert ab._emotional is None
        assert ab._chapters == {}


# === Chapter Testleri ===


class TestChapter:
    """AutobiographicalMemory bolum yonetimi testleri."""

    def test_create_chapter(self) -> None:
        """Yeni bolum olusturma testi."""
        ab = _make_autobio()
        chapter = ab.create_chapter("Bolum 1", description="Ilk bolum")

        assert chapter.title == "Bolum 1"
        assert chapter.description == "Ilk bolum"
        assert chapter.status == LifeChapterStatus.ACTIVE
        assert ab._active_chapter_id == chapter.id

    def test_create_chapter_with_themes(self) -> None:
        """Temali bolum olusturma testi."""
        ab = _make_autobio()
        chapter = ab.create_chapter("Tema Bolumu", themes=["kariyer", "gelisim"])

        assert chapter.themes == ["kariyer", "gelisim"]

    def test_close_chapter(self) -> None:
        """Bolum kapatma testi."""
        ab = _make_autobio()
        chapter = ab.create_chapter("Kapatilacak Bolum")

        closed = ab.close_chapter(chapter.id)

        assert closed is not None
        assert closed.status == LifeChapterStatus.CLOSED
        assert closed.end_date is not None
        assert ab._active_chapter_id is None

    def test_close_unknown_chapter_returns_none(self) -> None:
        """Bilinmeyen bolum kapatma girisi None donmesi testi."""
        ab = _make_autobio()
        result = ab.close_chapter("nonexistent-id")
        assert result is None

    def test_get_chapter(self) -> None:
        """Bolum getirme testi."""
        ab = _make_autobio()
        chapter = ab.create_chapter("Getirilecek Bolum")

        fetched = ab.get_chapter(chapter.id)
        assert fetched is not None
        assert fetched.title == "Getirilecek Bolum"

    def test_get_unknown_chapter_returns_none(self) -> None:
        """Bilinmeyen bolum getirme girisi None donmesi testi."""
        ab = _make_autobio()
        result = ab.get_chapter("nonexistent-id")
        assert result is None

    def test_auto_closes_previous_active(self) -> None:
        """Yeni bolum olustururken onceki aktif bolumu kapatma testi."""
        ab = _make_autobio()
        ch1 = ab.create_chapter("Bolum 1")
        ch2 = ab.create_chapter("Bolum 2")

        # Onceki bolum kapatilmis olmali
        assert ab.get_chapter(ch1.id).status == LifeChapterStatus.CLOSED
        assert ab._active_chapter_id == ch2.id


# === AddEpisode Testleri ===


class TestAddEpisode:
    """AutobiographicalMemory.add_episode_to_chapter testleri."""

    def test_adds_to_chapter(self) -> None:
        """Olayi bolume ekleme testi."""
        ep = EpisodicMemory()
        ab = _make_autobio(episodic=ep)
        chapter = ab.create_chapter("Test Bolumu")
        episode = ep.store("test olayi")

        result = ab.add_episode_to_chapter(chapter.id, episode.id)

        assert result is True
        assert episode.id in chapter.episode_ids

    def test_returns_false_for_unknown_chapter(self) -> None:
        """Bilinmeyen bolum icin False donmesi testi."""
        ab = _make_autobio()
        result = ab.add_episode_to_chapter("nonexistent", "ep-id")
        assert result is False


# === Narrative Testleri ===


class TestNarrative:
    """AutobiographicalMemory.build_narrative testleri."""

    def test_builds_narrative_string(self) -> None:
        """Anlatim metni olusturma testi."""
        ep = EpisodicMemory()
        ab = _make_autobio(episodic=ep)
        chapter = ab.create_chapter("Hikaye Bolumu")
        episode = ep.store("onemli bir olay", where="Istanbul")
        ab.add_episode_to_chapter(chapter.id, episode.id)

        narrative = ab.build_narrative(chapter_id=chapter.id)

        assert "Hikaye Bolumu" in narrative
        assert isinstance(narrative, str)

    def test_contains_episode_info(self) -> None:
        """Anlatimin olay bilgilerini icermesi testi."""
        ep = EpisodicMemory()
        ab = _make_autobio(episodic=ep)
        chapter = ab.create_chapter("Detay Bolumu")
        episode = ep.store("sunucu coktu", where="ofis")
        ab.add_episode_to_chapter(chapter.id, episode.id)

        narrative = ab.build_narrative(chapter_id=chapter.id)

        assert "sunucu coktu" in narrative
        assert "ofis" in narrative

    def test_empty_narrative_for_unknown_chapter(self) -> None:
        """Bilinmeyen bolum icin bos anlatim testi."""
        ab = _make_autobio()
        narrative = ab.build_narrative(chapter_id="nonexistent")
        assert narrative == ""

    def test_narrative_all_chapters(self) -> None:
        """Tum bolumlerin anlatimini olusturma testi."""
        ab = _make_autobio()
        ab.create_chapter("Bolum 1")
        ab.create_chapter("Bolum 2")

        narrative = ab.build_narrative()
        assert "Bolum 1" in narrative
        assert "Bolum 2" in narrative


# === Timeline Testleri ===


class TestTimeline:
    """AutobiographicalMemory.get_timeline testleri."""

    def test_returns_personal_timeline(self) -> None:
        """PersonalTimeline donmesi testi."""
        ab = _make_autobio()
        ab.create_chapter("Bolum 1")

        timeline = ab.get_timeline()

        assert len(timeline.chapters) == 1
        assert timeline.chapters[0].title == "Bolum 1"

    def test_total_episodes_count(self) -> None:
        """Toplam olay sayisi testi."""
        ep = EpisodicMemory()
        ab = _make_autobio(episodic=ep)
        chapter = ab.create_chapter("Test Bolumu")
        e1 = ep.store("olay 1")
        e2 = ep.store("olay 2")
        ab.add_episode_to_chapter(chapter.id, e1.id)
        ab.add_episode_to_chapter(chapter.id, e2.id)

        timeline = ab.get_timeline()
        assert timeline.total_episodes == 2

    def test_identity_beliefs_included(self) -> None:
        """Kimlik inanclarinin dahil edilmesi testi."""
        ab = _make_autobio()
        ab.update_identity("problem_solver", 0.8)

        timeline = ab.get_timeline()
        assert "problem_solver" in timeline.identity_beliefs
        assert timeline.identity_beliefs["problem_solver"] == 0.8


# === Identity Testleri ===


class TestIdentity:
    """AutobiographicalMemory kimlik inanclari testleri."""

    def test_update_identity(self) -> None:
        """Kimlik inanci guncelleme testi."""
        ab = _make_autobio()
        result = ab.update_identity("lider", 0.5)

        assert result == 0.5
        assert ab._identity["lider"] == 0.5

    def test_get_identity(self) -> None:
        """Kimlik inanclarini getirme testi."""
        ab = _make_autobio()
        ab.update_identity("yaratici", 0.7)
        ab.update_identity("analitik", 0.3)

        identity = ab.get_identity()
        assert identity == {"yaratici": 0.7, "analitik": 0.3}

    def test_clamped_to_max(self) -> None:
        """Kimlik gucunun 1.0 ile sinirlanmasi testi."""
        ab = _make_autobio()
        result = ab.update_identity("cesur", 1.5)
        assert result == 1.0

    def test_clamped_to_min(self) -> None:
        """Kimlik gucunun 0.0 ile sinirlanmasi testi."""
        ab = _make_autobio()
        result = ab.update_identity("korkak", -0.5)
        assert result == 0.0

    def test_delta_accumulation(self) -> None:
        """Ardisik delta birikimi testi."""
        ab = _make_autobio()
        ab.update_identity("uzman", 0.3)
        result = ab.update_identity("uzman", 0.4)
        assert result == 0.7


# === GoalRelevant Testleri ===


class TestGoalRelevant:
    """AutobiographicalMemory.get_goal_relevant_memories testleri."""

    def test_finds_matching_episodes(self) -> None:
        """Hedefle eslesen olaylari bulma testi."""
        ep = EpisodicMemory()
        ab = _make_autobio(episodic=ep)
        ep.store("sunucu sorununu cozdum", tags=["sunucu", "sorun"])
        ep.store("kahve ictim", tags=["mola"])

        results = ab.get_goal_relevant_memories("sunucu sorun")

        assert len(results) >= 1
        assert results[0].what == "sunucu sorununu cozdum"

    def test_empty_when_no_episodic(self) -> None:
        """Epizodik hafiza yokken bos liste donmesi testi."""
        ab = AutobiographicalMemory()
        results = ab.get_goal_relevant_memories("herhangi bir hedef")
        assert results == []


# === ChapterSummary Testleri ===


class TestChapterSummary:
    """AutobiographicalMemory.get_chapter_summary testleri."""

    def test_returns_summary_dict(self) -> None:
        """Ozet sozlugu donmesi testi."""
        ep = EpisodicMemory()
        ab = _make_autobio(episodic=ep)
        chapter = ab.create_chapter("Ozet Bolumu", themes=["test"])
        e = ep.store("olay 1")
        ab.add_episode_to_chapter(chapter.id, e.id)

        summary = ab.get_chapter_summary(chapter.id)

        assert summary is not None
        assert summary["title"] == "Ozet Bolumu"
        assert summary["status"] == LifeChapterStatus.ACTIVE.value
        assert summary["episode_count"] == 1
        assert summary["themes"] == ["test"]
        assert "duration_days" in summary
        assert "emotions" in summary

    def test_none_for_unknown_chapter(self) -> None:
        """Bilinmeyen bolum icin None donmesi testi."""
        ab = _make_autobio()
        result = ab.get_chapter_summary("nonexistent")
        assert result is None
