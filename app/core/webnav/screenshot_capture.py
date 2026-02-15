"""ATLAS Ekran Görüntüsü modülü.

Tam sayfa yakalama, eleman yakalama,
viewport yakalama, açıklama desteği,
karşılaştırma.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class ScreenshotCapture:
    """Ekran görüntüsü yakalayıcı.

    Web sayfalarının ekran görüntülerini alır.

    Attributes:
        _captures: Yakalama geçmişi.
        _annotations: Açıklamalar.
    """

    def __init__(
        self,
        default_width: int = 1920,
        default_height: int = 1080,
    ) -> None:
        """Yakalayıcıyı başlatır.

        Args:
            default_width: Varsayılan genişlik.
            default_height: Varsayılan yükseklik.
        """
        self._captures: list[
            dict[str, Any]
        ] = []
        self._annotations: dict[
            str, list[dict[str, Any]]
        ] = {}
        self._default_width = default_width
        self._default_height = default_height
        self._counter = 0
        self._stats = {
            "full_page": 0,
            "element": 0,
            "viewport": 0,
            "comparisons": 0,
        }

        logger.info(
            "ScreenshotCapture baslatildi",
        )

    def capture_full_page(
        self,
        url: str,
        width: int | None = None,
    ) -> dict[str, Any]:
        """Tam sayfa yakalar.

        Args:
            url: Sayfa URL.
            width: Genişlik.

        Returns:
            Yakalama bilgisi.
        """
        self._counter += 1
        sid = f"ss_{self._counter}"
        w = width or self._default_width

        capture = {
            "screenshot_id": sid,
            "url": url,
            "type": "full_page",
            "width": w,
            "height": self._default_height * 3,
            "file_path": f"/tmp/{sid}.png",
            "file_size_kb": 450,
            "captured_at": time.time(),
        }
        self._captures.append(capture)
        self._stats["full_page"] += 1

        return capture

    def capture_element(
        self,
        url: str,
        selector: str,
    ) -> dict[str, Any]:
        """Eleman yakalar.

        Args:
            url: Sayfa URL.
            selector: CSS seçici.

        Returns:
            Yakalama bilgisi.
        """
        self._counter += 1
        sid = f"ss_{self._counter}"

        capture = {
            "screenshot_id": sid,
            "url": url,
            "type": "element",
            "selector": selector,
            "width": 400,
            "height": 200,
            "file_path": f"/tmp/{sid}.png",
            "file_size_kb": 50,
            "captured_at": time.time(),
        }
        self._captures.append(capture)
        self._stats["element"] += 1

        return capture

    def capture_viewport(
        self,
        url: str,
        width: int | None = None,
        height: int | None = None,
    ) -> dict[str, Any]:
        """Viewport yakalar.

        Args:
            url: Sayfa URL.
            width: Genişlik.
            height: Yükseklik.

        Returns:
            Yakalama bilgisi.
        """
        self._counter += 1
        sid = f"ss_{self._counter}"
        w = width or self._default_width
        h = height or self._default_height

        capture = {
            "screenshot_id": sid,
            "url": url,
            "type": "viewport",
            "width": w,
            "height": h,
            "file_path": f"/tmp/{sid}.png",
            "file_size_kb": 200,
            "captured_at": time.time(),
        }
        self._captures.append(capture)
        self._stats["viewport"] += 1

        return capture

    def annotate(
        self,
        screenshot_id: str,
        annotations: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Açıklama ekler.

        Args:
            screenshot_id: Görüntü ID.
            annotations: Açıklamalar.

        Returns:
            Ekleme bilgisi.
        """
        if screenshot_id not in (
            self._annotations
        ):
            self._annotations[
                screenshot_id
            ] = []

        self._annotations[
            screenshot_id
        ].extend(annotations)

        return {
            "screenshot_id": screenshot_id,
            "annotations_added": len(
                annotations,
            ),
            "total_annotations": len(
                self._annotations[
                    screenshot_id
                ],
            ),
        }

    def compare(
        self,
        screenshot_id_1: str,
        screenshot_id_2: str,
    ) -> dict[str, Any]:
        """Karşılaştırma yapar.

        Args:
            screenshot_id_1: İlk görüntü.
            screenshot_id_2: İkinci görüntü.

        Returns:
            Karşılaştırma bilgisi.
        """
        s1 = None
        s2 = None
        for c in self._captures:
            if c["screenshot_id"] == (
                screenshot_id_1
            ):
                s1 = c
            if c["screenshot_id"] == (
                screenshot_id_2
            ):
                s2 = c

        if not s1 or not s2:
            return {
                "error": "screenshot_not_found",
            }

        self._stats["comparisons"] += 1
        same_size = (
            s1["width"] == s2["width"]
            and s1["height"] == s2["height"]
        )

        return {
            "screenshot_1": screenshot_id_1,
            "screenshot_2": screenshot_id_2,
            "same_dimensions": same_size,
            "similarity_score": (
                0.95 if same_size else 0.5
            ),
            "compared": True,
        }

    def get_captures(
        self,
        capture_type: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Yakalamaları getirir.

        Args:
            capture_type: Tip filtresi.
            limit: Maks kayıt.

        Returns:
            Yakalama listesi.
        """
        results = self._captures
        if capture_type:
            results = [
                c for c in results
                if c["type"] == capture_type
            ]
        return list(results[-limit:])

    @property
    def capture_count(self) -> int:
        """Toplam yakalama sayısı."""
        return len(self._captures)

    @property
    def comparison_count(self) -> int:
        """Karşılaştırma sayısı."""
        return self._stats["comparisons"]
