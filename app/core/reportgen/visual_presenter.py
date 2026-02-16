"""ATLAS Görsel Sunucu modülü.

Grafik üretimi, çizge oluşturma,
infografik, veri görselleştirme,
etkileşimli elemanlar.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class VisualPresenter:
    """Görsel sunucu.

    Veriyi görsel formatlara dönüştürür.

    Attributes:
        _visuals: Görsel geçmişi.
    """

    def __init__(self) -> None:
        """Sunucuyu başlatır."""
        self._visuals: list[
            dict[str, Any]
        ] = []
        self._counter = 0
        self._stats = {
            "charts_created": 0,
            "graphs_created": 0,
            "infographics_created": 0,
            "tables_created": 0,
        }

        logger.info(
            "VisualPresenter baslatildi",
        )

    def create_chart(
        self,
        chart_type: str,
        data: dict[str, Any],
        title: str = "",
        options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Grafik oluşturur.

        Args:
            chart_type: Grafik tipi.
            data: Veri.
            title: Başlık.
            options: Seçenekler.

        Returns:
            Grafik bilgisi.
        """
        self._counter += 1
        vid = f"vis_{self._counter}"

        visual = {
            "visual_id": vid,
            "type": chart_type,
            "title": title,
            "data": data,
            "options": options or {},
            "format": "svg",
            "width": options.get(
                "width", 800,
            ) if options else 800,
            "height": options.get(
                "height", 400,
            ) if options else 400,
            "created_at": time.time(),
        }
        self._visuals.append(visual)
        self._stats["charts_created"] += 1

        return {
            "visual_id": vid,
            "type": chart_type,
            "title": title,
            "format": "svg",
            "created": True,
        }

    def create_bar_chart(
        self,
        labels: list[str],
        values: list[float],
        title: str = "",
    ) -> dict[str, Any]:
        """Bar grafik oluşturur.

        Args:
            labels: Etiketler.
            values: Değerler.
            title: Başlık.

        Returns:
            Grafik bilgisi.
        """
        return self.create_chart(
            chart_type="bar",
            data={
                "labels": labels,
                "values": values,
            },
            title=title,
        )

    def create_line_chart(
        self,
        x_values: list[Any],
        y_values: list[float],
        title: str = "",
    ) -> dict[str, Any]:
        """Çizgi grafik oluşturur.

        Args:
            x_values: X değerleri.
            y_values: Y değerleri.
            title: Başlık.

        Returns:
            Grafik bilgisi.
        """
        return self.create_chart(
            chart_type="line",
            data={
                "x": x_values,
                "y": y_values,
            },
            title=title,
        )

    def create_pie_chart(
        self,
        labels: list[str],
        values: list[float],
        title: str = "",
    ) -> dict[str, Any]:
        """Pasta grafik oluşturur.

        Args:
            labels: Etiketler.
            values: Değerler.
            title: Başlık.

        Returns:
            Grafik bilgisi.
        """
        return self.create_chart(
            chart_type="pie",
            data={
                "labels": labels,
                "values": values,
            },
            title=title,
        )

    def create_graph(
        self,
        nodes: list[dict[str, Any]],
        edges: list[dict[str, Any]],
        title: str = "",
    ) -> dict[str, Any]:
        """Çizge oluşturur.

        Args:
            nodes: Düğümler.
            edges: Kenarlar.
            title: Başlık.

        Returns:
            Çizge bilgisi.
        """
        self._counter += 1
        vid = f"vis_{self._counter}"

        visual = {
            "visual_id": vid,
            "type": "graph",
            "title": title,
            "data": {
                "nodes": nodes,
                "edges": edges,
            },
            "node_count": len(nodes),
            "edge_count": len(edges),
            "created_at": time.time(),
        }
        self._visuals.append(visual)
        self._stats["graphs_created"] += 1

        return {
            "visual_id": vid,
            "type": "graph",
            "title": title,
            "node_count": len(nodes),
            "edge_count": len(edges),
            "created": True,
        }

    def create_infographic(
        self,
        sections: list[dict[str, Any]],
        title: str = "",
        style: str = "modern",
    ) -> dict[str, Any]:
        """İnfografik oluşturur.

        Args:
            sections: Bölümler.
            title: Başlık.
            style: Stil.

        Returns:
            İnfografik bilgisi.
        """
        self._counter += 1
        vid = f"vis_{self._counter}"

        visual = {
            "visual_id": vid,
            "type": "infographic",
            "title": title,
            "sections": sections,
            "style": style,
            "created_at": time.time(),
        }
        self._visuals.append(visual)
        self._stats[
            "infographics_created"
        ] += 1

        return {
            "visual_id": vid,
            "type": "infographic",
            "title": title,
            "section_count": len(sections),
            "style": style,
            "created": True,
        }

    def create_data_table(
        self,
        headers: list[str],
        rows: list[list[Any]],
        title: str = "",
        highlight_max: bool = False,
    ) -> dict[str, Any]:
        """Veri tablosu oluşturur.

        Args:
            headers: Başlıklar.
            rows: Satırlar.
            title: Başlık.
            highlight_max: Maks vurgula.

        Returns:
            Tablo bilgisi.
        """
        self._counter += 1
        vid = f"vis_{self._counter}"

        visual = {
            "visual_id": vid,
            "type": "table",
            "title": title,
            "headers": headers,
            "rows": rows,
            "highlight_max": highlight_max,
            "created_at": time.time(),
        }
        self._visuals.append(visual)
        self._stats["tables_created"] += 1

        return {
            "visual_id": vid,
            "type": "table",
            "title": title,
            "row_count": len(rows),
            "column_count": len(headers),
            "created": True,
        }

    def get_visuals(
        self,
        visual_type: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Görselleri getirir.

        Args:
            visual_type: Tip filtresi.
            limit: Maks kayıt.

        Returns:
            Görsel listesi.
        """
        results = self._visuals
        if visual_type:
            results = [
                v for v in results
                if v["type"] == visual_type
            ]
        return list(results[-limit:])

    @property
    def visual_count(self) -> int:
        """Toplam görsel sayısı."""
        return len(self._visuals)

    @property
    def chart_count(self) -> int:
        """Grafik sayısı."""
        return self._stats["charts_created"]
