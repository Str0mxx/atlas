"""ATLAS Gercek Zamanli Panel modulu.

Canli metrikler, grafik guncellemeleri,
alarm goruntuleme, detay inceleme
ve paylasim.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class RealtimeDashboard:
    """Gercek zamanli panel.

    Canli verileri gorsellestirir.

    Attributes:
        _dashboards: Paneller.
        _widgets: Widget'lar.
    """

    def __init__(self) -> None:
        """Paneli baslatir."""
        self._dashboards: dict[
            str, dict[str, Any]
        ] = {}
        self._widgets: dict[
            str, list[dict[str, Any]]
        ] = {}
        self._live_metrics: dict[
            str, dict[str, Any]
        ] = {}
        self._alerts_display: list[
            dict[str, Any]
        ] = []
        self._shares: dict[
            str, dict[str, Any]
        ] = {}

        logger.info(
            "RealtimeDashboard baslatildi",
        )

    def create_dashboard(
        self,
        name: str,
        title: str = "",
        layout: str = "grid",
    ) -> dict[str, Any]:
        """Panel olusturur.

        Args:
            name: Panel adi.
            title: Baslik.
            layout: Yerlestirme.

        Returns:
            Olusturma bilgisi.
        """
        self._dashboards[name] = {
            "name": name,
            "title": title or name,
            "layout": layout,
            "status": "active",
            "created_at": time.time(),
            "updated_at": time.time(),
        }
        self._widgets[name] = []

        return {
            "name": name,
            "title": title or name,
            "layout": layout,
        }

    def add_widget(
        self,
        dashboard: str,
        widget_type: str,
        title: str,
        data_source: str = "",
        config: dict[str, Any]
            | None = None,
    ) -> dict[str, Any]:
        """Widget ekler.

        Args:
            dashboard: Panel adi.
            widget_type: Widget tipi.
            title: Baslik.
            data_source: Veri kaynagi.
            config: Konfigurasyon.

        Returns:
            Ekleme bilgisi.
        """
        if dashboard not in self._dashboards:
            return {"error": "dashboard_not_found"}

        widget = {
            "type": widget_type,
            "title": title,
            "data_source": data_source,
            "config": config or {},
            "data": [],
            "last_update": time.time(),
        }
        self._widgets[dashboard].append(widget)

        return {
            "dashboard": dashboard,
            "type": widget_type,
            "title": title,
        }

    def update_metric(
        self,
        name: str,
        value: float,
        labels: dict[str, str]
            | None = None,
    ) -> dict[str, Any]:
        """Canli metrigi gunceller.

        Args:
            name: Metrik adi.
            value: Deger.
            labels: Etiketler.

        Returns:
            Guncelleme bilgisi.
        """
        if name not in self._live_metrics:
            self._live_metrics[name] = {
                "name": name,
                "current": value,
                "history": [],
                "labels": labels or {},
            }

        metric = self._live_metrics[name]
        metric["current"] = value
        metric["history"].append({
            "value": value,
            "timestamp": time.time(),
        })

        # Gecmisi sinirla
        if len(metric["history"]) > 1000:
            metric["history"] = (
                metric["history"][-500:]
            )

        return {
            "name": name,
            "value": value,
        }

    def push_data(
        self,
        dashboard: str,
        widget_index: int,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Widget'a veri iter.

        Args:
            dashboard: Panel adi.
            widget_index: Widget indeksi.
            data: Veri.

        Returns:
            Push sonucu.
        """
        widgets = self._widgets.get(dashboard, [])
        if widget_index >= len(widgets):
            return {"error": "widget_not_found"}

        widget = widgets[widget_index]
        widget["data"].append(data)
        widget["last_update"] = time.time()

        # Veri sinirla
        if len(widget["data"]) > 500:
            widget["data"] = widget["data"][-250:]

        return {
            "dashboard": dashboard,
            "widget": widget_index,
            "data_points": len(widget["data"]),
        }

    def add_alert(
        self,
        title: str,
        message: str,
        level: str = "warning",
        source: str = "",
    ) -> dict[str, Any]:
        """Alarm ekler.

        Args:
            title: Baslik.
            message: Mesaj.
            level: Seviye.
            source: Kaynak.

        Returns:
            Alarm bilgisi.
        """
        alert = {
            "title": title,
            "message": message,
            "level": level,
            "source": source,
            "acknowledged": False,
            "timestamp": time.time(),
        }
        self._alerts_display.append(alert)

        return {
            "title": title,
            "level": level,
        }

    def acknowledge_alert(
        self,
        index: int,
    ) -> bool:
        """Alarmi onaylar.

        Args:
            index: Alarm indeksi.

        Returns:
            Basarili mi.
        """
        if 0 <= index < len(self._alerts_display):
            self._alerts_display[index][
                "acknowledged"
            ] = True
            return True
        return False

    def get_alerts(
        self,
        unacknowledged_only: bool = False,
    ) -> list[dict[str, Any]]:
        """Alarmlari getirir.

        Args:
            unacknowledged_only: Sadece onaylanmamis.

        Returns:
            Alarm listesi.
        """
        if unacknowledged_only:
            return [
                a for a in self._alerts_display
                if not a["acknowledged"]
            ]
        return list(self._alerts_display)

    def get_metric(
        self,
        name: str,
    ) -> dict[str, Any] | None:
        """Metrik getirir.

        Args:
            name: Metrik adi.

        Returns:
            Metrik bilgisi veya None.
        """
        return self._live_metrics.get(name)

    def get_metric_history(
        self,
        name: str,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Metrik gecmisini getirir.

        Args:
            name: Metrik adi.
            limit: Limit.

        Returns:
            Gecmis listesi.
        """
        metric = self._live_metrics.get(name)
        if not metric:
            return []
        return metric["history"][-limit:]

    def share_dashboard(
        self,
        name: str,
        share_with: str,
        permission: str = "view",
    ) -> dict[str, Any]:
        """Paneli payasir.

        Args:
            name: Panel adi.
            share_with: Kullanici.
            permission: Yetki.

        Returns:
            Paylasim bilgisi.
        """
        if name not in self._dashboards:
            return {"error": "dashboard_not_found"}

        key = f"{name}:{share_with}"
        self._shares[key] = {
            "dashboard": name,
            "user": share_with,
            "permission": permission,
            "shared_at": time.time(),
        }

        return {
            "dashboard": name,
            "shared_with": share_with,
            "permission": permission,
        }

    def get_dashboard(
        self,
        name: str,
    ) -> dict[str, Any] | None:
        """Panel bilgisini getirir.

        Args:
            name: Panel adi.

        Returns:
            Panel bilgisi veya None.
        """
        dash = self._dashboards.get(name)
        if not dash:
            return None
        return {
            **dash,
            "widgets": len(
                self._widgets.get(name, []),
            ),
        }

    def delete_dashboard(
        self,
        name: str,
    ) -> bool:
        """Paneli siler.

        Args:
            name: Panel adi.

        Returns:
            Basarili mi.
        """
        if name in self._dashboards:
            del self._dashboards[name]
            self._widgets.pop(name, None)
            return True
        return False

    @property
    def dashboard_count(self) -> int:
        """Panel sayisi."""
        return len(self._dashboards)

    @property
    def widget_count(self) -> int:
        """Toplam widget sayisi."""
        return sum(
            len(w)
            for w in self._widgets.values()
        )

    @property
    def metric_count(self) -> int:
        """Canli metrik sayisi."""
        return len(self._live_metrics)

    @property
    def alert_display_count(self) -> int:
        """Alarm sayisi."""
        return len(self._alerts_display)

    @property
    def share_count(self) -> int:
        """Paylasim sayisi."""
        return len(self._shares)
