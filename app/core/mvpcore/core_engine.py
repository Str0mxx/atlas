"""
Cekirdek motor modulu.

Uygulama baslatma, bilesen
baslangici, bagimlili enjeksiyonu,
yasam dongusu yonetimi, sinyal isleme.
"""

import logging
import signal
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class CoreEngine:
    """Cekirdek motor.

    Attributes:
        _components: Bilesenler.
        _dependencies: Bagimliliklar.
        _hooks: Yasam dongusu hook'lari.
        _state: Motor durumu.
        _stats: Istatistikler.
    """

    STATES: list[str] = [
        "created",
        "initializing",
        "running",
        "stopping",
        "stopped",
        "error",
    ]

    LIFECYCLE_EVENTS: list[str] = [
        "pre_init",
        "post_init",
        "pre_start",
        "post_start",
        "pre_stop",
        "post_stop",
    ]

    def __init__(
        self,
        app_name: str = "atlas",
        debug: bool = False,
    ) -> None:
        """Motoru baslatir.

        Args:
            app_name: Uygulama adi.
            debug: Hata ayiklama.
        """
        self._app_name = app_name
        self._debug = debug
        self._state = "created"
        self._components: dict[
            str, dict
        ] = {}
        self._dependencies: dict[
            str, list[str]
        ] = {}
        self._hooks: dict[
            str, list
        ] = {
            e: [] for e in
            self.LIFECYCLE_EVENTS
        }
        self._signals: dict[
            str, list
        ] = {}
        self._stats: dict[str, int] = {
            "components_registered": 0,
            "components_initialized": 0,
            "signals_handled": 0,
            "lifecycle_events": 0,
            "errors": 0,
        }
        self._started_at: str | None = (
            None
        )
        logger.info(
            "CoreEngine baslatildi: "
            f"{app_name}"
        )

    @property
    def state(self) -> str:
        """Motor durumu."""
        return self._state

    @property
    def component_count(self) -> int:
        """Bilesen sayisi."""
        return len(self._components)

    def register_component(
        self,
        name: str = "",
        component: Any = None,
        depends_on: (
            list[str] | None
        ) = None,
        metadata: dict | None = None,
    ) -> dict[str, Any]:
        """Bilesen kaydeder.

        Args:
            name: Bilesen adi.
            component: Bilesen nesnesi.
            depends_on: Bagimliliklar.
            metadata: Ek veri.

        Returns:
            Kayit bilgisi.
        """
        try:
            cid = (
                f"comp_{uuid4()!s:.8}"
            )
            self._components[name] = {
                "component_id": cid,
                "name": name,
                "instance": component,
                "depends_on": (
                    depends_on or []
                ),
                "metadata": (
                    metadata or {}
                ),
                "status": "registered",
                "registered_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
            }
            self._dependencies[name] = (
                depends_on or []
            )
            self._stats[
                "components_registered"
            ] += 1
            return {
                "component_id": cid,
                "name": name,
                "registered": True,
            }
        except Exception as e:
            logger.error(f"Hata: {e}")
            self._stats["errors"] += 1
            return {
                "registered": False,
                "error": str(e),
            }

    def get_component(
        self, name: str = ""
    ) -> Any:
        """Bilesen getirir.

        Args:
            name: Bilesen adi.

        Returns:
            Bilesen nesnesi veya None.
        """
        comp = self._components.get(
            name
        )
        if comp:
            return comp["instance"]
        return None

    def resolve_dependencies(
        self,
    ) -> dict[str, Any]:
        """Bagimliliklari cozer.

        Returns:
            Cozum bilgisi.
        """
        try:
            order: list[str] = []
            visited: set[str] = set()
            temp: set[str] = set()

            def visit(name: str) -> bool:
                if name in temp:
                    return False
                if name in visited:
                    return True
                temp.add(name)
                for dep in (
                    self._dependencies
                    .get(name, [])
                ):
                    if dep in (
                        self._components
                    ):
                        if not visit(dep):
                            return False
                temp.discard(name)
                visited.add(name)
                order.append(name)
                return True

            for name in self._components:
                if name not in visited:
                    if not visit(name):
                        return {
                            "resolved": False,
                            "error": (
                                "Dongusel "
                                "bagimlilik"
                            ),
                        }

            return {
                "order": order,
                "count": len(order),
                "resolved": True,
            }
        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "resolved": False,
                "error": str(e),
            }

    def initialize(
        self,
    ) -> dict[str, Any]:
        """Motoru baslatir.

        Returns:
            Baslatma bilgisi.
        """
        try:
            self._state = "initializing"
            self._fire_hooks("pre_init")

            # Bagimliliklari coz
            dep_result = (
                self.resolve_dependencies()
            )
            if not dep_result.get(
                "resolved"
            ):
                self._state = "error"
                return {
                    "initialized": False,
                    "error": dep_result.get(
                        "error"
                    ),
                }

            order = dep_result.get(
                "order", []
            )
            initialized: list[str] = []

            for name in order:
                comp = (
                    self._components[name]
                )
                instance = comp[
                    "instance"
                ]

                # initialize metodu varsa cagir
                if hasattr(
                    instance, "initialize"
                ) and callable(
                    getattr(
                        instance,
                        "initialize",
                    )
                ):
                    instance.initialize()

                comp["status"] = (
                    "initialized"
                )
                initialized.append(name)
                self._stats[
                    "components_"
                    "initialized"
                ] += 1

            self._fire_hooks("post_init")
            self._state = "running"
            self._started_at = (
                datetime.now(
                    timezone.utc
                ).isoformat()
            )

            return {
                "initialized": (
                    initialized
                ),
                "count": len(
                    initialized
                ),
                "state": self._state,
                "started": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            self._state = "error"
            self._stats["errors"] += 1
            return {
                "started": False,
                "error": str(e),
            }

    def shutdown(
        self,
    ) -> dict[str, Any]:
        """Motoru durdurur.

        Returns:
            Durdurma bilgisi.
        """
        try:
            self._state = "stopping"
            self._fire_hooks("pre_stop")

            stopped: list[str] = []
            # Ters sirada durdur
            names = list(
                self._components.keys()
            )
            for name in reversed(names):
                comp = (
                    self._components[name]
                )
                instance = comp[
                    "instance"
                ]
                if hasattr(
                    instance, "shutdown"
                ) and callable(
                    getattr(
                        instance,
                        "shutdown",
                    )
                ):
                    instance.shutdown()
                comp["status"] = "stopped"
                stopped.append(name)

            self._fire_hooks("post_stop")
            self._state = "stopped"

            return {
                "stopped": stopped,
                "count": len(stopped),
                "state": self._state,
                "shutdown": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            self._state = "error"
            return {
                "shutdown": False,
                "error": str(e),
            }

    def add_hook(
        self,
        event: str = "",
        callback: Any = None,
    ) -> dict[str, Any]:
        """Yasam dongusu hook'u ekler.

        Args:
            event: Olay adi.
            callback: Geri cagirim.

        Returns:
            Ekleme bilgisi.
        """
        try:
            if (
                event
                not in self._hooks
            ):
                return {
                    "added": False,
                    "error": (
                        "Gecersiz olay"
                    ),
                }
            self._hooks[event].append(
                callback
            )
            return {
                "event": event,
                "added": True,
            }
        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "added": False,
                "error": str(e),
            }

    def _fire_hooks(
        self, event: str
    ) -> None:
        """Hook'lari atesler."""
        for cb in self._hooks.get(
            event, []
        ):
            try:
                if callable(cb):
                    cb()
                self._stats[
                    "lifecycle_events"
                ] += 1
            except Exception as e:
                logger.error(
                    f"Hook hatasi: {e}"
                )

    def register_signal(
        self,
        sig_name: str = "",
        handler: Any = None,
    ) -> dict[str, Any]:
        """Sinyal isleyici kaydeder.

        Args:
            sig_name: Sinyal adi.
            handler: Isleyici.

        Returns:
            Kayit bilgisi.
        """
        try:
            self._signals.setdefault(
                sig_name, []
            )
            self._signals[
                sig_name
            ].append(handler)
            return {
                "signal": sig_name,
                "registered": True,
            }
        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "registered": False,
                "error": str(e),
            }

    def emit_signal(
        self,
        sig_name: str = "",
        data: Any = None,
    ) -> dict[str, Any]:
        """Sinyal yayar.

        Args:
            sig_name: Sinyal adi.
            data: Veri.

        Returns:
            Yayin bilgisi.
        """
        try:
            handlers = (
                self._signals.get(
                    sig_name, []
                )
            )
            results: list[Any] = []
            for h in handlers:
                if callable(h):
                    r = h(data)
                    results.append(r)
            self._stats[
                "signals_handled"
            ] += len(handlers)
            return {
                "signal": sig_name,
                "handlers_called": len(
                    handlers
                ),
                "emitted": True,
            }
        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "emitted": False,
                "error": str(e),
            }

    def get_summary(
        self,
    ) -> dict[str, Any]:
        """Ozet getirir."""
        try:
            return {
                "app_name": self._app_name,
                "state": self._state,
                "components": len(
                    self._components
                ),
                "started_at": (
                    self._started_at
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
