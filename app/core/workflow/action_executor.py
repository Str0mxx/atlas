"""ATLAS Aksiyon Yurutucu modulu.

Dahili aksiyonlar, ozel aksiyonlar,
API cagrilari, script calistirma
ve agent delege etme.
"""

import logging
import time
from typing import Any, Callable

from app.models.workflow_engine import ActionType

logger = logging.getLogger(__name__)


class ActionExecutor:
    """Aksiyon yurutucu.

    Is akisi aksiyonlarini calistirir
    ve yonetir.

    Attributes:
        _actions: Kayitli aksiyonlar.
        _history: Calistirma gecmisi.
    """

    def __init__(self) -> None:
        """Aksiyon yurutucuyu baslatir."""
        self._actions: dict[
            str, dict[str, Any]
        ] = {}
        self._custom_handlers: dict[
            str, Callable[..., Any]
        ] = {}
        self._history: list[dict[str, Any]] = []

        # Dahili aksiyonlari kaydet
        self._register_builtins()

        logger.info("ActionExecutor baslatildi")

    def _register_builtins(self) -> None:
        """Dahili aksiyonlari kaydeder."""
        builtins = [
            "log", "notify", "wait", "set_variable",
            "http_request", "transform_data",
        ]
        for name in builtins:
            self._actions[name] = {
                "name": name,
                "type": ActionType.BUILTIN.value,
                "enabled": True,
            }

    def register_action(
        self,
        name: str,
        action_type: ActionType,
        handler: Callable[..., Any] | None = None,
        config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Aksiyon kaydeder.

        Args:
            name: Aksiyon adi.
            action_type: Aksiyon turu.
            handler: Isleyici fonksiyon.
            config: Yapilandirma.

        Returns:
            Aksiyon bilgisi.
        """
        action = {
            "name": name,
            "type": action_type.value,
            "config": config or {},
            "enabled": True,
        }
        self._actions[name] = action
        if handler:
            self._custom_handlers[name] = handler
        return action

    def execute(
        self,
        action_name: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Aksiyon calistirir.

        Args:
            action_name: Aksiyon adi.
            params: Parametreler.

        Returns:
            Calistirma sonucu.
        """
        action = self._actions.get(action_name)
        if not action or not action["enabled"]:
            return {
                "success": False,
                "action": action_name,
                "reason": "action_not_found",
            }

        start = time.time()
        result_data: Any = None
        error = ""

        try:
            handler = self._custom_handlers.get(
                action_name,
            )
            if handler:
                result_data = handler(
                    **(params or {}),
                )
            else:
                result_data = self._run_builtin(
                    action_name, params or {},
                )
        except Exception as e:
            error = str(e)

        duration = time.time() - start
        success = not error

        result = {
            "success": success,
            "action": action_name,
            "type": action["type"],
            "result": result_data,
            "error": error,
            "duration": round(duration, 4),
        }
        self._history.append(result)

        return result

    def execute_sequence(
        self,
        actions: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Sirayla calistirir.

        Args:
            actions: Aksiyon listesi.

        Returns:
            Sonuc listesi.
        """
        results: list[dict[str, Any]] = []
        for action in actions:
            name = action.get("name", "")
            params = action.get("params")
            result = self.execute(name, params)
            results.append(result)
            if not result["success"]:
                break
        return results

    def _run_builtin(
        self,
        name: str,
        params: dict[str, Any],
    ) -> Any:
        """Dahili aksiyon calistirir.

        Args:
            name: Aksiyon adi.
            params: Parametreler.

        Returns:
            Sonuc.
        """
        if name == "log":
            msg = params.get("message", "")
            logger.info("Workflow log: %s", msg)
            return {"logged": msg}
        if name == "wait":
            return {"waited": True}
        if name == "set_variable":
            return {
                "key": params.get("key"),
                "value": params.get("value"),
            }
        if name == "notify":
            return {
                "notified": params.get(
                    "recipient", "",
                ),
            }
        if name == "http_request":
            return {
                "url": params.get("url"),
                "status": 200,
            }
        if name == "transform_data":
            return {
                "transformed": True,
                "data": params.get("data"),
            }
        return None

    def enable_action(
        self,
        name: str,
    ) -> bool:
        """Aksiyon aktif eder.

        Args:
            name: Aksiyon adi.

        Returns:
            Basarili ise True.
        """
        action = self._actions.get(name)
        if action:
            action["enabled"] = True
            return True
        return False

    def disable_action(
        self,
        name: str,
    ) -> bool:
        """Aksiyon devre disi birakir.

        Args:
            name: Aksiyon adi.

        Returns:
            Basarili ise True.
        """
        action = self._actions.get(name)
        if action:
            action["enabled"] = False
            return True
        return False

    @property
    def action_count(self) -> int:
        """Aksiyon sayisi."""
        return len(self._actions)

    @property
    def history_count(self) -> int:
        """Gecmis sayisi."""
        return len(self._history)

    @property
    def builtin_count(self) -> int:
        """Dahili aksiyon sayisi."""
        return sum(
            1 for a in self._actions.values()
            if a["type"] == ActionType.BUILTIN.value
        )
