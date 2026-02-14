"""ATLAS Log Disa Aktarici modulu.

Dosya aktarimi, bulut aktarimi,
SIEM entegrasyonu, arsiv yonetimi
ve sikistirma.
"""

import json
import logging
import time
import zlib
from typing import Any

logger = logging.getLogger(__name__)


class LogExporter:
    """Log disa aktarici.

    Loglari cesitli hedeflere aktarir.

    Attributes:
        _exports: Aktarim kayitlari.
        _targets: Hedef tanimlari.
    """

    def __init__(self) -> None:
        """Log disa aktariciyi baslatir."""
        self._exports: list[
            dict[str, Any]
        ] = []
        self._targets: dict[
            str, dict[str, Any]
        ] = {}
        self._archives: list[
            dict[str, Any]
        ] = []

        logger.info(
            "LogExporter baslatildi",
        )

    def register_target(
        self,
        name: str,
        target_type: str,
        config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Hedef kaydeder.

        Args:
            name: Hedef adi.
            target_type: Hedef tipi.
            config: Yapilandirma.

        Returns:
            Hedef bilgisi.
        """
        target = {
            "name": name,
            "type": target_type,
            "config": config or {},
            "export_count": 0,
        }
        self._targets[name] = target
        return target

    def export_to_file(
        self,
        logs: list[dict[str, Any]],
        filename: str = "logs.json",
        fmt: str = "json",
    ) -> dict[str, Any]:
        """Dosyaya aktarir.

        Args:
            logs: Log kayitlari.
            filename: Dosya adi.
            fmt: Format.

        Returns:
            Aktarim bilgisi.
        """
        if fmt == "json":
            content = json.dumps(
                logs, default=str,
            )
        elif fmt == "csv":
            lines = []
            for log in logs:
                line = (
                    f"{log.get('timestamp', '')},"
                    f"{log.get('level', '')},"
                    f"{log.get('source', '')},"
                    f"\"{log.get('message', '')}\""
                )
                lines.append(line)
            content = "\n".join(lines)
        else:
            content = "\n".join(
                str(log) for log in logs
            )

        export = {
            "type": "file",
            "filename": filename,
            "format": fmt,
            "record_count": len(logs),
            "size_bytes": len(content.encode()),
            "timestamp": time.time(),
        }
        self._exports.append(export)
        return export

    def export_to_cloud(
        self,
        logs: list[dict[str, Any]],
        target_name: str,
    ) -> dict[str, Any]:
        """Buluta aktarir.

        Args:
            logs: Log kayitlari.
            target_name: Hedef adi.

        Returns:
            Aktarim bilgisi.
        """
        target = self._targets.get(target_name)
        if not target:
            return {
                "success": False,
                "error": "target_not_found",
            }

        target["export_count"] += 1

        export = {
            "type": "cloud",
            "target": target_name,
            "record_count": len(logs),
            "success": True,
            "timestamp": time.time(),
        }
        self._exports.append(export)
        return export

    def export_to_siem(
        self,
        logs: list[dict[str, Any]],
        target_name: str,
    ) -> dict[str, Any]:
        """SIEM'e aktarir.

        Args:
            logs: Log kayitlari.
            target_name: SIEM hedefi.

        Returns:
            Aktarim bilgisi.
        """
        target = self._targets.get(target_name)
        if not target:
            return {
                "success": False,
                "error": "target_not_found",
            }

        target["export_count"] += 1

        # Syslog formati
        formatted = []
        for log in logs:
            formatted.append({
                "facility": "local0",
                "severity": log.get("level", "info"),
                "message": log.get("message", ""),
                "timestamp": log.get(
                    "timestamp", "",
                ),
            })

        export = {
            "type": "siem",
            "target": target_name,
            "record_count": len(logs),
            "formatted_count": len(formatted),
            "success": True,
            "timestamp": time.time(),
        }
        self._exports.append(export)
        return export

    def archive(
        self,
        logs: list[dict[str, Any]],
        archive_name: str = "",
        compress: bool = True,
    ) -> dict[str, Any]:
        """Arsivler.

        Args:
            logs: Log kayitlari.
            archive_name: Arsiv adi.
            compress: Sikistir.

        Returns:
            Arsiv bilgisi.
        """
        content = json.dumps(
            logs, default=str,
        ).encode()
        original_size = len(content)

        if compress:
            compressed = zlib.compress(content)
            compressed_size = len(compressed)
        else:
            compressed_size = original_size

        name = archive_name or (
            f"archive_{int(time.time())}"
        )

        archive = {
            "name": name,
            "record_count": len(logs),
            "original_size": original_size,
            "compressed_size": compressed_size,
            "compression_ratio": round(
                compressed_size / original_size,
                4,
            ) if original_size > 0 else 1.0,
            "compressed": compress,
            "timestamp": time.time(),
        }
        self._archives.append(archive)
        self._exports.append({
            "type": "archive",
            "name": name,
            "record_count": len(logs),
            "timestamp": time.time(),
        })
        return archive

    def get_export_history(
        self,
        export_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """Aktarim gecmisini getirir.

        Args:
            export_type: Tip filtresi.

        Returns:
            Gecmis listesi.
        """
        if export_type:
            return [
                e for e in self._exports
                if e.get("type") == export_type
            ]
        return list(self._exports)

    def get_archive(
        self,
        name: str,
    ) -> dict[str, Any] | None:
        """Arsiv getirir.

        Args:
            name: Arsiv adi.

        Returns:
            Arsiv veya None.
        """
        for a in self._archives:
            if a["name"] == name:
                return a
        return None

    @property
    def export_count(self) -> int:
        """Aktarim sayisi."""
        return len(self._exports)

    @property
    def target_count(self) -> int:
        """Hedef sayisi."""
        return len(self._targets)

    @property
    def archive_count(self) -> int:
        """Arsiv sayisi."""
        return len(self._archives)
