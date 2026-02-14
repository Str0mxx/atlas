"""ATLAS Pipeline Is Zamanlayici modulu.

Cron zamanlama, bagimlilik tabanli,
yeniden deneme politikalari, hata
islemleri ve izleme.
"""

import logging
import time
from typing import Any

from app.models.pipeline import (
    JobFrequency,
    PipelineStatus,
)

logger = logging.getLogger(__name__)


class PipelineJobScheduler:
    """Pipeline is zamanlayici.

    Pipeline islerini zamanlar
    ve yonetir.

    Attributes:
        _jobs: Kayitli isler.
        _history: Calistirma gecmisi.
    """

    def __init__(
        self,
        max_retries: int = 3,
    ) -> None:
        """Is zamanlayiciyi baslatir.

        Args:
            max_retries: Maks yeniden deneme.
        """
        self._jobs: dict[str, dict[str, Any]] = {}
        self._history: list[dict[str, Any]] = []
        self._max_retries = max_retries
        self._job_counter = 0

        logger.info(
            "PipelineJobScheduler baslatildi",
        )

    def schedule(
        self,
        pipeline_id: str,
        frequency: JobFrequency,
        cron_expr: str = "",
        depends_on: list[str] | None = None,
    ) -> dict[str, Any]:
        """Is zamanlar.

        Args:
            pipeline_id: Pipeline ID.
            frequency: Siklik.
            cron_expr: Cron ifadesi.
            depends_on: Bagimli isler.

        Returns:
            Is bilgisi.
        """
        self._job_counter += 1
        job_id = f"job_{self._job_counter}"

        job = {
            "job_id": job_id,
            "pipeline_id": pipeline_id,
            "frequency": frequency.value,
            "cron_expr": cron_expr,
            "depends_on": depends_on or [],
            "enabled": True,
            "status": PipelineStatus.PENDING.value,
            "retries": 0,
            "last_run": None,
            "next_run": None,
        }
        self._jobs[job_id] = job

        logger.info(
            "Is zamanlandi: %s (%s)",
            job_id, frequency.value,
        )
        return job

    def run_job(
        self,
        job_id: str,
    ) -> dict[str, Any]:
        """Is calistirir.

        Args:
            job_id: Is ID.

        Returns:
            Calistirma sonucu.
        """
        job = self._jobs.get(job_id)
        if not job or not job["enabled"]:
            return {
                "success": False,
                "job_id": job_id,
                "reason": "job_not_found",
            }

        # Bagimlilik kontrolu
        for dep_id in job["depends_on"]:
            dep = self._jobs.get(dep_id)
            if dep and dep["status"] != (
                PipelineStatus.COMPLETED.value
            ):
                return {
                    "success": False,
                    "job_id": job_id,
                    "reason": "dependency_pending",
                    "blocked_by": dep_id,
                }

        job["status"] = PipelineStatus.RUNNING.value
        start = time.time()

        # Simule edilmis calistirma
        success = True
        error = ""

        duration = time.time() - start
        job["last_run"] = time.time()

        if success:
            job["status"] = (
                PipelineStatus.COMPLETED.value
            )
            job["retries"] = 0
        else:
            job["status"] = (
                PipelineStatus.FAILED.value
            )

        result = {
            "success": success,
            "job_id": job_id,
            "pipeline_id": job["pipeline_id"],
            "duration": round(duration, 4),
            "error": error,
        }
        self._history.append(result)

        return result

    def retry_job(
        self,
        job_id: str,
    ) -> dict[str, Any]:
        """Is yeniden dener.

        Args:
            job_id: Is ID.

        Returns:
            Yeniden deneme sonucu.
        """
        job = self._jobs.get(job_id)
        if not job:
            return {
                "success": False,
                "reason": "job_not_found",
            }

        if job["retries"] >= self._max_retries:
            return {
                "success": False,
                "job_id": job_id,
                "reason": "max_retries_exceeded",
                "retries": job["retries"],
            }

        job["retries"] += 1
        return self.run_job(job_id)

    def enable_job(self, job_id: str) -> bool:
        """Is aktif eder.

        Args:
            job_id: Is ID.

        Returns:
            Basarili ise True.
        """
        job = self._jobs.get(job_id)
        if job:
            job["enabled"] = True
            return True
        return False

    def disable_job(self, job_id: str) -> bool:
        """Is devre disi birakir.

        Args:
            job_id: Is ID.

        Returns:
            Basarili ise True.
        """
        job = self._jobs.get(job_id)
        if job:
            job["enabled"] = False
            return True
        return False

    def cancel_job(self, job_id: str) -> bool:
        """Is iptal eder.

        Args:
            job_id: Is ID.

        Returns:
            Basarili ise True.
        """
        job = self._jobs.get(job_id)
        if job:
            job["status"] = (
                PipelineStatus.CANCELLED.value
            )
            job["enabled"] = False
            return True
        return False

    def get_job(
        self,
        job_id: str,
    ) -> dict[str, Any] | None:
        """Is getirir.

        Args:
            job_id: Is ID.

        Returns:
            Is veya None.
        """
        return self._jobs.get(job_id)

    def get_pending(self) -> list[dict[str, Any]]:
        """Bekleyen isleri getirir.

        Returns:
            Bekleyen isler.
        """
        return [
            j for j in self._jobs.values()
            if j["status"]
            == PipelineStatus.PENDING.value
            and j["enabled"]
        ]

    def get_running(self) -> list[dict[str, Any]]:
        """Calisan isleri getirir.

        Returns:
            Calisan isler.
        """
        return [
            j for j in self._jobs.values()
            if j["status"]
            == PipelineStatus.RUNNING.value
        ]

    def get_failed(self) -> list[dict[str, Any]]:
        """Basarisiz isleri getirir.

        Returns:
            Basarisiz isler.
        """
        return [
            j for j in self._jobs.values()
            if j["status"]
            == PipelineStatus.FAILED.value
        ]

    def remove_job(self, job_id: str) -> bool:
        """Is kaldirir.

        Args:
            job_id: Is ID.

        Returns:
            Basarili ise True.
        """
        if job_id in self._jobs:
            del self._jobs[job_id]
            return True
        return False

    @property
    def job_count(self) -> int:
        """Is sayisi."""
        return len(self._jobs)

    @property
    def active_count(self) -> int:
        """Aktif is sayisi."""
        return sum(
            1 for j in self._jobs.values()
            if j["enabled"]
            and j["status"]
            in (
                PipelineStatus.PENDING.value,
                PipelineStatus.RUNNING.value,
            )
        )

    @property
    def history_count(self) -> int:
        """Gecmis sayisi."""
        return len(self._history)
