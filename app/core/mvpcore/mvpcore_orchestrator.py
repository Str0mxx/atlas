"""
MVP Core orkestrator modulu.

Tam MVP baslatma, docker compose
hazir, FastAPI + WebSocket + Telegram +
LLM, tek komut baslangic.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from .config_loader import (
    CoreConfigLoader,
)
from .core_engine import CoreEngine
from .event_loop import CoreEventLoop
from .graceful_shutdown import (
    GracefulShutdown,
)
from .health_endpoint import (
    HealthEndpoint,
)
from .session_manager import (
    CoreSessionManager,
)
from .task_executor import (
    CoreTaskExecutor,
)
from .websocket_server import (
    CoreWebSocketServer,
)

logger = logging.getLogger(__name__)


class MVPCoreOrchestrator:
    """MVP Core orkestratoru.

    Tum cekirdek bilesenleri birlestirir
    ve tek komutla baslatir.

    Attributes:
        _engine: Cekirdek motor.
        _event_loop: Olay dongusu.
        _session_mgr: Oturum yoneticisi.
        _ws_server: WebSocket sunucu.
        _task_executor: Gorev yurutucusu.
        _config_loader: Yapilandirma.
        _health: Saglik endpoint'i.
        _shutdown: Zarif kapanma.
        _stats: Istatistikler.
    """

    def __init__(
        self,
        app_name: str = "atlas",
        debug: bool = False,
        ws_port: int = 8765,
        max_concurrent_tasks: int = 10,
        health_check_interval: int = 30,
        shutdown_timeout: int = 30,
    ) -> None:
        """Orkestratoru baslatir.

        Args:
            app_name: Uygulama adi.
            debug: Hata ayiklama.
            ws_port: WebSocket portu.
            max_concurrent_tasks: Max gorev.
            health_check_interval: Saglik araligi.
            shutdown_timeout: Kapanma zamani.
        """
        # Bilesenler
        self._engine = CoreEngine(
            app_name=app_name,
            debug=debug,
        )
        self._event_loop = (
            CoreEventLoop()
        )
        self._session_mgr = (
            CoreSessionManager()
        )
        self._ws_server = (
            CoreWebSocketServer(
                port=ws_port,
            )
        )
        self._task_executor = (
            CoreTaskExecutor(
                max_concurrent=(
                    max_concurrent_tasks
                ),
            )
        )
        self._config_loader = (
            CoreConfigLoader()
        )
        self._health = HealthEndpoint(
            check_interval=(
                health_check_interval
            ),
        )
        self._shutdown = (
            GracefulShutdown(
                timeout=(
                    shutdown_timeout
                ),
            )
        )

        self._running = False
        self._started_at: str | None = (
            None
        )
        self._stats: dict[str, int] = {
            "startups": 0,
            "shutdowns": 0,
            "events_processed": 0,
            "tasks_executed": 0,
            "sessions_created": 0,
            "errors": 0,
        }

        logger.info(
            "MVPCoreOrchestrator "
            f"baslatildi: {app_name}"
        )

    @property
    def is_running(self) -> bool:
        """Calisiyor mu."""
        return self._running

    def startup(
        self,
    ) -> dict[str, Any]:
        """Tam MVP baslatma.

        Tum bilesenleri sirayla baslatir:
        1. Config yukle
        2. Engine initialize
        3. Event loop baslat
        4. WebSocket baslat
        5. Health kontrolleri kaydet

        Returns:
            Baslatma bilgisi.
        """
        try:
            steps: list[dict] = []

            # 1. Yapilandirma
            self._config_loader.set_defaults({
                "app_name": "atlas",
                "debug": False,
                "version": "1.0.0",
            })
            steps.append({
                "step": "config",
                "success": True,
            })

            # 2. Bilesenleri kaydet
            components = {
                "event_loop": (
                    self._event_loop
                ),
                "session_mgr": (
                    self._session_mgr
                ),
                "ws_server": (
                    self._ws_server
                ),
                "task_executor": (
                    self._task_executor
                ),
                "config_loader": (
                    self._config_loader
                ),
                "health": self._health,
                "shutdown": (
                    self._shutdown
                ),
            }

            for name, comp in (
                components.items()
            ):
                self._engine.register_component(
                    name=name,
                    component=comp,
                )

            steps.append({
                "step": "components",
                "count": len(components),
                "success": True,
            })

            # 3. Engine baslat
            init_result = (
                self._engine.initialize()
            )
            steps.append({
                "step": "engine",
                "success": init_result.get(
                    "started", False
                ),
            })

            # 4. Event loop baslat
            self._event_loop.start()
            steps.append({
                "step": "event_loop",
                "success": True,
            })

            # 5. WebSocket baslat
            ws_result = (
                self._ws_server.start()
            )
            steps.append({
                "step": "websocket",
                "success": ws_result.get(
                    "started", False
                ),
            })

            # 6. Saglik kontrolleri
            self._health.register_check(
                name="engine",
                check_func=(
                    lambda: (
                        self._engine.state
                        == "running"
                    )
                ),
                check_type="liveness",
                critical=True,
            )
            self._health.register_check(
                name="event_loop",
                check_func=(
                    lambda: (
                        self._event_loop
                        .is_running
                    )
                ),
                check_type="readiness",
            )
            steps.append({
                "step": "health",
                "success": True,
            })

            # 7. Kapanma handler'lari
            self._shutdown.register_handler(
                name="ws_stop",
                handler=(
                    self._ws_server.stop
                ),
                priority=10,
            )
            self._shutdown.register_handler(
                name="event_drain",
                handler=(
                    self._event_loop.drain
                ),
                priority=20,
            )
            self._shutdown.register_handler(
                name="engine_shutdown",
                handler=(
                    self._engine.shutdown
                ),
                priority=100,
            )
            steps.append({
                "step": "shutdown_handlers",
                "success": True,
            })

            self._running = True
            self._started_at = (
                datetime.now(
                    timezone.utc
                ).isoformat()
            )
            self._stats["startups"] += 1

            all_ok = all(
                s.get("success")
                for s in steps
            )

            return {
                "steps": steps,
                "all_success": all_ok,
                "started_at": (
                    self._started_at
                ),
                "startup": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            self._stats["errors"] += 1
            return {
                "startup": False,
                "error": str(e),
            }

    def shutdown(
        self,
    ) -> dict[str, Any]:
        """Tam MVP kapatma.

        Returns:
            Kapatma bilgisi.
        """
        try:
            result = (
                self._shutdown
                .initiate_shutdown()
            )
            self._running = False
            self._stats["shutdowns"] += 1

            return {
                "shutdown_result": result,
                "shutdown": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            self._running = False
            return {
                "shutdown": False,
                "error": str(e),
            }

    def dispatch_event(
        self,
        event_type: str = "",
        data: Any = None,
        priority: str = "normal",
    ) -> dict[str, Any]:
        """Olay dagitir.

        Args:
            event_type: Olay tipi.
            data: Olay verisi.
            priority: Oncelik.

        Returns:
            Dagitim bilgisi.
        """
        try:
            result = (
                self._event_loop.dispatch(
                    event_type=event_type,
                    data=data,
                    priority=priority,
                )
            )
            if result.get("dispatched"):
                self._stats[
                    "events_processed"
                ] += 1
            return result

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "dispatched": False,
                "error": str(e),
            }

    def submit_task(
        self,
        func: Any = None,
        args: tuple | None = None,
        kwargs: dict | None = None,
        priority: str = "normal",
    ) -> dict[str, Any]:
        """Gorev gonderir.

        Args:
            func: Fonksiyon.
            args: Argumanlar.
            kwargs: Isimli argumanlar.
            priority: Oncelik.

        Returns:
            Gonderim bilgisi.
        """
        try:
            result = (
                self._task_executor
                .submit(
                    func=func,
                    args=args,
                    kwargs=kwargs,
                    priority=priority,
                )
            )
            if result.get("submitted"):
                self._stats[
                    "tasks_executed"
                ] += 1
            return result

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "submitted": False,
                "error": str(e),
            }

    def create_session(
        self,
        user_id: str = "",
        metadata: dict | None = None,
    ) -> dict[str, Any]:
        """Oturum olusturur.

        Args:
            user_id: Kullanici ID.
            metadata: Ek veri.

        Returns:
            Oturum bilgisi.
        """
        try:
            result = (
                self._session_mgr
                .create_session(
                    user_id=user_id,
                    metadata=metadata,
                )
            )
            if result.get("created"):
                self._stats[
                    "sessions_created"
                ] += 1
            return result

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "created": False,
                "error": str(e),
            }

    def health_check(
        self,
    ) -> dict[str, Any]:
        """Saglik kontrolu.

        Returns:
            Saglik bilgisi.
        """
        try:
            return self._health.run_all()
        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "checked": False,
                "error": str(e),
            }

    def get_config(
        self,
        key: str = "",
        default: Any = None,
    ) -> Any:
        """Yapilandirma degeri getirir.

        Args:
            key: Anahtar.
            default: Varsayilan.

        Returns:
            Deger.
        """
        return self._config_loader.get(
            key, default
        )

    def get_analytics(
        self,
    ) -> dict[str, Any]:
        """Analitik verileri getirir.

        Returns:
            Analitik bilgisi.
        """
        try:
            return {
                "engine": (
                    self._engine
                    .get_summary()
                ),
                "event_loop": (
                    self._event_loop
                    .get_summary()
                ),
                "sessions": (
                    self._session_mgr
                    .get_summary()
                ),
                "websocket": (
                    self._ws_server
                    .get_summary()
                ),
                "tasks": (
                    self._task_executor
                    .get_summary()
                ),
                "health": (
                    self._health
                    .get_summary()
                ),
                "shutdown": (
                    self._shutdown
                    .get_summary()
                ),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }

    def get_summary(
        self,
    ) -> dict[str, Any]:
        """Ozet getirir."""
        try:
            return {
                "running": self._running,
                "started_at": (
                    self._started_at
                ),
                "engine_state": (
                    self._engine.state
                ),
                "event_loop_running": (
                    self._event_loop
                    .is_running
                ),
                "ws_connections": (
                    self._ws_server
                    .connection_count
                ),
                "active_sessions": (
                    self._session_mgr
                    .active_count
                ),
                "task_queue": (
                    self._task_executor
                    .queue_size
                ),
                "health_status": (
                    self._health.status
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
