"""ATLAS Dolandırıcılık Tespit Orkestratörü.

Tam tespit pipeline,
Scan → Match → Score → Triage → Report,
gerçek zamanlı izleme, analitik.
"""

import logging
import time
from typing import Any

from app.core.frauddetect.alert_triager import (
    AlertTriager,
)
from app.core.frauddetect.anomaly_scanner import (
    AnomalyScanner,
)
from app.core.frauddetect.behavior_baseline import (
    BehaviorBaseline,
)
from app.core.frauddetect.false_positive_filter import (
    FalsePositiveFilter,
)
from app.core.frauddetect.fraud_pattern_matcher import (
    FraudPatternMatcher,
)
from app.core.frauddetect.incident_reporter import (
    FraudIncidentReporter,
)
from app.core.frauddetect.learning_detector import (
    LearningDetector,
)
from app.core.frauddetect.risk_scorer import (
    FraudRiskScorer,
)

logger = logging.getLogger(__name__)


class FraudDetectOrchestrator:
    """Dolandırıcılık tespit orkestratörü.

    Tüm tespit bileşenlerini koordine eder.

    Attributes:
        scanner: Anomali tarayıcı.
        patterns: Kalıp eşleştirici.
        baseline: Davranış temeli.
        triager: Uyarı önceliklendirici.
        fp_filter: Yanlış pozitif filtresi.
        reporter: Olay raporlayıcı.
        detector: Öğrenen dedektör.
        scorer: Risk puanlayıcı.
    """

    def __init__(self) -> None:
        """Orkestratörü başlatır."""
        self.scanner = AnomalyScanner()
        self.patterns = (
            FraudPatternMatcher()
        )
        self.baseline = BehaviorBaseline()
        self.triager = AlertTriager()
        self.fp_filter = (
            FalsePositiveFilter()
        )
        self.reporter = (
            FraudIncidentReporter()
        )
        self.detector = LearningDetector()
        self.scorer = FraudRiskScorer()
        self._stats = {
            "pipelines_run": 0,
            "frauds_detected": 0,
        }

        logger.info(
            "FraudDetectOrchestrator "
            "baslatildi",
        )

    def run_detection_pipeline(
        self,
        entity: str,
        data: dict[str, float]
        | None = None,
        signals: list[str]
        | None = None,
    ) -> dict[str, Any]:
        """Tam tespit pipeline çalıştırır.

        Args:
            entity: Varlık.
            data: Veri.
            signals: Sinyaller.

        Returns:
            Pipeline bilgisi.
        """
        data = data or {}
        signals = signals or []

        # 1. Scan - anomali kontrolü
        anomaly_score = 0.0
        for key, val in data.items():
            self.scanner.add_data_point(
                entity, val,
            )
            result = (
                self.scanner
                .detect_statistical(
                    entity, val,
                )
            )
            if result.get("is_anomaly"):
                anomaly_score = max(
                    anomaly_score, 80.0,
                )

        # 2. Match - kalıp kontrolü
        match_result = (
            self.patterns
            .match_known_pattern(signals)
        )
        pattern_score = (
            70.0 if match_result["matched"]
            else 0.0
        )

        # 3. Score
        risk = self.scorer.calculate_risk(
            entity,
            factors={
                "anomaly": anomaly_score,
                "pattern": pattern_score,
            },
        )

        # 4. Triage
        alert_id = f"alert_{entity}"
        self.triager.score_alert(
            alert_id,
            severity=risk.get("score", 0),
            confidence=50.0,
            impact=anomaly_score,
        )
        self.triager.assign_priority(
            alert_id,
        )

        # 5. FP check
        fp_check = (
            self.fp_filter
            .check_false_positive(
                alert_id,
                entity=entity,
                score=risk.get("score", 0),
            )
        )

        is_fraud = (
            not fp_check["is_fp"]
            and risk.get("score", 0) >= 40
        )

        if is_fraud:
            self._stats[
                "frauds_detected"
            ] += 1

        self._stats["pipelines_run"] += 1

        return {
            "entity": entity,
            "risk_score": risk.get(
                "score", 0,
            ),
            "risk_level": risk.get(
                "level", "low",
            ),
            "is_fraud": is_fraud,
            "is_fp": fp_check["is_fp"],
            "pattern_matched": (
                match_result["matched"]
            ),
            "pipeline_complete": True,
        }

    def monitor_realtime(
        self,
        entity: str,
        value: float,
        source: str = "default",
    ) -> dict[str, Any]:
        """Gerçek zamanlı izleme yapar.

        Args:
            entity: Varlık.
            value: Değer.
            source: Kaynak.

        Returns:
            İzleme bilgisi.
        """
        self.scanner.add_data_point(
            source, value,
        )
        result = (
            self.scanner.detect_statistical(
                source, value,
            )
        )

        alert_generated = result.get(
            "is_anomaly", False,
        )

        return {
            "entity": entity,
            "value": value,
            "is_anomaly": result.get(
                "is_anomaly", False,
            ),
            "alert_generated": (
                alert_generated
            ),
            "monitored": True,
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
            "frauds_detected": self._stats[
                "frauds_detected"
            ],
            "scans": (
                self.scanner.scan_count
            ),
            "anomalies": (
                self.scanner.anomaly_count
            ),
            "patterns": (
                self.patterns.pattern_count
            ),
            "pattern_matches": (
                self.patterns.match_count
            ),
            "profiles": (
                self.baseline.profile_count
            ),
            "triaged": (
                self.triager.triage_count
            ),
            "false_positives": (
                self.fp_filter.fp_count
            ),
            "incidents": (
                self.reporter
                .incident_count
            ),
            "ml_detections": (
                self.detector
                .detection_count
            ),
            "risk_scores": (
                self.scorer.score_count
            ),
        }

    @property
    def pipeline_count(self) -> int:
        """Pipeline sayısı."""
        return self._stats[
            "pipelines_run"
        ]

    @property
    def fraud_count(self) -> int:
        """Dolandırıcılık sayısı."""
        return self._stats[
            "frauds_detected"
        ]
