"""ATLAS Panel Olusturucu modulu.

Panel olusturma, widget tipleri,
veri kaynaklari, yerlesim yonetimi
ve paylasim.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class DashboardBuilder:
    """Panel olusturucu.

    Izleme panelleri olusturur.

    Attributes:
        _dashboards: Panel tanimlari.
        _widgets: Widget tanimlari.
    """

    def __init__(self) -> None:
        """Panel olusturucuyu baslatir."""
        self._dashboards: dict[
            str, dict[str, Any]
        ] = {}
        self._data_sources: dict[
            str, dict[str, Any]
        ] = {}
        self._shared: dict[
            str, dict[str, Any]
        ] = {}

        logger.info(
            "DashboardBuilder baslatildi",
        )

    def create_dashboard(
        self,
        name: str,
        title: str = "",
        description: str = "",
        layout: str = "grid",
    ) -> dict[str, Any]:
        """Panel olusturur.

        Args:
            name: Panel adi.
            title: Baslik.
            description: Aciklama.
            layout: Yerlesim tipi.

        Returns:
            Panel bilgisi.
        """
        dashboard = {
            "name": name,
            "title": title or name,
            "description": description,
            "layout": layout,
            "widgets": [],
            "created_at": time.time(),
            "updated_at": time.time(),
        }
        self._dashboards[name] = dashboard
        return {
            "name": name,
            "title": dashboard["title"],
        }

    def delete_dashboard(
        self,
        name: str,
    ) -> bool:
        """Panel siler.

        Args:
            name: Panel adi.

        Returns:
            Basarili mi.
        """
        if name in self._dashboards:
            del self._dashboards[name]
            return True
        return False

    def add_widget(
        self,
        dashboard_name: str,
        widget_type: str,
        title: str,
        data_source: str = "",
        config: dict[str, Any] | None = None,
        position: dict[str, int] | None = None,
    ) -> dict[str, Any]:
        """Widget ekler.

        Args:
            dashboard_name: Panel adi.
            widget_type: Widget tipi.
            title: Baslik.
            data_source: Veri kaynagi.
            config: Konfigurasyon.
            position: Konum.

        Returns:
            Widget bilgisi.
        """
        dashboard = self._dashboards.get(
            dashboard_name,
        )
        if not dashboard:
            return {
                "status": "error",
                "reason": "dashboard_not_found",
            }

        widget = {
            "type": widget_type,
            "title": title,
            "data_source": data_source,
            "config": config or {},
            "position": position or {},
            "index": len(dashboard["widgets"]),
        }
        dashboard["widgets"].append(widget)
        dashboard["updated_at"] = time.time()

        return {
            "dashboard": dashboard_name,
            "widget_index": widget["index"],
            "type": widget_type,
        }

    def remove_widget(
        self,
        dashboard_name: str,
        widget_index: int,
    ) -> bool:
        """Widget kaldirir.

        Args:
            dashboard_name: Panel adi.
            widget_index: Widget indeksi.

        Returns:
            Basarili mi.
        """
        dashboard = self._dashboards.get(
            dashboard_name,
        )
        if not dashboard:
            return False
        widgets = dashboard["widgets"]
        if 0 <= widget_index < len(widgets):
            widgets.pop(widget_index)
            # Indeksleri guncelle
            for i, w in enumerate(widgets):
                w["index"] = i
            return True
        return False

    def add_data_source(
        self,
        name: str,
        source_type: str,
        config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Veri kaynagi ekler.

        Args:
            name: Kaynak adi.
            source_type: Kaynak tipi.
            config: Konfigurasyon.

        Returns:
            Kaynak bilgisi.
        """
        self._data_sources[name] = {
            "name": name,
            "type": source_type,
            "config": config or {},
            "created_at": time.time(),
        }
        return {"name": name, "type": source_type}

    def remove_data_source(
        self,
        name: str,
    ) -> bool:
        """Veri kaynagi kaldirir.

        Args:
            name: Kaynak adi.

        Returns:
            Basarili mi.
        """
        if name in self._data_sources:
            del self._data_sources[name]
            return True
        return False

    def get_dashboard(
        self,
        name: str,
    ) -> dict[str, Any] | None:
        """Panel bilgisi getirir.

        Args:
            name: Panel adi.

        Returns:
            Panel veya None.
        """
        d = self._dashboards.get(name)
        if d:
            return dict(d)
        return None

    def list_dashboards(self) -> list[dict[str, Any]]:
        """Panel listesi getirir.

        Returns:
            Panel listesi.
        """
        return [
            {
                "name": d["name"],
                "title": d["title"],
                "widget_count": len(d["widgets"]),
            }
            for d in self._dashboards.values()
        ]

    def share_dashboard(
        self,
        name: str,
        shared_with: str,
        permission: str = "view",
    ) -> dict[str, Any]:
        """Panel paylasirir.

        Args:
            name: Panel adi.
            shared_with: Kullanici.
            permission: Yetki.

        Returns:
            Paylasim bilgisi.
        """
        if name not in self._dashboards:
            return {
                "status": "error",
                "reason": "not_found",
            }

        if name not in self._shared:
            self._shared[name] = {}
        self._shared[name][shared_with] = {
            "permission": permission,
            "shared_at": time.time(),
        }
        return {
            "dashboard": name,
            "shared_with": shared_with,
            "permission": permission,
        }

    def get_shared_users(
        self,
        name: str,
    ) -> list[str]:
        """Paylasilan kullanicilari getirir.

        Args:
            name: Panel adi.

        Returns:
            Kullanici listesi.
        """
        return list(
            self._shared.get(name, {}).keys(),
        )

    def clone_dashboard(
        self,
        source_name: str,
        new_name: str,
    ) -> dict[str, Any]:
        """Panel klonlar.

        Args:
            source_name: Kaynak panel.
            new_name: Yeni panel adi.

        Returns:
            Klonlama sonucu.
        """
        source = self._dashboards.get(source_name)
        if not source:
            return {
                "status": "error",
                "reason": "not_found",
            }

        import copy
        cloned = copy.deepcopy(source)
        cloned["name"] = new_name
        cloned["title"] = f"{source['title']} (Copy)"
        cloned["created_at"] = time.time()
        self._dashboards[new_name] = cloned

        return {
            "name": new_name,
            "widgets": len(cloned["widgets"]),
        }

    @property
    def dashboard_count(self) -> int:
        """Panel sayisi."""
        return len(self._dashboards)

    @property
    def data_source_count(self) -> int:
        """Veri kaynagi sayisi."""
        return len(self._data_sources)

    @property
    def total_widgets(self) -> int:
        """Toplam widget sayisi."""
        return sum(
            len(d["widgets"])
            for d in self._dashboards.values()
        )
