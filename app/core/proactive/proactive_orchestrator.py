"""ATLAS Proaktif Orkestratör modülü.

Tam 7/24 beyin, Tara→Tespit→Sırala→Karar→Aksiyon/Bildir,
tüm sistemlerle entegrasyon, analitik.
"""

import logging
from typing import Any

from app.core.proactive.action_decider import (
    ActionDecider,
)
from app.core.proactive.continuous_scanner import (
    ContinuousScanner,
)
from app.core.proactive.opportunity_ranker import (
    OpportunityRanker,
)
from app.core.proactive.periodic_reporter import (
    PeriodicReporter,
)
from app.core.proactive.proactive_anomaly_detector import (
    ProactiveAnomalyDetector,
)
from app.core.proactive.proactive_notifier import (
    ProactiveNotifier,
)
from app.core.proactive.priority_queue import (
    ProactivePriorityQueue,
)
from app.core.proactive.sleep_cycle_manager import (
    SleepCycleManager,
)

logger = logging.getLogger(__name__)


class ProactiveOrchestrator:
    """Proaktif orkestratör.

    Tüm proaktif bileşenleri koordine eder.

    Attributes:
        scanner: Sürekli tarayıcı.
        ranker: Fırsat sıralayıcı.
        detector: Anomali dedektörü.
        notifier: Bildirimci.
        reporter: Periyodik raporlayıcı.
        queue: Öncelik kuyruğu.
        sleep: Uyku döngüsü yöneticisi.
        decider: Aksiyon karar verici.
    """

    def __init__(
        self,
        scan_interval: int = 300,
        quiet_start: int = 23,
        quiet_end: int = 7,
        auto_threshold: float = 0.8,
    ) -> None:
        """Orkestratörü başlatır.

        Args:
            scan_interval: Tarama aralığı (sn).
            quiet_start: Sessiz saat başlangıcı.
            quiet_end: Sessiz saat bitişi.
            auto_threshold: Otomatik işlem eşiği.
        """
        self.scanner = ContinuousScanner(
            scan_interval=scan_interval,
        )
        self.ranker = OpportunityRanker()
        self.detector = (
            ProactiveAnomalyDetector()
        )
        self.notifier = ProactiveNotifier()
        self.reporter = PeriodicReporter()
        self.queue = ProactivePriorityQueue()
        self.sleep = SleepCycleManager(
            quiet_start=quiet_start,
            quiet_end=quiet_end,
        )
        self.decider = ActionDecider(
            auto_threshold=auto_threshold,
        )

        self._stats = {
            "cycles_completed": 0,
        }

        logger.info(
            "ProactiveOrchestrator "
            "baslatildi",
        )

    def run_cycle(
        self,
        data_map: dict[str, dict[str, Any]]
        | None = None,
    ) -> dict[str, Any]:
        """Tam proaktif döngü çalıştırır.

        Tara → Tespit → Sırala → Karar → Aksiyon.

        Args:
            data_map: Kaynak-veri eşlemesi.

        Returns:
            Döngü sonucu.
        """
        # 1) Tarama
        scan_result = self.scanner.scan_all(
            data_map,
        )

        # 2) Anomali tespiti
        anomalies = []
        if data_map:
            for source, data in data_map.items():
                for key, value in data.items():
                    if isinstance(
                        value, (int, float),
                    ):
                        result = (
                            self.detector
                            .detect_anomaly(
                                f"{source}.{key}",
                                value,
                            )
                        )
                        if result.get("anomaly"):
                            anomalies.append(
                                result,
                            )

        # 3) Bulgulari kuyruğa ekle
        queued = 0
        for finding in self._extract_findings(
            scan_result,
        ):
            priority = self._finding_priority(
                finding,
            )
            self.queue.enqueue(
                title=finding.get(
                    "type", "unknown",
                ),
                priority=priority,
                context=finding,
            )
            queued += 1

        # 4) Anomalileri kuyruğa ekle
        for anomaly in anomalies:
            sev_priority = {
                "critical": 10,
                "warning": 7,
                "notice": 5,
                "info": 3,
                "normal": 1,
            }
            priority = sev_priority.get(
                anomaly.get("severity", "info"),
                3,
            )
            self.queue.enqueue(
                title=(
                    f"anomaly:{anomaly['metric']}"
                ),
                priority=priority,
                context=anomaly,
            )

        # 5) Kuyruktan işle ve karar ver
        decisions = []
        process_limit = min(
            self.queue.size, 10,
        )
        for _ in range(process_limit):
            if self.queue.is_empty:
                break
            item = self.queue.dequeue()
            decision = self.decider.decide(
                action=item.get("title", ""),
                confidence=0.7,
                impact=self._estimate_impact(
                    item,
                ),
                risk=self._estimate_risk(item),
                context=item.get("context", {}),
            )
            decisions.append(decision)

            # Bildirim gönder
            should = self.sleep.should_notify(
                priority=item.get("priority", 5),
            )
            if should["should_notify"]:
                self.notifier.send_notification(
                    title=item.get(
                        "title", "Event",
                    ),
                    message=(
                        f"Decision: "
                        f"{decision['decision_type']}"
                    ),
                    priority=item.get(
                        "priority", 5,
                    ),
                )

        self._stats["cycles_completed"] += 1

        return {
            "cycle": self._stats[
                "cycles_completed"
            ],
            "sources_scanned": scan_result.get(
                "sources_scanned", 0,
            ),
            "total_findings": scan_result.get(
                "total_findings", 0,
            ),
            "anomalies_detected": len(anomalies),
            "items_queued": queued,
            "decisions_made": len(decisions),
            "decisions": decisions,
        }

    def _extract_findings(
        self,
        scan_result: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Tarama sonuçlarından bulguları çıkarır.

        Args:
            scan_result: Tarama sonucu.

        Returns:
            Bulgu listesi.
        """
        findings = []
        for result in scan_result.get(
            "results", [],
        ):
            for finding in result.get(
                "findings", [],
            ):
                findings.append(finding)
        return findings

    def _finding_priority(
        self,
        finding: dict[str, Any],
    ) -> int:
        """Bulgunun önceliğini belirler.

        Args:
            finding: Bulgu.

        Returns:
            Öncelik (1-10).
        """
        ftype = finding.get("type", "")
        if ftype == "error_detected":
            return 8
        if ftype == "threshold_exceeded":
            return 6
        if ftype == "warning_detected":
            return 5
        if ftype == "negative_value":
            return 4
        return 3

    def _estimate_impact(
        self,
        item: dict[str, Any],
    ) -> str:
        """Etki tahmin eder.

        Args:
            item: Kuyruk öğesi.

        Returns:
            Etki seviyesi.
        """
        priority = item.get("priority", 5)
        if priority >= 8:
            return "high"
        if priority >= 5:
            return "medium"
        return "low"

    def _estimate_risk(
        self,
        item: dict[str, Any],
    ) -> float:
        """Risk tahmin eder.

        Args:
            item: Kuyruk öğesi.

        Returns:
            Risk seviyesi (0-1).
        """
        priority = item.get("priority", 5)
        return min(1.0, priority / 10.0)

    def add_scan_source(
        self,
        name: str,
        source_type: str = "system",
    ) -> dict[str, Any]:
        """Tarama kaynağı ekler.

        Args:
            name: Kaynak adı.
            source_type: Kaynak tipi.

        Returns:
            Kayıt bilgisi.
        """
        return self.scanner.register_source(
            name, source_type,
        )

    def score_opportunity(
        self,
        title: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Fırsatı puanlar.

        Args:
            title: Fırsat başlığı.
            **kwargs: Ek parametreler.

        Returns:
            Puanlama bilgisi.
        """
        return self.ranker.score_opportunity(
            title, **kwargs,
        )

    def get_analytics(self) -> dict[str, Any]:
        """Analitik raporu.

        Returns:
            Rapor.
        """
        return {
            "cycles_completed": self._stats[
                "cycles_completed"
            ],
            "scan_sources": (
                self.scanner.source_count
            ),
            "total_scans": (
                self.scanner.scan_count
            ),
            "opportunities": (
                self.ranker.opportunity_count
            ),
            "anomalies": (
                self.detector.anomaly_count
            ),
            "baselines": (
                self.detector.baseline_count
            ),
            "notifications": (
                self.notifier.notification_count
            ),
            "reports": (
                self.reporter.report_count
            ),
            "queue_size": self.queue.size,
            "decisions": (
                self.decider.decision_count
            ),
            "auto_handle_rate": (
                self.decider.auto_handle_rate
            ),
        }

    def get_status(self) -> dict[str, Any]:
        """Durum bilgisi.

        Returns:
            Durum.
        """
        return {
            "cycles_completed": self._stats[
                "cycles_completed"
            ],
            "scan_sources": (
                self.scanner.source_count
            ),
            "queue_size": self.queue.size,
            "decisions_made": (
                self.decider.decision_count
            ),
        }

    @property
    def cycles_completed(self) -> int:
        """Tamamlanan döngü sayısı."""
        return self._stats["cycles_completed"]
