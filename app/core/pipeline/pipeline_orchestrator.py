"""ATLAS Pipeline Orkestratoru modulu.

Tam ETL yonetimi, calistirma izleme,
hata islemleri, performans
optimizasyonu ve analitik.
"""

import logging
import time
from typing import Any

from app.models.pipeline import (
    PipelineSnapshot,
    PipelineStatus,
    SourceType,
    StepType,
)

from app.core.pipeline.data_extractor import (
    DataExtractor,
)
from app.core.pipeline.data_transformer import (
    DataTransformer,
)
from app.core.pipeline.data_loader import DataLoader
from app.core.pipeline.pipeline_builder import (
    PipelineBuilder,
)
from app.core.pipeline.data_validator import (
    DataValidator,
)
from app.core.pipeline.stream_processor import (
    StreamProcessor,
)
from app.core.pipeline.job_scheduler import (
    PipelineJobScheduler,
)
from app.core.pipeline.lineage_tracker import (
    LineageTracker,
)

logger = logging.getLogger(__name__)


class PipelineOrchestrator:
    """Pipeline orkestratoru.

    Tum pipeline alt sistemlerini
    koordine eder ve birlesik
    arayuz saglar.

    Attributes:
        extractor: Veri cikarici.
        transformer: Veri donusturucu.
        loader: Veri yukleyici.
        builder: Pipeline olusturucu.
        validator: Veri dogrulayici.
        stream: Akis isleyici.
        scheduler: Is zamanlayici.
        lineage: Soy takipcisi.
    """

    def __init__(
        self,
        max_parallel: int = 5,
        default_batch: int = 100,
        retry_attempts: int = 3,
        lineage_retention: int = 90,
    ) -> None:
        """Orkestratoru baslatir.

        Args:
            max_parallel: Maks paralel is.
            default_batch: Varsayilan parti.
            retry_attempts: Yeniden deneme.
            lineage_retention: Soy saklama (gun).
        """
        self.extractor = DataExtractor()
        self.transformer = DataTransformer()
        self.loader = DataLoader(
            default_batch_size=default_batch,
        )
        self.builder = PipelineBuilder()
        self.validator = DataValidator()
        self.stream = StreamProcessor()
        self.scheduler = PipelineJobScheduler(
            max_retries=retry_attempts,
        )
        self.lineage = LineageTracker(
            retention_days=lineage_retention,
        )

        self._max_parallel = max_parallel
        self._executions: list[dict[str, Any]] = []

        logger.info(
            "PipelineOrchestrator baslatildi",
        )

    def run_etl(
        self,
        source_name: str,
        target_name: str,
        mapping_name: str = "",
        query: str = "",
        validate: bool = True,
    ) -> dict[str, Any]:
        """Tam ETL calistirir.

        Args:
            source_name: Kaynak adi.
            target_name: Hedef adi.
            mapping_name: Esleme adi.
            query: Sorgu.
            validate: Dogrulama yap.

        Returns:
            ETL sonucu.
        """
        start = time.time()

        # 1. Extract
        extract_result = self.extractor.extract(
            source_name, query,
        )
        if not extract_result["success"]:
            return {
                "success": False,
                "stage": "extract",
                "reason": extract_result.get(
                    "reason", "extract_failed",
                ),
            }

        data = extract_result["data"]

        # 2. Transform
        if mapping_name:
            data = self.transformer.apply_mapping(
                data, mapping_name,
            )

        # 3. Validate
        if validate and data:
            quality = self.validator.check_quality(
                data,
            )
            if quality["score"] < 0.5:
                return {
                    "success": False,
                    "stage": "validate",
                    "reason": "low_quality",
                    "score": quality["score"],
                }

        # 4. Load
        load_result = self.loader.load(
            target_name, data,
        )
        if not load_result["success"]:
            return {
                "success": False,
                "stage": "load",
                "reason": load_result.get(
                    "reason", "load_failed",
                ),
            }

        duration = time.time() - start

        # 5. Lineage
        self.lineage.record(
            source_name, target_name,
            f"etl:{mapping_name}",
        )

        result = {
            "success": True,
            "source": source_name,
            "target": target_name,
            "extracted": extract_result[
                "record_count"
            ],
            "loaded": load_result["loaded"],
            "duration": round(duration, 4),
        }
        self._executions.append(result)

        logger.info(
            "ETL tamamlandi: %s -> %s (%d kayit)",
            source_name, target_name,
            load_result["loaded"],
        )
        return result

    def run_pipeline(
        self,
        pipeline_id: str,
    ) -> dict[str, Any]:
        """Pipeline calistirir.

        Args:
            pipeline_id: Pipeline ID.

        Returns:
            Calistirma sonucu.
        """
        pipeline = self.builder.get_pipeline(
            pipeline_id,
        )
        if not pipeline:
            return {
                "success": False,
                "reason": "pipeline_not_found",
            }

        pipeline.status = PipelineStatus.RUNNING
        start = time.time()

        order = self.builder.get_execution_order(
            pipeline_id,
        )
        steps = self.builder.get_steps(pipeline_id)
        completed = 0
        failed = 0

        for step in steps:
            step.status = PipelineStatus.RUNNING
            # Simule edilmis calistirma
            step.status = PipelineStatus.COMPLETED
            step.output_count = 1
            completed += 1

        duration = time.time() - start
        pipeline.status = PipelineStatus.COMPLETED

        result = {
            "success": True,
            "pipeline_id": pipeline_id,
            "name": pipeline.name,
            "steps_completed": completed,
            "steps_failed": failed,
            "duration": round(duration, 4),
        }
        self._executions.append(result)

        return result

    def get_analytics(self) -> dict[str, Any]:
        """Analitik verileri getirir.

        Returns:
            Analitik.
        """
        total = len(self._executions)
        success = sum(
            1 for e in self._executions
            if e.get("success")
        )
        failed = total - success

        avg_dur = 0.0
        if total > 0:
            durations = [
                e.get("duration", 0)
                for e in self._executions
            ]
            avg_dur = round(
                sum(durations) / total, 4,
            )

        return {
            "total_executions": total,
            "successful": success,
            "failed": failed,
            "success_rate": round(
                success / max(1, total), 3,
            ),
            "avg_duration": avg_dur,
            "total_sources": (
                self.extractor.source_count
            ),
            "total_targets": (
                self.loader.target_count
            ),
            "total_pipelines": (
                self.builder.pipeline_count
            ),
            "active_jobs": (
                self.scheduler.active_count
            ),
            "lineage_entries": (
                self.lineage.entry_count
            ),
        }

    def get_snapshot(self) -> PipelineSnapshot:
        """Goruntusu getirir.

        Returns:
            Goruntusu.
        """
        analytics = self.get_analytics()

        total_records = (
            self.extractor.total_records
            + self.loader.total_loaded
        )

        return PipelineSnapshot(
            total_pipelines=analytics[
                "total_pipelines"
            ],
            running=len(
                self.scheduler.get_running(),
            ),
            completed=analytics["successful"],
            failed=analytics["failed"],
            total_records_processed=total_records,
            avg_duration=analytics["avg_duration"],
            active_jobs=analytics["active_jobs"],
            lineage_entries=analytics[
                "lineage_entries"
            ],
        )

    @property
    def execution_count(self) -> int:
        """Calistirma sayisi."""
        return len(self._executions)
