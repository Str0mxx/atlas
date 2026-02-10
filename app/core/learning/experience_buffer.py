"""ATLAS deneyim tamponu modulu.

Oncelikli deneyim tekrari (Prioritized Experience Replay) ile
deneyimleri depolama ve ornekleme.
"""

import logging
from typing import Any

import numpy as np

from app.models.learning import Experience, PrioritizedExperience

logger = logging.getLogger("atlas.learning.experience_buffer")


class SumTree:
    """Segment agaci tabanli toplam agaci.

    Oncelikli ornekleme icin O(log n) karmasiklik saglar.

    Attributes:
        capacity: Yaprak dugum kapasitesi.
        tree: Agac dizisi.
        data: Yaprak verileri.
        write_idx: Yazma indeksi.
        size: Mevcut eleman sayisi.
    """

    def __init__(self, capacity: int) -> None:
        """SumTree'yi baslatir.

        Args:
            capacity: Maksimum eleman sayisi.
        """
        self.capacity = capacity
        self.tree = np.zeros(2 * capacity - 1)
        self.data: list[Any] = [None] * capacity
        self.write_idx = 0
        self.size = 0

    def _propagate(self, idx: int, change: float) -> None:
        """Degisikligi kok dugume yayar."""
        parent = (idx - 1) // 2
        self.tree[parent] += change
        if parent != 0:
            self._propagate(parent, change)

    def _retrieve(self, idx: int, s: float) -> int:
        """Toplam degerine gore yaprak dugumu bulur."""
        left = 2 * idx + 1
        right = left + 1

        if left >= len(self.tree):
            return idx

        if s <= self.tree[left]:
            return self._retrieve(left, s)
        return self._retrieve(right, s - self.tree[left])

    def total(self) -> float:
        """Toplam oncelik degerini dondurur."""
        return float(self.tree[0])

    def add(self, priority: float, data: Any) -> None:
        """Yeni eleman ekler veya en eskisini degistirir.

        Args:
            priority: Oncelik degeri.
            data: Depolanacak veri.
        """
        idx = self.write_idx + self.capacity - 1
        self.data[self.write_idx] = data
        self._update(idx, priority)

        self.write_idx = (self.write_idx + 1) % self.capacity
        self.size = min(self.size + 1, self.capacity)

    def _update(self, idx: int, priority: float) -> None:
        """Agac dugumunu gunceller."""
        change = priority - self.tree[idx]
        self.tree[idx] = priority
        if idx != 0:
            self._propagate(idx, change)

    def get(self, s: float) -> tuple[int, float, Any]:
        """Toplam degerine gore eleman getirir.

        Args:
            s: Ornekleme degeri [0, total).

        Returns:
            (indeks, oncelik, veri) uclusi.
        """
        idx = self._retrieve(0, s)
        data_idx = idx - self.capacity + 1
        return idx, float(self.tree[idx]), self.data[data_idx]

    def update(self, idx: int, priority: float) -> None:
        """Mevcut elemanin onceligini gunceller.

        Args:
            idx: Agac indeksi.
            priority: Yeni oncelik degeri.
        """
        self._update(idx, priority)


class ExperienceBuffer:
    """Oncelikli deneyim tekrari tamponu.

    TD-hata tabanli oncelikli ornekleme ile deneyimleri depolar.

    Attributes:
        max_size: Maksimum tampon boyutu.
        alpha: Onceliklendirme ussu (0=uniform, 1=tam oncelikli).
        beta: Onem ornekleme duzeltme ussu.
        beta_increment: Beta artis miktari.
    """

    def __init__(
        self,
        max_size: int = 10000,
        alpha: float = 0.6,
        beta: float = 0.4,
        beta_increment: float = 0.001,
    ) -> None:
        """ExperienceBuffer'i baslatir.

        Args:
            max_size: Maksimum tampon boyutu.
            alpha: Onceliklendirme ussu.
            beta: Onem ornekleme duzeltme ussu.
            beta_increment: Beta artis miktari.
        """
        self.max_size = max_size
        self.alpha = alpha
        self.beta = beta
        self.beta_increment = beta_increment
        self._tree = SumTree(max_size)
        self._max_priority = 1.0
        self._total_added = 0
        logger.info(
            "ExperienceBuffer olusturuldu (max_size=%d, alpha=%.2f)",
            max_size, alpha,
        )

    def add(self, experience: Experience, priority: float | None = None) -> None:
        """Deneyim ekler.

        Args:
            experience: Eklenecek deneyim.
            priority: Oncelik degeri (None ise max oncelik).
        """
        p = priority if priority is not None else self._max_priority
        p = max(abs(p) ** self.alpha, 1e-6)
        self._tree.add(p, experience)
        self._max_priority = max(self._max_priority, p)
        self._total_added += 1

    def sample(self, batch_size: int = 32) -> list[PrioritizedExperience]:
        """Oncelikli ornekleme yapar.

        Args:
            batch_size: Ornek sayisi.

        Returns:
            Oncelikli deneyim listesi.
        """
        n = min(batch_size, len(self))
        if n == 0:
            return []

        self.beta = min(1.0, self.beta + self.beta_increment)

        total = self._tree.total()
        if total <= 0:
            return []

        segment = total / n
        samples: list[PrioritizedExperience] = []

        min_prob = 1e-6
        if self._tree.size > 0:
            min_prob = max(min_prob, np.min(
                self._tree.tree[-self._tree.capacity:][:self._tree.size],
            ) / total)

        max_weight = (min_prob * self._tree.size) ** (-self.beta)
        if max_weight <= 0:
            max_weight = 1.0

        for i in range(n):
            lo = segment * i
            hi = segment * (i + 1)
            s = np.random.uniform(lo, hi)

            idx, priority, data = self._tree.get(s)
            if data is None:
                continue

            prob = priority / total
            weight = (prob * self._tree.size) ** (-self.beta)
            weight = weight / max_weight

            samples.append(PrioritizedExperience(
                experience=data,
                priority=priority,
                weight=weight,
            ))

        return samples

    def update_priorities(
        self,
        indices: list[int],
        priorities: list[float],
    ) -> None:
        """Deneyim onceliklerini gunceller.

        Args:
            indices: Agac indeksleri.
            priorities: Yeni oncelik degerleri.
        """
        for idx, p in zip(indices, priorities):
            p = max(abs(p) ** self.alpha, 1e-6)
            self._tree.update(idx, p)
            self._max_priority = max(self._max_priority, p)

    def __len__(self) -> int:
        """Tampondaki deneyim sayisi."""
        return self._tree.size

    def clear(self) -> None:
        """Tamponu temizler."""
        self._tree = SumTree(self.max_size)
        self._max_priority = 1.0
        self._total_added = 0
        logger.info("ExperienceBuffer temizlendi")

    def get_stats(self) -> dict[str, Any]:
        """Tampon istatistiklerini dondurur."""
        return {
            "size": len(self),
            "max_size": self.max_size,
            "total_added": self._total_added,
            "max_priority": self._max_priority,
            "total_priority": self._tree.total(),
            "beta": self.beta,
        }
