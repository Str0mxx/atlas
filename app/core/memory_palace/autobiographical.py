"""ATLAS Otobiyografik (Ozyasam) Hafiza Sistemi.

Yasam bolumlerini yonetir, kisisel anlatim olusturur,
kimlik inanclarini takip eder ve hedefe yonelik
hafiza erisimi saglar. Epizodik ve duygusal hafiza
alt sistemleri ile entegre calisir.
"""

import logging
from datetime import datetime, timezone

from app.core.memory_palace.emotional_memory import EmotionalMemory
from app.core.memory_palace.episodic_memory import EpisodicMemory
from app.models.memory_palace import (
    EmotionType,
    Episode,
    LifeChapter,
    LifeChapterStatus,
    PersonalTimeline,
)

logger = logging.getLogger(__name__)


class AutobiographicalMemory:
    """Otobiyografik (ozyasam) hafiza sistemi.

    Yasam bolumlerini kronolojik olarak yonetir, olaylari
    bolumlere atar, kisisel anlatim olusturur ve kimlik
    inanclarini takip eder.

    Attributes:
        _episodic: Epizodik hafiza alt sistemi.
        _emotional: Duygusal hafiza alt sistemi.
        _chapters: Yasam bolumleri (id -> LifeChapter).
        _identity: Kimlik inanclari (inanc -> guc 0.0-1.0).
        _active_chapter_id: Aktif bolum ID'si.
    """

    def __init__(
        self,
        episodic: EpisodicMemory | None = None,
        emotional: EmotionalMemory | None = None,
    ) -> None:
        """Otobiyografik hafiza sistemini baslatir.

        Args:
            episodic: Epizodik hafiza alt sistemi.
            emotional: Duygusal hafiza alt sistemi.
        """
        self._episodic = episodic
        self._emotional = emotional
        self._chapters: dict[str, LifeChapter] = {}
        self._identity: dict[str, float] = {}
        self._active_chapter_id: str | None = None
        logger.info("Otobiyografik hafiza sistemi baslatildi")

    def create_chapter(
        self,
        title: str,
        description: str = "",
        themes: list[str] | None = None,
    ) -> LifeChapter:
        """Yeni yasam bolumu olusturur.

        Onceki aktif bolum varsa otomatik olarak kapatilir,
        yeni bolum aktif olarak isaretlenir.

        Args:
            title: Bolum basligi.
            description: Bolum aciklamasi.
            themes: Bolum temalari.

        Returns:
            Olusturulan LifeChapter nesnesi.
        """
        # Onceki aktif bolumu kapat
        if self._active_chapter_id is not None:
            self.close_chapter(self._active_chapter_id)

        chapter = LifeChapter(
            title=title,
            description=description,
            status=LifeChapterStatus.ACTIVE,
            themes=themes or [],
        )

        self._chapters[chapter.id] = chapter
        self._active_chapter_id = chapter.id

        logger.info(
            "Yeni yasam bolumu olusturuldu: '%s' (id=%s)",
            title,
            chapter.id,
        )
        return chapter

    def close_chapter(self, chapter_id: str) -> LifeChapter | None:
        """Yasam bolumunu kapatir.

        Bolum durumunu CLOSED olarak degistirir ve bitis
        tarihini simdiki zaman olarak ayarlar.

        Args:
            chapter_id: Kapatilacak bolum ID'si.

        Returns:
            Kapatilmis LifeChapter veya bulunamazsa None.
        """
        chapter = self._chapters.get(chapter_id)
        if chapter is None:
            logger.warning("Bolum bulunamadi: %s", chapter_id)
            return None

        chapter.status = LifeChapterStatus.CLOSED
        chapter.end_date = datetime.now(timezone.utc)

        if self._active_chapter_id == chapter_id:
            self._active_chapter_id = None

        logger.info("Bolum kapatildi: '%s' (id=%s)", chapter.title, chapter_id)
        return chapter

    def add_episode_to_chapter(
        self,
        chapter_id: str,
        episode_id: str,
    ) -> bool:
        """Olayi bir yasam bolumune ekler.

        Args:
            chapter_id: Hedef bolum ID'si.
            episode_id: Eklenecek olay ID'si.

        Returns:
            Basarili ise True, bolum bulunamazsa False.
        """
        chapter = self._chapters.get(chapter_id)
        if chapter is None:
            logger.warning(
                "Olay eklenemedi: bolum %s bulunamadi", chapter_id
            )
            return False

        chapter.episode_ids.append(episode_id)
        logger.debug(
            "Olay bolume eklendi: episode=%s -> chapter='%s'",
            episode_id,
            chapter.title,
        )
        return True

    def get_chapter(self, chapter_id: str) -> LifeChapter | None:
        """Yasam bolumunu getirir.

        Args:
            chapter_id: Bolum ID'si.

        Returns:
            LifeChapter nesnesi veya bulunamazsa None.
        """
        return self._chapters.get(chapter_id)

    def build_narrative(self, chapter_id: str | None = None) -> str:
        """Kronolojik anlatim metni olusturur.

        Belirli bir bolum veya tum bolumleri kronolojik
        sirada gezerk anlatim olusturur. Epizodik hafiza
        mevcutsa olay detaylari eklenir.

        Args:
            chapter_id: Anlatim olusturulacak bolum ID (None ise tum bolumler).

        Returns:
            Formatlenmis anlatim metni.
        """
        if chapter_id is not None:
            chapters_to_narrate = []
            ch = self._chapters.get(chapter_id)
            if ch is not None:
                chapters_to_narrate.append(ch)
        else:
            # Tum bolumleri baslangic tarihine gore sirala
            chapters_to_narrate = sorted(
                self._chapters.values(),
                key=lambda c: c.start_date,
            )

        if not chapters_to_narrate:
            return ""

        lines: list[str] = []
        for chapter in chapters_to_narrate:
            lines.append(f"Chapter: {chapter.title}")

            if self._episodic is not None and chapter.episode_ids:
                for ep_id in chapter.episode_ids:
                    episode = self._episodic.recall(ep_id)
                    if episode is not None:
                        when_str = episode.when.strftime("%Y-%m-%d %H:%M")
                        where_str = episode.where if episode.where else "?"
                        lines.append(
                            f"  - {when_str}: {episode.what} ({where_str})"
                        )
            elif not chapter.episode_ids:
                lines.append(f"  ({chapter.description})")

        narrative = "\n".join(lines)
        logger.debug(
            "Anlatim olusturuldu: %d bolum, %d satir",
            len(chapters_to_narrate),
            len(lines),
        )
        return narrative

    def get_timeline(self) -> PersonalTimeline:
        """Kisisel zaman cizgisi olusturur.

        Tum bolumleri baslangic tarihine gore siralar,
        toplam olay sayisini hesaplar ve kimlik inanclarini ekler.

        Returns:
            PersonalTimeline nesnesi.
        """
        sorted_chapters = sorted(
            self._chapters.values(),
            key=lambda c: c.start_date,
        )

        total_episodes = sum(
            len(ch.episode_ids) for ch in sorted_chapters
        )

        timeline = PersonalTimeline(
            chapters=sorted_chapters,
            total_episodes=total_episodes,
            identity_beliefs=dict(self._identity),
        )

        logger.debug(
            "Zaman cizgisi olusturuldu: %d bolum, %d olay",
            len(sorted_chapters),
            total_episodes,
        )
        return timeline

    def update_identity(self, belief: str, strength_delta: float) -> float:
        """Kimlik inancini gunceller.

        Mevcut inanc gucune delta ekler ve 0.0-1.0 araligina
        keser (clamp). Inanc yoksa 0.0'dan baslar.

        Args:
            belief: Inanc adi.
            strength_delta: Guc degisimi (pozitif veya negatif).

        Returns:
            Guncel inanc gucu.
        """
        current = self._identity.get(belief, 0.0)
        new_value = max(0.0, min(1.0, current + strength_delta))
        self._identity[belief] = new_value

        logger.debug(
            "Kimlik inanci guncellendi: '%s' %.3f -> %.3f (delta=%.3f)",
            belief,
            current,
            new_value,
            strength_delta,
        )
        return new_value

    def get_identity(self) -> dict[str, float]:
        """Kimlik inanclarinin kopyasini dondurur.

        Returns:
            Inanc -> guc eslemesi sozlugu.
        """
        return dict(self._identity)

    def get_goal_relevant_memories(
        self,
        goal: str,
        limit: int = 10,
    ) -> list[Episode]:
        """Hedefle iliskili olaylari bulur.

        Hedef metnindeki anahtar kelimeler ile episode etiketleri,
        what alani ve context anahtarlari eslestirilir. Esleme puani
        yuksek olanlari dondurur.

        Args:
            goal: Hedef metni.
            limit: Maksimum sonuc sayisi.

        Returns:
            Puanina gore azalan sirali Episode listesi.
        """
        if self._episodic is None:
            return []

        keywords = set(goal.lower().split())
        if not keywords:
            return []

        scored: list[tuple[Episode, int]] = []

        for episode in self._episodic.get_timeline():
            score = 0

            # Etiketlerle eslesme
            for tag in episode.tags:
                if tag.lower() in keywords:
                    score += 1

            # what alani ile eslesme
            what_words = set(episode.what.lower().split())
            score += len(keywords & what_words)

            # Context anahtarlari ile eslesme
            for key in episode.context:
                if key.lower() in keywords:
                    score += 1

            if score > 0:
                scored.append((episode, score))

        # Puana gore azalan sirala
        scored.sort(key=lambda x: x[1], reverse=True)

        results = [ep for ep, _score in scored[:limit]]
        logger.debug(
            "Hedef iliskili hafiza arama: hedef='%s', %d sonuc",
            goal[:50],
            len(results),
        )
        return results

    def get_chapter_summary(self, chapter_id: str) -> dict | None:
        """Yasam bolumunun ozetini olusturur.

        Bolum basligi, durumu, olay sayisi, temalar, sure ve
        duygusal dagilim bilgilerini iceren sozluk dondurur.

        Args:
            chapter_id: Ozetlenecek bolum ID'si.

        Returns:
            Ozet sozlugu veya bolum bulunamazsa None.
        """
        chapter = self._chapters.get(chapter_id)
        if chapter is None:
            return None

        # Sure hesapla
        end = chapter.end_date or datetime.now(timezone.utc)
        duration_days = (end - chapter.start_date).days

        # Duygusal etiket ozeti
        emotions: dict[str, int] = {}
        if self._emotional is not None:
            for ep_id in chapter.episode_ids:
                associations = self._emotional.get_emotions(ep_id)
                for assoc in associations:
                    emotion_name = assoc.emotion.value
                    emotions[emotion_name] = emotions.get(emotion_name, 0) + 1

        summary = {
            "title": chapter.title,
            "status": chapter.status.value,
            "episode_count": len(chapter.episode_ids),
            "themes": list(chapter.themes),
            "duration_days": duration_days,
            "emotions": emotions,
        }

        logger.debug("Bolum ozeti olusturuldu: '%s'", chapter.title)
        return summary

    def count_chapters(self) -> int:
        """Toplam yasam bolumu sayisini dondurur.

        Returns:
            Kayitli bolum sayisi.
        """
        return len(self._chapters)
