"""
Özel görünüm oluşturucu modülü.

Görünüm oluşturma, filtre yapılandırma,
sütun seçimi, sıralama, kaydetme/paylaşma.
"""

import logging
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class CustomViewBuilder:
    """Özel görünüm oluşturucu.

    Attributes:
        _views: Görünüm kayıtları.
        _stats: İstatistikler.
    """

    def __init__(self) -> None:
        """Oluşturucuyu başlatır."""
        self._views: list[dict] = []
        self._stats: dict[str, int] = {
            "views_created": 0,
        }
        logger.info(
            "CustomViewBuilder baslatildi"
        )

    @property
    def view_count(self) -> int:
        """Görünüm sayısı."""
        return len(self._views)

    def create_view(
        self,
        name: str = "",
        base_data: str = "",
    ) -> dict[str, Any]:
        """Görünüm oluşturur.

        Args:
            name: Görünüm adı.
            base_data: Temel veri.

        Returns:
            Görünüm bilgisi.
        """
        try:
            vid = f"vw_{uuid4()!s:.8}"

            record = {
                "view_id": vid,
                "name": name,
                "base_data": base_data,
                "filters": [],
                "columns": [],
                "sort": None,
                "shared": False,
            }
            self._views.append(record)
            self._stats["views_created"] += 1

            return {
                "view_id": vid,
                "name": name,
                "base_data": base_data,
                "created": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "created": False,
                "error": str(e),
            }

    def configure_filters(
        self,
        view_id: str = "",
        filters: list[dict] | None = None,
    ) -> dict[str, Any]:
        """Filtre yapılandırır.

        Args:
            view_id: Görünüm ID.
            filters: Filtre listesi.

        Returns:
            Filtre bilgisi.
        """
        try:
            view = None
            for v in self._views:
                if v["view_id"] == view_id:
                    view = v
                    break

            if not view:
                return {
                    "configured": False,
                    "error": "view_not_found",
                }

            filter_list = filters or []
            view["filters"] = filter_list

            return {
                "view_id": view_id,
                "filter_count": len(
                    filter_list
                ),
                "filters": filter_list,
                "configured": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "configured": False,
                "error": str(e),
            }

    def select_columns(
        self,
        view_id: str = "",
        columns: list[str] | None = None,
    ) -> dict[str, Any]:
        """Sütun seçer.

        Args:
            view_id: Görünüm ID.
            columns: Sütun listesi.

        Returns:
            Sütun bilgisi.
        """
        try:
            view = None
            for v in self._views:
                if v["view_id"] == view_id:
                    view = v
                    break

            if not view:
                return {
                    "selected": False,
                    "error": "view_not_found",
                }

            col_list = columns or []
            view["columns"] = col_list

            return {
                "view_id": view_id,
                "column_count": len(col_list),
                "columns": col_list,
                "selected": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "selected": False,
                "error": str(e),
            }

    def set_sort(
        self,
        view_id: str = "",
        sort_by: str = "",
        direction: str = "asc",
    ) -> dict[str, Any]:
        """Sıralama ayarlar.

        Args:
            view_id: Görünüm ID.
            sort_by: Sıralama alanı.
            direction: Yön (asc/desc).

        Returns:
            Sıralama bilgisi.
        """
        try:
            view = None
            for v in self._views:
                if v["view_id"] == view_id:
                    view = v
                    break

            if not view:
                return {
                    "set": False,
                    "error": "view_not_found",
                }

            view["sort"] = {
                "field": sort_by,
                "direction": direction,
            }

            return {
                "view_id": view_id,
                "sort_by": sort_by,
                "direction": direction,
                "set": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "set": False,
                "error": str(e),
            }

    def save_and_share(
        self,
        view_id: str = "",
        share: bool = False,
    ) -> dict[str, Any]:
        """Kaydeder ve paylaşır.

        Args:
            view_id: Görünüm ID.
            share: Paylaş.

        Returns:
            Kaydetme bilgisi.
        """
        try:
            view = None
            for v in self._views:
                if v["view_id"] == view_id:
                    view = v
                    break

            if not view:
                return {
                    "saved": False,
                    "error": "view_not_found",
                }

            view["shared"] = share

            share_url = (
                f"https://atlas.app/views/{view_id}"
                if share
                else None
            )

            return {
                "view_id": view_id,
                "name": view["name"],
                "shared": share,
                "share_url": share_url,
                "saved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "saved": False,
                "error": str(e),
            }
