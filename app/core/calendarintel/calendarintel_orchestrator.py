"""ATLAS Takvim Zekası Orkestratörü.

Tam takvim zekası pipeline,
Schedule → Optimize → Prepare → Follow-up,
akıllı zamanlama, analitik.
"""

import logging
import time
from typing import Any

from app.core.calendarintel.agenda_creator import (
    AgendaCreator,
)
from app.core.calendarintel.availability_finder import (
    CalendarAvailabilityFinder,
)
from app.core.calendarintel.calendar_analyzer import (
    CalendarAnalyzer,
)
from app.core.calendarintel.conflict_resolver import (
    CalendarConflictResolver,
)
from app.core.calendarintel.meeting_followup_scheduler import (
    MeetingFollowUpScheduler,
)
from app.core.calendarintel.meeting_optimizer import (
    MeetingOptimizer,
)
from app.core.calendarintel.prep_brief_generator import (
    PrepBriefGenerator,
)
from app.core.calendarintel.timezone_manager import (
    CalendarTimezoneManager,
)

logger = logging.getLogger(__name__)


class CalendarIntelOrchestrator:
    """Takvim zekası orkestratörü.

    Tüm takvim zekası bileşenlerini
    koordine eder.

    Attributes:
        optimizer: Toplantı optimizasyonu.
        availability: Müsaitlik bulucu.
        timezones: Saat dilimi yöneticisi.
        conflicts: Çakışma çözücü.
        briefs: Hazırlık özeti üretici.
        agendas: Gündem oluşturucu.
        followups: Takip zamanlayıcı.
        analyzer: Takvim analizcisi.
    """

    def __init__(self) -> None:
        """Orkestratörü başlatır."""
        self.optimizer = MeetingOptimizer()
        self.availability = (
            CalendarAvailabilityFinder()
        )
        self.timezones = (
            CalendarTimezoneManager()
        )
        self.conflicts = (
            CalendarConflictResolver()
        )
        self.briefs = PrepBriefGenerator()
        self.agendas = AgendaCreator()
        self.followups = (
            MeetingFollowUpScheduler()
        )
        self.analyzer = CalendarAnalyzer()
        self._stats = {
            "pipelines_run": 0,
            "meetings_scheduled": 0,
        }

        logger.info(
            "CalendarIntelOrchestrator "
            "baslatildi",
        )

    def schedule_optimize_prepare(
        self,
        meeting_id: str,
        title: str = "",
        participants: list[str]
        | None = None,
        duration_minutes: int = 60,
        preferred_hour: int = 10,
    ) -> dict[str, Any]:
        """Schedule → Optimize → Prepare → Follow-up.

        Args:
            meeting_id: Toplantı kimliği.
            title: Başlık.
            participants: Katılımcılar.
            duration_minutes: Süre (dk).
            preferred_hour: Tercih saati.

        Returns:
            Pipeline bilgisi.
        """
        participants = participants or []

        # 1. Optimize
        optimal = (
            self.optimizer.find_optimal_time(
                participants=participants,
                duration_minutes=(
                    duration_minutes
                ),
                preferred_hour=(
                    preferred_hour
                ),
            )
        )

        # 2. Create agenda
        agenda = self.agendas.auto_create(
            meeting_id=meeting_id,
            duration_minutes=(
                duration_minutes
            ),
        )

        # 3. Prepare brief
        brief = self.briefs.generate_brief(
            meeting_id=meeting_id,
            title=title,
        )

        # 4. Schedule follow-up
        followup = (
            self.followups
            .schedule_followup(
                meeting_id=meeting_id,
                title=(
                    f"Follow-up: {title}"
                ),
            )
        )

        # 5. Add to analyzer
        self.analyzer.add_event(
            title=title,
            start_hour=preferred_hour,
            end_hour=(
                preferred_hour
                + duration_minutes // 60
            ),
        )

        self._stats[
            "pipelines_run"
        ] += 1
        self._stats[
            "meetings_scheduled"
        ] += 1

        return {
            "meeting_id": meeting_id,
            "suggested_time": optimal[
                "suggested_start"
            ],
            "agenda_created": agenda[
                "created"
            ],
            "brief_generated": brief[
                "generated"
            ],
            "followup_scheduled": followup[
                "scheduled"
            ],
            "pipeline_complete": True,
        }

    def smart_schedule(
        self,
        title: str = "",
        participants: list[str]
        | None = None,
        duration_minutes: int = 60,
    ) -> dict[str, Any]:
        """Akıllı zamanlama yapar.

        Args:
            title: Başlık.
            participants: Katılımcılar.
            duration_minutes: Süre (dk).

        Returns:
            Zamanlama bilgisi.
        """
        participants = participants or []

        # Müsaitlik kontrolü
        multi = (
            self.availability
            .find_multi_person(
                persons=participants,
                duration_hours=max(
                    duration_minutes // 60,
                    1,
                ),
            )
        )

        # Optimal süre
        optimal_dur = (
            self.optimizer
            .optimize_duration(
                participant_count=len(
                    participants,
                ),
            )
        )

        slot = (
            multi["common_slots"][0]
            if multi.get("common_slots")
            else {"start_hour": 10}
        )

        return {
            "title": title,
            "suggested_hour": slot.get(
                "start_hour", 10,
            ),
            "optimal_duration": (
                optimal_dur[
                    "optimal_duration"
                ]
            ),
            "slots_available": multi[
                "count"
            ],
            "scheduled": True,
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
            "meetings_scheduled": (
                self._stats[
                    "meetings_scheduled"
                ]
            ),
            "optimizations": (
                self.optimizer
                .optimization_count
            ),
            "availability_searches": (
                self.availability
                .search_count
            ),
            "conflicts_detected": (
                self.conflicts
                .conflict_count
            ),
            "briefs_generated": (
                self.briefs.brief_count
            ),
            "agendas_created": (
                self.agendas.agenda_count
            ),
            "followups_scheduled": (
                self.followups
                .followup_count
            ),
            "analyses": (
                self.analyzer
                .analysis_count
            ),
        }

    @property
    def pipeline_count(self) -> int:
        """Pipeline sayısı."""
        return self._stats[
            "pipelines_run"
        ]

    @property
    def meeting_count(self) -> int:
        """Toplantı sayısı."""
        return self._stats[
            "meetings_scheduled"
        ]
