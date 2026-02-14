"""ATLAS Log Bicimlendirici modulu.

JSON format, duz metin formati,
ozel formatlar, zaman damgasi
ve renk kodlama.
"""

import json
import logging
import time
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


class LogFormatter:
    """Log bicimlendirici.

    Log kayitlarini cesitli formatlara
    donusturur.

    Attributes:
        _formats: Format tanimlari.
        _colors: Renk kodlari.
    """

    def __init__(
        self,
        default_format: str = "json",
        include_timestamp: bool = True,
    ) -> None:
        """Log bicimlendiriciyi baslatir.

        Args:
            default_format: Varsayilan format.
            include_timestamp: Zaman damgasi ekle.
        """
        self._default_format = default_format
        self._include_timestamp = include_timestamp
        self._custom_formats: dict[
            str, str
        ] = {}
        self._colors = {
            "debug": "grey",
            "info": "green",
            "warning": "yellow",
            "error": "red",
            "critical": "bold_red",
        }
        self._formatted_count = 0

        logger.info(
            "LogFormatter baslatildi",
        )

    def format_json(
        self,
        record: dict[str, Any],
    ) -> str:
        """JSON formatina donusturur.

        Args:
            record: Log kaydi.

        Returns:
            JSON string.
        """
        self._formatted_count += 1
        output = dict(record)
        if self._include_timestamp:
            ts = output.get("timestamp")
            if isinstance(ts, (int, float)):
                output["timestamp"] = (
                    datetime.fromtimestamp(
                        ts, tz=timezone.utc,
                    ).isoformat()
                )
        return json.dumps(output, default=str)

    def format_plain(
        self,
        record: dict[str, Any],
    ) -> str:
        """Duz metin formatina donusturur.

        Args:
            record: Log kaydi.

        Returns:
            Duz metin.
        """
        self._formatted_count += 1
        ts = record.get("timestamp", "")
        if isinstance(ts, (int, float)):
            ts = datetime.fromtimestamp(
                ts, tz=timezone.utc,
            ).strftime("%Y-%m-%d %H:%M:%S")

        level = record.get("level", "INFO").upper()
        source = record.get("source", "")
        message = record.get("message", "")

        parts = []
        if self._include_timestamp:
            parts.append(f"[{ts}]")
        parts.append(f"[{level}]")
        if source:
            parts.append(f"[{source}]")
        parts.append(message)

        return " ".join(parts)

    def format_csv(
        self,
        record: dict[str, Any],
    ) -> str:
        """CSV formatina donusturur.

        Args:
            record: Log kaydi.

        Returns:
            CSV satiri.
        """
        self._formatted_count += 1
        ts = record.get("timestamp", "")
        if isinstance(ts, (int, float)):
            ts = datetime.fromtimestamp(
                ts, tz=timezone.utc,
            ).isoformat()
        level = record.get("level", "")
        source = record.get("source", "")
        message = record.get("message", "")
        # Virgul iceren mesajlari tirnak icine al
        message = message.replace('"', '""')
        return f'{ts},{level},{source},"{message}"'

    def format(
        self,
        record: dict[str, Any],
        fmt: str | None = None,
    ) -> str:
        """Belirtilen formata donusturur.

        Args:
            record: Log kaydi.
            fmt: Format tipi.

        Returns:
            Formatlanmis metin.
        """
        fmt = fmt or self._default_format

        if fmt == "json":
            return self.format_json(record)
        elif fmt == "plain":
            return self.format_plain(record)
        elif fmt == "csv":
            return self.format_csv(record)
        elif fmt in self._custom_formats:
            return self._apply_custom(
                record, self._custom_formats[fmt],
            )
        return self.format_json(record)

    def _apply_custom(
        self,
        record: dict[str, Any],
        template: str,
    ) -> str:
        """Ozel format uygular.

        Args:
            record: Log kaydi.
            template: Format sablonu.

        Returns:
            Formatlanmis metin.
        """
        self._formatted_count += 1
        result = template
        for key, val in record.items():
            result = result.replace(
                f"{{{key}}}", str(val),
            )
        return result

    def register_format(
        self,
        name: str,
        template: str,
    ) -> None:
        """Ozel format kaydeder.

        Args:
            name: Format adi.
            template: Sablon.
        """
        self._custom_formats[name] = template

    def get_color(
        self,
        level: str,
    ) -> str:
        """Renk kodu getirir.

        Args:
            level: Log seviyesi.

        Returns:
            Renk adi.
        """
        return self._colors.get(
            level.lower(), "default",
        )

    def set_color(
        self,
        level: str,
        color: str,
    ) -> None:
        """Renk kodu ayarlar.

        Args:
            level: Log seviyesi.
            color: Renk adi.
        """
        self._colors[level.lower()] = color

    def format_batch(
        self,
        records: list[dict[str, Any]],
        fmt: str | None = None,
    ) -> list[str]:
        """Toplu formatlama.

        Args:
            records: Log kayitlari.
            fmt: Format tipi.

        Returns:
            Formatlanmis liste.
        """
        return [
            self.format(r, fmt) for r in records
        ]

    @property
    def formatted_count(self) -> int:
        """Formatlanan log sayisi."""
        return self._formatted_count

    @property
    def custom_format_count(self) -> int:
        """Ozel format sayisi."""
        return len(self._custom_formats)
