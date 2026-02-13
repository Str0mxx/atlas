"""ATLAS Memory Palace Yoneticisi.

Tum hafiza alt sistemlerini (epizodik, prosedurel, duygusal, iliskisel,
calisma bellegi, unutma egrisi, pekistirme, otobiyografik) orkestre eder.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from app.core.memory_palace.associative_network import AssociativeNetwork
from app.core.memory_palace.autobiographical import AutobiographicalMemory
from app.core.memory_palace.emotional_memory import EmotionalMemory
from app.core.memory_palace.episodic_memory import EpisodicMemory
from app.core.memory_palace.forgetting_curve import ForgettingCurve
from app.core.memory_palace.memory_consolidator import MemoryConsolidator
from app.core.memory_palace.procedural_memory import ProceduralMemory
from app.core.memory_palace.working_memory import WorkingMemory
from app.models.memory_palace import (
    AssociationType,
    ConceptLink,
    ConsolidationCycle,
    EmotionType,
    MemoryPalaceStats,
    MemorySearchQuery,
    MemorySearchResult,
    MemoryType,
    WorkingMemoryItem,
)

logger = logging.getLogger(__name__)


class MemoryPalaceManager:
    """Tum Memory Palace alt sistemlerini yoneten orkestrator.

    Attributes:
        episodic: Epizodik (olay) hafiza.
        procedural: Prosedurel (beceri) hafiza.
        emotional: Duygusal hafiza.
        forgetting_curve: Unutma egrisi.
        associative: Iliskisel ag.
        working_memory: Calisma bellegi.
        consolidator: Hafiza pekistirici.
        autobiographical: Otobiyografik hafiza.
    """

    def __init__(
        self,
        max_working_memory: int = 7,
        forgetting_rate: float = 0.1,
        emotional_weight: float = 0.3,
        consolidation_interval: int = 3600,
    ) -> None:
        """Memory Palace yoneticisini baslatir.

        Args:
            max_working_memory: Calisma bellegi kapasitesi.
            forgetting_rate: Temel unutma orani.
            emotional_weight: Duygusal agirlik faktoru.
            consolidation_interval: Pekistirme araligi (saniye).
        """
        self.episodic = EpisodicMemory()
        self.procedural = ProceduralMemory()
        self.emotional = EmotionalMemory(emotional_weight=emotional_weight)
        self.forgetting_curve = ForgettingCurve(base_forgetting_rate=forgetting_rate)
        self.associative = AssociativeNetwork()
        self.working_memory = WorkingMemory(capacity=max_working_memory)
        self.consolidator = MemoryConsolidator(
            episodic=self.episodic,
            forgetting_curve=self.forgetting_curve,
            emotional=self.emotional,
            associative=self.associative,
        )
        self.autobiographical = AutobiographicalMemory(
            episodic=self.episodic,
            emotional=self.emotional,
        )
        self._consolidation_interval = consolidation_interval
        self._last_consolidation: datetime | None = None
        logger.info(
            "MemoryPalaceManager baslatildi (wm=%d, forget=%.2f, emo=%.2f, cons=%ds)",
            max_working_memory, forgetting_rate, emotional_weight, consolidation_interval,
        )

    def encode(
        self,
        content: str,
        memory_type: MemoryType,
        importance: float = 0.5,
        emotion: EmotionType | None = None,
        emotion_intensity: float = 0.5,
        context: dict[str, Any] | None = None,
    ) -> str:
        """Yeni bilgiyi uygun alt sisteme yonlendirir.

        Args:
            content: Kodlanacak icerik.
            memory_type: Hedef hafiza tipi.
            importance: Onem derecesi (0.0-1.0).
            emotion: Opsiyonel duygu etiketi.
            emotion_intensity: Duygu yogunlugu.
            context: Ek baglamsal bilgi.

        Returns:
            Olusturulan hafiza ID'si.
        """
        ctx = context or {}
        memory_id = self._route_to_subsystem(content, memory_type, importance=importance, context=ctx)
        # Unutma egrisi kaydı
        if memory_type in {MemoryType.EPISODIC, MemoryType.AUTOBIOGRAPHICAL}:
            self.forgetting_curve.register_memory(memory_id, memory_type, importance=importance)
        # Duygusal etiketleme
        if emotion is not None:
            self.emotional.tag_memory(memory_id, emotion, intensity=emotion_intensity)
        logger.info("Hafiza kodlandi: id=%s, tip=%s, onem=%.2f", memory_id, memory_type.value, importance)
        return memory_id

    def retrieve(self, memory_id: str, memory_type: MemoryType) -> dict[str, Any] | None:
        """Belirtilen hafizayi getirir ve unutma egrisi uygular.

        Args:
            memory_id: Hafiza kimlik numarasi.
            memory_type: Hafiza tipi.

        Returns:
            Hafiza icerigi veya None.
        """
        result: dict[str, Any] | None = None
        if memory_type == MemoryType.EPISODIC:
            episode = self.episodic.recall(memory_id)
            if episode:
                result = episode.model_dump()
        elif memory_type == MemoryType.PROCEDURAL:
            skill = self.procedural.retrieve_skill(memory_id)
            if skill:
                result = skill.model_dump()
        elif memory_type == MemoryType.WORKING:
            item = self.working_memory.get(memory_id)
            if item:
                result = item.model_dump()
        if result is not None:
            # Unutma egrisi gucu ekle
            retention = self.forgetting_curve.calculate_retention(memory_id)
            result["_retention"] = retention
            # Duygusal etiketler ekle
            emotions = self.emotional.get_emotions(memory_id)
            if emotions:
                result["_emotions"] = [e.model_dump() for e in emotions]
            logger.debug("Hafiza getirildi: id=%s, tip=%s", memory_id, memory_type.value)
        return result

    def search(self, query: MemorySearchQuery) -> list[MemorySearchResult]:
        """Tum alt sistemlerde paralel arama yapar.

        Args:
            query: Arama sorgusu.

        Returns:
            Birlestirilmis ve siralanmis arama sonuclari.
        """
        results: list[MemorySearchResult] = []
        search_types = query.memory_types or list(MemoryType)
        keywords = set(query.query.lower().split())

        # Epizodik arama
        if MemoryType.EPISODIC in search_types:
            for ep_id, episode in self.episodic._episodes.items():
                score = self._calculate_relevance(keywords, episode.what, episode.tags, episode.context)
                if score >= query.min_relevance:
                    emotional_tag = None
                    if query.include_emotional:
                        emotions = self.emotional.get_emotions(ep_id)
                        emotional_tag = emotions[0] if emotions else None
                    if query.mood_filter and emotional_tag:
                        if emotional_tag.emotion != query.mood_filter:
                            continue
                    retention = self.forgetting_curve.calculate_retention(ep_id)
                    results.append(MemorySearchResult(
                        memory_id=ep_id, memory_type=MemoryType.EPISODIC,
                        content={"what": episode.what, "where": episode.where},
                        relevance=score, emotional_tag=emotional_tag, strength=retention,
                    ))

        # Prosedurel arama
        if MemoryType.PROCEDURAL in search_types:
            for sk_id, skill in self.procedural._skills.items():
                score = self._calculate_relevance(keywords, skill.name, [skill.domain], {})
                if score >= query.min_relevance:
                    results.append(MemorySearchResult(
                        memory_id=sk_id, memory_type=MemoryType.PROCEDURAL,
                        content={"name": skill.name, "domain": skill.domain},
                        relevance=score,
                    ))

        # Siralanmis ve sinirlandirilmis sonuclar
        results.sort(key=lambda r: r.relevance, reverse=True)
        logger.debug("Hafiza arama: sorgu='%s', sonuc=%d", query.query, len(results))
        return results[:query.limit]

    def associate(
        self,
        memory_id_a: str,
        memory_id_b: str,
        weight: float = 0.5,
        association_type: AssociationType = AssociationType.SEMANTIC,
    ) -> ConceptLink | None:
        """Iki hafiza arasinda iliskisel baglanti kurar.

        Args:
            memory_id_a: Birinci hafiza ID.
            memory_id_b: Ikinci hafiza ID.
            weight: Baglanti gucu.
            association_type: Iliski tipi.

        Returns:
            Olusturulan baglanti veya None.
        """
        # Kavramlarin var oldugundan emin ol
        node_a = self.associative.get_concept(memory_id_a)
        if node_a is None:
            node_a = self.associative.add_concept(memory_id_a, category="memory")
        node_b = self.associative.get_concept(memory_id_b)
        if node_b is None:
            node_b = self.associative.add_concept(memory_id_b, category="memory")
        link = self.associative.link_concepts(node_a.id, node_b.id, weight, association_type)
        if link:
            logger.debug("Iliski kuruldu: %s <-> %s (agirlik=%.2f)", memory_id_a, memory_id_b, weight)
        return link

    def consolidate(self) -> ConsolidationCycle | None:
        """Pekistirme dongusunu tetikler (aralik kontrolu ile).

        Returns:
            Pekistirme dongusu sonucu veya None (cok erken ise).
        """
        now = datetime.now(timezone.utc)
        if self._last_consolidation is not None:
            elapsed = (now - self._last_consolidation).total_seconds()
            if elapsed < self._consolidation_interval:
                logger.debug("Pekistirme atlanıyor: %.0f/%ds", elapsed, self._consolidation_interval)
                return None
        cycle = self.consolidator.run_consolidation_cycle()
        self._last_consolidation = now
        logger.info(
            "Pekistirme dongusu tamamlandi: islenen=%d, oruntu=%d",
            cycle.memories_processed, cycle.patterns_found,
        )
        return cycle

    def force_consolidate(self) -> ConsolidationCycle:
        """Aralik kontrolu olmadan pekistirme dongusunu zorla calistirir.

        Returns:
            Pekistirme dongusu sonucu.
        """
        cycle = self.consolidator.run_consolidation_cycle()
        self._last_consolidation = datetime.now(timezone.utc)
        logger.info("Zorla pekistirme tamamlandi: islenen=%d", cycle.memories_processed)
        return cycle

    def get_stats(self) -> MemoryPalaceStats:
        """Tum alt sistem istatistiklerini toplar.

        Returns:
            Birlestirilmis istatistikler.
        """
        # Ortalama hafiza gucu
        decay_map = self.forgetting_curve.decay_all()
        avg_strength = sum(decay_map.values()) / len(decay_map) if decay_map else 0.0
        # Calisma bellegi kullanimi
        wm_state = self.working_memory.get_state()
        wm_usage = wm_state.current_load

        stats = MemoryPalaceStats(
            total_episodes=self.episodic.count(),
            total_skills=self.procedural.count(),
            total_concepts=self.associative.count_nodes(),
            total_associations=self.associative.count_links(),
            working_memory_usage=wm_usage,
            avg_memory_strength=round(avg_strength, 4),
            consolidation_cycles=len(self.consolidator.get_cycles()),
        )
        return stats

    def load_to_working_memory(
        self,
        memory_id: str,
        memory_type: MemoryType,
        priority: float = 0.5,
    ) -> WorkingMemoryItem | None:
        """Uzun sureli hafizadan calisma bellegine yukler.

        Args:
            memory_id: Hafiza ID.
            memory_type: Hafiza tipi.
            priority: Calisma bellegi onceligi.

        Returns:
            Eklenen calisma bellegi ogesi veya None.
        """
        content = self.retrieve(memory_id, memory_type)
        if content is None:
            return None
        item = self.working_memory.add(content=content, priority=priority)
        if item:
            logger.debug("Calisma bellegine yuklendi: %s -> %s", memory_id, item.id)
        return item

    def _route_to_subsystem(
        self,
        content: str,
        memory_type: MemoryType,
        **kwargs: Any,
    ) -> str:
        """Icerigi uygun alt sisteme yonlendirir.

        Args:
            content: Kodlanacak icerik.
            memory_type: Hedef hafiza tipi.
            **kwargs: Ek parametreler.

        Returns:
            Olusturulan hafiza ID'si.
        """
        if memory_type == MemoryType.EPISODIC:
            importance = kwargs.get("importance", 0.5)
            ctx = kwargs.get("context", {})
            episode = self.episodic.store(
                what=content, importance=importance,
                context=ctx,
                where=ctx.get("where", ""),
                who=ctx.get("who"),
                tags=ctx.get("tags"),
            )
            return episode.id

        if memory_type == MemoryType.PROCEDURAL:
            ctx = kwargs.get("context", {})
            skill = self.procedural.register_skill(
                name=content,
                domain=ctx.get("domain", ""),
                steps=ctx.get("steps"),
            )
            return skill.id

        if memory_type == MemoryType.WORKING:
            item = self.working_memory.add(content=content)
            return item.id if item else ""

        if memory_type == MemoryType.AUTOBIOGRAPHICAL:
            importance = kwargs.get("importance", 0.5)
            ctx = kwargs.get("context", {})
            episode = self.episodic.store(
                what=content, importance=importance, context=ctx,
            )
            if self.autobiographical._active_chapter_id:
                self.autobiographical.add_episode_to_chapter(
                    self.autobiographical._active_chapter_id, episode.id,
                )
            return episode.id

        # Fallback: epizodik olarak kaydet
        episode = self.episodic.store(what=content)
        return episode.id

    def _calculate_relevance(
        self,
        keywords: set[str],
        text: str,
        tags: list[str],
        context: dict[str, Any],
    ) -> float:
        """Anahtar kelime eslesmesiyle ilgi puani hesaplar.

        Args:
            keywords: Arama anahtar kelimeleri.
            text: Metin icerigi.
            tags: Etiketler.
            context: Baglamsal bilgi.

        Returns:
            Ilgi puani (0.0-1.0).
        """
        if not keywords:
            return 0.0
        text_words = set(text.lower().split())
        tag_words = {t.lower() for t in tags}
        context_words = set()
        for v in context.values():
            if isinstance(v, str):
                context_words.update(v.lower().split())
        all_words = text_words | tag_words | context_words
        matches = len(keywords & all_words)
        return min(1.0, matches / len(keywords))
