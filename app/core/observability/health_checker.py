"""ATLAS Saglik Kontrolcusu modulu.

Yasam sondasi, hazirlik sondasi,
bagimlilik kontrolleri, ozel saglik
kontrolleri ve durum toplulastirma.
"""

import logging
import time
from typing import Any, Callable

logger = logging.getLogger(__name__)


class HealthChecker:
    """Saglik kontrolcusu.

    Sistem sagligini kontrol eder.

    Attributes:
        _checks: Saglik kontrolleri.
        _results: Kontrol sonuclari.
    """

    def __init__(self) -> None:
        """Saglik kontrolcusunu baslatir."""
        self._liveness_checks: dict[
            str, Callable[..., bool]
        ] = {}
        self._readiness_checks: dict[
            str, Callable[..., bool]
        ] = {}
        self._dependency_checks: dict[
            str, dict[str, Any]
        ] = {}
        self._custom_checks: dict[
            str, Callable[..., dict[str, Any]]
        ] = {}
        self._results: list[
            dict[str, Any]
        ] = []
        self._status_cache: dict[
            str, dict[str, Any]
        ] = {}

        logger.info("HealthChecker baslatildi")

    def add_liveness_check(
        self,
        name: str,
        check_fn: Callable[..., bool],
    ) -> None:
        """Yasam sondasi ekler.

        Args:
            name: Kontrol adi.
            check_fn: Kontrol fonksiyonu.
        """
        self._liveness_checks[name] = check_fn

    def add_readiness_check(
        self,
        name: str,
        check_fn: Callable[..., bool],
    ) -> None:
        """Hazirlik sondasi ekler.

        Args:
            name: Kontrol adi.
            check_fn: Kontrol fonksiyonu.
        """
        self._readiness_checks[name] = check_fn

    def add_dependency_check(
        self,
        name: str,
        check_fn: Callable[..., bool],
        critical: bool = True,
    ) -> None:
        """Bagimlilik kontrolu ekler.

        Args:
            name: Kontrol adi.
            check_fn: Kontrol fonksiyonu.
            critical: Kritik mi.
        """
        self._dependency_checks[name] = {
            "check_fn": check_fn,
            "critical": critical,
        }

    def add_custom_check(
        self,
        name: str,
        check_fn: Callable[..., dict[str, Any]],
    ) -> None:
        """Ozel kontrol ekler.

        Args:
            name: Kontrol adi.
            check_fn: Kontrol fonksiyonu.
        """
        self._custom_checks[name] = check_fn

    def check_liveness(self) -> dict[str, Any]:
        """Yasam kontrolu yapar.

        Returns:
            Kontrol sonucu.
        """
        checks = {}
        all_alive = True

        for name, fn in (
            self._liveness_checks.items()
        ):
            try:
                result = fn()
                checks[name] = {
                    "alive": result,
                    "error": None,
                }
                if not result:
                    all_alive = False
            except Exception as e:
                checks[name] = {
                    "alive": False,
                    "error": str(e),
                }
                all_alive = False

        result = {
            "alive": all_alive,
            "checks": checks,
            "timestamp": time.time(),
        }
        self._results.append(result)
        self._status_cache["liveness"] = result
        return result

    def check_readiness(self) -> dict[str, Any]:
        """Hazirlik kontrolu yapar.

        Returns:
            Kontrol sonucu.
        """
        checks = {}
        all_ready = True

        for name, fn in (
            self._readiness_checks.items()
        ):
            try:
                result = fn()
                checks[name] = {
                    "ready": result,
                    "error": None,
                }
                if not result:
                    all_ready = False
            except Exception as e:
                checks[name] = {
                    "ready": False,
                    "error": str(e),
                }
                all_ready = False

        result = {
            "ready": all_ready,
            "checks": checks,
            "timestamp": time.time(),
        }
        self._results.append(result)
        self._status_cache["readiness"] = result
        return result

    def check_dependencies(self) -> dict[str, Any]:
        """Bagimlilik kontrolu yapar.

        Returns:
            Kontrol sonucu.
        """
        checks = {}
        all_healthy = True
        critical_ok = True

        for name, dep in (
            self._dependency_checks.items()
        ):
            try:
                result = dep["check_fn"]()
                checks[name] = {
                    "healthy": result,
                    "critical": dep["critical"],
                    "error": None,
                }
                if not result:
                    all_healthy = False
                    if dep["critical"]:
                        critical_ok = False
            except Exception as e:
                checks[name] = {
                    "healthy": False,
                    "critical": dep["critical"],
                    "error": str(e),
                }
                all_healthy = False
                if dep["critical"]:
                    critical_ok = False

        result = {
            "healthy": all_healthy,
            "critical_ok": critical_ok,
            "checks": checks,
            "timestamp": time.time(),
        }
        self._results.append(result)
        return result

    def check_custom(
        self,
        name: str,
    ) -> dict[str, Any]:
        """Ozel kontrol yapar.

        Args:
            name: Kontrol adi.

        Returns:
            Kontrol sonucu.
        """
        fn = self._custom_checks.get(name)
        if not fn:
            return {
                "status": "error",
                "reason": "check_not_found",
            }
        try:
            return fn()
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
            }

    def get_aggregate_status(
        self,
    ) -> dict[str, Any]:
        """Toplu durum getirir.

        Returns:
            Toplu durum.
        """
        liveness = self.check_liveness()
        readiness = self.check_readiness()
        deps = self.check_dependencies()

        if not liveness["alive"]:
            status = "unhealthy"
        elif not deps.get("critical_ok", True):
            status = "unhealthy"
        elif not readiness["ready"]:
            status = "degraded"
        elif not deps["healthy"]:
            status = "degraded"
        else:
            status = "healthy"

        return {
            "status": status,
            "liveness": liveness["alive"],
            "readiness": readiness["ready"],
            "dependencies": deps["healthy"],
            "timestamp": time.time(),
        }

    def remove_check(
        self,
        name: str,
    ) -> bool:
        """Kontrol kaldirir.

        Args:
            name: Kontrol adi.

        Returns:
            Basarili mi.
        """
        removed = False
        if name in self._liveness_checks:
            del self._liveness_checks[name]
            removed = True
        if name in self._readiness_checks:
            del self._readiness_checks[name]
            removed = True
        if name in self._dependency_checks:
            del self._dependency_checks[name]
            removed = True
        if name in self._custom_checks:
            del self._custom_checks[name]
            removed = True
        return removed

    @property
    def liveness_count(self) -> int:
        """Yasam sondasi sayisi."""
        return len(self._liveness_checks)

    @property
    def readiness_count(self) -> int:
        """Hazirlik sondasi sayisi."""
        return len(self._readiness_checks)

    @property
    def dependency_count(self) -> int:
        """Bagimlilik kontrolu sayisi."""
        return len(self._dependency_checks)

    @property
    def check_count(self) -> int:
        """Toplam kontrol sayisi."""
        return (
            len(self._liveness_checks)
            + len(self._readiness_checks)
            + len(self._dependency_checks)
            + len(self._custom_checks)
        )
