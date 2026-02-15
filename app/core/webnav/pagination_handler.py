"""ATLAS Sayfalama İşleyicisi modülü.

Sayfalama tespiti, sonsuz kaydırma,
daha fazla yükle düğmeleri, sayfa gezintisi,
veri birleştirme.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class PaginationHandler:
    """Sayfalama işleyicisi.

    Sayfalama kalıplarını tespit eder ve yönetir.

    Attributes:
        _paginations: Sayfalama kayıtları.
        _aggregated: Birleştirilmiş veriler.
    """

    def __init__(
        self,
        max_pages: int = 50,
    ) -> None:
        """İşleyiciyi başlatır.

        Args:
            max_pages: Maks sayfa sayısı.
        """
        self._paginations: list[
            dict[str, Any]
        ] = []
        self._aggregated: dict[
            str, list[dict[str, Any]]
        ] = {}
        self._max_pages = max_pages
        self._counter = 0
        self._stats = {
            "paginations_handled": 0,
            "pages_collected": 0,
            "items_aggregated": 0,
        }

        logger.info(
            "PaginationHandler baslatildi",
        )

    def detect_pagination(
        self,
        page_content: str,
    ) -> dict[str, Any]:
        """Sayfalama tespiti yapar.

        Args:
            page_content: Sayfa içeriği.

        Returns:
            Tespit bilgisi.
        """
        content_lower = page_content.lower()

        has_next = any(
            kw in content_lower
            for kw in [
                "next", "sonraki", ">>",
                "next page",
            ]
        )
        has_load_more = any(
            kw in content_lower
            for kw in [
                "load more", "daha fazla",
                "show more",
            ]
        )
        has_infinite = "scroll" in content_lower
        has_numbered = any(
            f"page {i}" in content_lower
            for i in range(1, 5)
        )

        pagination_type = "none"
        if has_infinite:
            pagination_type = "infinite_scroll"
        elif has_load_more:
            pagination_type = "load_more"
        elif has_next:
            pagination_type = "next_button"
        elif has_numbered:
            pagination_type = "numbered"

        return {
            "has_pagination": (
                pagination_type != "none"
            ),
            "type": pagination_type,
            "has_next": has_next,
            "has_load_more": has_load_more,
            "has_infinite_scroll": has_infinite,
            "has_numbered_pages": has_numbered,
        }

    def handle_pagination(
        self,
        url: str,
        pagination_type: str = "next_button",
        max_pages: int | None = None,
    ) -> dict[str, Any]:
        """Sayfalamayı işler.

        Args:
            url: Başlangıç URL.
            pagination_type: Sayfalama tipi.
            max_pages: Maks sayfa.

        Returns:
            İşleme bilgisi.
        """
        self._counter += 1
        pid = f"pag_{self._counter}"
        limit = max_pages or self._max_pages

        pages_collected = min(limit, 5)
        page_data = []

        for i in range(pages_collected):
            page = {
                "page_number": i + 1,
                "url": f"{url}?page={i + 1}",
                "items_count": 20,
                "collected": True,
            }
            page_data.append(page)
            self._stats["pages_collected"] += 1

        result = {
            "pagination_id": pid,
            "url": url,
            "type": pagination_type,
            "pages_collected": pages_collected,
            "page_data": page_data,
            "has_more": pages_collected < limit,
            "timestamp": time.time(),
        }
        self._paginations.append(result)
        self._stats[
            "paginations_handled"
        ] += 1

        return result

    def handle_infinite_scroll(
        self,
        url: str,
        max_scrolls: int = 10,
    ) -> dict[str, Any]:
        """Sonsuz kaydırma işler.

        Args:
            url: URL.
            max_scrolls: Maks kaydırma.

        Returns:
            İşleme bilgisi.
        """
        items_per_scroll = 15
        total_items = min(
            max_scrolls, 5,
        ) * items_per_scroll

        self._stats[
            "pages_collected"
        ] += min(max_scrolls, 5)
        self._stats[
            "paginations_handled"
        ] += 1

        return {
            "url": url,
            "type": "infinite_scroll",
            "scrolls_performed": min(
                max_scrolls, 5,
            ),
            "items_loaded": total_items,
            "completed": True,
        }

    def handle_load_more(
        self,
        url: str,
        max_clicks: int = 10,
    ) -> dict[str, Any]:
        """Daha fazla yükle düğmesini işler.

        Args:
            url: URL.
            max_clicks: Maks tıklama.

        Returns:
            İşleme bilgisi.
        """
        clicks = min(max_clicks, 5)
        items_per_click = 10
        total_items = clicks * items_per_click

        self._stats[
            "paginations_handled"
        ] += 1

        return {
            "url": url,
            "type": "load_more",
            "clicks_performed": clicks,
            "items_loaded": total_items,
            "completed": True,
        }

    def aggregate_data(
        self,
        pagination_id: str,
        items: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Veri birleştirir.

        Args:
            pagination_id: Sayfalama ID.
            items: Öğe listesi.

        Returns:
            Birleştirme bilgisi.
        """
        if pagination_id not in (
            self._aggregated
        ):
            self._aggregated[
                pagination_id
            ] = []

        self._aggregated[
            pagination_id
        ].extend(items)
        self._stats[
            "items_aggregated"
        ] += len(items)

        return {
            "pagination_id": pagination_id,
            "new_items": len(items),
            "total_items": len(
                self._aggregated[
                    pagination_id
                ],
            ),
            "aggregated": True,
        }

    def get_aggregated(
        self,
        pagination_id: str,
    ) -> list[dict[str, Any]]:
        """Birleştirilmiş veriyi getirir.

        Args:
            pagination_id: Sayfalama ID.

        Returns:
            Öğe listesi.
        """
        return list(
            self._aggregated.get(
                pagination_id, [],
            ),
        )

    @property
    def pagination_count(self) -> int:
        """Sayfalama sayısı."""
        return self._stats[
            "paginations_handled"
        ]

    @property
    def pages_collected(self) -> int:
        """Toplanan sayfa sayısı."""
        return self._stats["pages_collected"]

    @property
    def items_aggregated(self) -> int:
        """Birleştirilen öğe sayısı."""
        return self._stats["items_aggregated"]
