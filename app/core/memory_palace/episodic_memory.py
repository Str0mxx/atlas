"""ATLAS Epizodik hafiza modulu.

Olay bazli hafiza kaydi, geri cagirma, kronolojik zaman
cizgisi, flashbulb hafiza ve konsolidasyon islemleri.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from app.models.memory_palace import (
    Episode,
    EpisodeQuery,
    MemoryStrength,
)

logger = logging.getLogger(__name__)


class EpisodicMemory:
    """Olay (epizodik) hafiza sistemi.

    Yasanan olaylari kronolojik olarak kayit eder,
    onem derecesine gore flashbulb hafiza olusturur
    ve dusuk onemli olaylari konsolide eder.

    Attributes:
        _episodes: Kayitli olaylar (id -> Episode).
        _timeline: Episode ID'ler kronolojik sirayla.
        _flashbulb_threshold: Flashbulb hafiza esigi.
    """

    def __init__(self, flashbulb_threshold: float = 0.9) -> None:
        self._episodes: dict[str, Episode] = {}
        self._timeline: list[str] = []
        self._flashbulb_threshold = flashbulb_threshold

    def store(
        self,
        what: str,
        where: str = "",
        who: list[str] | None = None,
        importance: float = 0.5,
        tags: list[str] | None = None,
        context: dict[str, Any] | None = None,
    ) -> Episode:
        """Yeni olay kaydeder.

        importance >= flashbulb_threshold ise is_flashbulb=True olarak
        isaretlenir ve memory_strength FLASHBULB olarak ayarlanir.

        Args:
            what: Ne oldugu.
            where: Nerede oldugu.
            who: Katilimcilar listesi.
            importance: Onem derecesi (0.0-1.0).
            tags: Olay etiketleri.
            context: Ek baglamsal bilgi.

        Returns:
            Olusturulan Episode nesnesi.
        """
        is_flashbulb = importance >= self._flashbulb_threshold

        if is_flashbulb:
            strength = MemoryStrength.FLASHBULB
        elif importance >= 0.7:
            strength = MemoryStrength.STRONG
        elif importance >= 0.4:
            strength = MemoryStrength.MODERATE
        else:
            strength = MemoryStrength.WEAK

        episode = Episode(
            what=what,
            where=where,
            who=who or [],
            importance=importance,
            tags=tags or [],
            context=context or {},
            is_flashbulb=is_flashbulb,
            memory_strength=strength,
        )

        self._episodes[episode.id] = episode
        self._insert_into_timeline(episode)

        logger.info(
            "Olay kaydedildi: %s (onem=%.2f, flashbulb=%s)",
            episode.id,
            importance,
            is_flashbulb,
        )
        return episode

    def recall(self, episode_id: str) -> Episode | None:
        """Episode'u getirir ve erisim bilgilerini gunceller.

        Her cagirildiginda access_count bir arttirilir ve
        last_accessed simdi olarak ayarlanir.

        Args:
            episode_id: Getirilecek olayin ID'si.

        Returns:
            Episode nesnesi veya bulunamazsa None.
        """
        episode = self._episodes.get(episode_id)
        if episode is None:
            return None

        episode.access_count += 1
        episode.last_accessed = datetime.now(timezone.utc)

        logger.debug(
            "Olay geri cagirildi: %s (erisim=%d)",
            episode_id,
            episode.access_count,
        )
        return episode

    def query(self, query: EpisodeQuery) -> list[Episode]:
        """Filtreli arama yapar.

        Zaman araligi, konum, katilimci, etiket ve minimum
        onem kriterlerine gore filtreler. Sonuclar onem
        derecesine gore azalan sirada dondurulur.

        Args:
            query: Arama sorgusu parametreleri.

        Returns:
            Filtrelenmis ve siralanmis Episode listesi.
        """
        results: list[Episode] = []

        for episode in self._episodes.values():
            if not self._matches_query(episode, query):
                continue
            results.append(episode)

        # Oneme gore azalan sirada sirala
        results.sort(key=lambda e: e.importance, reverse=True)

        return results[: query.limit]

    def get_timeline(
        self,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[Episode]:
        """Kronolojik olay listesi dondurur.

        Opsiyonel zaman filtreleri ile belirli bir aralik
        icerisindeki olaylari getirir.

        Args:
            start: Baslangic zamani filtresi.
            end: Bitis zamani filtresi.

        Returns:
            Kronolojik sirali Episode listesi.
        """
        results: list[Episode] = []

        for episode_id in self._timeline:
            episode = self._episodes.get(episode_id)
            if episode is None:
                continue

            if start is not None and episode.when < start:
                continue
            if end is not None and episode.when > end:
                continue

            results.append(episode)

        return results

    def get_flashbulb_memories(self) -> list[Episode]:
        """Flashbulb (parlak) hafizalari dondurur.

        Returns:
            is_flashbulb=True olan Episode listesi.
        """
        return [
            episode
            for episode in self._episodes.values()
            if episode.is_flashbulb
        ]

    def consolidate(self, importance_threshold: float = 0.3) -> int:
        """Dusuk onemli ve hic erisilmemis olaylari siler.

        importance < threshold VE access_count == 0 olan
        olaylar hafizadan kaldirilir.

        Args:
            importance_threshold: Minimum onem esigi.

        Returns:
            Silinen olay sayisi.
        """
        to_remove: list[str] = []

        for episode_id, episode in self._episodes.items():
            if (
                episode.importance < importance_threshold
                and episode.access_count == 0
            ):
                to_remove.append(episode_id)

        for episode_id in to_remove:
            del self._episodes[episode_id]
            if episode_id in self._timeline:
                self._timeline.remove(episode_id)

        if to_remove:
            logger.info(
                "Konsolidasyon: %d olay silindi (esik=%.2f)",
                len(to_remove),
                importance_threshold,
            )

        return len(to_remove)

    def count(self) -> int:
        """Toplam olay sayisini dondurur.

        Returns:
            Kayitli Episode sayisi.
        """
        return len(self._episodes)

    def _insert_into_timeline(self, episode: Episode) -> None:
        """Episode'u kronolojik zaman cizgisine ekler.

        Binary search ile dogru konumu bulur ve ekler,
        boylece _timeline her zaman sirali kalir.

        Args:
            episode: Eklenecek Episode nesnesi.
        """
        when = episode.when
        lo = 0
        hi = len(self._timeline)

        while lo < hi:
            mid = (lo + hi) // 2
            mid_episode = self._episodes.get(self._timeline[mid])
            if mid_episode is not None and mid_episode.when <= when:
                lo = mid + 1
            else:
                hi = mid

        self._timeline.insert(lo, episode.id)

    def _matches_query(self, episode: Episode, query: EpisodeQuery) -> bool:
        """Episode'un arama kriterlerine uyup uymadigini kontrol eder.

        Args:
            episode: Kontrol edilecek Episode.
            query: Arama sorgusu.

        Returns:
            Kriterlere uyuyorsa True.
        """
        # Zaman filtresi
        if query.time_start is not None and episode.when < query.time_start:
            return False
        if query.time_end is not None and episode.when > query.time_end:
            return False

        # Konum filtresi (icerme kontrolu)
        if query.location and query.location.lower() not in episode.where.lower():
            return False

        # Katilimci filtresi (kesisim kontrolu)
        if query.participants:
            episode_who_set = set(episode.who)
            query_who_set = set(query.participants)
            if not episode_who_set.intersection(query_who_set):
                return False

        # Etiket filtresi (kesisim kontrolu)
        if query.tags:
            episode_tag_set = set(episode.tags)
            query_tag_set = set(query.tags)
            if not episode_tag_set.intersection(query_tag_set):
                return False

        # Minimum onem filtresi
        if episode.importance < query.min_importance:
            return False

        return True
