"""ATLAS Müsaitlik Orkestratörü modülü.

Tam müsaitlik yönetimi pipeline'ı,
Learn → Detect → Buffer → Decide → Deliver,
kullanıcı deneyimi optimizasyonu,
analitik ve raporlama.
"""

import logging
from typing import Any

from app.core.availability.availability_learner import (
    AvailabilityLearner,
)
from app.core.availability.digest_compiler import (
    DigestCompiler,
)
from app.core.availability.interrupt_decider import (
    InterruptDecider,
)
from app.core.availability.message_buffer import (
    MessageBuffer,
)
from app.core.availability.priority_scorer import (
    ContextualPriorityScorer,
)
from app.core.availability.quiet_hours_manager import (
    QuietHoursManager,
)
from app.core.availability.routine_detector import (
    RoutineDetector,
)
from app.core.availability.urgency_override import (
    UrgencyOverride,
)

logger = logging.getLogger(__name__)


class AvailabilityOrchestrator:
    """Müsaitlik orkestratörü.

    Tüm müsaitlik bileşenlerini koordine eder.

    Attributes:
        learner: Müsaitlik öğrenici.
        scorer: Öncelik puanlayıcı.
        buffer: Mesaj tamponu.
        decider: Kesme kararıcı.
        detector: Rutin tespitçisi.
        quiet_hours: Sessiz saat yöneticisi.
        urgency: Aciliyet geçersiz kılma.
        digest: Özet derleyici.
    """

    def __init__(
        self,
        quiet_start: str = "22:00",
        quiet_end: str = "08:00",
        learning_enabled: bool = True,
        digest_enabled: bool = True,
    ) -> None:
        """Orkestratörü başlatır.

        Args:
            quiet_start: Sessiz saat başlangıcı.
            quiet_end: Sessiz saat bitişi.
            learning_enabled: Öğrenme aktif.
            digest_enabled: Özet aktif.
        """
        self.learner = AvailabilityLearner()
        self.scorer = ContextualPriorityScorer()
        self.buffer = MessageBuffer()
        self.decider = InterruptDecider()
        self.detector = RoutineDetector()
        self.quiet_hours = QuietHoursManager(
            default_start=quiet_start,
            default_end=quiet_end,
        )
        self.urgency = UrgencyOverride()
        self.digest = DigestCompiler()

        self._learning_enabled = learning_enabled
        self._digest_enabled = digest_enabled
        self._stats = {
            "messages_processed": 0,
            "delivered_immediately": 0,
            "buffered": 0,
            "digested": 0,
        }

        logger.info(
            "AvailabilityOrchestrator "
            "baslatildi",
        )

    def process_message(
        self,
        content: str,
        source: str = "user",
        urgency: float = 0.5,
        impact: float = 0.5,
        hour: int = 12,
        day_of_week: int = 0,
        user_state: str = "available",
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Mesaj işler.

        Tam pipeline: Score → QuietCheck →
        Emergency → Decide → Buffer/Deliver.

        Args:
            content: Mesaj içeriği.
            source: Kaynak.
            urgency: Aciliyet.
            impact: Etki.
            hour: Saat.
            day_of_week: Gün.
            user_state: Kullanıcı durumu.
            context: Bağlam.

        Returns:
            İşleme bilgisi.
        """
        self._stats["messages_processed"] += 1
        ctx = context or {}

        # 1) Score
        score_result = self.scorer.score(
            message=content,
            source=source,
            urgency=urgency,
            impact=impact,
            context=ctx,
        )
        priority_score = score_result[
            "total_score"
        ]

        # 2) Learn (gözlem kaydet)
        if self._learning_enabled:
            self.learner.observe(
                state=user_state,
                hour=hour,
                day_of_week=day_of_week,
            )
            self.detector.record_event(
                event_type=user_state,
                hour=hour,
                day_of_week=day_of_week,
            )

        # 3) Quiet hours check
        quiet_check = (
            self.quiet_hours.is_quiet_hours(
                hour=hour,
                day_of_week=day_of_week,
            )
        )
        is_quiet = quiet_check["is_quiet"]

        # 4) Emergency check
        emergency = (
            self.urgency.detect_emergency(
                message=content,
                priority_score=priority_score,
                source=source,
            )
        )

        # Acil durum override
        if emergency["is_emergency"]:
            self.urgency.override(
                reason="emergency_detected",
                source=source,
            )
            if is_quiet:
                self.quiet_hours.emergency_bypass(
                    reason="emergency_message",
                    source=source,
                )
            self._stats[
                "delivered_immediately"
            ] += 1
            return {
                "action": "deliver_now",
                "priority_score": priority_score,
                "level": score_result["level"],
                "is_emergency": True,
                "content": content,
            }

        # 5) Decide
        decision = self.decider.decide(
            priority_score=priority_score,
            user_state=user_state,
            is_quiet_hours=is_quiet,
            context=ctx,
        )

        action = decision["action"]

        # 6) Execute action
        if action == "deliver_now":
            self._stats[
                "delivered_immediately"
            ] += 1
            return {
                "action": "deliver_now",
                "priority_score": priority_score,
                "level": score_result["level"],
                "is_emergency": False,
                "content": content,
            }

        if action == "digest":
            self.buffer.enqueue(
                content=content,
                priority=score_result["level"],
                source=source,
            )
            self._stats["digested"] += 1
            return {
                "action": "digest",
                "priority_score": priority_score,
                "level": score_result["level"],
                "is_emergency": False,
                "buffered": True,
            }

        # Default: buffer
        self.buffer.enqueue(
            content=content,
            priority=score_result["level"],
            source=source,
        )
        self._stats["buffered"] += 1
        return {
            "action": "buffer",
            "priority_score": priority_score,
            "level": score_result["level"],
            "is_emergency": False,
            "buffered": True,
        }

    def deliver_digest(
        self,
        title: str = "Özet",
    ) -> dict[str, Any]:
        """Özet teslim eder.

        Args:
            title: Özet başlığı.

        Returns:
            Teslimat bilgisi.
        """
        if not self._digest_enabled:
            return {
                "delivered": False,
                "reason": "digest_disabled",
            }

        messages = self.buffer.batch_collect(
            min_priority="informational",
        )

        if not messages:
            return {
                "delivered": False,
                "reason": "no_messages",
                "message_count": 0,
            }

        digest_result = self.digest.compile(
            messages=messages,
            title=title,
        )

        return {
            "delivered": True,
            "digest_id": digest_result[
                "digest_id"
            ],
            "message_count": digest_result[
                "message_count"
            ],
            "summary": digest_result["summary"],
            "actions": digest_result["actions"],
        }

    def get_analytics(self) -> dict[str, Any]:
        """Analitik raporu.

        Returns:
            Rapor.
        """
        return {
            "messages_processed": self._stats[
                "messages_processed"
            ],
            "delivered_immediately": self._stats[
                "delivered_immediately"
            ],
            "buffered": self._stats["buffered"],
            "digested": self._stats["digested"],
            "buffer_size": self.buffer.size,
            "patterns_learned": (
                self.learner.pattern_count
            ),
            "routines_detected": (
                self.detector.routine_count
            ),
            "quiet_periods": (
                self.quiet_hours.period_count
            ),
            "emergencies": (
                self.urgency.emergency_count
            ),
            "overrides": (
                self.urgency.override_count
            ),
            "digests_created": (
                self.digest.digest_count
            ),
            "scores_calculated": (
                self.scorer.scores_calculated
            ),
            "decisions_made": (
                self.decider.decisions_made
            ),
        }

    def get_status(self) -> dict[str, Any]:
        """Durum bilgisi.

        Returns:
            Durum.
        """
        return {
            "messages_processed": self._stats[
                "messages_processed"
            ],
            "buffer_size": self.buffer.size,
            "learning_enabled": (
                self._learning_enabled
            ),
            "digest_enabled": (
                self._digest_enabled
            ),
            "patterns_learned": (
                self.learner.pattern_count
            ),
        }

    @property
    def messages_processed(self) -> int:
        """İşlenen mesaj sayısı."""
        return self._stats[
            "messages_processed"
        ]
