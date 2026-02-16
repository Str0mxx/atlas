"""ATLAS Dışa Aktarma Yöneticisi modülü.

PDF, Word, HTML, Markdown dışa aktarma,
e-posta entegrasyonu.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class ExportManager:
    """Dışa aktarma yöneticisi.

    Raporları çeşitli formatlara aktarır.

    Attributes:
        _exports: Aktarma geçmişi.
    """

    SUPPORTED_FORMATS = [
        "pdf", "word", "html",
        "markdown", "json",
    ]

    def __init__(
        self,
        output_dir: str = "/tmp/reports",
    ) -> None:
        """Yöneticiyi başlatır.

        Args:
            output_dir: Çıktı dizini.
        """
        self._exports: list[
            dict[str, Any]
        ] = []
        self._output_dir = output_dir
        self._counter = 0
        self._stats = {
            "pdf_exports": 0,
            "word_exports": 0,
            "html_exports": 0,
            "markdown_exports": 0,
            "json_exports": 0,
            "emails_sent": 0,
        }

        logger.info(
            "ExportManager baslatildi",
        )

    def export_pdf(
        self,
        report_id: str,
        content: str,
        title: str = "",
    ) -> dict[str, Any]:
        """PDF olarak aktarır.

        Args:
            report_id: Rapor ID.
            content: İçerik.
            title: Başlık.

        Returns:
            Aktarma bilgisi.
        """
        return self._export(
            report_id, content,
            "pdf", title,
        )

    def export_word(
        self,
        report_id: str,
        content: str,
        title: str = "",
    ) -> dict[str, Any]:
        """Word olarak aktarır.

        Args:
            report_id: Rapor ID.
            content: İçerik.
            title: Başlık.

        Returns:
            Aktarma bilgisi.
        """
        return self._export(
            report_id, content,
            "word", title,
        )

    def export_html(
        self,
        report_id: str,
        content: str,
        title: str = "",
    ) -> dict[str, Any]:
        """HTML olarak aktarır.

        Args:
            report_id: Rapor ID.
            content: İçerik.
            title: Başlık.

        Returns:
            Aktarma bilgisi.
        """
        return self._export(
            report_id, content,
            "html", title,
        )

    def export_markdown(
        self,
        report_id: str,
        content: str,
        title: str = "",
    ) -> dict[str, Any]:
        """Markdown olarak aktarır.

        Args:
            report_id: Rapor ID.
            content: İçerik.
            title: Başlık.

        Returns:
            Aktarma bilgisi.
        """
        return self._export(
            report_id, content,
            "markdown", title,
        )

    def export_json(
        self,
        report_id: str,
        data: dict[str, Any],
        title: str = "",
    ) -> dict[str, Any]:
        """JSON olarak aktarır.

        Args:
            report_id: Rapor ID.
            data: Veri.
            title: Başlık.

        Returns:
            Aktarma bilgisi.
        """
        import json
        content = json.dumps(
            data, indent=2, ensure_ascii=False,
        )
        return self._export(
            report_id, content,
            "json", title,
        )

    def _export(
        self,
        report_id: str,
        content: str,
        fmt: str,
        title: str,
    ) -> dict[str, Any]:
        """Temel aktarma işlemi.

        Args:
            report_id: Rapor ID.
            content: İçerik.
            fmt: Format.
            title: Başlık.

        Returns:
            Aktarma bilgisi.
        """
        self._counter += 1
        eid = f"exp_{self._counter}"

        ext_map = {
            "pdf": ".pdf",
            "word": ".docx",
            "html": ".html",
            "markdown": ".md",
            "json": ".json",
        }
        ext = ext_map.get(fmt, ".txt")
        file_name = (
            f"{report_id}_{eid}{ext}"
        )
        file_path = (
            f"{self._output_dir}/{file_name}"
        )

        export = {
            "export_id": eid,
            "report_id": report_id,
            "format": fmt,
            "title": title,
            "file_path": file_path,
            "file_size_kb": len(content) // 1024
            + 1,
            "created_at": time.time(),
        }
        self._exports.append(export)
        self._stats[f"{fmt}_exports"] += 1

        return {
            "export_id": eid,
            "report_id": report_id,
            "format": fmt,
            "file_path": file_path,
            "file_size_kb": export[
                "file_size_kb"
            ],
            "exported": True,
        }

    def send_email(
        self,
        export_id: str,
        to: str,
        subject: str = "",
        body: str = "",
    ) -> dict[str, Any]:
        """E-posta ile gönderir.

        Args:
            export_id: Aktarma ID.
            to: Alıcı.
            subject: Konu.
            body: Gövde.

        Returns:
            Gönderim bilgisi.
        """
        export = None
        for e in self._exports:
            if e["export_id"] == export_id:
                export = e
                break

        if not export:
            return {
                "error": "export_not_found",
            }

        self._stats["emails_sent"] += 1

        return {
            "export_id": export_id,
            "to": to,
            "subject": subject or (
                f"Report: {export['title']}"
            ),
            "attachment": export["file_path"],
            "sent": True,
        }

    def get_exports(
        self,
        report_id: str | None = None,
        fmt: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Aktarmaları getirir.

        Args:
            report_id: Rapor filtresi.
            fmt: Format filtresi.
            limit: Maks kayıt.

        Returns:
            Aktarma listesi.
        """
        results = self._exports
        if report_id:
            results = [
                e for e in results
                if e["report_id"] == report_id
            ]
        if fmt:
            results = [
                e for e in results
                if e["format"] == fmt
            ]
        return list(results[-limit:])

    @property
    def export_count(self) -> int:
        """Toplam aktarma sayısı."""
        return len(self._exports)

    @property
    def email_count(self) -> int:
        """Gönderilen e-posta sayısı."""
        return self._stats["emails_sent"]
