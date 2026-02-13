"""ATLAS Cagrisimsal (iliskisel) ag modulu.

Kavram dugumleri arasi baglanti, yayilan aktivasyon,
yaratici baglanti kesfi, priming ve en kisa yol bulma.
"""

import logging
from collections import deque
from uuid import uuid4

from app.models.memory_palace import (
    ActivationResult,
    AssociationType,
    ConceptLink,
    ConceptNode,
)

logger = logging.getLogger(__name__)


class AssociativeNetwork:
    """Cagrisim (iliskisel) ag sistemi.

    Kavramlar arasi semantik, zamansal, nedensel ve duygusal
    baglantilari modeller. Yayilan aktivasyon ile iliskili
    kavramlari kesfeder ve yaratici baglantilar bulur.

    Attributes:
        _nodes: Kavram dugumleri (id -> ConceptNode).
        _links: Giden baglantilar (source_id -> [ConceptLink]).
        _reverse_links: Gelen baglantilar (target_id -> [ConceptLink]).
        _decay_factor: Aktivasyon azalma carpani.
        _activation_threshold: Minimum aktivasyon esigi.
    """

    def __init__(
        self,
        decay_factor: float = 0.8,
        activation_threshold: float = 0.1,
    ) -> None:
        self._nodes: dict[str, ConceptNode] = {}
        self._links: dict[str, list[ConceptLink]] = {}
        self._reverse_links: dict[str, list[ConceptLink]] = {}
        self._decay_factor = decay_factor
        self._activation_threshold = activation_threshold

    def add_concept(
        self,
        name: str,
        category: str = "",
        metadata: dict | None = None,
    ) -> ConceptNode:
        """Yeni kavram dugumu ekler.

        Args:
            name: Kavram adi.
            category: Kavram kategorisi.
            metadata: Ek bilgi sozlugu.

        Returns:
            Olusturulan ConceptNode nesnesi.
        """
        node = ConceptNode(
            name=name,
            category=category,
            metadata=metadata or {},
        )
        self._nodes[node.id] = node
        self._links[node.id] = []
        self._reverse_links[node.id] = []

        logger.info("Kavram eklendi: %s (id=%s)", name, node.id)
        return node

    def get_concept(self, node_id: str) -> ConceptNode | None:
        """Kavram dugumu getirir.

        Args:
            node_id: Dugum kimlik numarasi.

        Returns:
            ConceptNode nesnesi veya bulunamazsa None.
        """
        return self._nodes.get(node_id)

    def get_concept_by_name(self, name: str) -> ConceptNode | None:
        """Isme gore kavram bulur.

        Args:
            name: Aranacak kavram adi.

        Returns:
            Eslesen ilk ConceptNode veya bulunamazsa None.
        """
        for node in self._nodes.values():
            if node.name == name:
                return node
        return None

    def link_concepts(
        self,
        source_id: str,
        target_id: str,
        weight: float = 0.5,
        association_type: AssociationType = AssociationType.SEMANTIC,
    ) -> ConceptLink | None:
        """Iki kavram arasinda baglanti olusturur.

        Kaynak ve hedef dugumlerin her ikisi de mevcut olmalidir.
        Baglanti hem _links (kaynak) hem _reverse_links (hedef) altinda saklanir.

        Args:
            source_id: Kaynak dugum ID.
            target_id: Hedef dugum ID.
            weight: Baglanti gucu (0.0-1.0).
            association_type: Iliski tipi.

        Returns:
            Olusturulan ConceptLink veya dugum bulunamazsa None.
        """
        if source_id not in self._nodes or target_id not in self._nodes:
            logger.warning(
                "Baglanti olusturulamadi: kaynak=%s, hedef=%s",
                source_id,
                target_id,
            )
            return None

        link = ConceptLink(
            source_id=source_id,
            target_id=target_id,
            weight=weight,
            association_type=association_type,
        )
        self._links[source_id].append(link)
        self._reverse_links[target_id].append(link)

        logger.debug(
            "Baglanti olusturuldu: %s -> %s (agirlik=%.2f)",
            source_id,
            target_id,
            weight,
        )
        return link

    def spread_activation(
        self,
        start_id: str,
        initial_activation: float = 1.0,
        max_depth: int = 3,
    ) -> list[ActivationResult]:
        """BFS ile yayilan aktivasyon hesaplar.

        Baslangic dugumune initial_activation verilir. Her komsunun
        aktivasyonu: ebeveyn_aktivasyon * baglanti_agirligi * decay_factor^derinlik.
        Aktivasyon esik altinda kalirsa yayilim durur. Ziyaret edilmis
        dugumler tekrar islenmez.

        Args:
            start_id: Baslangic dugum ID.
            initial_activation: Baslangic aktivasyon degeri.
            max_depth: Maksimum yayilim derinligi.

        Returns:
            Aktivasyon seviyesine gore azalan sirali ActivationResult listesi.
        """
        if start_id not in self._nodes:
            return []

        results: dict[str, ActivationResult] = {}
        visited: set[str] = set()

        # (node_id, activation, depth)
        queue: deque[tuple[str, float, int]] = deque()
        queue.append((start_id, initial_activation, 0))
        visited.add(start_id)

        start_node = self._nodes[start_id]
        results[start_id] = ActivationResult(
            node_id=start_id,
            node_name=start_node.name,
            activation_level=initial_activation,
            depth=0,
        )

        while queue:
            current_id, current_activation, depth = queue.popleft()

            if depth >= max_depth:
                continue

            for link in self._links.get(current_id, []):
                neighbor_id = link.target_id
                if neighbor_id in visited:
                    continue

                next_depth = depth + 1
                neighbor_activation = (
                    current_activation
                    * link.weight
                    * (self._decay_factor ** next_depth)
                )

                if neighbor_activation < self._activation_threshold:
                    continue

                visited.add(neighbor_id)
                neighbor_node = self._nodes[neighbor_id]
                results[neighbor_id] = ActivationResult(
                    node_id=neighbor_id,
                    node_name=neighbor_node.name,
                    activation_level=neighbor_activation,
                    depth=next_depth,
                )
                queue.append((neighbor_id, neighbor_activation, next_depth))

        sorted_results = sorted(
            results.values(),
            key=lambda r: r.activation_level,
            reverse=True,
        )

        logger.debug(
            "Yayilan aktivasyon: baslangic=%s, %d dugum aktif",
            start_id,
            len(sorted_results),
        )
        return sorted_results

    def prime(self, concept_ids: list[str], boost: float = 0.3) -> int:
        """Kavramlarin aktivasyonunu arttirir (priming).

        Her kavraminin aktivasyonu boost kadar arttirilir,
        ancak 1.0'i gecemez.

        Args:
            concept_ids: Aktive edilecek kavram ID listesi.
            boost: Aktivasyon artis miktari.

        Returns:
            Basariyla aktive edilen kavram sayisi.
        """
        primed_count = 0
        for node_id in concept_ids:
            node = self._nodes.get(node_id)
            if node is None:
                continue
            node.activation = min(1.0, node.activation + boost)
            primed_count += 1

        logger.info("%d kavram prime edildi (boost=%.2f)", primed_count, boost)
        return primed_count

    def find_path(
        self,
        source_id: str,
        target_id: str,
        max_depth: int = 5,
    ) -> list[str]:
        """BFS ile en kisa yolu bulur.

        Args:
            source_id: Kaynak dugum ID.
            target_id: Hedef dugum ID.
            max_depth: Maksimum arama derinligi.

        Returns:
            Dugum ID listesi (kaynak dahil, hedef dahil).
            Yol bulunamazsa bos liste.
        """
        if source_id not in self._nodes or target_id not in self._nodes:
            return []

        if source_id == target_id:
            return [source_id]

        visited: set[str] = {source_id}
        # (node_id, path)
        queue: deque[tuple[str, list[str]]] = deque()
        queue.append((source_id, [source_id]))

        while queue:
            current_id, path = queue.popleft()

            if len(path) - 1 >= max_depth:
                continue

            for link in self._links.get(current_id, []):
                neighbor_id = link.target_id
                if neighbor_id in visited:
                    continue

                new_path = path + [neighbor_id]
                if neighbor_id == target_id:
                    return new_path

                visited.add(neighbor_id)
                queue.append((neighbor_id, new_path))

        return []

    def find_creative_connections(
        self,
        source_id: str,
        min_distance: int = 2,
        max_distance: int = 4,
    ) -> list[ActivationResult]:
        """Yaratici (uzak) baglantilar bulur.

        Yayilan aktivasyon kullanarak belirli bir mesafe araligindaki
        kavramlari dondurur. Yakin baglantilar filtrelenir, boylece
        sadece beklenmedik iliskiler ortaya cikar.

        Args:
            source_id: Baslangic kavram ID.
            min_distance: Minimum yayilim derinligi.
            max_distance: Maksimum yayilim derinligi.

        Returns:
            Mesafe araligindaki ActivationResult listesi (aktivasyon desc).
        """
        all_activations = self.spread_activation(
            start_id=source_id,
            max_depth=max_distance,
        )
        creative = [
            result
            for result in all_activations
            if min_distance <= result.depth <= max_distance
        ]

        logger.debug(
            "Yaratici baglanti: kaynak=%s, %d sonuc (mesafe %d-%d)",
            source_id,
            len(creative),
            min_distance,
            max_distance,
        )
        return creative

    def get_neighbors(self, node_id: str) -> list[ConceptNode]:
        """Dogrudan bagli komsu kavramlari dondurur.

        Args:
            node_id: Dugum kimlik numarasi.

        Returns:
            Komsu ConceptNode listesi.
        """
        neighbors: list[ConceptNode] = []
        for link in self._links.get(node_id, []):
            node = self._nodes.get(link.target_id)
            if node is not None:
                neighbors.append(node)
        return neighbors

    def decay_activations(self, factor: float | None = None) -> None:
        """Tum aktivasyonlari azaltir.

        Her dugumun aktivasyonu verilen carpan ile carpilir.
        Esik altina dusen aktivasyonlar sifira ayarlanir.

        Args:
            factor: Azalma carpani. None ise _decay_factor kullanilir.
        """
        decay = factor if factor is not None else self._decay_factor
        for node in self._nodes.values():
            node.activation *= decay
            if node.activation < self._activation_threshold:
                node.activation = 0.0

        logger.debug("Aktivasyonlar azaltildi (carpar=%.2f)", decay)

    def get_strongest_links(
        self,
        node_id: str,
        limit: int = 5,
    ) -> list[ConceptLink]:
        """En guclu baglantilari dondurur.

        Args:
            node_id: Dugum kimlik numarasi.
            limit: Maksimum sonuc sayisi.

        Returns:
            Agirliga gore azalan sirali ConceptLink listesi.
        """
        links = self._links.get(node_id, [])
        sorted_links = sorted(links, key=lambda lnk: lnk.weight, reverse=True)
        return sorted_links[:limit]

    def count_nodes(self) -> int:
        """Dugum sayisini dondurur.

        Returns:
            Agtaki toplam kavram sayisi.
        """
        return len(self._nodes)

    def count_links(self) -> int:
        """Baglanti sayisini dondurur.

        Returns:
            Agtaki toplam baglanti sayisi.
        """
        total = 0
        for link_list in self._links.values():
            total += len(link_list)
        return total
