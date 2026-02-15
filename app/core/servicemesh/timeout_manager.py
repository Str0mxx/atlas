"""ATLAS Zaman Asimi Yoneticisi modulu.

Istek zaman asimlari, baglanti
zaman asimlari, son tarih yayilimi,
zaman asimi butceleri ve zarif isleme.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class TimeoutManager:
    """Zaman asimi yoneticisi.

    Zaman asimlarini yonetir.

    Attributes:
        _timeouts: Zaman asimi tanimlari.
        _active: Aktif istekler.
    """

    def __init__(
        self,
        default_timeout: float = 30.0,
        default_connect_timeout: float = 5.0,
    ) -> None:
        """Zaman asimi yoneticisini baslatir.

        Args:
            default_timeout: Varsayilan istek (sn).
            default_connect_timeout: Baglanti (sn).
        """
        self._default_timeout = default_timeout
        self._default_connect = (
            default_connect_timeout
        )
        self._service_timeouts: dict[
            str, dict[str, float]
        ] = {}
        self._active: dict[
            str, dict[str, Any]
        ] = {}
        self._budgets: dict[
            str, dict[str, float]
        ] = {}
        self._history: list[
            dict[str, Any]
        ] = []
        self._total_timeouts = 0

        logger.info(
            "TimeoutManager baslatildi: "
            "default=%.1fs",
            default_timeout,
        )

    def set_timeout(
        self,
        service: str,
        request_timeout: float | None = None,
        connect_timeout: float | None = None,
    ) -> dict[str, float]:
        """Servis zaman asimini ayarlar.

        Args:
            service: Servis adi.
            request_timeout: Istek (sn).
            connect_timeout: Baglanti (sn).

        Returns:
            Zaman asimi bilgisi.
        """
        self._service_timeouts[service] = {
            "request": (
                request_timeout
                or self._default_timeout
            ),
            "connect": (
                connect_timeout
                or self._default_connect
            ),
        }
        return self._service_timeouts[service]

    def get_timeout(
        self,
        service: str,
    ) -> dict[str, float]:
        """Zaman asimini getirir.

        Args:
            service: Servis adi.

        Returns:
            Zaman asimi bilgisi.
        """
        return self._service_timeouts.get(
            service,
            {
                "request": self._default_timeout,
                "connect": self._default_connect,
            },
        )

    def start_request(
        self,
        request_id: str,
        service: str,
        deadline: float | None = None,
    ) -> dict[str, Any]:
        """Istegi baslatir.

        Args:
            request_id: Istek ID.
            service: Servis adi.
            deadline: Son tarih (timestamp).

        Returns:
            Istek bilgisi.
        """
        timeouts = self.get_timeout(service)
        if deadline is None:
            deadline = (
                time.time()
                + timeouts["request"]
            )

        self._active[request_id] = {
            "service": service,
            "start_time": time.time(),
            "deadline": deadline,
            "timeout": timeouts["request"],
        }

        return {
            "request_id": request_id,
            "deadline": deadline,
            "remaining": deadline - time.time(),
        }

    def check_timeout(
        self,
        request_id: str,
    ) -> dict[str, Any]:
        """Zaman asimi kontrol eder.

        Args:
            request_id: Istek ID.

        Returns:
            Kontrol sonucu.
        """
        active = self._active.get(request_id)
        if not active:
            return {
                "status": "not_found",
                "timed_out": False,
            }

        now = time.time()
        remaining = active["deadline"] - now
        timed_out = remaining <= 0

        if timed_out:
            self._total_timeouts += 1
            self._history.append({
                "request_id": request_id,
                "service": active["service"],
                "elapsed": now - active["start_time"],
                "timeout": active["timeout"],
                "timestamp": now,
            })

        return {
            "timed_out": timed_out,
            "remaining": max(0, remaining),
            "elapsed": now - active["start_time"],
        }

    def end_request(
        self,
        request_id: str,
    ) -> dict[str, Any] | None:
        """Istegi sonlandirir.

        Args:
            request_id: Istek ID.

        Returns:
            Istek bilgisi veya None.
        """
        active = self._active.pop(
            request_id, None,
        )
        if active:
            return {
                "elapsed": (
                    time.time()
                    - active["start_time"]
                ),
                "service": active["service"],
            }
        return None

    def propagate_deadline(
        self,
        parent_id: str,
        child_id: str,
        service: str,
        overhead: float = 0.5,
    ) -> dict[str, Any]:
        """Son tarihi yayar.

        Args:
            parent_id: Ust istek ID.
            child_id: Alt istek ID.
            service: Servis adi.
            overhead: Ek sure (sn).

        Returns:
            Propagasyon bilgisi.
        """
        parent = self._active.get(parent_id)
        if not parent:
            return self.start_request(
                child_id, service,
            )

        child_deadline = (
            parent["deadline"] - overhead
        )
        return self.start_request(
            child_id, service, child_deadline,
        )

    def set_budget(
        self,
        service: str,
        total_budget: float,
    ) -> None:
        """Zaman asimi butcesi ayarlar.

        Args:
            service: Servis adi.
            total_budget: Toplam butce (sn).
        """
        self._budgets[service] = {
            "total": total_budget,
            "remaining": total_budget,
        }

    def consume_budget(
        self,
        service: str,
        amount: float,
    ) -> dict[str, Any]:
        """Butceden harcar.

        Args:
            service: Servis adi.
            amount: Miktar (sn).

        Returns:
            Butce bilgisi.
        """
        budget = self._budgets.get(service)
        if not budget:
            return {
                "status": "no_budget",
                "remaining": float("inf"),
            }

        budget["remaining"] = max(
            0, budget["remaining"] - amount,
        )
        return {
            "status": "ok",
            "remaining": budget["remaining"],
            "exhausted": budget["remaining"] <= 0,
        }

    def get_timeout_history(
        self,
        service: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Zaman asimi gecmisi.

        Args:
            service: Filtre.
            limit: Limit.

        Returns:
            Gecmis listesi.
        """
        history = self._history
        if service:
            history = [
                h for h in history
                if h["service"] == service
            ]
        return history[-limit:]

    @property
    def active_count(self) -> int:
        """Aktif istek sayisi."""
        return len(self._active)

    @property
    def timeout_count(self) -> int:
        """Toplam zaman asimi sayisi."""
        return self._total_timeouts

    @property
    def default_timeout(self) -> float:
        """Varsayilan zaman asimi."""
        return self._default_timeout
