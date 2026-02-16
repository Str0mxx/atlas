"""ATLAS Gündem Analizcisi.

Oturum analizi, konuşmacı takibi,
konu çıkarma, program optimizasyonu ve çakışma.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class EventAgendaAnalyzer:
    """Gündem analizcisi.

    Etkinlik gündemlerini analiz eder,
    oturumları optimize eder ve çakışmaları tespit eder.

    Attributes:
        _sessions: Oturum kayıtları.
        _stats: İstatistikler.
    """

    def __init__(self) -> None:
        """Analizcisini başlatır."""
        self._sessions: dict[str, dict] = {}
        self._stats = {
            "sessions_analyzed": 0,
            "conflicts_detected": 0,
        }
        logger.info(
            "EventAgendaAnalyzer baslatildi",
        )

    @property
    def analyzed_count(self) -> int:
        """Analiz edilen oturum sayısı."""
        return self._stats[
            "sessions_analyzed"
        ]

    @property
    def conflict_count(self) -> int:
        """Tespit edilen çakışma sayısı."""
        return self._stats[
            "conflicts_detected"
        ]

    def analyze_session(
        self,
        session_id: str,
        title: str = "",
        speaker: str = "",
        time_slot: str = "",
    ) -> dict[str, Any]:
        """Oturum analizi yapar.

        Args:
            session_id: Oturum kimliği.
            title: Başlık.
            speaker: Konuşmacı.
            time_slot: Zaman dilimi.

        Returns:
            Analiz bilgisi.
        """
        self._sessions[session_id] = {
            "title": title,
            "speaker": speaker,
            "time_slot": time_slot,
        }
        self._stats[
            "sessions_analyzed"
        ] += 1

        return {
            "session_id": session_id,
            "title": title,
            "speaker": speaker,
            "time_slot": time_slot,
            "analyzed": True,
        }

    def track_speakers(
        self,
        event_id: str,
        speakers: list[str] | None = None,
    ) -> dict[str, Any]:
        """Konuşmacıları takip eder.

        Args:
            event_id: Etkinlik kimliği.
            speakers: Konuşmacı listesi.

        Returns:
            Takip bilgisi.
        """
        if speakers is None:
            speakers = []

        return {
            "event_id": event_id,
            "speaker_count": len(speakers),
            "speakers": speakers,
            "tracked": True,
        }

    def extract_topics(
        self,
        event_id: str,
        session_titles: list[str]
        | None = None,
    ) -> dict[str, Any]:
        """Konu çıkarma yapar.

        Args:
            event_id: Etkinlik kimliği.
            session_titles: Oturum başlıkları.

        Returns:
            Konu bilgisi.
        """
        if session_titles is None:
            session_titles = []

        topics = list(set(
            word.lower()
            for title in session_titles
            for word in title.split()
            if len(word) > 3
        ))[:10]

        return {
            "event_id": event_id,
            "topics": topics,
            "topic_count": len(topics),
            "extracted": True,
        }

    def optimize_schedule(
        self,
        sessions: list[dict[str, Any]]
        | None = None,
        max_per_day: int = 5,
    ) -> dict[str, Any]:
        """Program optimizasyonu yapar.

        Args:
            sessions: Oturum listesi.
            max_per_day: Günlük maksimum.

        Returns:
            Optimizasyon bilgisi.
        """
        if sessions is None:
            sessions = []

        selected = sessions[:max_per_day]

        return {
            "total_sessions": len(sessions),
            "selected_count": len(selected),
            "max_per_day": max_per_day,
            "optimized": True,
        }

    def detect_conflicts(
        self,
        sessions: list[dict[str, Any]]
        | None = None,
    ) -> dict[str, Any]:
        """Çakışma tespiti yapar.

        Args:
            sessions: Oturum listesi
                (her biri time_slot içerir).

        Returns:
            Çakışma bilgisi.
        """
        if sessions is None:
            sessions = []

        slots: dict[str, list[str]] = {}
        for s in sessions:
            slot = s.get("time_slot", "")
            sid = s.get("session_id", "")
            if slot not in slots:
                slots[slot] = []
            slots[slot].append(sid)

        conflicts = {
            slot: ids
            for slot, ids in slots.items()
            if len(ids) > 1
        }
        self._stats[
            "conflicts_detected"
        ] += len(conflicts)

        return {
            "conflict_count": len(conflicts),
            "conflicts": conflicts,
            "detected": True,
        }
