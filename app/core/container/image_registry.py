"""ATLAS Imaj Kayit Defteri modulu.

Imaj push/pull, etiket yonetimi,
surum takibi, guvenlik taramasi
ve temizlik politikalari.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class ImageRegistry:
    """Imaj kayit defteri.

    Konteyner imajlarini yonetir.

    Attributes:
        _images: Kayitli imajlar.
        _tags: Etiket haritasi.
    """

    def __init__(
        self,
        registry_url: str = "localhost:5000",
    ) -> None:
        """Kayit defterini baslatir.

        Args:
            registry_url: Kayit defteri URL.
        """
        self._registry_url = registry_url
        self._images: dict[
            str, dict[str, Any]
        ] = {}
        self._tags: dict[str, list[str]] = {}
        self._vulnerabilities: dict[
            str, list[dict[str, Any]]
        ] = {}
        self._cleanup_policies: dict[
            str, dict[str, Any]
        ] = {}
        self._stats = {
            "pushes": 0,
            "pulls": 0,
            "scans": 0,
            "cleaned": 0,
        }

        logger.info(
            "ImageRegistry baslatildi: %s",
            registry_url,
        )

    def push(
        self,
        name: str,
        tag: str = "latest",
        size_mb: int = 0,
        layers: int = 0,
    ) -> dict[str, Any]:
        """Imaj push eder.

        Args:
            name: Imaj adi.
            tag: Etiket.
            size_mb: Boyut.
            layers: Katman sayisi.

        Returns:
            Push bilgisi.
        """
        key = f"{name}:{tag}"
        self._images[key] = {
            "name": name,
            "tag": tag,
            "size_mb": size_mb,
            "layers": layers,
            "digest": f"sha256:{hash(key) % (10**12):012x}",
            "pushed_at": time.time(),
        }

        self._tags.setdefault(name, [])
        if tag not in self._tags[name]:
            self._tags[name].append(tag)

        self._stats["pushes"] += 1
        return {
            "image": key,
            "digest": self._images[key]["digest"],
            "status": "pushed",
        }

    def pull(
        self,
        name: str,
        tag: str = "latest",
    ) -> dict[str, Any] | None:
        """Imaj pull eder.

        Args:
            name: Imaj adi.
            tag: Etiket.

        Returns:
            Imaj bilgisi veya None.
        """
        key = f"{name}:{tag}"
        image = self._images.get(key)
        if not image:
            return None

        self._stats["pulls"] += 1
        return {
            **image,
            "status": "pulled",
        }

    def tag(
        self,
        name: str,
        source_tag: str,
        target_tag: str,
    ) -> dict[str, Any] | None:
        """Imaj etiketler.

        Args:
            name: Imaj adi.
            source_tag: Kaynak etiket.
            target_tag: Hedef etiket.

        Returns:
            Etiket bilgisi veya None.
        """
        src_key = f"{name}:{source_tag}"
        if src_key not in self._images:
            return None

        # Yeni etiketi kaydet
        tgt_key = f"{name}:{target_tag}"
        self._images[tgt_key] = {
            **self._images[src_key],
            "tag": target_tag,
        }

        self._tags.setdefault(name, [])
        if target_tag not in self._tags[name]:
            self._tags[name].append(target_tag)

        return {
            "image": name,
            "source": source_tag,
            "target": target_tag,
        }

    def get_tags(
        self,
        name: str,
    ) -> list[str]:
        """Imaj etiketlerini getirir.

        Args:
            name: Imaj adi.

        Returns:
            Etiket listesi.
        """
        return list(
            self._tags.get(name, []),
        )

    def get_image(
        self,
        name: str,
        tag: str = "latest",
    ) -> dict[str, Any] | None:
        """Imaj bilgisini getirir.

        Args:
            name: Imaj adi.
            tag: Etiket.

        Returns:
            Imaj bilgisi veya None.
        """
        return self._images.get(
            f"{name}:{tag}",
        )

    def delete(
        self,
        name: str,
        tag: str = "latest",
    ) -> bool:
        """Imaj siler.

        Args:
            name: Imaj adi.
            tag: Etiket.

        Returns:
            Basarili mi.
        """
        key = f"{name}:{tag}"
        if key not in self._images:
            return False

        del self._images[key]
        if name in self._tags:
            tags = self._tags[name]
            if tag in tags:
                tags.remove(tag)
            if not tags:
                del self._tags[name]

        return True

    def scan(
        self,
        name: str,
        tag: str = "latest",
    ) -> dict[str, Any]:
        """Guvenlik taramasi yapar.

        Args:
            name: Imaj adi.
            tag: Etiket.

        Returns:
            Tarama sonucu.
        """
        key = f"{name}:{tag}"
        self._stats["scans"] += 1

        if key not in self._images:
            return {
                "image": key,
                "status": "not_found",
                "vulnerabilities": [],
            }

        # Simule tarama
        vulns = self._vulnerabilities.get(key, [])
        severity_counts = {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
        }
        for v in vulns:
            sev = v.get("severity", "low")
            severity_counts[sev] = (
                severity_counts.get(sev, 0) + 1
            )

        return {
            "image": key,
            "status": "scanned",
            "total_vulnerabilities": len(vulns),
            "severity": severity_counts,
            "clean": len(vulns) == 0,
            "scanned_at": time.time(),
        }

    def add_vulnerability(
        self,
        name: str,
        tag: str,
        cve_id: str,
        severity: str = "medium",
        description: str = "",
    ) -> None:
        """Guvenlik acigi ekler (test icin).

        Args:
            name: Imaj adi.
            tag: Etiket.
            cve_id: CVE ID.
            severity: Ciddiyet.
            description: Aciklama.
        """
        key = f"{name}:{tag}"
        self._vulnerabilities.setdefault(key, [])
        self._vulnerabilities[key].append({
            "cve_id": cve_id,
            "severity": severity,
            "description": description,
        })

    def set_cleanup_policy(
        self,
        name: str,
        max_tags: int = 10,
        max_age_days: int = 90,
    ) -> dict[str, Any]:
        """Temizlik politikasi ayarlar.

        Args:
            name: Imaj adi.
            max_tags: Maks etiket.
            max_age_days: Maks yas (gun).

        Returns:
            Politika bilgisi.
        """
        self._cleanup_policies[name] = {
            "max_tags": max_tags,
            "max_age_days": max_age_days,
            "created_at": time.time(),
        }
        return {
            "image": name,
            "max_tags": max_tags,
            "max_age_days": max_age_days,
        }

    def run_cleanup(
        self,
        name: str,
    ) -> dict[str, Any]:
        """Temizlik calistirir.

        Args:
            name: Imaj adi.

        Returns:
            Temizlik sonucu.
        """
        policy = self._cleanup_policies.get(name)
        if not policy:
            return {"cleaned": 0, "reason": "no_policy"}

        tags = self._tags.get(name, [])
        max_tags = policy["max_tags"]
        removed = 0

        if len(tags) > max_tags:
            to_remove = tags[:-max_tags]
            for t in to_remove:
                if self.delete(name, t):
                    removed += 1

        self._stats["cleaned"] += removed
        return {
            "image": name,
            "cleaned": removed,
            "remaining": len(
                self._tags.get(name, []),
            ),
        }

    def list_images(self) -> list[str]:
        """Tum imajlari listeler.

        Returns:
            Imaj listesi.
        """
        return list(self._images.keys())

    @property
    def image_count(self) -> int:
        """Imaj sayisi."""
        return len(self._images)

    @property
    def tag_count(self) -> int:
        """Toplam etiket sayisi."""
        return sum(
            len(t) for t in self._tags.values()
        )

    @property
    def push_count(self) -> int:
        """Push sayisi."""
        return self._stats["pushes"]

    @property
    def pull_count(self) -> int:
        """Pull sayisi."""
        return self._stats["pulls"]

    @property
    def scan_count(self) -> int:
        """Tarama sayisi."""
        return self._stats["scans"]
