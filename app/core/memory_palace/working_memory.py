"""ATLAS Calisma bellegi modulu.

Sinirli kapasiteli calisma bellegi, bilissel yuk yonetimi,
chunking (gruplama), onceliklendirme ve eviction (cikarma).
"""

import logging
from datetime import datetime, timezone
from typing import Any, Callable
from uuid import uuid4

from app.models.memory_palace import (
    WorkingMemoryItem,
    WorkingMemoryState,
)

logger = logging.getLogger(__name__)


class WorkingMemory:
    """Calisma bellegi sistemi (sinirli kapasite).

    Insan calisma bellegini modeller: sinirli slot sayisi,
    bilissel yuk limiti, chunking ile kapasite artirimi
    ve oncelik bazli cikarma mekanizmasi.

    Attributes:
        _items: Mevcut ogeler (id -> WorkingMemoryItem).
        _capacity: Maksimum slot sayisi.
        _max_load: Maksimum bilissel yuk.
        _chunks: Gruplama bilgisi (chunk_id -> [item_ids]).
    """

    def __init__(
        self,
        capacity: int = 7,
        max_cognitive_load: float = 1.0,
    ) -> None:
        self._items: dict[str, WorkingMemoryItem] = {}
        self._capacity = capacity
        self._max_load = max_cognitive_load
        self._chunks: dict[str, list[str]] = {}

    def add(
        self,
        content: Any,
        priority: float = 0.5,
        cognitive_load: float = 0.1,
    ) -> WorkingMemoryItem | None:
        """Calisma bellegine oge ekler.

        Bilissel yuk limiti asilacaksa ekleme reddedilir.
        Kapasite doluysa en dusuk oncelikli (en eski) oge cikarilir.

        Args:
            content: Oge icerigi.
            priority: Oncelik degeri (0.0-1.0).
            cognitive_load: Bilissel yuk degeri (0.0-1.0).

        Returns:
            Eklenen WorkingMemoryItem veya yuk asimi durumunda None.
        """
        new_total_load = self.current_load() + cognitive_load
        if new_total_load > self._max_load:
            logger.warning(
                "Bilissel yuk asimi: mevcut=%.2f, ek=%.2f, maks=%.2f",
                self.current_load(),
                cognitive_load,
                self._max_load,
            )
            return None

        # Kapasite kontrolu ve cikarma
        while self._effective_item_count() >= self._capacity:
            evict_id = self._find_eviction_target()
            if evict_id is None:
                break
            self.remove(evict_id)
            logger.debug("Kapasite icin oge cikarildi: %s", evict_id)

        item = WorkingMemoryItem(
            content=content,
            priority=priority,
            cognitive_load=cognitive_load,
        )
        self._items[item.id] = item

        logger.info(
            "Oge eklendi: %s (oncelik=%.2f, yuk=%.2f)",
            item.id,
            priority,
            cognitive_load,
        )
        return item

    def remove(self, item_id: str) -> bool:
        """Ogeyi calisma belleginden cikarir.

        Oge bir chunk'a aitse, chunk'tan da cikarilir.

        Args:
            item_id: Cikarilacak oge ID.

        Returns:
            Basariyla cikarildiysa True, bulunamadiysa False.
        """
        if item_id not in self._items:
            return False

        item = self._items[item_id]

        # Chunk'tan cikar
        if item.chunk_id and item.chunk_id in self._chunks:
            chunk_items = self._chunks[item.chunk_id]
            if item_id in chunk_items:
                chunk_items.remove(item_id)
            # Bos chunk'u temizle
            if not chunk_items:
                del self._chunks[item.chunk_id]

        del self._items[item_id]
        logger.debug("Oge cikarildi: %s", item_id)
        return True

    def get(self, item_id: str) -> WorkingMemoryItem | None:
        """Ogeyi getirir ve erisim zamanini gunceller.

        Args:
            item_id: Getirilecek oge ID.

        Returns:
            WorkingMemoryItem veya bulunamazsa None.
        """
        item = self._items.get(item_id)
        if item is None:
            return None

        item.accessed_at = datetime.now(timezone.utc)
        return item

    def focus(
        self,
        item_id: str,
        new_priority: float = 1.0,
    ) -> WorkingMemoryItem | None:
        """Ogenin onceligi gunceller (odaklanma).

        Args:
            item_id: Odaklanilacak oge ID.
            new_priority: Yeni oncelik degeri (0.0-1.0).

        Returns:
            Guncellenen WorkingMemoryItem veya bulunamazsa None.
        """
        item = self._items.get(item_id)
        if item is None:
            return None

        item.priority = new_priority
        item.accessed_at = datetime.now(timezone.utc)

        logger.debug("Odaklanma: %s -> oncelik=%.2f", item_id, new_priority)
        return item

    def chunk(
        self,
        item_ids: list[str],
        chunk_label: str = "",
    ) -> str | None:
        """Ogeleri bir grup (chunk) altinda birlestirir.

        Gruplanan ogeler kapasite hesaplamasinda tek slot olarak sayilir.
        Tum oge ID'leri gecerli olmalidir.

        Args:
            item_ids: Gruplanacak oge ID listesi.
            chunk_label: Grup etiketi (bilgilendirme amacli).

        Returns:
            Olusturulan chunk_id veya herhangi bir oge bulunamazsa None.
        """
        for item_id in item_ids:
            if item_id not in self._items:
                logger.warning("Chunking basarisiz: oge bulunamadi %s", item_id)
                return None

        chunk_id = str(uuid4())
        self._chunks[chunk_id] = list(item_ids)

        for item_id in item_ids:
            self._items[item_id].chunk_id = chunk_id

        logger.info(
            "Chunk olusturuldu: %s (%d oge, etiket='%s')",
            chunk_id,
            len(item_ids),
            chunk_label,
        )
        return chunk_id

    def unchunk(self, chunk_id: str) -> list[WorkingMemoryItem]:
        """Grubu cozer, ogeleri bagimsiz hale getirir.

        Her ogenin chunk_id alani None olarak ayarlanir.
        Ogeler artik kapasitede ayri ayri sayilir.

        Args:
            chunk_id: Cozulecek grup ID.

        Returns:
            Gruptaki WorkingMemoryItem listesi.
        """
        item_ids = self._chunks.pop(chunk_id, [])
        unchunked: list[WorkingMemoryItem] = []

        for item_id in item_ids:
            item = self._items.get(item_id)
            if item is not None:
                item.chunk_id = None
                unchunked.append(item)

        logger.info("Chunk cozuldu: %s (%d oge)", chunk_id, len(unchunked))
        return unchunked

    def manipulate(
        self,
        item_id: str,
        transform: Callable[[Any], Any],
    ) -> WorkingMemoryItem | None:
        """Oge icerigine donusum uygular.

        Args:
            item_id: Donusturulecek oge ID.
            transform: Icerige uygulanacak fonksiyon.

        Returns:
            Guncellenen WorkingMemoryItem veya bulunamazsa None.
        """
        item = self._items.get(item_id)
        if item is None:
            return None

        item.content = transform(item.content)
        item.accessed_at = datetime.now(timezone.utc)

        logger.debug("Oge manipule edildi: %s", item_id)
        return item

    def get_state(self) -> WorkingMemoryState:
        """Calisma belleginin mevcut durumunu dondurur.

        Returns:
            WorkingMemoryState nesnesi.
        """
        return WorkingMemoryState(
            items=list(self._items.values()),
            capacity=self._capacity,
            current_load=self.current_load(),
            chunks={
                chunk_id: list(item_ids)
                for chunk_id, item_ids in self._chunks.items()
            },
        )

    def available_capacity(self) -> int:
        """Kullanilabilir slot sayisini dondurur.

        Chunk'taki ogeler tek slot olarak sayilir.

        Returns:
            Bos slot sayisi.
        """
        return self._capacity - self._effective_item_count()

    def current_load(self) -> float:
        """Toplam bilissel yuku hesaplar.

        Returns:
            Tum ogelerin bilissel yukleri toplami.
        """
        return sum(item.cognitive_load for item in self._items.values())

    def clear(self) -> int:
        """Tum ogeleri ve chunklari temizler.

        Returns:
            Temizlenen oge sayisi.
        """
        count = len(self._items)
        self._items.clear()
        self._chunks.clear()

        logger.info("Calisma bellegi temizlendi: %d oge", count)
        return count

    def _effective_item_count(self) -> int:
        """Efektif oge sayisini hesaplar.

        Chunk'a ait ogeler grup basina tek slot olarak sayilir.
        Chunk'siz ogeler ayri ayri sayilir.

        Returns:
            Efektif slot kullanimi.
        """
        # Chunk'a ait olan ogelerin ID seti
        chunked_item_ids: set[str] = set()
        for item_ids in self._chunks.values():
            chunked_item_ids.update(item_ids)

        # Bagimsiz ogeler (chunk'a ait olmayanlar)
        standalone_count = sum(
            1 for item_id in self._items
            if item_id not in chunked_item_ids
        )

        # Her chunk bir slot
        chunk_count = len(self._chunks)

        return standalone_count + chunk_count

    def _find_eviction_target(self) -> str | None:
        """Cikarma icin en uygun ogeyi bulur.

        Chunk'siz ogeler arasindan en dusuk oncelikli olani secer.
        Esit onceliklerde en eski (added_at) olan tercih edilir.

        Returns:
            Cikarilacak oge ID veya uygun oge yoksa None.
        """
        # Chunk'a ait ogelerin ID seti
        chunked_item_ids: set[str] = set()
        for item_ids in self._chunks.values():
            chunked_item_ids.update(item_ids)

        target_id: str | None = None
        target_priority: float = float("inf")
        target_added: datetime | None = None

        for item_id, item in self._items.items():
            if item_id in chunked_item_ids:
                continue

            if (
                item.priority < target_priority
                or (
                    item.priority == target_priority
                    and target_added is not None
                    and item.added_at < target_added
                )
            ):
                target_id = item_id
                target_priority = item.priority
                target_added = item.added_at

        return target_id
