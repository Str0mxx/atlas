"""ATLAS Arama Başlatıcı modülü.

Giden aramalar, Twilio/Vonage entegrasyonu,
arama zamanlama, yeniden deneme, acil aramalar.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class CallInitiator:
    """Arama başlatıcı.

    Giden aramaları yönetir.

    Attributes:
        _calls: Arama kayıtları.
        _providers: Sağlayıcı yapılandırmaları.
    """

    def __init__(
        self,
        default_provider: str = "twilio",
        max_retries: int = 3,
    ) -> None:
        """Başlatıcıyı oluşturur.

        Args:
            default_provider: Varsayılan sağlayıcı.
            max_retries: Maks yeniden deneme.
        """
        self._calls: list[dict[str, Any]] = []
        self._providers: dict[
            str, dict[str, Any]
        ] = {
            "twilio": {
                "enabled": True,
                "priority": 1,
            },
            "vonage": {
                "enabled": True,
                "priority": 2,
            },
        }
        self._default_provider = default_provider
        self._max_retries = max_retries
        self._counter = 0
        self._stats = {
            "calls_initiated": 0,
            "calls_completed": 0,
            "calls_failed": 0,
            "retries": 0,
            "emergency_calls": 0,
        }

        logger.info("CallInitiator baslatildi")

    def initiate_call(
        self,
        callee: str,
        caller: str = "system",
        provider: str | None = None,
        purpose: str = "general",
        priority: int = 5,
    ) -> dict[str, Any]:
        """Arama başlatır.

        Args:
            callee: Aranan numara/kişi.
            caller: Arayan.
            provider: Sağlayıcı.
            purpose: Arama amacı.
            priority: Öncelik.

        Returns:
            Arama bilgisi.
        """
        self._counter += 1
        cid = f"call_{self._counter}"
        used_provider = (
            provider or self._default_provider
        )

        call = {
            "call_id": cid,
            "callee": callee,
            "caller": caller,
            "provider": used_provider,
            "purpose": purpose,
            "priority": max(1, min(10, priority)),
            "direction": "outbound",
            "status": "ringing",
            "retries": 0,
            "initiated_at": time.time(),
            "ended_at": None,
        }
        self._calls.append(call)
        self._stats["calls_initiated"] += 1

        return call

    def complete_call(
        self,
        call_id: str,
        duration_seconds: int = 0,
    ) -> dict[str, Any]:
        """Aramayı tamamlar.

        Args:
            call_id: Arama ID.
            duration_seconds: Süre (saniye).

        Returns:
            Tamamlama bilgisi.
        """
        call = self._find_call(call_id)
        if not call:
            return {"error": "call_not_found"}

        call["status"] = "completed"
        call["duration"] = duration_seconds
        call["ended_at"] = time.time()
        self._stats["calls_completed"] += 1

        return {
            "call_id": call_id,
            "status": "completed",
            "duration": duration_seconds,
        }

    def fail_call(
        self,
        call_id: str,
        reason: str = "unknown",
    ) -> dict[str, Any]:
        """Aramayı başarısız olarak işaretler.

        Args:
            call_id: Arama ID.
            reason: Başarısızlık nedeni.

        Returns:
            Başarısızlık bilgisi.
        """
        call = self._find_call(call_id)
        if not call:
            return {"error": "call_not_found"}

        call["status"] = "failed"
        call["failure_reason"] = reason
        call["ended_at"] = time.time()
        self._stats["calls_failed"] += 1

        return {
            "call_id": call_id,
            "status": "failed",
            "reason": reason,
        }

    def retry_call(
        self,
        call_id: str,
    ) -> dict[str, Any]:
        """Aramayı yeniden dener.

        Args:
            call_id: Arama ID.

        Returns:
            Yeniden deneme bilgisi.
        """
        call = self._find_call(call_id)
        if not call:
            return {"error": "call_not_found"}

        if call["retries"] >= self._max_retries:
            return {
                "error": "max_retries_exceeded",
                "retries": call["retries"],
            }

        call["retries"] += 1
        call["status"] = "ringing"
        call["ended_at"] = None
        self._stats["retries"] += 1

        return {
            "call_id": call_id,
            "retry_count": call["retries"],
            "status": "ringing",
        }

    def emergency_call(
        self,
        callee: str,
        reason: str = "emergency",
    ) -> dict[str, Any]:
        """Acil arama başlatır.

        Args:
            callee: Aranan.
            reason: Acil durum nedeni.

        Returns:
            Arama bilgisi.
        """
        call = self.initiate_call(
            callee=callee,
            caller="emergency_system",
            purpose=reason,
            priority=10,
        )
        call["direction"] = "emergency"
        call["emergency"] = True
        self._stats["emergency_calls"] += 1

        return call

    def configure_provider(
        self,
        name: str,
        enabled: bool = True,
        priority: int = 1,
        config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Sağlayıcı yapılandırır.

        Args:
            name: Sağlayıcı adı.
            enabled: Etkin mi.
            priority: Öncelik.
            config: Yapılandırma.

        Returns:
            Yapılandırma bilgisi.
        """
        self._providers[name] = {
            "enabled": enabled,
            "priority": priority,
            "config": config or {},
        }
        return {
            "provider": name,
            "configured": True,
        }

    def _find_call(
        self,
        call_id: str,
    ) -> dict[str, Any] | None:
        """Arama bulur.

        Args:
            call_id: Arama ID.

        Returns:
            Arama veya None.
        """
        for call in self._calls:
            if call["call_id"] == call_id:
                return call
        return None

    def get_call(
        self,
        call_id: str,
    ) -> dict[str, Any]:
        """Arama detayı getirir.

        Args:
            call_id: Arama ID.

        Returns:
            Arama bilgisi.
        """
        call = self._find_call(call_id)
        if not call:
            return {"error": "call_not_found"}
        return dict(call)

    def get_active_calls(self) -> list[dict[str, Any]]:
        """Aktif aramaları getirir.

        Returns:
            Aktif arama listesi.
        """
        return [
            c for c in self._calls
            if c["status"] in (
                "ringing", "active",
            )
        ]

    def get_call_history(
        self,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Arama geçmişini getirir.

        Args:
            limit: Maks kayıt.

        Returns:
            Arama listesi.
        """
        return list(self._calls[-limit:])

    @property
    def call_count(self) -> int:
        """Toplam arama sayısı."""
        return self._stats["calls_initiated"]

    @property
    def active_call_count(self) -> int:
        """Aktif arama sayısı."""
        return len(self.get_active_calls())

    @property
    def provider_count(self) -> int:
        """Sağlayıcı sayısı."""
        return len(self._providers)
