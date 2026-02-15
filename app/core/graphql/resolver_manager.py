"""ATLAS Cozumleyici Yoneticisi modulu.

Cozumleyici kaydi, alan cozumleyicileri,
toplu cozumleyiciler, varsayilan
cozumleyiciler ve hata yonetimi.
"""

import logging
import time
from typing import Any, Callable

logger = logging.getLogger(__name__)


class ResolverManager:
    """Cozumleyici yoneticisi.

    GraphQL cozumleyicilerini yonetir.

    Attributes:
        _resolvers: Cozumleyiciler.
        _defaults: Varsayilan cozumleyiciler.
    """

    def __init__(self) -> None:
        """Yoneticiyi baslatir."""
        self._resolvers: dict[
            str, dict[str, Any]
        ] = {}
        self._batch_resolvers: dict[
            str, dict[str, Any]
        ] = {}
        self._defaults: dict[
            str, Callable[..., Any]
        ] = {}
        self._error_handlers: dict[
            str,
            Callable[[str, Exception], Any],
        ] = {}
        self._middleware: list[
            Callable[..., Any]
        ] = []
        self._stats = {
            "resolved": 0,
            "errors": 0,
            "cache_hits": 0,
        }

        logger.info(
            "ResolverManager baslatildi",
        )

    def register(
        self,
        type_name: str,
        field_name: str,
        resolver: Callable[..., Any],
        resolver_type: str = "field",
    ) -> dict[str, Any]:
        """Cozumleyici kaydeder.

        Args:
            type_name: Tip adi.
            field_name: Alan adi.
            resolver: Cozumleyici fonksiyonu.
            resolver_type: Cozumleyici tipi.

        Returns:
            Kayit bilgisi.
        """
        key = f"{type_name}.{field_name}"
        self._resolvers[key] = {
            "type_name": type_name,
            "field_name": field_name,
            "resolver": resolver,
            "resolver_type": resolver_type,
            "call_count": 0,
            "registered_at": time.time(),
        }

        return {
            "key": key,
            "type": resolver_type,
        }

    def register_batch(
        self,
        type_name: str,
        field_name: str,
        resolver: Callable[
            [list[Any]], list[Any]
        ],
    ) -> dict[str, Any]:
        """Toplu cozumleyici kaydeder.

        Args:
            type_name: Tip adi.
            field_name: Alan adi.
            resolver: Toplu cozumleyici.

        Returns:
            Kayit bilgisi.
        """
        key = f"{type_name}.{field_name}"
        self._batch_resolvers[key] = {
            "type_name": type_name,
            "field_name": field_name,
            "resolver": resolver,
            "call_count": 0,
        }

        return {"key": key, "type": "batch"}

    def set_default(
        self,
        type_name: str,
        resolver: Callable[..., Any],
    ) -> None:
        """Varsayilan cozumleyici ayarlar.

        Args:
            type_name: Tip adi.
            resolver: Cozumleyici.
        """
        self._defaults[type_name] = resolver

    def resolve(
        self,
        type_name: str,
        field_name: str,
        parent: Any = None,
        args: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
    ) -> Any:
        """Alani cozumler.

        Args:
            type_name: Tip adi.
            field_name: Alan adi.
            parent: Ust nesne.
            args: Argumanlar.
            context: Baglam.

        Returns:
            Cozumlenens deger.
        """
        key = f"{type_name}.{field_name}"

        # Middleware
        for mw in self._middleware:
            try:
                mw(type_name, field_name, args)
            except Exception:
                pass

        # Ozel cozumleyici
        entry = self._resolvers.get(key)
        if entry:
            try:
                entry["call_count"] += 1
                result = entry["resolver"](
                    parent, args or {}, context or {},
                )
                self._stats["resolved"] += 1
                return result
            except Exception as e:
                self._stats["errors"] += 1
                handler = self._error_handlers.get(
                    type_name,
                )
                if handler:
                    return handler(field_name, e)
                return None

        # Varsayilan
        default = self._defaults.get(type_name)
        if default:
            try:
                self._stats["resolved"] += 1
                return default(
                    parent, field_name,
                    args or {}, context or {},
                )
            except Exception:
                self._stats["errors"] += 1
                return None

        # Parent'tan al
        if isinstance(parent, dict):
            self._stats["resolved"] += 1
            return parent.get(field_name)

        return None

    def resolve_batch(
        self,
        type_name: str,
        field_name: str,
        keys: list[Any],
    ) -> list[Any]:
        """Toplu cozumler.

        Args:
            type_name: Tip adi.
            field_name: Alan adi.
            keys: Anahtarlar.

        Returns:
            Cozumlenen degerler.
        """
        key = f"{type_name}.{field_name}"
        entry = self._batch_resolvers.get(key)
        if not entry:
            return [None] * len(keys)

        try:
            entry["call_count"] += 1
            return entry["resolver"](keys)
        except Exception:
            self._stats["errors"] += 1
            return [None] * len(keys)

    def set_error_handler(
        self,
        type_name: str,
        handler: Callable[
            [str, Exception], Any
        ],
    ) -> None:
        """Hata isleyici ayarlar.

        Args:
            type_name: Tip adi.
            handler: Hata fonksiyonu.
        """
        self._error_handlers[type_name] = handler

    def add_middleware(
        self,
        middleware: Callable[..., Any],
    ) -> None:
        """Middleware ekler.

        Args:
            middleware: Middleware fonksiyonu.
        """
        self._middleware.append(middleware)

    def get_resolver(
        self,
        type_name: str,
        field_name: str,
    ) -> dict[str, Any] | None:
        """Cozumleyici bilgisini getirir.

        Args:
            type_name: Tip adi.
            field_name: Alan adi.

        Returns:
            Bilgi veya None.
        """
        key = f"{type_name}.{field_name}"
        entry = self._resolvers.get(key)
        if not entry:
            return None
        return {
            "key": key,
            "type": entry["resolver_type"],
            "call_count": entry["call_count"],
        }

    def remove(
        self,
        type_name: str,
        field_name: str,
    ) -> bool:
        """Cozumleyici kaldirir.

        Args:
            type_name: Tip adi.
            field_name: Alan adi.

        Returns:
            Basarili mi.
        """
        key = f"{type_name}.{field_name}"
        if key in self._resolvers:
            del self._resolvers[key]
            return True
        return False

    def get_stats(self) -> dict[str, int]:
        """Istatistikleri getirir.

        Returns:
            Istatistikler.
        """
        return dict(self._stats)

    @property
    def resolver_count(self) -> int:
        """Cozumleyici sayisi."""
        return len(self._resolvers)

    @property
    def batch_count(self) -> int:
        """Toplu cozumleyici sayisi."""
        return len(self._batch_resolvers)

    @property
    def default_count(self) -> int:
        """Varsayilan cozumleyici sayisi."""
        return len(self._defaults)

    @property
    def middleware_count(self) -> int:
        """Middleware sayisi."""
        return len(self._middleware)

    @property
    def resolved_count(self) -> int:
        """Cozumlenen alan sayisi."""
        return self._stats["resolved"]
