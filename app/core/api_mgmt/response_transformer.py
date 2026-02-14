"""ATLAS Yanit Donusturucu modulu.

Format donusumu, alan filtreleme,
veri maskeleme, sayfalama
ve HATEOAS linkler.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class ResponseTransformer:
    """Yanit donusturucu.

    API yanitlarini donusturur
    ve zenginlestirir.

    Attributes:
        _masks: Maskeleme kurallari.
        _transforms: Donusum kurallari.
    """

    def __init__(self) -> None:
        """Yanit donusturucuyu baslatir."""
        self._masks: dict[str, str] = {}
        self._transforms: dict[
            str, dict[str, Any]
        ] = {}
        self._transformations = 0

        logger.info(
            "ResponseTransformer baslatildi",
        )

    def filter_fields(
        self,
        data: dict[str, Any],
        fields: list[str],
    ) -> dict[str, Any]:
        """Alanlari filtreler.

        Args:
            data: Kaynak veri.
            fields: Istenen alanlar.

        Returns:
            Filtrelenmis veri.
        """
        self._transformations += 1
        return {
            k: v for k, v in data.items()
            if k in fields
        }

    def exclude_fields(
        self,
        data: dict[str, Any],
        fields: list[str],
    ) -> dict[str, Any]:
        """Alanlari dislar.

        Args:
            data: Kaynak veri.
            fields: Dislanan alanlar.

        Returns:
            Filtrelenmis veri.
        """
        self._transformations += 1
        return {
            k: v for k, v in data.items()
            if k not in fields
        }

    def mask_field(
        self,
        value: str,
        visible_chars: int = 4,
        mask_char: str = "*",
    ) -> str:
        """Alani maskeler.

        Args:
            value: Deger.
            visible_chars: Gorunen karakter.
            mask_char: Maske karakteri.

        Returns:
            Maskelenmis deger.
        """
        if len(value) <= visible_chars:
            return mask_char * len(value)
        masked_len = len(value) - visible_chars
        return (
            mask_char * masked_len
            + value[-visible_chars:]
        )

    def mask_data(
        self,
        data: dict[str, Any],
        fields: list[str],
    ) -> dict[str, Any]:
        """Veri maskeler.

        Args:
            data: Kaynak veri.
            fields: Maskelenecek alanlar.

        Returns:
            Maskelenmis veri.
        """
        self._transformations += 1
        result = dict(data)
        for field in fields:
            if field in result:
                val = result[field]
                if isinstance(val, str):
                    result[field] = self.mask_field(
                        val,
                    )
        return result

    def paginate(
        self,
        items: list[Any],
        page: int = 1,
        page_size: int = 20,
        base_url: str = "",
    ) -> dict[str, Any]:
        """Sayfalama yapar.

        Args:
            items: Tam liste.
            page: Sayfa numarasi.
            page_size: Sayfa boyutu.
            base_url: Temel URL.

        Returns:
            Sayfalanmis yanit.
        """
        self._transformations += 1
        total = len(items)
        total_pages = max(
            1, (total + page_size - 1)
            // page_size,
        )
        page = max(1, min(page, total_pages))

        start = (page - 1) * page_size
        end = start + page_size
        page_items = items[start:end]

        result: dict[str, Any] = {
            "data": page_items,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_items": total,
                "total_pages": total_pages,
            },
        }

        # HATEOAS linkler
        if base_url:
            links: dict[str, str] = {
                "self": f"{base_url}?page={page}",
            }
            if page > 1:
                links["prev"] = (
                    f"{base_url}?page={page - 1}"
                )
            if page < total_pages:
                links["next"] = (
                    f"{base_url}?page={page + 1}"
                )
            links["first"] = (
                f"{base_url}?page=1"
            )
            links["last"] = (
                f"{base_url}?page={total_pages}"
            )
            result["_links"] = links

        return result

    def add_links(
        self,
        data: dict[str, Any],
        links: dict[str, str],
    ) -> dict[str, Any]:
        """HATEOAS link ekler.

        Args:
            data: Yanit verisi.
            links: Linkler.

        Returns:
            Linkli yanit.
        """
        self._transformations += 1
        result = dict(data)
        result["_links"] = links
        return result

    def rename_fields(
        self,
        data: dict[str, Any],
        mapping: dict[str, str],
    ) -> dict[str, Any]:
        """Alan adlarini degistirir.

        Args:
            data: Kaynak veri.
            mapping: Eski->yeni esleme.

        Returns:
            Yeniden adlandirilmis veri.
        """
        self._transformations += 1
        result: dict[str, Any] = {}
        for k, v in data.items():
            new_key = mapping.get(k, k)
            result[new_key] = v
        return result

    def wrap_response(
        self,
        data: Any,
        status: str = "success",
        message: str = "",
    ) -> dict[str, Any]:
        """Yaniti sarar.

        Args:
            data: Yanit verisi.
            status: Durum.
            message: Mesaj.

        Returns:
            Sarili yanit.
        """
        self._transformations += 1
        result: dict[str, Any] = {
            "status": status,
            "data": data,
        }
        if message:
            result["message"] = message
        return result

    def to_format(
        self,
        data: dict[str, Any],
        fmt: str = "json",
    ) -> dict[str, Any]:
        """Formata donusturur.

        Args:
            data: Veri.
            fmt: Hedef format.

        Returns:
            Donusturulmus veri.
        """
        self._transformations += 1
        return {
            "format": fmt,
            "data": data,
        }

    @property
    def transformation_count(self) -> int:
        """Donusum sayisi."""
        return self._transformations

    @property
    def mask_rule_count(self) -> int:
        """Maske kurali sayisi."""
        return len(self._masks)
