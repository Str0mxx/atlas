"""ATLAS Etkinlik Zekası Orkestratörü.

Tam etkinlik yönetim pipeline,
Discover → Register → Attend → Network → Follow-up,
etkinlik zekası, analitik.
"""

import logging
from typing import Any

from app.core.eventintel.agenda_analyzer import (
    EventAgendaAnalyzer,
)
from app.core.eventintel.event_discovery import (
    EventDiscovery,
)
from app.core.eventintel.event_roi_calculator import (
    EventROICalculator,
)
from app.core.eventintel.networking_planner import (
    NetworkingPlanner,
)
from app.core.eventintel.post_event_followup import (
    PostEventFollowUp,
)
from app.core.eventintel.registration_automator import (
    RegistrationAutomator,
)
from app.core.eventintel.relevance_scorer import (
    EventRelevanceScorer,
)
from app.core.eventintel.speaker_tracker import (
    SpeakerTracker,
)

logger = logging.getLogger(__name__)


class EventIntelOrchestrator:
    """Etkinlik zekası orkestratörü.

    Tüm etkinlik bileşenlerini koordine eder.

    Attributes:
        discovery: Etkinlik keşifçisi.
        scorer: Alaka puanlayıcı.
        registrar: Kayıt otomatikleştirici.
        agenda: Gündem analizcisi.
        networking: Ağ kurma planlayıcı.
        followup: Etkinlik sonrası takip.
        speakers: Konuşmacı takipçisi.
        roi: ROI hesaplayıcı.
    """

    def __init__(self) -> None:
        """Orkestratörü başlatır."""
        self.discovery = EventDiscovery()
        self.scorer = EventRelevanceScorer()
        self.registrar = (
            RegistrationAutomator()
        )
        self.agenda = EventAgendaAnalyzer()
        self.networking = NetworkingPlanner()
        self.followup = PostEventFollowUp()
        self.speakers = SpeakerTracker()
        self.roi = EventROICalculator()
        self._stats = {
            "pipelines_run": 0,
            "events_managed": 0,
        }

        logger.info(
            "EventIntelOrchestrator "
            "baslatildi",
        )

    @property
    def pipeline_count(self) -> int:
        """Pipeline sayısı."""
        return self._stats["pipelines_run"]

    @property
    def managed_count(self) -> int:
        """Yönetilen etkinlik sayısı."""
        return self._stats[
            "events_managed"
        ]

    def discover_and_register(
        self,
        query: str,
        category: str = "conference",
        attendee_name: str = "",
    ) -> dict[str, Any]:
        """Keşif ve kayıt pipeline.

        Args:
            query: Arama sorgusu.
            category: Etkinlik kategorisi.
            attendee_name: Katılımcı adı.

        Returns:
            Pipeline bilgisi.
        """
        # 1. Keşfet
        event = self.discovery.search_events(
            query, category,
        )

        # 2. Puanla
        score = self.scorer.score_relevance(
            event["event_id"],
            topic_match=0.7,
            speaker_quality=0.6,
            networking_value=0.5,
        )

        # 3. Kayıt ol
        reg = self.registrar.auto_register(
            event["event_id"],
            attendee_name,
        )

        self._stats["pipelines_run"] += 1
        self._stats[
            "events_managed"
        ] += 1

        return {
            "event_id": event["event_id"],
            "relevance": score["score"],
            "registration_id": reg[
                "registration_id"
            ],
            "pipeline_complete": True,
        }

    def post_event_process(
        self,
        event_id: str,
        contacts: list[str] | None = None,
    ) -> dict[str, Any]:
        """Etkinlik sonrası süreç.

        Args:
            event_id: Etkinlik kimliği.
            contacts: İletişim listesi.

        Returns:
            Süreç bilgisi.
        """
        if contacts is None:
            contacts = []

        collected = []
        for name in contacts:
            c = self.followup.collect_contact(
                name, event_id=event_id,
            )
            collected.append(
                c["contact_id"],
            )

        self._stats["pipelines_run"] += 1

        return {
            "event_id": event_id,
            "contacts_collected": len(
                collected,
            ),
            "processed": True,
        }

    def get_analytics(
        self,
    ) -> dict[str, Any]:
        """Analitik döndürür.

        Returns:
            Analitik bilgisi.
        """
        return {
            "pipelines_run": self._stats[
                "pipelines_run"
            ],
            "events_managed": self._stats[
                "events_managed"
            ],
            "events_discovered": (
                self.discovery
                .discovered_count
            ),
            "events_scored": (
                self.scorer.scored_count
            ),
            "registrations_done": (
                self.registrar
                .registration_count
            ),
            "sessions_analyzed": (
                self.agenda.analyzed_count
            ),
            "targets_identified": (
                self.networking.target_count
            ),
            "contacts_collected": (
                self.followup.contact_count
            ),
            "speakers_tracked": (
                self.speakers.tracked_count
            ),
            "rois_calculated": (
                self.roi.calculated_count
            ),
        }
