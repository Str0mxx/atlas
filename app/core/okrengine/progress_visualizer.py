"""ATLAS İlerleme Görselleştirici.

OKR ilerleme grafikleri, trend görselleştirme,
karşılaştırma paneli, özet rapor, dashboard.
"""

import logging
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class OKRProgressVisualizer:
    """İlerleme görselleştirici.

    OKR ilerlemesini grafiklerle görselleştirir,
    trend analizi yapar, karşılaştırma ve raporlar oluşturur.

    Attributes:
        _charts: Grafik kayıtları.
        _stats: İstatistikler.
    """

    def __init__(self) -> None:
        """Görselleştiriciyi başlatır."""
        self._charts: list[dict] = []
        self._stats = {
            "charts_created": 0,
        }
        logger.info(
            "OKRProgressVisualizer baslatildi",
        )

    @property
    def chart_count(self) -> int:
        """Grafik sayısı."""
        return self._stats["charts_created"]

    def generate_progress_chart(
        self,
        objective_id: str,
        progress_pct: float = 0.0,
        label: str = "",
    ) -> dict[str, Any]:
        """İlerleme grafiği oluşturur.

        Args:
            objective_id: Hedef ID.
            progress_pct: İlerleme yüzdesi.
            label: Grafik etiketi.

        Returns:
            Grafik bilgisi.
        """
        filled = int(progress_pct / 10)
        bar = "█" * filled + "░" * (10 - filled)

        if progress_pct >= 70:
            color = "green"
        elif progress_pct >= 40:
            color = "yellow"
        else:
            color = "red"

        self._charts.append(
            {
                "objective_id": objective_id,
                "progress_pct": progress_pct,
                "bar": bar,
                "color": color,
                "label": label,
            },
        )
        self._stats["charts_created"] += 1

        logger.info(
            f"Ilerleme grafigi olusturuldu: {objective_id} - {progress_pct}%",
        )

        return {
            "objective_id": objective_id,
            "progress_pct": progress_pct,
            "bar": bar,
            "color": color,
            "label": label,
            "chart_type": "progress_bar",
            "generated": True,
        }

    def visualize_trend(
        self,
        kr_id: str,
        data_points: list[float] | None = None,
    ) -> dict[str, Any]:
        """Trend görselleştirir.

        Args:
            kr_id: Anahtar sonuç ID.
            data_points: Veri noktaları.

        Returns:
            Trend görselleştirme bilgisi.
        """
        if data_points is None:
            data_points = []

        if len(data_points) >= 2:
            if data_points[-1] > data_points[0]:
                trend = "improving"
            elif data_points[-1] < data_points[0]:
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "insufficient_data"

        avg = round(
            sum(data_points) / max(len(data_points), 1),
            1,
        )

        logger.info(
            f"Trend gorsellesti: {kr_id} - {trend} (avg: {avg})",
        )

        return {
            "kr_id": kr_id,
            "data_points": data_points,
            "trend": trend,
            "average": avg,
            "point_count": len(data_points),
            "visualized": True,
        }

    def create_comparison(
        self,
        objectives: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Karşılaştırma oluşturur.

        Args:
            objectives: Hedef listesi.

        Returns:
            Karşılaştırma bilgisi.
        """
        if objectives is None:
            objectives = []

        ranked = sorted(
            objectives,
            key=lambda o: o.get("progress", 0),
            reverse=True,
        )

        leader = ranked[0]["name"] if ranked else ""
        laggard = ranked[-1]["name"] if ranked else ""
        avg_progress = round(
            sum(o.get("progress", 0) for o in objectives) / max(len(objectives), 1),
            1,
        )

        logger.info(
            f"Karsilastirma olusturuldu: {len(objectives)} hedef - Lider: {leader}",
        )

        return {
            "ranked": ranked,
            "leader": leader,
            "laggard": laggard,
            "avg_progress": avg_progress,
            "count": len(objectives),
            "compared": True,
        }

    def build_dashboard(
        self,
        widgets: list[str] | None = None,
    ) -> dict[str, Any]:
        """Dashboard oluşturur.

        Args:
            widgets: Widget listesi.

        Returns:
            Dashboard bilgisi.
        """
        if widgets is None:
            widgets = [
                "overall_progress",
                "top_okrs",
                "at_risk",
                "recent_updates",
            ]

        layout = "grid" if len(widgets) <= 4 else "scroll"
        dashboard_id = f"dash_{str(uuid4())[:6]}"

        logger.info(
            f"Dashboard olusturuldu: {dashboard_id} - {len(widgets)} widget",
        )

        return {
            "widgets": widgets,
            "widget_count": len(widgets),
            "layout": layout,
            "dashboard_id": dashboard_id,
            "built": True,
        }

    def export_report(
        self,
        format: str = "summary",
        objective_count: int = 0,
        kr_count: int = 0,
        avg_score: float = 0.0,
    ) -> dict[str, Any]:
        """Rapor dışa aktarır.

        Args:
            format: Rapor formatı (summary/detailed).
            objective_count: Hedef sayısı.
            kr_count: Anahtar sonuç sayısı.
            avg_score: Ortalama skor.

        Returns:
            Dışa aktarma bilgisi.
        """
        if format == "summary":
            sections = ["overview", "highlights"]
        elif format == "detailed":
            sections = [
                "overview",
                "highlights",
                "details",
                "recommendations",
            ]
        else:
            sections = ["overview"]

        logger.info(
            f"Rapor disa aktarildi: {format} - {len(sections)} bolum",
        )

        return {
            "format": format,
            "sections": sections,
            "objective_count": objective_count,
            "kr_count": kr_count,
            "avg_score": avg_score,
            "section_count": len(sections),
            "exported": True,
        }
