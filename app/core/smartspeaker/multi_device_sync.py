"""
Multi-Device Sync - Çoklu cihaz senkronizasyon modülü.

Bu modül cihaz kayıt, durum senkronizasyonu, handoff ve tercih yönetimi
sağlar.
"""

import logging
import time
from typing import Any, Optional

logger = logging.getLogger(__name__)


class MultiDeviceSync:
    """Çoklu cihaz senkronizasyon yönetim sınıfı."""

    def __init__(self) -> None:
        """MultiDeviceSync başlatıcı."""
        self._devices: dict[str, dict] = {}
        self._state: dict[str, dict] = {}
        self._preferences: dict[str, dict] = {}
        self._stats = {"devices_registered": 0, "syncs_done": 0}
        logger.info("MultiDeviceSync başlatıldı")

    @property
    def device_count(self) -> int:
        """Kayıtlı cihaz sayısını döndürür."""
        return self._stats["devices_registered"]

    @property
    def sync_count(self) -> int:
        """Yapılan senkronizasyon sayısını döndürür."""
        return self._stats["syncs_done"]

    def register_device(
        self,
        device_id: str,
        name: str,
        platform: str = "alexa",
        location: str = ""
    ) -> dict[str, Any]:
        """
        Yeni bir cihaz kaydeder.

        Args:
            device_id: Cihaz benzersiz kimliği
            name: Cihaz adı
            platform: Platform (alexa, google, siri)
            location: Cihaz konumu

        Returns:
            Cihaz kayıt sonucu
        """
        self._devices[device_id] = {
            "name": name,
            "platform": platform,
            "location": location,
            "registered_at": time.time()
        }

        self._state[device_id] = {}
        self._stats["devices_registered"] += 1

        logger.info(
            f"Cihaz kaydedildi: {device_id} - {name} ({platform})"
        )

        return {
            "device_id": device_id,
            "name": name,
            "platform": platform,
            "registered": True
        }

    def sync_state(
        self,
        source_device_id: str,
        target_device_id: str,
        state_data: Optional[dict] = None
    ) -> dict[str, Any]:
        """
        Cihazlar arası durum senkronizasyonu yapar.

        Args:
            source_device_id: Kaynak cihaz kimliği
            target_device_id: Hedef cihaz kimliği
            state_data: Senkronize edilecek durum verisi

        Returns:
            Senkronizasyon sonucu
        """
        if source_device_id not in self._devices:
            logger.warning(f"Kaynak cihaz bulunamadı: {source_device_id}")
            return {"found": False}

        if target_device_id not in self._devices:
            logger.warning(f"Hedef cihaz bulunamadı: {target_device_id}")
            return {"found": False}

        if state_data is None:
            state_data = {}

        # Durumu hedef cihaza kopyala
        if target_device_id not in self._state:
            self._state[target_device_id] = {}

        self._state[target_device_id].update(state_data)
        self._stats["syncs_done"] += 1

        logger.info(
            f"Durum senkronize edildi: {source_device_id} -> "
            f"{target_device_id} ({len(state_data)} key)"
        )

        return {
            "source": source_device_id,
            "target": target_device_id,
            "keys_synced": len(state_data),
            "synced": True
        }

    def handoff(
        self,
        source_device_id: str,
        target_device_id: str,
        context: Optional[dict] = None
    ) -> dict[str, Any]:
        """
        Cihazlar arası context handoff yapar.

        Args:
            source_device_id: Kaynak cihaz kimliği
            target_device_id: Hedef cihaz kimliği
            context: Transfer edilecek context

        Returns:
            Handoff sonucu
        """
        if source_device_id not in self._devices:
            logger.warning(f"Kaynak cihaz bulunamadı: {source_device_id}")
            return {"found": False}

        if target_device_id not in self._devices:
            logger.warning(f"Hedef cihaz bulunamadı: {target_device_id}")
            return {"found": False}

        context_transferred = bool(context)

        logger.info(
            f"Handoff yapıldı: {source_device_id} -> {target_device_id} "
            f"(context: {context_transferred})"
        )

        return {
            "source": source_device_id,
            "target": target_device_id,
            "context_transferred": context_transferred,
            "handoff": True
        }

    def sync_preferences(
        self,
        device_id: str,
        preferences: Optional[dict] = None
    ) -> dict[str, Any]:
        """
        Cihaz tercihlerini senkronize eder.

        Args:
            device_id: Cihaz kimliği
            preferences: Tercih verileri

        Returns:
            Tercih senkronizasyon sonucu
        """
        if device_id not in self._devices:
            logger.warning(f"Cihaz bulunamadı: {device_id}")
            return {"found": False}

        if preferences is None:
            preferences = {}

        if device_id not in self._preferences:
            self._preferences[device_id] = {}

        self._preferences[device_id].update(preferences)

        logger.info(
            f"Tercihler senkronize edildi: {device_id} "
            f"({len(preferences)} tercih)"
        )

        return {
            "device_id": device_id,
            "preferences_synced": len(preferences),
            "synced": True
        }

    def resolve_conflict(
        self,
        device_id_a: str,
        device_id_b: str,
        strategy: str = "latest"
    ) -> dict[str, Any]:
        """
        Cihazlar arası çakışmaları çözümler.

        Args:
            device_id_a: Birinci cihaz kimliği
            device_id_b: İkinci cihaz kimliği
            strategy: Çözümleme stratejisi (latest, first)

        Returns:
            Çakışma çözümleme sonucu
        """
        winner = device_id_a if strategy == "latest" else device_id_b
        loser = device_id_b if winner == device_id_a else device_id_a

        logger.info(
            f"Çakışma çözüldü: kazanan={winner}, kaybeden={loser} "
            f"(strateji: {strategy})"
        )

        return {
            "winner": winner,
            "loser": loser,
            "strategy": strategy,
            "resolved": True
        }
