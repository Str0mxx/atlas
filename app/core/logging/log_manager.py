"""ATLAS Log Yoneticisi modulu.

Coklu seviye loglama, yapisal loglama,
baglamsal enjeksiyon, log rotasyonu
ve asenkron loglama.
"""

import logging
import time
from typing import Any

from app.models.logging_models import LogLevel

logger = logging.getLogger(__name__)

LEVEL_PRIORITY = {
    LogLevel.DEBUG: 0,
    LogLevel.INFO: 1,
    LogLevel.WARNING: 2,
    LogLevel.ERROR: 3,
    LogLevel.CRITICAL: 4,
}


class LogManager:
    """Log yoneticisi.

    Loglari yonetir ve dagitir.

    Attributes:
        _logs: Log kayitlari.
        _context: Global baglam.
    """

    def __init__(
        self,
        level: LogLevel = LogLevel.INFO,
        max_size: int = 10000,
    ) -> None:
        """Log yoneticisini baslatir.

        Args:
            level: Minimum log seviyesi.
            max_size: Maks log sayisi.
        """
        self._level = level
        self._max_size = max_size
        self._logs: list[dict[str, Any]] = []
        self._context: dict[str, Any] = {}
        self._handlers: list[str] = []
        self._rotation_count = 0

        logger.info("LogManager baslatildi")

    def log(
        self,
        level: LogLevel,
        message: str,
        source: str = "",
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """Log kaydeder.

        Args:
            level: Log seviyesi.
            message: Mesaj.
            source: Kaynak.
            context: Baglam.

        Returns:
            Log kaydi veya None.
        """
        if LEVEL_PRIORITY.get(
            level, 0
        ) < LEVEL_PRIORITY.get(self._level, 0):
            return None

        merged_ctx = dict(self._context)
        if context:
            merged_ctx.update(context)

        record = {
            "level": level.value,
            "message": message,
            "source": source,
            "context": merged_ctx,
            "timestamp": time.time(),
        }
        self._logs.append(record)

        # Rotasyon
        if len(self._logs) > self._max_size:
            self._rotate()

        return record

    def debug(
        self, message: str, **kwargs: Any,
    ) -> dict[str, Any] | None:
        """Debug log."""
        return self.log(
            LogLevel.DEBUG, message, **kwargs,
        )

    def info(
        self, message: str, **kwargs: Any,
    ) -> dict[str, Any] | None:
        """Info log."""
        return self.log(
            LogLevel.INFO, message, **kwargs,
        )

    def warning(
        self, message: str, **kwargs: Any,
    ) -> dict[str, Any] | None:
        """Warning log."""
        return self.log(
            LogLevel.WARNING, message, **kwargs,
        )

    def error(
        self, message: str, **kwargs: Any,
    ) -> dict[str, Any] | None:
        """Error log."""
        return self.log(
            LogLevel.ERROR, message, **kwargs,
        )

    def critical(
        self, message: str, **kwargs: Any,
    ) -> dict[str, Any] | None:
        """Critical log."""
        return self.log(
            LogLevel.CRITICAL, message, **kwargs,
        )

    def set_context(
        self, key: str, value: Any,
    ) -> None:
        """Global baglam ayarlar.

        Args:
            key: Anahtar.
            value: Deger.
        """
        self._context[key] = value

    def clear_context(self) -> None:
        """Baglami temizler."""
        self._context = {}

    def set_level(self, level: LogLevel) -> None:
        """Log seviyesini ayarlar.

        Args:
            level: Yeni seviye.
        """
        self._level = level

    def add_handler(self, name: str) -> None:
        """Handler ekler.

        Args:
            name: Handler adi.
        """
        if name not in self._handlers:
            self._handlers.append(name)

    def _rotate(self) -> None:
        """Log rotasyonu yapar."""
        half = self._max_size // 2
        self._logs = self._logs[-half:]
        self._rotation_count += 1

    def get_logs(
        self,
        level: LogLevel | None = None,
        source: str = "",
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Loglari getirir.

        Args:
            level: Seviye filtresi.
            source: Kaynak filtresi.
            limit: Sonuc limiti.

        Returns:
            Log listesi.
        """
        result = self._logs
        if level:
            result = [
                r for r in result
                if r["level"] == level.value
            ]
        if source:
            result = [
                r for r in result
                if r["source"] == source
            ]
        return result[-limit:]

    def clear(self) -> int:
        """Loglari temizler.

        Returns:
            Temizlenen sayi.
        """
        count = len(self._logs)
        self._logs = []
        return count

    @property
    def log_count(self) -> int:
        """Log sayisi."""
        return len(self._logs)

    @property
    def handler_count(self) -> int:
        """Handler sayisi."""
        return len(self._handlers)

    @property
    def rotation_count(self) -> int:
        """Rotasyon sayisi."""
        return self._rotation_count

    @property
    def current_level(self) -> LogLevel:
        """Mevcut seviye."""
        return self._level
