"""ATLAS Feromon Sistemi modulu.

Dolayli iletisim, iz birakma, iz takip,
isaret bozunmasi ve bilgi yayilimi.
"""

import logging
from typing import Any

from app.models.swarm import PheromoneMarker, PheromoneType

logger = logging.getLogger(__name__)


class PheromoneSystem:
    """Feromon sistemi (stigmergy).

    Agent'lar arasi dolayli iletisim saglar.
    Isaretler zamanla bozunur, guclu isaretler kalir.

    Attributes:
        _markers: Feromon isaretleri.
        _decay_rate: Bozunma orani.
        _min_intensity: Min yogunluk (altinda silinir).
    """

    def __init__(
        self,
        decay_rate: float = 0.1,
        min_intensity: float = 0.05,
    ) -> None:
        """Feromon sistemini baslatir.

        Args:
            decay_rate: Bozunma orani (0-1).
            min_intensity: Min yogunluk esigi.
        """
        self._markers: dict[str, PheromoneMarker] = {}
        self._location_index: dict[str, list[str]] = {}
        self._decay_rate = decay_rate
        self._min_intensity = min_intensity

        logger.info(
            "PheromoneSystem baslatildi (decay=%.2f)",
            decay_rate,
        )

    def leave_marker(
        self,
        agent_id: str,
        location: str,
        pheromone_type: PheromoneType = PheromoneType.TRAIL,
        intensity: float = 1.0,
        data: dict[str, Any] | None = None,
    ) -> PheromoneMarker:
        """Feromon isareti birakir.

        Args:
            agent_id: Agent ID.
            location: Konum.
            pheromone_type: Feromon tipi.
            intensity: Yogunluk.
            data: Ek veri.

        Returns:
            PheromoneMarker nesnesi.
        """
        marker = PheromoneMarker(
            pheromone_type=pheromone_type,
            source_agent=agent_id,
            location=location,
            intensity=min(1.0, max(0.0, intensity)),
            data=data or {},
        )

        self._markers[marker.marker_id] = marker

        if location not in self._location_index:
            self._location_index[location] = []
        self._location_index[location].append(marker.marker_id)

        return marker

    def get_markers_at(
        self,
        location: str,
        pheromone_type: PheromoneType | None = None,
    ) -> list[PheromoneMarker]:
        """Konumdaki isaretleri getirir.

        Args:
            location: Konum.
            pheromone_type: Tip filtresi.

        Returns:
            PheromoneMarker listesi.
        """
        marker_ids = self._location_index.get(location, [])
        markers = [
            self._markers[mid]
            for mid in marker_ids
            if mid in self._markers
        ]

        if pheromone_type is not None:
            markers = [m for m in markers if m.pheromone_type == pheromone_type]

        return sorted(markers, key=lambda m: m.intensity, reverse=True)

    def get_strongest_trail(
        self,
        location: str,
    ) -> PheromoneMarker | None:
        """En guclu izi getirir.

        Args:
            location: Konum.

        Returns:
            PheromoneMarker veya None.
        """
        markers = self.get_markers_at(location, PheromoneType.TRAIL)
        return markers[0] if markers else None

    def reinforce_marker(
        self,
        marker_id: str,
        boost: float = 0.2,
    ) -> bool:
        """Isareti guclendIrir.

        Args:
            marker_id: Isaret ID.
            boost: Guc artisi.

        Returns:
            Basarili ise True.
        """
        marker = self._markers.get(marker_id)
        if not marker:
            return False

        marker.intensity = min(1.0, marker.intensity + boost)
        return True

    def decay_all(self) -> int:
        """Tum isaretleri bozundurur.

        Returns:
            Silinen isaret sayisi.
        """
        to_remove: list[str] = []

        for mid, marker in self._markers.items():
            marker.intensity *= (1.0 - self._decay_rate)
            if marker.intensity < self._min_intensity:
                to_remove.append(mid)

        for mid in to_remove:
            self._remove_marker(mid)

        return len(to_remove)

    def broadcast_signal(
        self,
        agent_id: str,
        locations: list[str],
        pheromone_type: PheromoneType,
        intensity: float = 0.8,
        data: dict[str, Any] | None = None,
    ) -> int:
        """Birden fazla konuma sinyal yayar.

        Args:
            agent_id: Agent ID.
            locations: Konumlar.
            pheromone_type: Feromon tipi.
            intensity: Yogunluk.
            data: Ek veri.

        Returns:
            Olusturulan isaret sayisi.
        """
        count = 0
        for loc in locations:
            self.leave_marker(agent_id, loc, pheromone_type, intensity, data)
            count += 1
        return count

    def get_attraction_score(self, location: str) -> float:
        """Konumun cekim puanini hesaplar.

        Args:
            location: Konum.

        Returns:
            Cekim puani (-1 ile 1 arasi).
        """
        markers = self.get_markers_at(location)
        if not markers:
            return 0.0

        score = 0.0
        for m in markers:
            if m.pheromone_type in (PheromoneType.ATTRACTION, PheromoneType.SUCCESS):
                score += m.intensity
            elif m.pheromone_type in (PheromoneType.REPULSION, PheromoneType.ALARM):
                score -= m.intensity

        return max(-1.0, min(1.0, score))

    def get_locations_by_type(
        self,
        pheromone_type: PheromoneType,
    ) -> list[str]:
        """Feromon tipine gore konumlari getirir.

        Args:
            pheromone_type: Feromon tipi.

        Returns:
            Konum listesi.
        """
        locations: set[str] = set()
        for marker in self._markers.values():
            if marker.pheromone_type == pheromone_type:
                locations.add(marker.location)
        return list(locations)

    def clear_location(self, location: str) -> int:
        """Konumdaki tum isaretleri temizler.

        Args:
            location: Konum.

        Returns:
            Silinen isaret sayisi.
        """
        marker_ids = list(self._location_index.get(location, []))
        for mid in marker_ids:
            self._remove_marker(mid)
        return len(marker_ids)

    def _remove_marker(self, marker_id: str) -> None:
        """Isareti siler."""
        marker = self._markers.pop(marker_id, None)
        if marker and marker.location in self._location_index:
            ids = self._location_index[marker.location]
            if marker_id in ids:
                ids.remove(marker_id)
            if not ids:
                del self._location_index[marker.location]

    @property
    def total_markers(self) -> int:
        """Toplam isaret sayisi."""
        return len(self._markers)

    @property
    def active_locations(self) -> int:
        """Aktif konum sayisi."""
        return len(self._location_index)
