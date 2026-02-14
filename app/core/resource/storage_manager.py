"""ATLAS Depolama Yoneticisi modulu.

Disk alani izleme, dosya temizligi,
arsiv yonetimi, kota zorlama
ve sikistirma.
"""

import logging
from typing import Any

from app.models.resource import ResourceStatus

logger = logging.getLogger(__name__)


class StorageManager:
    """Depolama yoneticisi.

    Disk ve dosya kaynaklarini yonetir.

    Attributes:
        _volumes: Disk bolumleri.
        _files: Dosya kayitlari.
        _archives: Arsiv kayitlari.
        _quotas: Kota ayarlari.
    """

    def __init__(
        self,
        threshold: float = 0.8,
    ) -> None:
        """Depolama yoneticisini baslatir.

        Args:
            threshold: Uyari esigi.
        """
        self._volumes: dict[str, dict[str, Any]] = {}
        self._files: dict[str, dict[str, Any]] = {}
        self._archives: list[dict[str, Any]] = []
        self._quotas: dict[str, float] = {}
        self._threshold = max(0.1, min(1.0, threshold))
        self._cleaned_bytes = 0.0

        logger.info("StorageManager baslatildi")

    def add_volume(
        self,
        name: str,
        total_gb: float,
        used_gb: float = 0.0,
    ) -> dict[str, Any]:
        """Disk bolumu ekler.

        Args:
            name: Bolum adi.
            total_gb: Toplam alan (GB).
            used_gb: Kullanilan alan (GB).

        Returns:
            Bolum bilgisi.
        """
        vol = {
            "name": name,
            "total_gb": max(0.1, total_gb),
            "used_gb": max(0.0, min(total_gb, used_gb)),
        }
        self._volumes[name] = vol
        return vol

    def check_volume(self, name: str) -> ResourceStatus:
        """Bolum durumunu kontrol eder.

        Args:
            name: Bolum adi.

        Returns:
            Kaynak durumu.
        """
        vol = self._volumes.get(name)
        if not vol:
            return ResourceStatus.NORMAL
        ratio = vol["used_gb"] / vol["total_gb"]
        if ratio >= 0.95:
            return ResourceStatus.CRITICAL
        if ratio >= self._threshold:
            return ResourceStatus.WARNING
        return ResourceStatus.NORMAL

    def register_file(
        self,
        path: str,
        size_mb: float,
        age_days: int = 0,
        category: str = "data",
    ) -> dict[str, Any]:
        """Dosya kaydeder.

        Args:
            path: Dosya yolu.
            size_mb: Boyut (MB).
            age_days: Yas (gun).
            category: Kategori.

        Returns:
            Dosya bilgisi.
        """
        f = {
            "path": path,
            "size_mb": size_mb,
            "age_days": age_days,
            "category": category,
        }
        self._files[path] = f
        return f

    def cleanup_old_files(
        self,
        max_age_days: int = 30,
    ) -> dict[str, Any]:
        """Eski dosyalari temizler.

        Args:
            max_age_days: Maks yas (gun).

        Returns:
            Temizlik sonucu.
        """
        to_remove = [
            p for p, f in self._files.items()
            if f["age_days"] > max_age_days
        ]
        freed = sum(
            self._files[p]["size_mb"] for p in to_remove
        )
        for p in to_remove:
            del self._files[p]

        self._cleaned_bytes += freed
        return {
            "removed_count": len(to_remove),
            "freed_mb": freed,
        }

    def archive_files(
        self,
        category: str,
    ) -> dict[str, Any]:
        """Dosyalari arsivler.

        Args:
            category: Arsivlenecek kategori.

        Returns:
            Arsiv sonucu.
        """
        to_archive = [
            p for p, f in self._files.items()
            if f["category"] == category
        ]
        total_mb = sum(
            self._files[p]["size_mb"] for p in to_archive
        )
        # Sikistirma simulasyonu: %50 tasarruf
        compressed_mb = total_mb * 0.5

        archive = {
            "category": category,
            "file_count": len(to_archive),
            "original_mb": total_mb,
            "compressed_mb": compressed_mb,
            "savings_mb": total_mb - compressed_mb,
        }
        self._archives.append(archive)

        for p in to_archive:
            del self._files[p]

        return archive

    def set_quota(
        self,
        name: str,
        max_gb: float,
    ) -> None:
        """Kota ayarlar.

        Args:
            name: Kullanici/servis adi.
            max_gb: Maks alan (GB).
        """
        self._quotas[name] = max(0.0, max_gb)

    def check_quota(
        self,
        name: str,
        current_gb: float,
    ) -> dict[str, Any]:
        """Kota kontrol eder.

        Args:
            name: Kullanici/servis.
            current_gb: Mevcut kullanim (GB).

        Returns:
            Kontrol sonucu.
        """
        limit = self._quotas.get(name)
        if limit is None:
            return {"within_quota": True, "no_quota": True}

        return {
            "within_quota": current_gb <= limit,
            "used_gb": current_gb,
            "limit_gb": limit,
            "remaining_gb": max(0.0, limit - current_gb),
        }

    def compress_estimate(
        self,
        path: str,
        ratio: float = 0.5,
    ) -> dict[str, Any] | None:
        """Sikistirma tahmini yapar.

        Args:
            path: Dosya yolu.
            ratio: Sikistirma orani.

        Returns:
            Tahmin bilgisi veya None.
        """
        f = self._files.get(path)
        if not f:
            return None
        compressed = f["size_mb"] * ratio
        return {
            "path": path,
            "original_mb": f["size_mb"],
            "estimated_mb": compressed,
            "savings_mb": f["size_mb"] - compressed,
        }

    @property
    def volume_count(self) -> int:
        """Bolum sayisi."""
        return len(self._volumes)

    @property
    def file_count(self) -> int:
        """Dosya sayisi."""
        return len(self._files)

    @property
    def archive_count(self) -> int:
        """Arsiv sayisi."""
        return len(self._archives)

    @property
    def cleaned_mb(self) -> float:
        """Temizlenen alan (MB)."""
        return self._cleaned_bytes
