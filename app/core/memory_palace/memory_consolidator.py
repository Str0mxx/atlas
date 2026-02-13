"""ATLAS Hafiza Pekistirme (Konsolidasyon) Sistemi.

Uyku benzeri pekistirme dongusu ile hafizalari guclendirir,
oruuntuleri cikarir, semalari olusturur ve onemsiz hatiralari
zayiflatir. Epizodik, unutma egrisi, duygusal ve iliskisel
alt sistemleri koordine eder.
"""

import logging
from collections import Counter
from datetime import datetime, timedelta, timezone
from itertools import combinations

from app.core.memory_palace.associative_network import AssociativeNetwork
from app.core.memory_palace.emotional_memory import EmotionalMemory
from app.core.memory_palace.episodic_memory import EpisodicMemory
from app.core.memory_palace.forgetting_curve import ForgettingCurve
from app.models.memory_palace import (
    ConsolidationCycle,
    ConsolidationPhase,
    Episode,
    MemoryStrength,
    MemoryType,
    Schema,
    SchemaType,
)

logger = logging.getLogger(__name__)


class MemoryConsolidator:
    """Hafiza pekistirme sistemi (uyku-benzeri konsolidasyon).

    Epizodik hatiralari periyodik olarak gozden gecirir,
    onemli olanlari guclendirir, onemsizleri zayiflatir
    ve tekrarlayan oruntulerden semalar cikarir.

    Attributes:
        _episodic: Epizodik hafiza alt sistemi.
        _forgetting_curve: Unutma egrisi alt sistemi.
        _emotional: Duygusal hafiza alt sistemi.
        _associative: Cagrisim agi alt sistemi.
        _cycles: Tamamlanan pekistirme donguleri.
        _schemas: Cikarilmis semalar (id -> Schema).
    """

    def __init__(
        self,
        episodic: EpisodicMemory | None = None,
        forgetting_curve: ForgettingCurve | None = None,
        emotional: EmotionalMemory | None = None,
        associative: AssociativeNetwork | None = None,
    ) -> None:
        """Pekistirme sistemini baslatir.

        Args:
            episodic: Epizodik hafiza alt sistemi.
            forgetting_curve: Unutma egrisi alt sistemi.
            emotional: Duygusal hafiza alt sistemi.
            associative: Cagrisim agi alt sistemi.
        """
        self._episodic = episodic
        self._forgetting_curve = forgetting_curve
        self._emotional = emotional
        self._associative = associative
        self._cycles: list[ConsolidationCycle] = []
        self._schemas: dict[str, Schema] = {}
        logger.info("Hafiza pekistirme sistemi baslatildi")

    def run_consolidation_cycle(self) -> ConsolidationCycle:
        """Tam pekistirme dongusu calistirir.

        Sirasyla:
        1. Son 24 saatteki hatiralari tekrar oynatir.
        2. Onemli hatiralari guclendirir (esik=0.7).
        3. Onemsiz hatiralari zayiflatir (esik=0.3).
        4. Tekrar oynatilanlardan oruntu cikarir.
        5. Dongu tamamlanma zamanini ayarlar.

        Returns:
            Tamamlanan pekistirme dongusu istatistikleri.
        """
        cycle = ConsolidationCycle(
            phase=ConsolidationPhase.CONSOLIDATION,
        )

        logger.info("Pekistirme dongusu baslatildi: %s", cycle.id)

        # 1. Son 24 saatteki hatiralari tekrar oynat
        replayed = self.replay_memories(recent_hours=24)
        cycle.memories_processed = len(replayed)

        # 2. Onemli hatiralari guclendirer
        strengthened = self.strengthen_important(importance_threshold=0.7)
        cycle.memories_strengthened = strengthened

        # 3. Onemsiz hatiralari zayiflat
        weakened = self.weaken_trivial(importance_threshold=0.3)
        cycle.memories_weakened = weakened

        # 4. Tekrar oynatilanlardan oruntu cikar
        patterns = self.extract_patterns(replayed)
        cycle.patterns_found = len(patterns)

        # 5. Donguyu tamamla
        cycle.completed_at = datetime.now(timezone.utc)
        self._cycles.append(cycle)

        logger.info(
            "Pekistirme dongusu tamamlandi: %s "
            "(islenen=%d, guclenen=%d, zayiflayan=%d, oruntu=%d)",
            cycle.id,
            cycle.memories_processed,
            cycle.memories_strengthened,
            cycle.memories_weakened,
            cycle.patterns_found,
        )
        return cycle

    def replay_memories(self, recent_hours: int = 24) -> list[Episode]:
        """Son N saatteki olaylari tekrar oynatir.

        Epizodik hafizadan zaman cizgisi araciligiyla son olaylari
        getirir ve her birini geri cagirarak erisim sayisini arttirir.

        Args:
            recent_hours: Kac saatlik gecmise bakilacagi.

        Returns:
            Tekrar oynanan Episode listesi.
        """
        if self._episodic is None:
            logger.debug("Epizodik hafiza yok, tekrar oynatma atlandi")
            return []

        now = datetime.now(timezone.utc)
        start = now - timedelta(hours=recent_hours)
        episodes = self._episodic.get_timeline(start=start, end=now)

        # Her olayi geri cagirarak erisim sayisini guncelle
        replayed: list[Episode] = []
        for episode in episodes:
            recalled = self._episodic.recall(episode.id)
            if recalled is not None:
                replayed.append(recalled)

        logger.info(
            "Hafiza tekrar oynandi: %d olay (son %d saat)",
            len(replayed),
            recent_hours,
        )
        return replayed

    def extract_patterns(self, episodes: list[Episode]) -> list[Schema]:
        """Olay listesinden tekrarlayan oruntuler cikarir.

        Her olay cifti icin etiket ortusme orani hesaplanir:
        overlap = |tags_a & tags_b| / min(|tags_a|, |tags_b|).
        Ortusme >= 0.5 olan ciftler gruplandiirilir. 3+ uyeli
        gruplardan sema olusturulur.

        Args:
            episodes: Oruntu aranacak Episode listesi.

        Returns:
            Cikarilmis Schema listesi.
        """
        if len(episodes) < 2:
            return []

        # Her episode cifti icin ortusme hesapla ve grupla
        groups: dict[str, list[Episode]] = {}
        assigned: set[str] = set()
        schemas_created: list[Schema] = []

        for ep_a, ep_b in combinations(episodes, 2):
            tags_a = set(ep_a.tags)
            tags_b = set(ep_b.tags)

            if not tags_a or not tags_b:
                continue

            overlap = len(tags_a & tags_b) / min(len(tags_a), len(tags_b))

            if overlap < 0.5:
                continue

            # Gruplama: ayni etiket kesisimini anahtar olarak kullan
            common_key = ",".join(sorted(tags_a & tags_b))
            if common_key not in groups:
                groups[common_key] = []

            if ep_a.id not in assigned:
                groups[common_key].append(ep_a)
                assigned.add(ep_a.id)
            if ep_b.id not in assigned:
                groups[common_key].append(ep_b)
                assigned.add(ep_b.id)

        # 3+ uyeli gruplardan sema olustur
        for _key, group_episodes in groups.items():
            if len(group_episodes) < 3:
                continue

            # En yaygin etiket
            all_tags: list[str] = []
            for ep in group_episodes:
                all_tags.extend(ep.tags)
            tag_counts = Counter(all_tags)
            most_common_tag = tag_counts.most_common(1)[0][0]

            # Ortak etiketler
            common_tags = set(group_episodes[0].tags)
            for ep in group_episodes[1:]:
                common_tags &= set(ep.tags)

            # Ortak context anahtarlari
            common_context_keys = set(group_episodes[0].context.keys())
            for ep in group_episodes[1:]:
                common_context_keys &= set(ep.context.keys())

            # Ortalama ortusme orani
            overlaps: list[float] = []
            for a, b in combinations(group_episodes, 2):
                t_a = set(a.tags)
                t_b = set(b.tags)
                if t_a and t_b:
                    overlaps.append(
                        len(t_a & t_b) / min(len(t_a), len(t_b))
                    )
            avg_overlap = sum(overlaps) / len(overlaps) if overlaps else 0.5

            pattern = {
                "common_tags": sorted(common_tags),
                "common_context_keys": sorted(common_context_keys),
            }
            source_ids = [ep.id for ep in group_episodes]

            schema = self.form_schema(
                pattern=pattern,
                source_ids=source_ids,
                name=most_common_tag,
            )
            schema.confidence = min(1.0, max(0.0, avg_overlap))
            schemas_created.append(schema)

        logger.info("Oruntu cikarildi: %d sema olusturuldu", len(schemas_created))
        return schemas_created

    def form_schema(
        self,
        pattern: dict,
        source_ids: list[str],
        name: str = "",
    ) -> Schema:
        """Verilen oruntu ve kaynaklardan sema olusturur.

        Args:
            pattern: Cikarilmis oruntu bilgisi.
            source_ids: Kaynak hafiza ID listesi.
            name: Sema adi (bos ise 'schema_N' kullanilir).

        Returns:
            Olusturulan Schema nesnesi.
        """
        schema_name = name or f"schema_{len(self._schemas)}"

        schema = Schema(
            name=schema_name,
            schema_type=SchemaType.EVENT_SCRIPT,
            pattern=pattern,
            source_memory_ids=list(source_ids),
            instance_count=len(source_ids),
        )

        self._schemas[schema.id] = schema

        logger.info(
            "Sema olusturuldu: %s (kaynak=%d, tip=%s)",
            schema_name,
            len(source_ids),
            SchemaType.EVENT_SCRIPT.value,
        )
        return schema

    def resolve_interference(self, memory_ids: list[str]) -> list[str]:
        """Catisan hatiralari tespit eder ve cozumler.

        Ayni yerde (where) ve 1 saatlik zaman penceresi icinde
        cakisan hatiralari bulur. Daha yuksek onemli olan korunur,
        esitlik durumunda erisim sayisi kriter olur.

        Args:
            memory_ids: Kontrol edilecek hafiza ID listesi.

        Returns:
            Korunan hafiza ID listesi.
        """
        if self._episodic is None:
            return list(memory_ids)

        # Episode bilgilerini topla
        episodes: dict[str, Episode] = {}
        for mid in memory_ids:
            ep = self._episodic.recall(mid)
            if ep is not None:
                episodes[mid] = ep

        removed: set[str] = set()
        episode_list = list(episodes.values())

        for ep_a, ep_b in combinations(episode_list, 2):
            if ep_a.id in removed or ep_b.id in removed:
                continue

            # Ayni yer kontrolu
            if not ep_a.where or not ep_b.where:
                continue
            if ep_a.where != ep_b.where:
                continue

            # Zaman penceresi kontrolu (1 saat)
            time_diff = abs((ep_a.when - ep_b.when).total_seconds())
            if time_diff > 3600:
                continue

            # Catisma bulundu: zayif olani kaldir
            if ep_a.importance > ep_b.importance:
                removed.add(ep_b.id)
            elif ep_b.importance > ep_a.importance:
                removed.add(ep_a.id)
            elif ep_a.access_count >= ep_b.access_count:
                removed.add(ep_b.id)
            else:
                removed.add(ep_a.id)

        kept = [mid for mid in memory_ids if mid not in removed]

        if removed:
            logger.info(
                "Catisma cozumlendi: %d korundu, %d cikarildi",
                len(kept),
                len(removed),
            )
        return kept

    def strengthen_important(self, importance_threshold: float = 0.7) -> int:
        """Onemli hatiralari unutma egrisinde guclendirir.

        Onemi esik degerine esit veya ustunde olan epizodik
        hatiralarin unutma egrisi kaydini gozden gecirir.

        Args:
            importance_threshold: Minimum onem esigi.

        Returns:
            Guclendirilen hafiza sayisi.
        """
        if self._episodic is None or self._forgetting_curve is None:
            return 0

        count = 0
        for episode in self._episodic.get_timeline():
            if episode.importance >= importance_threshold:
                trace = self._forgetting_curve.get_trace(episode.id)
                if trace is not None:
                    self._forgetting_curve.review(episode.id)
                    count += 1

        logger.info(
            "Onemli hatiralar guclendirildi: %d (esik=%.2f)",
            count,
            importance_threshold,
        )
        return count

    def weaken_trivial(self, importance_threshold: float = 0.3) -> int:
        """Onemsiz hatiralari zayiflatir.

        Onemi esik degerinin altinda olan ve hic erisilmemis
        (access_count == 0) hatiralarin hafiza gucunu WEAK
        olarak isaretler. Hafizadan silme yapmaz.

        Args:
            importance_threshold: Maksimum onem esigi.

        Returns:
            Zayiflatilan hafiza sayisi.
        """
        if self._episodic is None:
            return 0

        count = 0
        for episode in self._episodic.get_timeline():
            if (
                episode.importance < importance_threshold
                and episode.access_count == 0
            ):
                episode.memory_strength = MemoryStrength.WEAK
                count += 1

        logger.info(
            "Onemsiz hatiralar zayiflatildi: %d (esik=%.2f)",
            count,
            importance_threshold,
        )
        return count

    def get_schemas(self) -> list[Schema]:
        """Tum cikarilmis semalari dondurur.

        Returns:
            Schema listesi.
        """
        return list(self._schemas.values())

    def get_cycles(self) -> list[ConsolidationCycle]:
        """Tum pekistirme donguleri listesini dondurur.

        Returns:
            ConsolidationCycle listesi.
        """
        return list(self._cycles)
