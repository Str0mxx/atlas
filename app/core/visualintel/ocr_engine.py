"""ATLAS OCR Motoru modülü.

Metin çıkarma, çok dilli OCR,
el yazısı tanıma, tablo çıkarma,
güven puanlama.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class OCREngine:
    """OCR motoru.

    Görüntülerden metin çıkarma sağlar.

    Attributes:
        _results: OCR sonuçları.
        _supported_langs: Desteklenen diller.
    """

    def __init__(self) -> None:
        """Motoru başlatır."""
        self._results: list[
            dict[str, Any]
        ] = []
        self._supported_langs = [
            "tr", "en", "de", "fr", "ar",
        ]
        self._stats = {
            "extractions_done": 0,
            "tables_extracted": 0,
        }

        logger.info(
            "OCREngine baslatildi",
        )

    def extract_text(
        self,
        image_id: str,
        language: str = "en",
    ) -> dict[str, Any]:
        """Metin çıkarır.

        Args:
            image_id: Görüntü kimliği.
            language: Dil.

        Returns:
            Çıkarma bilgisi.
        """
        supported = (
            language in self._supported_langs
        )

        text = (
            f"[OCR text from {image_id}]"
            if supported
            else ""
        )
        confidence = (
            0.92 if supported else 0.0
        )

        result = {
            "image_id": image_id,
            "language": language,
            "text": text,
            "confidence": confidence,
            "supported": supported,
            "timestamp": time.time(),
        }
        self._results.append(result)

        self._stats[
            "extractions_done"
        ] += 1

        return {
            "image_id": image_id,
            "text": text,
            "confidence": confidence,
            "language": language,
            "extracted": True,
        }

    def multi_language_ocr(
        self,
        image_id: str,
        languages: list[str]
        | None = None,
    ) -> dict[str, Any]:
        """Çok dilli OCR yapar.

        Args:
            image_id: Görüntü kimliği.
            languages: Dil listesi.

        Returns:
            Çok dilli OCR bilgisi.
        """
        languages = languages or [
            "en", "tr",
        ]

        results = []
        best_confidence = 0.0
        best_lang = ""

        for lang in languages:
            conf = (
                0.92
                if lang
                in self._supported_langs
                else 0.3
            )
            results.append({
                "language": lang,
                "confidence": conf,
            })
            if conf > best_confidence:
                best_confidence = conf
                best_lang = lang

        return {
            "image_id": image_id,
            "languages_tried": len(
                languages,
            ),
            "best_language": best_lang,
            "best_confidence": (
                best_confidence
            ),
            "results": results,
            "processed": True,
        }

    def recognize_handwriting(
        self,
        image_id: str,
        language: str = "en",
    ) -> dict[str, Any]:
        """El yazısı tanır.

        Args:
            image_id: Görüntü kimliği.
            language: Dil.

        Returns:
            Tanıma bilgisi.
        """
        confidence = 0.75

        return {
            "image_id": image_id,
            "text": (
                f"[Handwriting from "
                f"{image_id}]"
            ),
            "confidence": confidence,
            "language": language,
            "handwriting": True,
            "recognized": True,
        }

    def extract_table(
        self,
        image_id: str,
        expected_cols: int = 0,
    ) -> dict[str, Any]:
        """Tablo çıkarır.

        Args:
            image_id: Görüntü kimliği.
            expected_cols: Beklenen sütun.

        Returns:
            Tablo bilgisi.
        """
        cols = expected_cols or 3
        rows = 5

        table_data = []
        for r in range(rows):
            row = []
            for c in range(cols):
                row.append(
                    f"cell_{r}_{c}",
                )
            table_data.append(row)

        self._stats[
            "tables_extracted"
        ] += 1

        return {
            "image_id": image_id,
            "rows": rows,
            "cols": cols,
            "data": table_data,
            "confidence": 0.85,
            "extracted": True,
        }

    def get_confidence_score(
        self,
        image_id: str,
    ) -> dict[str, Any]:
        """Güven puanı sorgular.

        Args:
            image_id: Görüntü kimliği.

        Returns:
            Güven bilgisi.
        """
        matching = [
            r
            for r in self._results
            if r["image_id"] == image_id
        ]

        if not matching:
            return {
                "image_id": image_id,
                "found": False,
            }

        avg_conf = sum(
            r["confidence"]
            for r in matching
        ) / len(matching)

        if avg_conf >= 0.9:
            grade = "excellent"
        elif avg_conf >= 0.7:
            grade = "good"
        elif avg_conf >= 0.5:
            grade = "moderate"
        else:
            grade = "poor"

        return {
            "image_id": image_id,
            "avg_confidence": round(
                avg_conf, 3,
            ),
            "grade": grade,
            "samples": len(matching),
            "found": True,
        }

    @property
    def extraction_count(self) -> int:
        """Çıkarma sayısı."""
        return self._stats[
            "extractions_done"
        ]

    @property
    def table_count(self) -> int:
        """Tablo çıkarma sayısı."""
        return self._stats[
            "tables_extracted"
        ]
