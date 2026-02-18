"""
Zarif kapanma modulu.

Kapanma sinyalleri, baglanti bosaltma,
gorev tamamlama, kaynak temizleme,
durum kaliciligi.
"""

import logging
import time
from datetime import datetime, timezone
from typing import Any, Callable
from uuid import uuid4

logger = logging.getLogger(__name__)


class GracefulShutdown:
    """Zarif kapanma yoneticisi.

    Attributes:
        _handlers: Kapanma isleyicileri.
        _resources: Kaynaklar.
        _state: Kapanma durumu.
        _stats: Istatistikler.
    """

    SHUTDOWN_PHASES: list[str] = [
        "running",
        "draining",
        "completing",
        "cleaning",
        "persisting",
        "stopped",
    ]

    def __init__(
        self,
        timeout: int = 30,
        drain_timeout: int = 10,
        force_after: int = 60,
    ) -> None:
        """Yoneticiyi baslatir.

        Args:
            timeout: Kapanma zaman asimi.
            drain_timeout: Bosaltma zamani.
            force_after: Zorla durdurma (sn).
        """
        self._timeout = timeout
        self._drain_timeout = (
            drain_timeout
        )
        self._force_after = force_after
        self._state = "running"
        self._handlers: list[dict] = []
        self._resources: dict[
            str, dict
        ] = {}
        self._pending_tasks: list[
            dict
        ] = []
        self._persisted_state: dict[
            str, Any
        ] = {}
        self._shutdown_log: list[
            dict
        ] = []
        self._stats: dict[str, int] = {
            "handlers_registered": 0,
            "handlers_executed": 0,
            "resources_cleaned": 0,
            "tasks_completed": 0,
            "tasks_aborted": 0,
            "states_persisted": 0,
        }
        logger.info(
            "GracefulShutdown baslatildi"
        )

    @property
    def phase(self) -> str:
        """Kapanma fazı."""
        return self._state

    @property
    def is_shutting_down(self) -> bool:
        """Kapaniyor mu."""
        return self._state != "running"

    def register_handler(
        self,
        name: str = "",
        handler: Callable | None = None,
        priority: int = 100,
        timeout: int | None = None,
    ) -> dict[str, Any]:
        """Kapanma isleyici kaydeder.

        Args:
            name: Isleyici adi.
            handler: Isleyici fonksiyonu.
            priority: Oncelik (dusuk = once).
            timeout: Isleyici zamani.

        Returns:
            Kayit bilgisi.
        """
        try:
            hid = (
                f"sh_{uuid4()!s:.8}"
            )
            entry = {
                "handler_id": hid,
                "name": name,
                "handler": handler,
                "priority": priority,
                "timeout": (
                    timeout
                    or self._timeout
                ),
                "executed": False,
            }

            self._handlers.append(entry)
            self._handlers.sort(
                key=lambda x: x[
                    "priority"
                ]
            )
            self._stats[
                "handlers_registered"
            ] += 1

            return {
                "handler_id": hid,
                "name": name,
                "registered": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "registered": False,
                "error": str(e),
            }

    def register_resource(
        self,
        name: str = "",
        cleanup_func: (
            Callable | None
        ) = None,
        metadata: dict | None = None,
    ) -> dict[str, Any]:
        """Temizlenecek kaynak kaydeder.

        Args:
            name: Kaynak adi.
            cleanup_func: Temizleme fonksiyonu.
            metadata: Ek veri.

        Returns:
            Kayit bilgisi.
        """
        try:
            rid = (
                f"res_{uuid4()!s:.8}"
            )
            self._resources[name] = {
                "resource_id": rid,
                "name": name,
                "cleanup_func": (
                    cleanup_func
                ),
                "metadata": (
                    metadata or {}
                ),
                "cleaned": False,
            }

            return {
                "resource_id": rid,
                "name": name,
                "registered": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "registered": False,
                "error": str(e),
            }

    def add_pending_task(
        self,
        task_id: str = "",
        description: str = "",
    ) -> dict[str, Any]:
        """Bekleyen gorev ekler.

        Args:
            task_id: Gorev ID.
            description: Aciklama.

        Returns:
            Ekleme bilgisi.
        """
        try:
            self._pending_tasks.append({
                "task_id": task_id,
                "description": description,
                "added_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
                "completed": False,
            })

            return {
                "task_id": task_id,
                "added": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "added": False,
                "error": str(e),
            }

    def complete_task(
        self, task_id: str = ""
    ) -> dict[str, Any]:
        """Bekleyen gorevi tamamlar.

        Args:
            task_id: Gorev ID.

        Returns:
            Tamamlama bilgisi.
        """
        try:
            for task in (
                self._pending_tasks
            ):
                if (
                    task["task_id"]
                    == task_id
                ):
                    task[
                        "completed"
                    ] = True
                    self._stats[
                        "tasks_completed"
                    ] += 1
                    return {
                        "task_id": task_id,
                        "completed": True,
                    }

            return {
                "completed": False,
                "error": (
                    "Gorev bulunamadi"
                ),
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "completed": False,
                "error": str(e),
            }

    def persist_state(
        self,
        key: str = "",
        value: Any = None,
    ) -> dict[str, Any]:
        """Durumu kalici depoya yazar.

        Args:
            key: Anahtar.
            value: Deger.

        Returns:
            Kalicilik bilgisi.
        """
        try:
            self._persisted_state[
                key
            ] = value
            self._stats[
                "states_persisted"
            ] += 1

            return {
                "key": key,
                "persisted": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "persisted": False,
                "error": str(e),
            }

    def initiate_shutdown(
        self,
    ) -> dict[str, Any]:
        """Zarif kapanmayi baslatir.

        Returns:
            Kapanma bilgisi.
        """
        try:
            start_time = time.time()
            results: list[dict] = []

            # Faz 1: Bosaltma
            self._state = "draining"
            self._log_phase("draining")

            # Faz 2: Gorevleri tamamla
            self._state = "completing"
            self._log_phase("completing")

            pending = [
                t
                for t in
                self._pending_tasks
                if not t["completed"]
            ]
            for task in pending:
                task["completed"] = True
                self._stats[
                    "tasks_completed"
                ] += 1

            aborted = 0
            # Faz 3: Handler'lari calistir
            for h in self._handlers:
                try:
                    func = h["handler"]
                    if callable(func):
                        func()
                    h["executed"] = True
                    self._stats[
                        "handlers_executed"
                    ] += 1
                    results.append({
                        "name": h["name"],
                        "success": True,
                    })
                except Exception as he:
                    results.append({
                        "name": h["name"],
                        "success": False,
                        "error": str(he),
                    })
                    aborted += 1

            # Faz 4: Kaynak temizligi
            self._state = "cleaning"
            self._log_phase("cleaning")

            for name, res in (
                self._resources.items()
            ):
                try:
                    func = res[
                        "cleanup_func"
                    ]
                    if callable(func):
                        func()
                    res["cleaned"] = True
                    self._stats[
                        "resources_cleaned"
                    ] += 1
                except Exception as ce:
                    logger.error(
                        f"Temizlik hatasi: "
                        f"{ce}"
                    )

            # Faz 5: Durum kaliciligi
            self._state = "persisting"
            self._log_phase("persisting")

            # Faz 6: Durduruldu
            self._state = "stopped"
            self._log_phase("stopped")

            elapsed = (
                time.time() - start_time
            )
            self._stats[
                "tasks_aborted"
            ] += aborted

            return {
                "phase": self._state,
                "handlers_run": len(
                    results
                ),
                "resources_cleaned": (
                    self._stats[
                        "resources_cleaned"
                    ]
                ),
                "tasks_completed": (
                    self._stats[
                        "tasks_completed"
                    ]
                ),
                "elapsed": elapsed,
                "shutdown": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            self._state = "stopped"
            return {
                "shutdown": False,
                "error": str(e),
            }

    def _log_phase(
        self, phase: str
    ) -> None:
        """Faz kaydeder."""
        self._shutdown_log.append({
            "phase": phase,
            "timestamp": (
                datetime.now(
                    timezone.utc
                ).isoformat()
            ),
        })

    def get_shutdown_log(
        self,
    ) -> list[dict]:
        """Kapanma gunlugunu getirir."""
        return list(self._shutdown_log)

    def get_persisted_state(
        self,
    ) -> dict[str, Any]:
        """Kalici durumu getirir."""
        return dict(
            self._persisted_state
        )

    def get_summary(
        self,
    ) -> dict[str, Any]:
        """Ozet getirir."""
        try:
            return {
                "phase": self._state,
                "handlers": len(
                    self._handlers
                ),
                "resources": len(
                    self._resources
                ),
                "pending_tasks": len([
                    t
                    for t in
                    self._pending_tasks
                    if not t["completed"]
                ]),
                "persisted_keys": len(
                    self._persisted_state
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
