"""ATLAS Yanit Sikistirici modulu.

Gzip sikistirma, brotli sikistirma,
secimli sikistirma, acma
ve boyut takibi.
"""

import logging
import zlib
from typing import Any

from app.models.caching import CompressionType

logger = logging.getLogger(__name__)


class ResponseCompressor:
    """Yanit sikistirici.

    Yanit verilerini sikistirir
    ve boyut tasarrufu saglar.

    Attributes:
        _stats: Sikistirma istatistikleri.
        _threshold: Min sikistirma boyutu.
    """

    def __init__(
        self,
        threshold: int = 1024,
        default_type: CompressionType = CompressionType.GZIP,
    ) -> None:
        """Yanit sikistiricisini baslatir.

        Args:
            threshold: Min boyut (byte).
            default_type: Varsayilan tur.
        """
        self._threshold = threshold
        self._default_type = default_type
        self._total_original = 0
        self._total_compressed = 0
        self._compressions = 0
        self._decompressions = 0

        logger.info(
            "ResponseCompressor baslatildi",
        )

    def compress(
        self,
        data: bytes,
        compression_type: CompressionType | None = None,
    ) -> dict[str, Any]:
        """Veri sikistirir.

        Args:
            data: Ham veri.
            compression_type: Sikistirma turu.

        Returns:
            Sikistirma sonucu.
        """
        ct = compression_type or self._default_type
        original_size = len(data)

        # Esik altindaysa sikistirma
        if original_size < self._threshold:
            return {
                "data": data,
                "compressed": False,
                "type": CompressionType.NONE.value,
                "original_size": original_size,
                "compressed_size": original_size,
                "ratio": 1.0,
            }

        if ct == CompressionType.GZIP:
            compressed = zlib.compress(
                data, level=6,
            )
        elif ct == CompressionType.ZLIB:
            compressed = zlib.compress(
                data, level=9,
            )
        elif ct == CompressionType.BROTLI:
            # Brotli simulasyonu (zlib ile)
            compressed = zlib.compress(
                data, level=9,
            )
        else:
            return {
                "data": data,
                "compressed": False,
                "type": CompressionType.NONE.value,
                "original_size": original_size,
                "compressed_size": original_size,
                "ratio": 1.0,
            }

        compressed_size = len(compressed)
        self._total_original += original_size
        self._total_compressed += compressed_size
        self._compressions += 1

        ratio = round(
            compressed_size / max(1, original_size),
            3,
        )

        return {
            "data": compressed,
            "compressed": True,
            "type": ct.value,
            "original_size": original_size,
            "compressed_size": compressed_size,
            "ratio": ratio,
        }

    def decompress(
        self,
        data: bytes,
        compression_type: CompressionType = CompressionType.GZIP,
    ) -> dict[str, Any]:
        """Veri acar.

        Args:
            data: Sikistirilmis veri.
            compression_type: Sikistirma turu.

        Returns:
            Acma sonucu.
        """
        try:
            decompressed = zlib.decompress(data)
            self._decompressions += 1
            return {
                "data": decompressed,
                "success": True,
                "original_size": len(data),
                "decompressed_size": len(
                    decompressed,
                ),
            }
        except zlib.error as e:
            return {
                "data": data,
                "success": False,
                "error": str(e),
            }

    def should_compress(
        self,
        data: bytes,
    ) -> bool:
        """Sikistirmali mi kontrol eder.

        Args:
            data: Veri.

        Returns:
            Sikistirmali ise True.
        """
        return len(data) >= self._threshold

    def get_stats(self) -> dict[str, Any]:
        """Istatistik getirir.

        Returns:
            Istatistik.
        """
        ratio = (
            round(
                self._total_compressed
                / max(1, self._total_original),
                3,
            )
            if self._total_original > 0
            else 0.0
        )
        savings = (
            self._total_original
            - self._total_compressed
        )

        return {
            "compressions": self._compressions,
            "decompressions": self._decompressions,
            "total_original": self._total_original,
            "total_compressed": (
                self._total_compressed
            ),
            "ratio": ratio,
            "savings_bytes": savings,
        }

    @property
    def compression_count(self) -> int:
        """Sikistirma sayisi."""
        return self._compressions

    @property
    def decompression_count(self) -> int:
        """Acma sayisi."""
        return self._decompressions

    @property
    def compression_ratio(self) -> float:
        """Sikistirma orani."""
        if self._total_original == 0:
            return 0.0
        return round(
            self._total_compressed
            / self._total_original,
            3,
        )

    @property
    def total_savings(self) -> int:
        """Toplam tasarruf (byte)."""
        return (
            self._total_original
            - self._total_compressed
        )
