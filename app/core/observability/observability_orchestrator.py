"""ATLAS Izlenebilirlik Orkestratoru modulu.

Tam izlenebilirlik pipeline'i,
birlesik gorunum, korelasyon,
analitik ve entegrasyon.
"""

import logging
import time
from typing import Any

from app.core.observability.alert_manager import (
    AlertManager,
)
from app.core.observability.anomaly_detector import (
    AnomalyDetector,
)
from app.core.observability.dashboard_builder import (
    DashboardBuilder,
)
from app.core.observability.health_checker import (
    HealthChecker,
)
from app.core.observability.metrics_collector import (
    MetricsCollector,
)
from app.core.observability.sla_monitor import (
    SLAMonitor,
)
from app.core.observability.span_collector import (
    SpanCollector,
)
from app.core.observability.trace_manager import (
    TraceManager,
)

logger = logging.getLogger(__name__)


class ObservabilityOrchestrator:
    """Izlenebilirlik orkestratoru.

    Tum izlenebilirlik bilesenlierini
    koordine eder.

    Attributes:
        traces: Iz yoneticisi.
        spans: Span toplayici.
        metrics: Metrik toplayici.
        health: Saglik kontrolcusu.
        alerts: Uyari yoneticisi.
        dashboards: Panel olusturucu.
        anomalies: Anomali tespitcisi.
        sla: SLA izleyici.
    """

    def __init__(
        self,
        sampling_rate: float = 1.0,
        sensitivity: float = 2.0,
    ) -> None:
        """Orkestratoru baslatir.

        Args:
            sampling_rate: Ornekleme orani.
            sensitivity: Anomali hassasiyeti.
        """
        self.traces = TraceManager(sampling_rate)
        self.spans = SpanCollector()
        self.metrics = MetricsCollector()
        self.health = HealthChecker()
        self.alerts = AlertManager()
        self.dashboards = DashboardBuilder()
        self.anomalies = AnomalyDetector(
            sensitivity,
        )
        self.sla = SLAMonitor()

        self._correlations: list[
            dict[str, Any]
        ] = []
        self._initialized = False

        logger.info(
            "ObservabilityOrchestrator baslatildi",
        )

    def initialize(
        self,
        default_dashboards: bool = True,
    ) -> dict[str, Any]:
        """Sistemi baslatir.

        Args:
            default_dashboards: Varsayilan paneller.

        Returns:
            Baslangic bilgisi.
        """
        components = 0

        if default_dashboards:
            self.dashboards.create_dashboard(
                "system",
                title="System Overview",
            )
            self.dashboards.create_dashboard(
                "alerts",
                title="Alert Dashboard",
            )
            components += 2

        self._initialized = True
        return {
            "status": "initialized",
            "components": components,
        }

    def record_request(
        self,
        name: str,
        duration_ms: float,
        success: bool = True,
        attributes: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Istek kaydeder (iz + metrik + SLA).

        Args:
            name: Istek adi.
            duration_ms: Sure (ms).
            success: Basarili mi.
            attributes: Nitelikler.

        Returns:
            Kayit sonucu.
        """
        # Iz olustur
        trace = self.traces.start_trace(
            name, attributes,
        )
        trace_id = trace.get("trace_id", "")

        if trace_id:
            span = self.traces.start_span(
                trace_id, name,
            )
            span_id = span.get("span_id", "")
            if span_id:
                self.traces.end_span(
                    trace_id, span_id,
                    "ok" if success else "error",
                )
            self.traces.end_trace(
                trace_id,
                "completed" if success
                else "error",
            )

        # Metrik kaydet
        self.metrics.increment(
            f"{name}_total",
        )
        self.metrics.observe(
            f"{name}_duration", duration_ms,
        )
        if not success:
            self.metrics.increment(
                f"{name}_errors",
            )

        # Anomali kontrol
        anomaly = self.anomalies.add_data_point(
            f"{name}_duration", duration_ms,
        )

        # Uyari degerlendirmesi
        alerts = self.alerts.evaluate(
            f"{name}_duration", duration_ms,
        )

        return {
            "trace_id": trace_id,
            "duration_ms": duration_ms,
            "success": success,
            "anomaly_detected": anomaly is not None,
            "alerts_triggered": len(alerts),
        }

    def check_system_health(
        self,
    ) -> dict[str, Any]:
        """Sistem sagligini kontrol eder.

        Returns:
            Saglik durumu.
        """
        health = self.health.get_aggregate_status()

        # Metrik olarak kaydet
        status_map = {
            "healthy": 1.0,
            "degraded": 0.5,
            "unhealthy": 0.0,
        }
        self.metrics.set_gauge(
            "system_health",
            status_map.get(
                health["status"], 0.0,
            ),
        )

        return health

    def correlate_events(
        self,
        event_a: dict[str, Any],
        event_b: dict[str, Any],
        relation: str = "caused_by",
    ) -> dict[str, Any]:
        """Olaylari iliskilendirir.

        Args:
            event_a: Olay A.
            event_b: Olay B.
            relation: Iliski.

        Returns:
            Korelasyon bilgisi.
        """
        correlation = {
            "event_a": event_a,
            "event_b": event_b,
            "relation": relation,
            "timestamp": time.time(),
        }
        self._correlations.append(correlation)
        return {
            "relation": relation,
            "correlation_index": len(
                self._correlations,
            ) - 1,
        }

    def get_unified_view(self) -> dict[str, Any]:
        """Birlesik gorunum getirir.

        Returns:
            Birlesik izlenebilirlik verisi.
        """
        health = self.health.get_aggregate_status()
        alert_summary = (
            self.alerts.get_alert_summary()
        )

        return {
            "health": health["status"],
            "active_traces": (
                self.traces.active_trace_count
            ),
            "completed_traces": (
                self.traces.completed_trace_count
            ),
            "total_metrics": (
                self.metrics.total_metrics
            ),
            "active_alerts": (
                alert_summary["active"]
            ),
            "anomalies": (
                self.anomalies.anomaly_count
            ),
            "slo_count": self.sla.slo_count,
            "dashboards": (
                self.dashboards.dashboard_count
            ),
            "correlations": len(
                self._correlations,
            ),
            "initialized": self._initialized,
            "timestamp": time.time(),
        }

    def get_analytics(self) -> dict[str, Any]:
        """Analitik raporu getirir.

        Returns:
            Analitik bilgisi.
        """
        return {
            "traces": {
                "active": (
                    self.traces.active_trace_count
                ),
                "completed": (
                    self.traces.completed_trace_count
                ),
                "sampling_rate": (
                    self.traces.sampling_rate
                ),
            },
            "metrics": {
                "counters": (
                    self.metrics.counter_count
                ),
                "gauges": self.metrics.gauge_count,
                "histograms": (
                    self.metrics.histogram_count
                ),
            },
            "alerts": (
                self.alerts.get_alert_summary()
            ),
            "anomalies": {
                "total": (
                    self.anomalies.anomaly_count
                ),
                "baselines": (
                    self.anomalies.baseline_count
                ),
            },
            "sla": {
                "total_slos": self.sla.slo_count,
                "breaches": self.sla.breach_count,
            },
            "timestamp": time.time(),
        }

    @property
    def correlation_count(self) -> int:
        """Korelasyon sayisi."""
        return len(self._correlations)

    @property
    def is_initialized(self) -> bool:
        """Baslatildi mi."""
        return self._initialized
