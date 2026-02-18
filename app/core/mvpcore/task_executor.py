"""
Gorev yurutme modulu.

Gorev yurutme, kuyruk yonetimi,
esZamanlilik, sonuc isleme, hata yonetimi.
"""

import logging
import time
from datetime import datetime, timezone
from typing import Any, Callable
from uuid import uuid4

logger = logging.getLogger(__name__)


class CoreTaskExecutor:
    """Cekirdek gorev yurutucusu.

    Attributes:
        _tasks: Gorevler.
        _queue: Gorev kuyrugu.
        _results: Sonuclar.
        _stats: Istatistikler.
    """

    TASK_STATES: list[str] = [
        "pending",
        "queued",
        "running",
        "completed",
        "failed",
        "cancelled",
        "timeout",
    ]

    PRIORITY_LEVELS: dict[str, int] = {
        "critical": 0,
        "high": 1,
        "normal": 2,
        "low": 3,
    }

    def __init__(
        self,
        max_concurrent: int = 10,
        max_queue_size: int = 1000,
        default_timeout: int = 300,
    ) -> None:
        """Yurutucu baslatir.

        Args:
            max_concurrent: Max esZamanli.
            max_queue_size: Max kuyruk.
            default_timeout: Varsayilan timeout.
        """
        self._max_concurrent = (
            max_concurrent
        )
        self._max_queue_size = (
            max_queue_size
        )
        self._default_timeout = (
            default_timeout
        )
        self._tasks: dict[
            str, dict
        ] = {}
        self._queue: list[dict] = []
        self._running_tasks: dict[
            str, dict
        ] = {}
        self._results: dict[
            str, dict
        ] = {}
        self._stats: dict[str, int] = {
            "tasks_submitted": 0,
            "tasks_completed": 0,
            "tasks_failed": 0,
            "tasks_cancelled": 0,
            "tasks_timeout": 0,
            "total_execution_time": 0,
        }
        logger.info(
            "CoreTaskExecutor baslatildi"
        )

    @property
    def queue_size(self) -> int:
        """Kuyruk boyutu."""
        return len(self._queue)

    @property
    def running_count(self) -> int:
        """Calisan gorev sayisi."""
        return len(self._running_tasks)

    def submit(
        self,
        func: Callable | None = None,
        args: tuple | None = None,
        kwargs: dict | None = None,
        priority: str = "normal",
        timeout: int | None = None,
        metadata: dict | None = None,
    ) -> dict[str, Any]:
        """Gorev gonderir.

        Args:
            func: Calistirilacak fonksiyon.
            args: Pozisyonel argumanlar.
            kwargs: Isimli argumanlar.
            priority: Oncelik.
            timeout: Zaman asimi.
            metadata: Ek veri.

        Returns:
            Gonderim bilgisi.
        """
        try:
            if (
                len(self._queue)
                >= self._max_queue_size
            ):
                return {
                    "submitted": False,
                    "error": (
                        "Kuyruk dolu"
                    ),
                }

            tid = (
                f"task_{uuid4()!s:.8}"
            )
            pri = (
                self.PRIORITY_LEVELS.get(
                    priority, 2
                )
            )

            task = {
                "task_id": tid,
                "func": func,
                "args": args or (),
                "kwargs": kwargs or {},
                "priority": priority,
                "priority_val": pri,
                "timeout": (
                    timeout
                    or self._default_timeout
                ),
                "metadata": (
                    metadata or {}
                ),
                "state": "queued",
                "submitted_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
                "started_at": None,
                "completed_at": None,
            }

            self._tasks[tid] = task
            self._queue.append(task)
            self._queue.sort(
                key=lambda x: x.get(
                    "priority_val", 2
                )
            )
            self._stats[
                "tasks_submitted"
            ] += 1

            return {
                "task_id": tid,
                "queue_position": (
                    self._queue.index(task)
                ),
                "submitted": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "submitted": False,
                "error": str(e),
            }

    def execute_next(
        self,
    ) -> dict[str, Any]:
        """Siradaki gorevi yurutur.

        Returns:
            Yurutme bilgisi.
        """
        try:
            if not self._queue:
                return {
                    "executed": False,
                    "error": (
                        "Kuyruk bos"
                    ),
                }

            if (
                len(self._running_tasks)
                >= self._max_concurrent
            ):
                return {
                    "executed": False,
                    "error": (
                        "Max esZamanli sinir"
                    ),
                }

            task = self._queue.pop(0)
            tid = task["task_id"]
            task["state"] = "running"
            task["started_at"] = (
                datetime.now(
                    timezone.utc
                ).isoformat()
            )
            self._running_tasks[tid] = (
                task
            )

            start_time = time.time()

            try:
                func = task["func"]
                if callable(func):
                    result = func(
                        *task["args"],
                        **task["kwargs"],
                    )
                else:
                    result = None

                elapsed = (
                    time.time() - start_time
                )
                task["state"] = "completed"
                task["completed_at"] = (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                )

                self._results[tid] = {
                    "task_id": tid,
                    "result": result,
                    "elapsed": elapsed,
                    "state": "completed",
                }

                self._stats[
                    "tasks_completed"
                ] += 1
                self._stats[
                    "total_execution_time"
                ] += int(elapsed)

                return {
                    "task_id": tid,
                    "result": result,
                    "elapsed": elapsed,
                    "executed": True,
                }

            except Exception as te:
                elapsed = (
                    time.time() - start_time
                )
                task["state"] = "failed"
                task["error"] = str(te)

                self._results[tid] = {
                    "task_id": tid,
                    "error": str(te),
                    "elapsed": elapsed,
                    "state": "failed",
                }

                self._stats[
                    "tasks_failed"
                ] += 1

                return {
                    "task_id": tid,
                    "error": str(te),
                    "executed": False,
                }

            finally:
                self._running_tasks.pop(
                    tid, None
                )

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "executed": False,
                "error": str(e),
            }

    def execute_all(
        self,
    ) -> dict[str, Any]:
        """Tum gorevleri yurutur.

        Returns:
            Yurutme bilgisi.
        """
        try:
            completed = 0
            failed = 0
            while self._queue:
                r = self.execute_next()
                if r.get("executed"):
                    completed += 1
                else:
                    if r.get(
                        "error"
                    ) == "Max esZamanli sinir":
                        break
                    failed += 1

            return {
                "completed": completed,
                "failed": failed,
                "remaining": len(
                    self._queue
                ),
                "executed": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "executed": False,
                "error": str(e),
            }

    def cancel(
        self, task_id: str = ""
    ) -> dict[str, Any]:
        """Gorevi iptal eder.

        Args:
            task_id: Gorev ID.

        Returns:
            Iptal bilgisi.
        """
        try:
            task = self._tasks.get(
                task_id
            )
            if not task:
                return {
                    "cancelled": False,
                    "error": (
                        "Gorev bulunamadi"
                    ),
                }

            if task["state"] in (
                "completed",
                "failed",
                "cancelled",
            ):
                return {
                    "cancelled": False,
                    "error": (
                        "Gorev zaten bitmis"
                    ),
                }

            task["state"] = "cancelled"
            # Kuyruktan cikar
            self._queue = [
                t
                for t in self._queue
                if t["task_id"]
                != task_id
            ]
            self._running_tasks.pop(
                task_id, None
            )
            self._stats[
                "tasks_cancelled"
            ] += 1

            return {
                "task_id": task_id,
                "cancelled": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "cancelled": False,
                "error": str(e),
            }

    def get_result(
        self, task_id: str = ""
    ) -> dict[str, Any]:
        """Gorev sonucunu getirir.

        Args:
            task_id: Gorev ID.

        Returns:
            Sonuc bilgisi.
        """
        try:
            result = self._results.get(
                task_id
            )
            if not result:
                return {
                    "found": False,
                    "error": (
                        "Sonuc bulunamadi"
                    ),
                }

            return {
                **result,
                "found": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "found": False,
                "error": str(e),
            }

    def get_task_status(
        self, task_id: str = ""
    ) -> dict[str, Any]:
        """Gorev durumunu getirir.

        Args:
            task_id: Gorev ID.

        Returns:
            Durum bilgisi.
        """
        try:
            task = self._tasks.get(
                task_id
            )
            if not task:
                return {
                    "found": False,
                    "error": (
                        "Gorev bulunamadi"
                    ),
                }

            return {
                "task_id": task_id,
                "state": task["state"],
                "priority": task[
                    "priority"
                ],
                "submitted_at": task[
                    "submitted_at"
                ],
                "started_at": task[
                    "started_at"
                ],
                "completed_at": task[
                    "completed_at"
                ],
                "found": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "found": False,
                "error": str(e),
            }

    def retry(
        self, task_id: str = ""
    ) -> dict[str, Any]:
        """Basarisiz gorevi tekrar dener.

        Args:
            task_id: Gorev ID.

        Returns:
            Tekrar deneme bilgisi.
        """
        try:
            task = self._tasks.get(
                task_id
            )
            if not task:
                return {
                    "retried": False,
                    "error": (
                        "Gorev bulunamadi"
                    ),
                }

            if task["state"] != "failed":
                return {
                    "retried": False,
                    "error": (
                        "Sadece basarisiz "
                        "gorevler tekrar "
                        "denenebilir"
                    ),
                }

            task["state"] = "queued"
            task["started_at"] = None
            task["completed_at"] = None
            self._queue.append(task)
            self._queue.sort(
                key=lambda x: x.get(
                    "priority_val", 2
                )
            )

            return {
                "task_id": task_id,
                "retried": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retried": False,
                "error": str(e),
            }

    def get_summary(
        self,
    ) -> dict[str, Any]:
        """Ozet getirir."""
        try:
            return {
                "total_tasks": len(
                    self._tasks
                ),
                "queue_size": len(
                    self._queue
                ),
                "running": len(
                    self._running_tasks
                ),
                "results": len(
                    self._results
                ),
                "stats": dict(
                    self._stats
                ),
                "retrieved": True,
            }
        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }
