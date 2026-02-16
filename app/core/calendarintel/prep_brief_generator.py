"""ATLAS Hazırlık Özeti Üretici modülü.

Toplantı bağlamı, katılımcı bilgisi,
önceki toplantılar, ilgili dokümanlar,
aksiyon öğeleri.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class PrepBriefGenerator:
    """Hazırlık özeti üretici.

    Toplantı hazırlık özetleri üretir.

    Attributes:
        _briefs: Özet kayıtları.
        _meeting_history: Toplantı geçmişi.
    """

    def __init__(self) -> None:
        """Üreticiyi başlatır."""
        self._briefs: list[
            dict[str, Any]
        ] = []
        self._meeting_history: dict[
            str, list[dict[str, Any]]
        ] = {}
        self._documents: dict[
            str, list[str]
        ] = {}
        self._action_items: dict[
            str, list[dict[str, Any]]
        ] = {}
        self._counter = 0
        self._stats = {
            "briefs_generated": 0,
        }

        logger.info(
            "PrepBriefGenerator "
            "baslatildi",
        )

    def generate_context(
        self,
        meeting_id: str,
        title: str = "",
        meeting_type: str = "review",
        objective: str = "",
    ) -> dict[str, Any]:
        """Toplantı bağlamı üretir.

        Args:
            meeting_id: Toplantı kimliği.
            title: Başlık.
            meeting_type: Toplantı tipi.
            objective: Amaç.

        Returns:
            Bağlam bilgisi.
        """
        context = {
            "meeting_id": meeting_id,
            "title": title,
            "type": meeting_type,
            "objective": (
                objective
                or f"{title} toplantısı"
            ),
        }

        return {
            **context,
            "generated": True,
        }

    def gather_participant_info(
        self,
        participants: list[dict[str, Any]]
        | None = None,
    ) -> dict[str, Any]:
        """Katılımcı bilgisi toplar.

        Args:
            participants: Katılımcılar.

        Returns:
            Bilgi listesi.
        """
        participants = participants or []

        info = [
            {
                "name": p.get("name", ""),
                "role": p.get("role", ""),
                "department": p.get(
                    "department", "",
                ),
            }
            for p in participants
        ]

        return {
            "participants": info,
            "count": len(info),
            "gathered": True,
        }

    def get_previous_meetings(
        self,
        meeting_series: str = "",
        limit: int = 5,
    ) -> dict[str, Any]:
        """Önceki toplantıları getirir.

        Args:
            meeting_series: Toplantı serisi.
            limit: Sınır.

        Returns:
            Geçmiş bilgisi.
        """
        history = self._meeting_history.get(
            meeting_series, [],
        )

        return {
            "series": meeting_series,
            "previous": history[-limit:],
            "count": min(
                len(history), limit,
            ),
            "retrieved": len(history) > 0,
        }

    def add_meeting_to_history(
        self,
        meeting_series: str,
        meeting_id: str = "",
        title: str = "",
        summary: str = "",
    ) -> dict[str, Any]:
        """Toplantıyı geçmişe ekler.

        Args:
            meeting_series: Seri.
            meeting_id: Kimlik.
            title: Başlık.
            summary: Özet.

        Returns:
            Ekleme bilgisi.
        """
        if meeting_series not in (
            self._meeting_history
        ):
            self._meeting_history[
                meeting_series
            ] = []

        self._meeting_history[
            meeting_series
        ].append({
            "meeting_id": meeting_id,
            "title": title,
            "summary": summary,
            "timestamp": time.time(),
        })

        return {
            "series": meeting_series,
            "added": True,
        }

    def attach_documents(
        self,
        meeting_id: str,
        documents: list[str] | None = None,
    ) -> dict[str, Any]:
        """İlgili dokümanlar ekler.

        Args:
            meeting_id: Toplantı kimliği.
            documents: Dokümanlar.

        Returns:
            Ekleme bilgisi.
        """
        documents = documents or []

        self._documents[meeting_id] = (
            documents
        )

        return {
            "meeting_id": meeting_id,
            "documents": documents,
            "count": len(documents),
            "attached": True,
        }

    def list_action_items(
        self,
        meeting_id: str,
        items: list[dict[str, Any]]
        | None = None,
    ) -> dict[str, Any]:
        """Aksiyon öğeleri listeler.

        Args:
            meeting_id: Toplantı kimliği.
            items: Öğeler.

        Returns:
            Liste bilgisi.
        """
        items = items or []

        self._action_items[meeting_id] = (
            items
        )

        return {
            "meeting_id": meeting_id,
            "action_items": items,
            "count": len(items),
            "listed": True,
        }

    def generate_brief(
        self,
        meeting_id: str,
        title: str = "",
        participants: list[dict[str, Any]]
        | None = None,
        meeting_series: str = "",
    ) -> dict[str, Any]:
        """Tam hazırlık özeti üretir.

        Args:
            meeting_id: Toplantı kimliği.
            title: Başlık.
            participants: Katılımcılar.
            meeting_series: Seri.

        Returns:
            Özet bilgisi.
        """
        self._counter += 1
        bid = f"br_{self._counter}"

        context = self.generate_context(
            meeting_id, title,
        )
        participant_info = (
            self.gather_participant_info(
                participants,
            )
        )
        previous = (
            self.get_previous_meetings(
                meeting_series,
            )
        )
        docs = self._documents.get(
            meeting_id, [],
        )
        actions = self._action_items.get(
            meeting_id, [],
        )

        brief = {
            "brief_id": bid,
            "meeting_id": meeting_id,
            "title": title,
            "context": context,
            "participants": (
                participant_info["count"]
            ),
            "previous_meetings": (
                previous["count"]
            ),
            "documents": len(docs),
            "action_items": len(actions),
            "generated": True,
        }

        self._briefs.append(brief)
        self._stats[
            "briefs_generated"
        ] += 1

        return brief

    @property
    def brief_count(self) -> int:
        """Özet sayısı."""
        return self._stats[
            "briefs_generated"
        ]
