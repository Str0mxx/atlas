"""ATLAS Gündem Oluşturucu modülü.

Otomatik gündem, zaman tahsisi,
konu önceliklendirme, katılımcı girişi,
şablon desteği.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class AgendaCreator:
    """Gündem oluşturucu.

    Toplantı gündemleri oluşturur.

    Attributes:
        _agendas: Gündem kayıtları.
        _templates: Şablon kayıtları.
    """

    def __init__(self) -> None:
        """Oluşturucuyu başlatır."""
        self._agendas: dict[
            str, dict[str, Any]
        ] = {}
        self._templates: dict[
            str, dict[str, Any]
        ] = {
            "standup": {
                "topics": [
                    "Yesterday",
                    "Today",
                    "Blockers",
                ],
                "duration": 15,
            },
            "review": {
                "topics": [
                    "Progress Review",
                    "Issues",
                    "Next Steps",
                ],
                "duration": 45,
            },
            "planning": {
                "topics": [
                    "Goals",
                    "Tasks",
                    "Timeline",
                    "Resources",
                ],
                "duration": 60,
            },
        }
        self._counter = 0
        self._stats = {
            "agendas_created": 0,
        }

        logger.info(
            "AgendaCreator baslatildi",
        )

    def auto_create(
        self,
        meeting_id: str,
        meeting_type: str = "review",
        duration_minutes: int = 45,
        topics: list[str] | None = None,
    ) -> dict[str, Any]:
        """Otomatik gündem oluşturur.

        Args:
            meeting_id: Toplantı kimliği.
            meeting_type: Toplantı tipi.
            duration_minutes: Süre (dk).
            topics: Konular (opsiyonel).

        Returns:
            Oluşturma bilgisi.
        """
        self._counter += 1
        aid = f"ag_{self._counter}"

        if topics:
            agenda_topics = topics
        else:
            template = self._templates.get(
                meeting_type,
                self._templates["review"],
            )
            agenda_topics = template[
                "topics"
            ]

        allocation = (
            self._allocate_time(
                agenda_topics,
                duration_minutes,
            )
        )

        agenda = {
            "agenda_id": aid,
            "meeting_id": meeting_id,
            "topics": allocation,
            "total_minutes": (
                duration_minutes
            ),
        }

        self._agendas[meeting_id] = agenda
        self._stats[
            "agendas_created"
        ] += 1

        return {
            **agenda,
            "created": True,
        }

    def allocate_time(
        self,
        topics: list[str] | None = None,
        total_minutes: int = 60,
    ) -> dict[str, Any]:
        """Zaman tahsisi yapar.

        Args:
            topics: Konular.
            total_minutes: Toplam süre.

        Returns:
            Tahsis bilgisi.
        """
        topics = topics or []

        allocation = (
            self._allocate_time(
                topics, total_minutes,
            )
        )

        return {
            "allocation": allocation,
            "total_minutes": total_minutes,
            "allocated": True,
        }

    def prioritize_topics(
        self,
        topics: list[dict[str, Any]]
        | None = None,
    ) -> dict[str, Any]:
        """Konu önceliklendirme yapar.

        Args:
            topics: Konular (ad, öncelik).

        Returns:
            Önceliklendirme bilgisi.
        """
        topics = topics or []

        priority_order = {
            "critical": 0,
            "high": 1,
            "medium": 2,
            "low": 3,
        }

        sorted_topics = sorted(
            topics,
            key=lambda t: priority_order.get(
                t.get("priority", "medium"),
                2,
            ),
        )

        return {
            "topics": sorted_topics,
            "count": len(sorted_topics),
            "prioritized": True,
        }

    def add_participant_input(
        self,
        meeting_id: str,
        participant: str = "",
        topic: str = "",
        notes: str = "",
    ) -> dict[str, Any]:
        """Katılımcı girişi ekler.

        Args:
            meeting_id: Toplantı kimliği.
            participant: Katılımcı.
            topic: Konu.
            notes: Notlar.

        Returns:
            Ekleme bilgisi.
        """
        agenda = self._agendas.get(
            meeting_id,
        )

        if agenda:
            if "inputs" not in agenda:
                agenda["inputs"] = []
            agenda["inputs"].append({
                "participant": participant,
                "topic": topic,
                "notes": notes,
            })

        return {
            "meeting_id": meeting_id,
            "participant": participant,
            "topic": topic,
            "added": agenda is not None,
        }

    def use_template(
        self,
        meeting_id: str,
        template_name: str = "review",
        duration_minutes: int = 0,
    ) -> dict[str, Any]:
        """Şablon kullanır.

        Args:
            meeting_id: Toplantı kimliği.
            template_name: Şablon adı.
            duration_minutes: Süre (dk).

        Returns:
            Kullanım bilgisi.
        """
        template = self._templates.get(
            template_name,
        )
        if not template:
            return {
                "template": template_name,
                "used": False,
            }

        duration = (
            duration_minutes
            or template["duration"]
        )

        return self.auto_create(
            meeting_id=meeting_id,
            meeting_type=template_name,
            duration_minutes=duration,
        )

    def _allocate_time(
        self,
        topics: list[str],
        total_minutes: int,
    ) -> list[dict[str, Any]]:
        """Zaman dağıtır."""
        if not topics:
            return []

        per_topic = total_minutes // len(
            topics,
        )
        remainder = total_minutes % len(
            topics,
        )

        allocation = []
        for i, topic in enumerate(topics):
            minutes = per_topic + (
                1 if i < remainder else 0
            )
            allocation.append({
                "topic": topic,
                "minutes": minutes,
            })

        return allocation

    @property
    def agenda_count(self) -> int:
        """Gündem sayısı."""
        return self._stats[
            "agendas_created"
        ]
