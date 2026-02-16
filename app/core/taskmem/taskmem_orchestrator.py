"""ATLAS Görev Hafızası Orkestratörü modülü.

Tam görev hafızası pipeline'ı,
Learn → Remember → Apply → Improve,
çapraz görev öğrenme, analitik.
"""

import logging
from typing import Any

from app.core.taskmem.command_pattern_learner import (
    CommandPatternLearner,
)
from app.core.taskmem.command_predictor import (
    CommandPredictor,
)
from app.core.taskmem.execution_memory import (
    ExecutionMemory,
)
from app.core.taskmem.feedback_integrator import (
    TaskFeedbackIntegrator,
)
from app.core.taskmem.personalization_engine import (
    PersonalizationEngine,
)
from app.core.taskmem.preference_tracker import (
    TaskPreferenceTracker,
)
from app.core.taskmem.quality_improver import (
    QualityImprover,
)
from app.core.taskmem.task_template_builder import (
    TaskTemplateBuilder,
)

logger = logging.getLogger(__name__)


class TaskMemOrchestrator:
    """Görev hafızası orkestratörü.

    Tüm görev hafızası bileşenlerini koordine eder.

    Attributes:
        patterns: Komut örüntü öğrenici.
        predictor: Komut tahmincisi.
        execution: Yürütme hafızası.
        feedback: Geri bildirim entegratörü.
        personalization: Kişiselleştirme motoru.
        preferences: Tercih takipçisi.
        quality: Kalite iyileştirici.
        templates: Şablon oluşturucu.
    """

    def __init__(
        self,
        learning_rate: float = 0.1,
        personalization_level: str = (
            "moderate"
        ),
    ) -> None:
        """Orkestratörü başlatır.

        Args:
            learning_rate: Öğrenme hızı.
            personalization_level: Seviye.
        """
        self.patterns = (
            CommandPatternLearner()
        )
        self.predictor = CommandPredictor()
        self.execution = ExecutionMemory()
        self.feedback = (
            TaskFeedbackIntegrator()
        )
        self.personalization = (
            PersonalizationEngine(
                level=personalization_level,
            )
        )
        self.preferences = (
            TaskPreferenceTracker()
        )
        self.quality = QualityImprover()
        self.templates = (
            TaskTemplateBuilder()
        )

        self._learning_rate = learning_rate
        self._stats = {
            "tasks_processed": 0,
            "learnings_applied": 0,
            "improvements_made": 0,
        }

        logger.info(
            "TaskMemOrchestrator baslatildi",
        )

    def process_task(
        self,
        task_id: str,
        command: str,
        context: str = "",
        success: bool = True,
        duration_ms: float = 0.0,
    ) -> dict[str, Any]:
        """Görev işler - tam pipeline.

        Args:
            task_id: Görev ID.
            command: Komut.
            context: Bağlam.
            success: Başarılı mı.
            duration_ms: Süre.

        Returns:
            İşlem bilgisi.
        """
        # 1) Komutu kaydet
        self.patterns.record_command(
            command=command,
            context=context,
        )

        # 2) Gözlemle (tahmin için)
        self.predictor.observe(
            command=command,
            context=context,
        )

        # 3) Yürütme kaydet
        self.execution.record_execution(
            task_id=task_id,
            command=command,
            success=success,
            duration_ms=duration_ms,
        )

        # 4) Örüntü çıkar
        patterns = (
            self.patterns.extract_patterns()
        )

        # 5) Sonraki tahmin
        prediction = (
            self.predictor.predict_next(
                command,
            )
        )

        self._stats["tasks_processed"] += 1

        return {
            "task_id": task_id,
            "command": command,
            "success": success,
            "patterns_found": patterns[
                "patterns_found"
            ],
            "next_prediction": (
                prediction["predictions"][:1]
            ),
            "processed": True,
        }

    def learn_from_feedback(
        self,
        task_id: str,
        rating: float,
        comment: str = "",
    ) -> dict[str, Any]:
        """Geri bildirimden öğrenir.

        Args:
            task_id: Görev ID.
            rating: Puan.
            comment: Yorum.

        Returns:
            Öğrenme bilgisi.
        """
        # Geri bildirim kaydet
        fb = self.feedback.record_explicit(
            task_id=task_id,
            rating=rating,
            comment=comment,
        )

        # Memnuniyet kontrol
        satisfaction = (
            self.feedback
            .get_satisfaction_score()
        )

        # Kişiselleştirme öğren
        if rating >= 4.0:
            self.personalization.learn(
                observation=(
                    f"High satisfaction "
                    f"for task {task_id}"
                ),
                category="satisfaction",
                confidence=0.8,
            )
        elif rating <= 2.0:
            self.personalization.learn(
                observation=(
                    f"Low satisfaction "
                    f"for task {task_id}: "
                    f"{comment}"
                ),
                category="improvement",
                confidence=0.9,
            )

        self._stats[
            "learnings_applied"
        ] += 1

        return {
            "task_id": task_id,
            "rating": rating,
            "satisfaction": satisfaction[
                "score"
            ],
            "trend": satisfaction["trend"],
            "learned": True,
        }

    def personalize_output(
        self,
        content: str,
        task_type: str = "",
        context: str = "",
    ) -> dict[str, Any]:
        """Çıktıyı kişiselleştirir.

        Args:
            content: İçerik.
            task_type: Görev tipi.
            context: Bağlam.

        Returns:
            Kişiselleştirilmiş çıktı.
        """
        # Tercihleri uygula
        prefs = self.preferences.apply_preferences(
            task_type,
        )

        # Kişiselleştir
        adapted = (
            self.personalization
            .adapt_response(
                content=content,
                context=context,
            )
        )

        self._stats[
            "improvements_made"
        ] += 1

        return {
            "original_length": len(content),
            "personalized_content": adapted[
                "adapted_content"
            ],
            "adaptations": adapted[
                "adaptations"
            ],
            "preferences": prefs.get(
                "preferences", {},
            ),
            "personalized": True,
        }

    def get_analytics(
        self,
    ) -> dict[str, Any]:
        """Analitik raporu.

        Returns:
            Rapor.
        """
        return {
            "tasks_processed": (
                self._stats[
                    "tasks_processed"
                ]
            ),
            "learnings_applied": (
                self._stats[
                    "learnings_applied"
                ]
            ),
            "improvements_made": (
                self._stats[
                    "improvements_made"
                ]
            ),
            "patterns_learned": (
                self.patterns.pattern_count
            ),
            "commands_recorded": (
                self.patterns.command_count
            ),
            "predictions_made": (
                self.predictor
                .prediction_count
            ),
            "prediction_accuracy": (
                self.predictor.accuracy
            ),
            "executions_recorded": (
                self.execution
                .execution_count
            ),
            "success_rate": (
                self.execution.success_rate
            ),
            "feedbacks_received": (
                self.feedback.feedback_count
            ),
            "templates_created": (
                self.templates.template_count
            ),
            "quality_scores": (
                self.quality.score_count
            ),
            "adaptations": (
                self.personalization
                .adaptation_count
            ),
        }

    def get_status(self) -> dict[str, Any]:
        """Durum bilgisi.

        Returns:
            Durum.
        """
        satisfaction = (
            self.feedback
            .get_satisfaction_score()
        )
        return {
            "tasks_processed": (
                self._stats[
                    "tasks_processed"
                ]
            ),
            "patterns": (
                self.patterns.pattern_count
            ),
            "templates": (
                self.templates.template_count
            ),
            "satisfaction": satisfaction[
                "score"
            ],
            "prediction_accuracy": (
                self.predictor.accuracy
            ),
        }

    @property
    def task_count(self) -> int:
        """İşlenen görev sayısı."""
        return self._stats[
            "tasks_processed"
        ]
