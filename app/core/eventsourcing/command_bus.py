"""ATLAS Komut Yolu modulu.

Komut dagitimi, isleyici esleme,
dogrulama, yetkilendirme ve loglama.
"""

import logging
import time
from typing import Any, Callable

logger = logging.getLogger(__name__)


class CommandBus:
    """Komut yolu.

    Komutlari isleyicilere yonlendirir.

    Attributes:
        _handlers: Komut isleyicileri.
        _validators: Dogrulayicilar.
    """

    def __init__(self) -> None:
        """Komut yolunu baslatir."""
        self._handlers: dict[
            str, dict[str, Any]
        ] = {}
        self._validators: dict[
            str, Callable[..., bool]
        ] = {}
        self._authorizers: dict[
            str, Callable[..., bool]
        ] = {}
        self._history: list[
            dict[str, Any]
        ] = []
        self._middleware: list[
            Callable[..., Any]
        ] = []

        logger.info("CommandBus baslatildi")

    def register_handler(
        self,
        command_type: str,
        handler: Callable[..., Any],
        handler_id: str = "",
    ) -> dict[str, Any]:
        """Komut isleyici kaydeder.

        Args:
            command_type: Komut tipi.
            handler: Isleyici fonksiyon.
            handler_id: Isleyici ID.

        Returns:
            Kayit bilgisi.
        """
        h_id = handler_id or (
            f"cmd_{command_type}"
        )
        self._handlers[command_type] = {
            "handler_id": h_id,
            "command_type": command_type,
            "handler": handler,
            "call_count": 0,
        }
        return {
            "handler_id": h_id,
            "command_type": command_type,
        }

    def register_validator(
        self,
        command_type: str,
        validator: Callable[..., bool],
    ) -> None:
        """Dogrulayici kaydeder.

        Args:
            command_type: Komut tipi.
            validator: Dogrulayici fonksiyon.
        """
        self._validators[
            command_type
        ] = validator

    def register_authorizer(
        self,
        command_type: str,
        authorizer: Callable[..., bool],
    ) -> None:
        """Yetkilendirici kaydeder.

        Args:
            command_type: Komut tipi.
            authorizer: Yetkilendirici.
        """
        self._authorizers[
            command_type
        ] = authorizer

    def add_middleware(
        self,
        middleware: Callable[..., Any],
    ) -> None:
        """Ara katman ekler.

        Args:
            middleware: Ara katman fonksiyonu.
        """
        self._middleware.append(middleware)

    def dispatch(
        self,
        command_type: str,
        payload: dict[str, Any] | None = None,
        actor: str = "",
    ) -> dict[str, Any]:
        """Komutu dagitir.

        Args:
            command_type: Komut tipi.
            payload: Komut verisi.
            actor: Komutu veren.

        Returns:
            Dagitim sonucu.
        """
        payload = payload or {}

        # Isleyici kontrol
        entry = self._handlers.get(command_type)
        if not entry:
            result = {
                "command_type": command_type,
                "status": "rejected",
                "reason": "no_handler",
                "timestamp": time.time(),
            }
            self._history.append(result)
            return result

        # Yetkilendirme
        authorizer = self._authorizers.get(
            command_type,
        )
        if authorizer:
            if not authorizer(actor, payload):
                result = {
                    "command_type": command_type,
                    "status": "rejected",
                    "reason": "unauthorized",
                    "actor": actor,
                    "timestamp": time.time(),
                }
                self._history.append(result)
                return result

        # Dogrulama
        validator = self._validators.get(
            command_type,
        )
        if validator:
            if not validator(payload):
                result = {
                    "command_type": command_type,
                    "status": "rejected",
                    "reason": "validation_failed",
                    "timestamp": time.time(),
                }
                self._history.append(result)
                return result

        # Middleware
        for mw in self._middleware:
            try:
                mw(command_type, payload)
            except Exception as e:
                logger.warning(
                    "Middleware hatasi: %s", e,
                )

        # Yurutme
        try:
            handler_result = entry["handler"](
                payload,
            )
            entry["call_count"] += 1

            result = {
                "command_type": command_type,
                "status": "completed",
                "result": handler_result,
                "actor": actor,
                "timestamp": time.time(),
            }
        except Exception as e:
            result = {
                "command_type": command_type,
                "status": "failed",
                "error": str(e),
                "actor": actor,
                "timestamp": time.time(),
            }

        self._history.append(result)
        return result

    def dispatch_batch(
        self,
        commands: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Toplu komut dagitir.

        Args:
            commands: Komut listesi.

        Returns:
            Toplam sonuc.
        """
        completed = 0
        failed = 0
        rejected = 0

        for cmd in commands:
            result = self.dispatch(
                command_type=cmd.get(
                    "command_type", "",
                ),
                payload=cmd.get("payload"),
                actor=cmd.get("actor", ""),
            )
            status = result["status"]
            if status == "completed":
                completed += 1
            elif status == "failed":
                failed += 1
            else:
                rejected += 1

        return {
            "total": len(commands),
            "completed": completed,
            "failed": failed,
            "rejected": rejected,
        }

    def get_history(
        self,
        command_type: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        """Gecmisi getirir.

        Args:
            command_type: Komut tipi filtresi.
            status: Durum filtresi.

        Returns:
            Gecmis listesi.
        """
        result = self._history
        if command_type:
            result = [
                h for h in result
                if h.get("command_type")
                == command_type
            ]
        if status:
            result = [
                h for h in result
                if h.get("status") == status
            ]
        return result

    @property
    def handler_count(self) -> int:
        """Isleyici sayisi."""
        return len(self._handlers)

    @property
    def command_count(self) -> int:
        """Islenenmis komut sayisi."""
        return len(self._history)

    @property
    def success_rate(self) -> float:
        """Basari orani."""
        if not self._history:
            return 0.0
        completed = sum(
            1 for h in self._history
            if h.get("status") == "completed"
        )
        return round(
            completed / len(self._history), 4,
        )
