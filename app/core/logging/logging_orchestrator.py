"""ATLAS Loglama Orkestratoru modulu.

Tam loglama pipeline, gercek zamanli
izleme, uyari entegrasyonu,
analitik ve yapilandirma.
"""

import logging
import time
from typing import Any

from app.models.logging_models import LogLevel
from app.core.logging.log_manager import (
    LogManager,
)
from app.core.logging.log_formatter import (
    LogFormatter,
)
from app.core.logging.log_aggregator import (
    LogAggregator,
)
from app.core.logging.audit_recorder import (
    AuditRecorder,
)
from app.core.logging.log_searcher import (
    LogSearcher,
)
from app.core.logging.log_analyzer import (
    LogAnalyzer,
)
from app.core.logging.compliance_reporter import (
    ComplianceReporter,
)
from app.core.logging.log_exporter import (
    LogExporter,
)

logger = logging.getLogger(__name__)


class LoggingOrchestrator:
    """Loglama orkestratoru.

    Tum loglama bilesenlerini
    koordine eder.

    Attributes:
        manager: Log yoneticisi.
        formatter: Log bicimlendirici.
        aggregator: Log toplayici.
        audit: Denetim kaydedici.
        searcher: Log arayici.
        analyzer: Log analizcisi.
        compliance: Uyumluluk raporlayici.
        exporter: Log disa aktarici.
    """

    def __init__(
        self,
        level: LogLevel = LogLevel.INFO,
    ) -> None:
        """Loglama orkestratorunu baslatir.

        Args:
            level: Log seviyesi.
        """
        self._started_at = time.time()

        self.manager = LogManager(level=level)
        self.formatter = LogFormatter()
        self.aggregator = LogAggregator()
        self.audit = AuditRecorder()
        self.searcher = LogSearcher()
        self.analyzer = LogAnalyzer()
        self.compliance = ComplianceReporter()
        self.exporter = LogExporter()

        self._alerts: list[
            dict[str, Any]
        ] = []

        logger.info(
            "LoggingOrchestrator baslatildi",
        )

    def log(
        self,
        level: LogLevel,
        message: str,
        source: str = "",
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """Log kaydeder ve isler.

        Args:
            level: Log seviyesi.
            message: Mesaj.
            source: Kaynak.
            context: Baglam.

        Returns:
            Log kaydi.
        """
        record = self.manager.log(
            level, message, source, context,
        )
        if record:
            # Arayiciya indeksle
            self.searcher.index_logs([record])

            # Toplayiciya ekle
            self.aggregator.collect(
                source or "main", record,
            )

            # Hata uyarisi
            if level in (
                LogLevel.ERROR,
                LogLevel.CRITICAL,
            ):
                self._alerts.append({
                    "level": level.value,
                    "message": message,
                    "source": source,
                    "timestamp": time.time(),
                })

        return record

    def audit_action(
        self,
        action: str,
        actor: str,
        resource: str,
        before: dict[str, Any] | None = None,
        after: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Denetim kaydeder.

        Args:
            action: Aksiyon.
            actor: Aktor.
            resource: Kaynak.
            before: Onceki durum.
            after: Sonraki durum.

        Returns:
            Denetim kaydi.
        """
        record = self.audit.record(
            action, actor, resource,
            before, after,
        )

        # Erisim logu
        self.compliance.log_access(
            actor, resource, action,
        )

        return record

    def search_logs(
        self,
        query: str = "",
        level: str = "",
        source: str = "",
    ) -> list[dict[str, Any]]:
        """Log arar.

        Args:
            query: Arama sorgusu.
            level: Seviye filtresi.
            source: Kaynak filtresi.

        Returns:
            Sonuclar.
        """
        return self.searcher.combined_search(
            query=query,
            level=level,
            source=source,
        )

    def analyze(self) -> dict[str, Any]:
        """Log analizi yapar.

        Returns:
            Analiz sonucu.
        """
        logs = self.manager.get_logs(limit=10000)
        patterns = self.analyzer.detect_patterns(
            logs,
        )
        anomalies = self.analyzer.detect_anomalies(
            logs,
        )
        trends = self.analyzer.analyze_trends(
            logs,
        )

        return {
            "patterns": len(patterns),
            "anomalies": len(anomalies),
            "trend": trends.get("trend", "stable"),
            "total_logs": len(logs),
        }

    def get_analytics(self) -> dict[str, Any]:
        """Analitik getirir.

        Returns:
            Analitik bilgisi.
        """
        return {
            "total_logs": self.manager.log_count,
            "total_audits": (
                self.audit.record_count
            ),
            "indexed": (
                self.searcher.indexed_count
            ),
            "alerts": len(self._alerts),
            "exports": (
                self.exporter.export_count
            ),
            "compliance_reports": (
                self.compliance.report_count
            ),
        }

    def snapshot(self) -> dict[str, Any]:
        """Loglama durumunu dondurur.

        Returns:
            Durum bilgisi.
        """
        return {
            "uptime": round(
                time.time() - self._started_at,
                2,
            ),
            "logs": self.manager.log_count,
            "audits": self.audit.record_count,
            "sources": (
                self.aggregator.source_count
            ),
            "indexed": (
                self.searcher.indexed_count
            ),
            "exports": (
                self.exporter.export_count
            ),
            "alerts": len(self._alerts),
            "chain_valid": self.audit.chain_valid,
        }

    @property
    def alert_count(self) -> int:
        """Uyari sayisi."""
        return len(self._alerts)
