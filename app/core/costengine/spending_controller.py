"""ATLAS Harcama Kontrolcusu modulu.

Limit durdurma, yuksek maliyet onay,
acil durdurma, override, bildirim.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class SpendingController:
    """Harcama kontrolcusu.

    Harcamalari kontrol eder ve sinirlar.

    Attributes:
        _limits: Harcama limitleri.
        _pending: Onay bekleyen islemler.
    """

    def __init__(
        self,
        pause_on_exceed: bool = True,
        require_approval_above: float = 50.0,
    ) -> None:
        """Harcama kontrolcusunu baslatir.

        Args:
            pause_on_exceed: Limit asiminda durdur.
            require_approval_above: Onay esigi.
        """
        self._limits: dict[
            str, dict[str, Any]
        ] = {}
        self._pending: dict[
            str, dict[str, Any]
        ] = {}
        self._overrides: dict[
            str, dict[str, Any]
        ] = {}
        self._history: list[
            dict[str, Any]
        ] = []
        self._paused = False
        self._emergency_stop = False
        self._pause_on_exceed = pause_on_exceed
        self._approval_threshold = (
            require_approval_above
        )
        self._request_counter = 0
        self._stats = {
            "checks": 0,
            "blocked": 0,
            "approved": 0,
        }

        logger.info(
            "SpendingController baslatildi",
        )

    def set_limit(
        self,
        limit_id: str,
        max_amount: float,
        period: str = "daily",
    ) -> dict[str, Any]:
        """Harcama limiti ayarlar.

        Args:
            limit_id: Limit ID.
            max_amount: Maksimum miktar.
            period: Donem.

        Returns:
            Ayarlama bilgisi.
        """
        self._limits[limit_id] = {
            "limit_id": limit_id,
            "max_amount": max_amount,
            "period": period,
            "current": 0.0,
            "set_at": time.time(),
        }

        return {
            "limit_id": limit_id,
            "max_amount": max_amount,
            "set": True,
        }

    def check_spending(
        self,
        amount: float,
        context: str = "",
        limit_id: str | None = None,
    ) -> dict[str, Any]:
        """Harcama kontrolu yapar.

        Args:
            amount: Miktar.
            context: Baglam.
            limit_id: Limit ID.

        Returns:
            Kontrol sonucu.
        """
        self._stats["checks"] += 1

        # Acil durdurma
        if self._emergency_stop:
            self._stats["blocked"] += 1
            return {
                "action": "block",
                "reason": "emergency_stop",
                "amount": amount,
            }

        # Duraklatma
        if self._paused:
            self._stats["blocked"] += 1
            return {
                "action": "pause",
                "reason": "spending_paused",
                "amount": amount,
            }

        # Onay esigi
        if amount > self._approval_threshold:
            self._request_counter += 1
            request_id = (
                f"req_{int(time.time())}"
                f"_{self._request_counter}"
            )
            self._pending[request_id] = {
                "request_id": request_id,
                "amount": amount,
                "context": context,
                "status": "pending",
                "created_at": time.time(),
            }
            return {
                "action": "approve",
                "reason": "above_threshold",
                "amount": amount,
                "request_id": request_id,
                "threshold": (
                    self._approval_threshold
                ),
            }

        # Limit kontrolu
        if limit_id and limit_id in self._limits:
            limit = self._limits[limit_id]
            remaining = (
                limit["max_amount"]
                - limit["current"]
            )
            if amount > remaining:
                if self._pause_on_exceed:
                    self._stats["blocked"] += 1
                    return {
                        "action": "block",
                        "reason": "limit_exceeded",
                        "amount": amount,
                        "remaining": round(
                            remaining, 6,
                        ),
                    }
                else:
                    return {
                        "action": "warn",
                        "reason": "limit_exceeded",
                        "amount": amount,
                        "remaining": round(
                            remaining, 6,
                        ),
                    }

        return {
            "action": "allow",
            "amount": amount,
        }

    def record_spending(
        self,
        amount: float,
        limit_id: str | None = None,
        context: str = "",
    ) -> dict[str, Any]:
        """Harcama kaydeder.

        Args:
            amount: Miktar.
            limit_id: Limit ID.
            context: Baglam.

        Returns:
            Kayit bilgisi.
        """
        entry = {
            "amount": amount,
            "limit_id": limit_id,
            "context": context,
            "timestamp": time.time(),
        }
        self._history.append(entry)

        if limit_id and limit_id in self._limits:
            self._limits[limit_id][
                "current"
            ] += amount

        return {
            "amount": amount,
            "recorded": True,
        }

    def approve_request(
        self,
        request_id: str,
    ) -> dict[str, Any]:
        """Harcama onaylar.

        Args:
            request_id: Istek ID.

        Returns:
            Onay bilgisi.
        """
        req = self._pending.get(request_id)
        if not req:
            return {"error": "request_not_found"}

        req["status"] = "approved"
        req["approved_at"] = time.time()
        self._stats["approved"] += 1

        return {
            "request_id": request_id,
            "amount": req["amount"],
            "approved": True,
        }

    def deny_request(
        self,
        request_id: str,
        reason: str = "",
    ) -> dict[str, Any]:
        """Harcama reddeder.

        Args:
            request_id: Istek ID.
            reason: Red sebebi.

        Returns:
            Red bilgisi.
        """
        req = self._pending.get(request_id)
        if not req:
            return {"error": "request_not_found"}

        req["status"] = "denied"
        req["denied_at"] = time.time()
        req["deny_reason"] = reason
        self._stats["blocked"] += 1

        return {
            "request_id": request_id,
            "denied": True,
            "reason": reason,
        }

    def emergency_stop(self) -> dict[str, Any]:
        """Acil durdurma aktiflestirir.

        Returns:
            Durdurma bilgisi.
        """
        self._emergency_stop = True

        return {
            "emergency_stop": True,
            "activated_at": time.time(),
        }

    def resume(self) -> dict[str, Any]:
        """Harcamalari devam ettirir.

        Returns:
            Devam bilgisi.
        """
        self._paused = False
        self._emergency_stop = False

        return {
            "resumed": True,
            "timestamp": time.time(),
        }

    def pause(self) -> dict[str, Any]:
        """Harcamalari duraklatir.

        Returns:
            Duraklatma bilgisi.
        """
        self._paused = True

        return {
            "paused": True,
            "timestamp": time.time(),
        }

    def add_override(
        self,
        override_id: str,
        context: str,
        max_amount: float,
    ) -> dict[str, Any]:
        """Override ekler.

        Args:
            override_id: Override ID.
            context: Baglam.
            max_amount: Maks miktar.

        Returns:
            Override bilgisi.
        """
        self._overrides[override_id] = {
            "override_id": override_id,
            "context": context,
            "max_amount": max_amount,
            "created_at": time.time(),
        }

        return {
            "override_id": override_id,
            "set": True,
        }

    def get_pending(
        self,
    ) -> list[dict[str, Any]]:
        """Bekleyen istekleri getirir.

        Returns:
            Bekleyen istek listesi.
        """
        return [
            dict(p)
            for p in self._pending.values()
            if p["status"] == "pending"
        ]

    @property
    def is_paused(self) -> bool:
        """Duraklatildi mi."""
        return self._paused

    @property
    def is_emergency(self) -> bool:
        """Acil durdurma aktif mi."""
        return self._emergency_stop

    @property
    def pending_count(self) -> int:
        """Bekleyen istek sayisi."""
        return sum(
            1 for p in self._pending.values()
            if p["status"] == "pending"
        )

    @property
    def check_count(self) -> int:
        """Kontrol sayisi."""
        return self._stats["checks"]
