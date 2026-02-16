"""ATLAS Rapor Oluşturucu modülü.

Şablon sistemi, bölüm yönetimi,
dinamik içerik, çoklu format çıktı,
stil seçenekleri.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class ReportBuilder:
    """Rapor oluşturucu.

    Şablon tabanlı raporlar oluşturur.

    Attributes:
        _reports: Rapor geçmişi.
        _templates: Şablon kütüphanesi.
    """

    def __init__(self) -> None:
        """Oluşturucuyu başlatır."""
        self._reports: dict[
            str, dict[str, Any]
        ] = {}
        self._templates: dict[
            str, dict[str, Any]
        ] = {}
        self._counter = 0
        self._stats = {
            "reports_created": 0,
            "sections_added": 0,
            "templates_registered": 0,
            "reports_finalized": 0,
        }

        logger.info(
            "ReportBuilder baslatildi",
        )

    def create_report(
        self,
        title: str,
        template_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Rapor oluşturur.

        Args:
            title: Rapor başlığı.
            template_id: Şablon ID.
            metadata: Ek bilgiler.

        Returns:
            Rapor bilgisi.
        """
        self._counter += 1
        rid = f"rpt_{self._counter}"

        template = None
        if template_id:
            template = self._templates.get(
                template_id,
            )

        report = {
            "report_id": rid,
            "title": title,
            "sections": [],
            "status": "draft",
            "template_id": template_id,
            "metadata": metadata or {},
            "style": {
                "font": "default",
                "theme": "professional",
            },
            "created_at": time.time(),
            "finalized_at": None,
        }

        # Şablondan bölümler
        if template:
            for sec in template.get(
                "sections", [],
            ):
                report["sections"].append({
                    "title": sec["title"],
                    "content": "",
                    "type": sec.get(
                        "type", "text",
                    ),
                })

        self._reports[rid] = report
        self._stats["reports_created"] += 1

        return {
            "report_id": rid,
            "title": title,
            "template_applied": (
                template is not None
            ),
            "created": True,
        }

    def add_section(
        self,
        report_id: str,
        title: str,
        content: str,
        section_type: str = "text",
    ) -> dict[str, Any]:
        """Bölüm ekler.

        Args:
            report_id: Rapor ID.
            title: Bölüm başlığı.
            content: İçerik.
            section_type: Bölüm tipi.

        Returns:
            Ekleme bilgisi.
        """
        report = self._reports.get(report_id)
        if not report:
            return {"error": "report_not_found"}

        section = {
            "title": title,
            "content": content,
            "type": section_type,
            "index": len(report["sections"]),
        }
        report["sections"].append(section)
        self._stats["sections_added"] += 1

        return {
            "report_id": report_id,
            "section_index": section["index"],
            "title": title,
            "added": True,
        }

    def set_style(
        self,
        report_id: str,
        font: str | None = None,
        theme: str | None = None,
    ) -> dict[str, Any]:
        """Stil ayarlar.

        Args:
            report_id: Rapor ID.
            font: Yazı tipi.
            theme: Tema.

        Returns:
            Ayar bilgisi.
        """
        report = self._reports.get(report_id)
        if not report:
            return {"error": "report_not_found"}

        if font:
            report["style"]["font"] = font
        if theme:
            report["style"]["theme"] = theme

        return {
            "report_id": report_id,
            "style": dict(report["style"]),
            "updated": True,
        }

    def set_dynamic_content(
        self,
        report_id: str,
        section_index: int,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Dinamik içerik ayarlar.

        Args:
            report_id: Rapor ID.
            section_index: Bölüm indeksi.
            data: Dinamik veri.

        Returns:
            Ayar bilgisi.
        """
        report = self._reports.get(report_id)
        if not report:
            return {"error": "report_not_found"}

        if section_index >= len(
            report["sections"],
        ):
            return {
                "error": "section_not_found",
            }

        section = report["sections"][
            section_index
        ]
        section["dynamic_data"] = data

        return {
            "report_id": report_id,
            "section_index": section_index,
            "dynamic_set": True,
        }

    def finalize(
        self,
        report_id: str,
        output_format: str = "markdown",
    ) -> dict[str, Any]:
        """Raporu sonuçlandırır.

        Args:
            report_id: Rapor ID.
            output_format: Çıktı formatı.

        Returns:
            Sonuçlandırma bilgisi.
        """
        report = self._reports.get(report_id)
        if not report:
            return {"error": "report_not_found"}

        # İçerik oluştur
        content_parts = [
            f"# {report['title']}\n",
        ]
        for section in report["sections"]:
            content_parts.append(
                f"## {section['title']}\n"
                f"{section.get('content', '')}\n",
            )

        content = "\n".join(content_parts)
        report["status"] = "ready"
        report["finalized_at"] = time.time()
        report["output_format"] = output_format
        report["content"] = content
        self._stats["reports_finalized"] += 1

        return {
            "report_id": report_id,
            "format": output_format,
            "sections": len(
                report["sections"],
            ),
            "content_length": len(content),
            "finalized": True,
        }

    def register_template(
        self,
        name: str,
        sections: list[dict[str, str]],
        description: str = "",
    ) -> dict[str, Any]:
        """Şablon kaydeder.

        Args:
            name: Şablon adı.
            sections: Bölüm tanımları.
            description: Açıklama.

        Returns:
            Kayıt bilgisi.
        """
        tid = f"tmpl_{name}"
        self._templates[tid] = {
            "name": name,
            "sections": sections,
            "description": description,
            "created_at": time.time(),
        }
        self._stats[
            "templates_registered"
        ] += 1

        return {
            "template_id": tid,
            "name": name,
            "sections": len(sections),
            "registered": True,
        }

    def get_report(
        self,
        report_id: str,
    ) -> dict[str, Any]:
        """Rapor getirir.

        Args:
            report_id: Rapor ID.

        Returns:
            Rapor bilgisi.
        """
        report = self._reports.get(report_id)
        if not report:
            return {"error": "report_not_found"}
        return dict(report)

    def get_reports(
        self,
        status: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Raporları getirir.

        Args:
            status: Durum filtresi.
            limit: Maks kayıt.

        Returns:
            Rapor listesi.
        """
        results = list(
            self._reports.values(),
        )
        if status:
            results = [
                r for r in results
                if r["status"] == status
            ]
        return results[-limit:]

    @property
    def report_count(self) -> int:
        """Rapor sayısı."""
        return self._stats["reports_created"]

    @property
    def template_count(self) -> int:
        """Şablon sayısı."""
        return self._stats[
            "templates_registered"
        ]

    @property
    def section_count(self) -> int:
        """Bölüm sayısı."""
        return self._stats["sections_added"]
