"""ATLAS Mesh Devre Kesici modulu.

Hata esigi, yari-acik durum,
kurtarma testi, fallback isleme
ve metrikler.
"""

import logging
import time
from typing import Any, Callable

logger = logging.getLogger(__name__)


class MeshCircuitBreaker:
    """Mesh devre kesici.

    Servis hatalarini yonetir.

    Attributes:
        _circuits: Devre durumlari.
        _fallbacks: Fallback fonksiyonlari.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        half_open_max: int = 1,
    ) -> None:
        """Devre kesiciyi baslatir.

        Args:
            failure_threshold: Hata esigi.
            recovery_timeout: Kurtarma suresi (sn).
            half_open_max: Yari-acik max deneme.
        """
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout
        self._half_open_max = half_open_max
        self._circuits: dict[
            str, dict[str, Any]
        ] = {}
        self._fallbacks: dict[
            str, Callable[..., Any]
        ] = {}
        self._metrics: dict[
            str, dict[str, int]
        ] = {}

        logger.info(
            "MeshCircuitBreaker baslatildi: "
            "threshold=%d",
            failure_threshold,
        )

    def _get_circuit(
        self,
        service: str,
    ) -> dict[str, Any]:
        """Devre bilgisi getirir/olusturur.

        Args:
            service: Servis adi.

        Returns:
            Devre bilgisi.
        """
        if service not in self._circuits:
            self._circuits[service] = {
                "state": "closed",
                "failure_count": 0,
                "success_count": 0,
                "last_failure": 0.0,
                "last_state_change": time.time(),
                "half_open_attempts": 0,
            }
            self._metrics[service] = {
                "total_calls": 0,
                "total_failures": 0,
                "total_successes": 0,
                "total_rejected": 0,
            }
        return self._circuits[service]

    def can_execute(
        self,
        service: str,
    ) -> bool:
        """Istek yapilabilir mi.

        Args:
            service: Servis adi.

        Returns:
            Izin var mi.
        """
        circuit = self._get_circuit(service)
        state = circuit["state"]

        if state == "closed":
            return True

        if state == "open":
            elapsed = (
                time.time() - circuit["last_failure"]
            )
            if elapsed >= self._recovery_timeout:
                circuit["state"] = "half_open"
                circuit["half_open_attempts"] = 0
                circuit["last_state_change"] = (
                    time.time()
                )
                return True
            self._metrics[service][
                "total_rejected"
            ] += 1
            return False

        if state == "half_open":
            if (
                circuit["half_open_attempts"]
                < self._half_open_max
            ):
                circuit["half_open_attempts"] += 1
                return True
            return False

        return True

    def record_success(
        self,
        service: str,
    ) -> dict[str, Any]:
        """Basari kaydeder.

        Args:
            service: Servis adi.

        Returns:
            Durum bilgisi.
        """
        circuit = self._get_circuit(service)
        self._metrics[service]["total_calls"] += 1
        self._metrics[service][
            "total_successes"
        ] += 1
        circuit["success_count"] += 1

        if circuit["state"] == "half_open":
            circuit["state"] = "closed"
            circuit["failure_count"] = 0
            circuit["last_state_change"] = (
                time.time()
            )

        return {
            "service": service,
            "state": circuit["state"],
        }

    def record_failure(
        self,
        service: str,
    ) -> dict[str, Any]:
        """Hata kaydeder.

        Args:
            service: Servis adi.

        Returns:
            Durum bilgisi.
        """
        circuit = self._get_circuit(service)
        self._metrics[service]["total_calls"] += 1
        self._metrics[service][
            "total_failures"
        ] += 1
        circuit["failure_count"] += 1
        circuit["last_failure"] = time.time()

        if circuit["state"] == "half_open":
            circuit["state"] = "open"
            circuit["last_state_change"] = (
                time.time()
            )
        elif (
            circuit["state"] == "closed"
            and circuit["failure_count"]
            >= self._failure_threshold
        ):
            circuit["state"] = "open"
            circuit["last_state_change"] = (
                time.time()
            )

        return {
            "service": service,
            "state": circuit["state"],
            "failure_count": circuit[
                "failure_count"
            ],
        }

    def get_state(
        self,
        service: str,
    ) -> str:
        """Devre durumunu getirir.

        Args:
            service: Servis adi.

        Returns:
            Durum.
        """
        circuit = self._get_circuit(service)
        return circuit["state"]

    def force_open(
        self,
        service: str,
    ) -> None:
        """Devreyi zorla acar.

        Args:
            service: Servis adi.
        """
        circuit = self._get_circuit(service)
        circuit["state"] = "open"
        circuit["last_failure"] = time.time()
        circuit["last_state_change"] = time.time()

    def force_close(
        self,
        service: str,
    ) -> None:
        """Devreyi zorla kapatir.

        Args:
            service: Servis adi.
        """
        circuit = self._get_circuit(service)
        circuit["state"] = "closed"
        circuit["failure_count"] = 0
        circuit["last_state_change"] = time.time()

    def reset(
        self,
        service: str,
    ) -> bool:
        """Devreyi sifirlar.

        Args:
            service: Servis adi.

        Returns:
            Basarili mi.
        """
        if service in self._circuits:
            del self._circuits[service]
            self._metrics.pop(service, None)
            return True
        return False

    def set_fallback(
        self,
        service: str,
        fallback_fn: Callable[..., Any],
    ) -> None:
        """Fallback fonksiyonu ayarlar.

        Args:
            service: Servis adi.
            fallback_fn: Fallback fonksiyonu.
        """
        self._fallbacks[service] = fallback_fn

    def get_fallback(
        self,
        service: str,
    ) -> Any | None:
        """Fallback calistirir.

        Args:
            service: Servis adi.

        Returns:
            Fallback sonucu veya None.
        """
        fn = self._fallbacks.get(service)
        if fn:
            try:
                return fn()
            except Exception:
                return None
        return None

    def get_metrics(
        self,
        service: str,
    ) -> dict[str, Any]:
        """Devre metriklerini getirir.

        Args:
            service: Servis adi.

        Returns:
            Metrikler.
        """
        circuit = self._get_circuit(service)
        metrics = self._metrics.get(service, {})
        return {
            "service": service,
            "state": circuit["state"],
            "failure_count": circuit[
                "failure_count"
            ],
            **metrics,
        }

    @property
    def circuit_count(self) -> int:
        """Devre sayisi."""
        return len(self._circuits)

    @property
    def open_count(self) -> int:
        """Acik devre sayisi."""
        return sum(
            1 for c in self._circuits.values()
            if c["state"] == "open"
        )
