"""ATLAS Zaman Çizelgesi Oluşturucu modulu.

Kronolojik olaylar, kilometre taşı işaretleme,
dönem analizi, kalıp tespiti, gelecek projeksiyonu.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class TimelineBuilder:
    """Zaman çizelgesi oluşturucu.

    Varlık olaylarını kronolojik yönetir.

    Attributes:
        _events: Olay kayıtları.
        _milestones: Kilometre taşları.
    """

    def __init__(self) -> None:
        """Oluşturucuyu başlatır."""
        self._events: dict[
            str, list[dict[str, Any]]
        ] = {}
        self._milestones: dict[
            str, list[dict[str, Any]]
        ] = {}
        self._counter = 0
        self._stats = {
            "events": 0,
            "milestones": 0,
        }

        logger.info(
            "TimelineBuilder baslatildi",
        )

    def add_event(
        self,
        entity_id: str,
        event_type: str,
        description: str,
        timestamp: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Olay ekler.

        Args:
            entity_id: Varlık ID.
            event_type: Olay tipi.
            description: Açıklama.
            timestamp: Zaman damgası.
            metadata: Ek veri.

        Returns:
            Ekleme bilgisi.
        """
        self._counter += 1
        evid = f"evt_{self._counter}"
        ts = timestamp or time.time()

        event = {
            "event_id": evid,
            "entity_id": entity_id,
            "event_type": event_type,
            "description": description,
            "timestamp": ts,
            "metadata": metadata or {},
        }

        if entity_id not in self._events:
            self._events[entity_id] = []
        self._events[entity_id].append(event)

        # Kronolojik sırala
        self._events[entity_id].sort(
            key=lambda x: x["timestamp"],
        )
        self._stats["events"] += 1

        return {
            "event_id": evid,
            "entity_id": entity_id,
            "event_type": event_type,
            "added": True,
        }

    def mark_milestone(
        self,
        entity_id: str,
        title: str,
        description: str = "",
        timestamp: float | None = None,
    ) -> dict[str, Any]:
        """Kilometre taşı işaretler.

        Args:
            entity_id: Varlık ID.
            title: Başlık.
            description: Açıklama.
            timestamp: Zaman damgası.

        Returns:
            İşaretleme bilgisi.
        """
        self._counter += 1
        mid = f"mst_{self._counter}"
        ts = timestamp or time.time()

        milestone = {
            "milestone_id": mid,
            "entity_id": entity_id,
            "title": title,
            "description": description,
            "timestamp": ts,
        }

        if entity_id not in self._milestones:
            self._milestones[entity_id] = []
        self._milestones[entity_id].append(
            milestone,
        )
        self._stats["milestones"] += 1

        # Ayrıca olay olarak ekle
        self.add_event(
            entity_id,
            "milestone",
            title,
            timestamp=ts,
        )

        return {
            "milestone_id": mid,
            "entity_id": entity_id,
            "title": title,
            "marked": True,
        }

    def get_timeline(
        self,
        entity_id: str,
        start: float | None = None,
        end: float | None = None,
    ) -> dict[str, Any]:
        """Zaman çizelgesi getirir.

        Args:
            entity_id: Varlık ID.
            start: Başlangıç zamanı.
            end: Bitiş zamanı.

        Returns:
            Çizelge bilgisi.
        """
        events = self._events.get(
            entity_id, [],
        )

        if start:
            events = [
                e for e in events
                if e["timestamp"] >= start
            ]
        if end:
            events = [
                e for e in events
                if e["timestamp"] <= end
            ]

        return {
            "entity_id": entity_id,
            "events": events,
            "event_count": len(events),
        }

    def analyze_period(
        self,
        entity_id: str,
        start: float,
        end: float,
    ) -> dict[str, Any]:
        """Dönem analizi yapar.

        Args:
            entity_id: Varlık ID.
            start: Başlangıç.
            end: Bitiş.

        Returns:
            Analiz bilgisi.
        """
        events = self._events.get(
            entity_id, [],
        )
        period_events = [
            e for e in events
            if start <= e["timestamp"] <= end
        ]

        # Tip dağılımı
        type_counts: dict[str, int] = {}
        for e in period_events:
            t = e["event_type"]
            type_counts[t] = (
                type_counts.get(t, 0) + 1
            )

        duration = end - start

        return {
            "entity_id": entity_id,
            "period_start": start,
            "period_end": end,
            "duration": round(duration, 2),
            "event_count": len(period_events),
            "type_distribution": type_counts,
            "events_per_day": round(
                len(period_events)
                / max(duration / 86400, 1),
                2,
            ),
        }

    def detect_patterns(
        self,
        entity_id: str,
    ) -> dict[str, Any]:
        """Kalıp tespit eder.

        Args:
            entity_id: Varlık ID.

        Returns:
            Kalıp bilgisi.
        """
        events = self._events.get(
            entity_id, [],
        )
        if len(events) < 2:
            return {
                "entity_id": entity_id,
                "patterns": [],
                "pattern_count": 0,
            }

        # Tip frekansları
        type_freq: dict[str, int] = {}
        for e in events:
            t = e["event_type"]
            type_freq[t] = (
                type_freq.get(t, 0) + 1
            )

        # Sık tekrar eden tipler
        patterns = []
        for t, cnt in type_freq.items():
            if cnt >= 3:
                patterns.append({
                    "event_type": t,
                    "frequency": cnt,
                    "pattern": "recurring",
                })

        # Ardışık tekrar
        for i in range(len(events) - 1):
            if (
                events[i]["event_type"]
                == events[i + 1]["event_type"]
            ):
                patterns.append({
                    "event_type": events[i][
                        "event_type"
                    ],
                    "pattern": "consecutive",
                    "index": i,
                })
                break  # İlk bulduğunu raporla

        return {
            "entity_id": entity_id,
            "patterns": patterns,
            "pattern_count": len(patterns),
        }

    def project_future(
        self,
        entity_id: str,
        days: int = 30,
    ) -> dict[str, Any]:
        """Gelecek projeksiyonu yapar.

        Args:
            entity_id: Varlık ID.
            days: Projeksiyon süresi.

        Returns:
            Projeksiyon bilgisi.
        """
        events = self._events.get(
            entity_id, [],
        )
        if len(events) < 2:
            return {
                "entity_id": entity_id,
                "projected_events": 0,
                "confidence": 0.0,
            }

        # Ortalama olay sıklığı
        first = events[0]["timestamp"]
        last = events[-1]["timestamp"]
        span_days = max(
            (last - first) / 86400, 1,
        )
        rate = len(events) / span_days

        projected = round(rate * days)
        confidence = min(
            0.9,
            len(events) / 20,
        )

        return {
            "entity_id": entity_id,
            "projection_days": days,
            "current_rate": round(rate, 2),
            "projected_events": projected,
            "confidence": round(confidence, 2),
        }

    def get_milestones(
        self,
        entity_id: str,
    ) -> list[dict[str, Any]]:
        """Kilometre taşlarını getirir.

        Args:
            entity_id: Varlık ID.

        Returns:
            Kilometre taşları.
        """
        return list(
            self._milestones.get(
                entity_id, [],
            ),
        )

    @property
    def event_count(self) -> int:
        """Olay sayısı."""
        return self._stats["events"]

    @property
    def milestone_count(self) -> int:
        """Kilometre taşı sayısı."""
        return self._stats["milestones"]
