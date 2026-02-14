"""ATLAS Veri Yukleyici modulu.

Veritabani, dosya, API cikislarina
veri yukleme, toplu ve artimsal
yukleme islemleri.
"""

import logging
import time
from typing import Any

from app.models.pipeline import SourceType

logger = logging.getLogger(__name__)


class DataLoader:
    """Veri yukleyici.

    Donusturulmus verileri hedef
    sistemlere yukler.

    Attributes:
        _targets: Hedef sistemler.
        _loads: Yukleme gecmisi.
    """

    def __init__(
        self,
        default_batch_size: int = 100,
    ) -> None:
        """Veri yukleyiciyi baslatir.

        Args:
            default_batch_size: Varsayilan parti boyutu.
        """
        self._targets: dict[str, dict[str, Any]] = {}
        self._loads: list[dict[str, Any]] = []
        self._default_batch_size = default_batch_size

        logger.info("DataLoader baslatildi")

    def register_target(
        self,
        name: str,
        target_type: SourceType,
        config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Hedef kaydeder.

        Args:
            name: Hedef adi.
            target_type: Hedef turu.
            config: Yapilandirma.

        Returns:
            Hedef bilgisi.
        """
        target = {
            "name": name,
            "type": target_type.value,
            "config": config or {},
            "enabled": True,
        }
        self._targets[name] = target
        return target

    def load(
        self,
        target_name: str,
        data: list[dict[str, Any]],
        mode: str = "append",
    ) -> dict[str, Any]:
        """Veri yukler.

        Args:
            target_name: Hedef adi.
            data: Veri.
            mode: Yukleme modu (append, replace,
                upsert).

        Returns:
            Yukleme sonucu.
        """
        target = self._targets.get(target_name)
        if not target or not target["enabled"]:
            return {
                "success": False,
                "target": target_name,
                "reason": "target_not_found",
                "loaded": 0,
            }

        start = time.time()
        loaded = len(data)
        duration = time.time() - start

        result = {
            "success": True,
            "target": target_name,
            "type": target["type"],
            "mode": mode,
            "loaded": loaded,
            "duration": round(duration, 4),
        }
        self._loads.append(result)

        logger.info(
            "Veri yuklendi: %s (%d kayit, %s)",
            target_name, loaded, mode,
        )
        return result

    def load_batch(
        self,
        target_name: str,
        data: list[dict[str, Any]],
        batch_size: int = 0,
    ) -> dict[str, Any]:
        """Toplu veri yukler.

        Args:
            target_name: Hedef adi.
            data: Veri.
            batch_size: Parti boyutu.

        Returns:
            Yukleme sonucu.
        """
        size = batch_size or self._default_batch_size
        batches: list[list[dict[str, Any]]] = []
        for i in range(0, len(data), size):
            batches.append(data[i : i + size])

        total_loaded = 0
        for batch in batches:
            result = self.load(
                target_name, batch, "append",
            )
            if result["success"]:
                total_loaded += result["loaded"]

        return {
            "success": True,
            "target": target_name,
            "total_loaded": total_loaded,
            "batch_count": len(batches),
            "batch_size": size,
        }

    def load_incremental(
        self,
        target_name: str,
        data: list[dict[str, Any]],
        key_field: str = "id",
    ) -> dict[str, Any]:
        """Artimsal veri yukler.

        Args:
            target_name: Hedef adi.
            data: Veri.
            key_field: Anahtar alan.

        Returns:
            Yukleme sonucu.
        """
        result = self.load(
            target_name, data, "upsert",
        )
        result["incremental"] = True
        result["key_field"] = key_field
        return result

    def enable_target(self, name: str) -> bool:
        """Hedef aktif eder.

        Args:
            name: Hedef adi.

        Returns:
            Basarili ise True.
        """
        target = self._targets.get(name)
        if target:
            target["enabled"] = True
            return True
        return False

    def disable_target(self, name: str) -> bool:
        """Hedef devre disi birakir.

        Args:
            name: Hedef adi.

        Returns:
            Basarili ise True.
        """
        target = self._targets.get(name)
        if target:
            target["enabled"] = False
            return True
        return False

    def remove_target(self, name: str) -> bool:
        """Hedef kaldirir.

        Args:
            name: Hedef adi.

        Returns:
            Basarili ise True.
        """
        if name in self._targets:
            del self._targets[name]
            return True
        return False

    @property
    def target_count(self) -> int:
        """Hedef sayisi."""
        return len(self._targets)

    @property
    def load_count(self) -> int:
        """Yukleme sayisi."""
        return len(self._loads)

    @property
    def total_loaded(self) -> int:
        """Toplam yuklenen kayit."""
        return sum(
            l["loaded"]
            for l in self._loads
            if l.get("success")
        )
