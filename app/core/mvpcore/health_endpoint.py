"""
Saglik endpoint modulu.

Saglik kontrolleri, hazirlik probe,
canlilik probe, bagimlilik kontrolleri,
durum raporlama.
"""

import logging
import time
from datetime import datetime, timezone
from typing import Any, Callable
from uuid import uuid4

logger = logging.getLogger(__name__)


class HealthEndpoint:
    """Saglik endpoint'i.

    Attributes:
        _checks: Saglik kontrolleri.
        _history: Kontrol gecmisi.
        _stats: Istatistikler.
    """

    HEALTH_STATES: list[str] = [
        "healthy",
        "degraded",
        "unhealthy",
        "unknown",
    ]

    CHECK_TYPES: list[str] = [
        "liveness",
        "readiness",
        "dependency",
        "custom",
    ]

    def __init__(
        self,
        check_interval: int = 30,
    ) -> None:
        """Endpoint'i baslatir.

        Args:
            check_interval: Kontrol araligi (sn).
        """
        self._check_interval = (
            check_interval
        )
        self._checks: dict[
            str, dict
        ] = {}
        self._history: list[dict] = []
        self._overall_status = "unknown"
        self._started_at = (
            datetime.now(
                timezone.utc
            ).isoformat()
        )
        self._stats: dict[str, int] = {
            "checks_registered": 0,
            "checks_executed": 0,
            "checks_passed": 0,
            "checks_failed": 0,
        }
        logger.info(
            "HealthEndpoint baslatildi"
        )

    @property
    def status(self) -> str:
        """Genel saglik durumu."""
        return self._overall_status

    @property
    def check_count(self) -> int:
        """Kontrol sayisi."""
        return len(self._checks)

    def register_check(
        self,
        name: str = "",
        check_func: (
            Callable | None
        ) = None,
        check_type: str = "custom",
        critical: bool = False,
        timeout: int = 10,
        metadata: dict | None = None,
    ) -> dict[str, Any]:
        """Saglik kontrolu kaydeder.

        Args:
            name: Kontrol adi.
            check_func: Kontrol fonksiyonu.
            check_type: Kontrol tipi.
            critical: Kritik mi.
            timeout: Zaman asimi.
            metadata: Ek veri.

        Returns:
            Kayit bilgisi.
        """
        try:
            cid = (
                f"hc_{uuid4()!s:.8}"
            )

            self._checks[name] = {
                "check_id": cid,
                "name": name,
                "check_func": check_func,
                "check_type": check_type,
                "critical": critical,
                "timeout": timeout,
                "metadata": (
                    metadata or {}
                ),
                "last_result": None,
                "last_checked": None,
                "consecutive_failures": 0,
            }

            self._stats[
                "checks_registered"
            ] += 1

            return {
                "check_id": cid,
                "name": name,
                "registered": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "registered": False,
                "error": str(e),
            }

    def run_check(
        self, name: str = ""
    ) -> dict[str, Any]:
        """Tek kontrol calistirir.

        Args:
            name: Kontrol adi.

        Returns:
            Kontrol sonucu.
        """
        try:
            check = self._checks.get(
                name
            )
            if not check:
                return {
                    "passed": False,
                    "error": (
                        "Kontrol bulunamadi"
                    ),
                }

            start = time.time()
            func = check["check_func"]

            try:
                if callable(func):
                    result = func()
                    passed = bool(result)
                else:
                    passed = True
            except Exception as ce:
                passed = False
                logger.error(
                    f"Kontrol hatasi: {ce}"
                )

            elapsed = (
                time.time() - start
            )

            now = datetime.now(
                timezone.utc
            ).isoformat()

            check["last_result"] = passed
            check["last_checked"] = now

            if passed:
                check[
                    "consecutive_failures"
                ] = 0
                self._stats[
                    "checks_passed"
                ] += 1
            else:
                check[
                    "consecutive_failures"
                ] += 1
                self._stats[
                    "checks_failed"
                ] += 1

            self._stats[
                "checks_executed"
            ] += 1

            result_entry = {
                "name": name,
                "passed": passed,
                "elapsed": elapsed,
                "checked_at": now,
            }
            self._history.append(
                result_entry
            )

            return {
                "name": name,
                "passed": passed,
                "elapsed": elapsed,
                "critical": check[
                    "critical"
                ],
                "checked": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "passed": False,
                "error": str(e),
            }

    def run_all(
        self,
    ) -> dict[str, Any]:
        """Tum kontrolleri calistirir.

        Returns:
            Tum sonuclar.
        """
        try:
            results: list[dict] = []
            all_passed = True
            critical_failed = False

            for name in self._checks:
                r = self.run_check(name)
                results.append(r)
                if not r.get("passed"):
                    all_passed = False
                    if r.get("critical"):
                        critical_failed = (
                            True
                        )

            if all_passed:
                self._overall_status = (
                    "healthy"
                )
            elif critical_failed:
                self._overall_status = (
                    "unhealthy"
                )
            else:
                self._overall_status = (
                    "degraded"
                )

            return {
                "status": (
                    self._overall_status
                ),
                "checks": results,
                "total": len(results),
                "passed": sum(
                    1
                    for r in results
                    if r.get("passed")
                ),
                "failed": sum(
                    1
                    for r in results
                    if not r.get("passed")
                ),
                "checked": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "checked": False,
                "error": str(e),
            }

    def liveness(
        self,
    ) -> dict[str, Any]:
        """Canlilik probe'u.

        Returns:
            Canlilik bilgisi.
        """
        try:
            checks = {
                n: c
                for n, c in
                self._checks.items()
                if c["check_type"]
                == "liveness"
            }

            if not checks:
                return {
                    "alive": True,
                    "status": "healthy",
                }

            all_ok = True
            for name in checks:
                r = self.run_check(name)
                if not r.get("passed"):
                    all_ok = False

            return {
                "alive": all_ok,
                "status": (
                    "healthy"
                    if all_ok
                    else "unhealthy"
                ),
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "alive": False,
                "error": str(e),
            }

    def readiness(
        self,
    ) -> dict[str, Any]:
        """Hazirlik probe'u.

        Returns:
            Hazirlik bilgisi.
        """
        try:
            checks = {
                n: c
                for n, c in
                self._checks.items()
                if c["check_type"]
                == "readiness"
            }

            if not checks:
                return {
                    "ready": True,
                    "status": "healthy",
                }

            all_ok = True
            for name in checks:
                r = self.run_check(name)
                if not r.get("passed"):
                    all_ok = False

            return {
                "ready": all_ok,
                "status": (
                    "healthy"
                    if all_ok
                    else "not_ready"
                ),
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "ready": False,
                "error": str(e),
            }

    def check_dependencies(
        self,
    ) -> dict[str, Any]:
        """Bagimlilik kontrolu.

        Returns:
            Bagimlilik bilgisi.
        """
        try:
            checks = {
                n: c
                for n, c in
                self._checks.items()
                if c["check_type"]
                == "dependency"
            }

            results: list[dict] = []
            all_ok = True

            for name in checks:
                r = self.run_check(name)
                results.append(r)
                if not r.get("passed"):
                    all_ok = False

            return {
                "all_healthy": all_ok,
                "dependencies": results,
                "total": len(results),
                "checked": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "checked": False,
                "error": str(e),
            }

    def get_report(
        self,
    ) -> dict[str, Any]:
        """Saglik raporu getirir.

        Returns:
            Rapor bilgisi.
        """
        try:
            check_details = {}
            for name, check in (
                self._checks.items()
            ):
                check_details[name] = {
                    "type": check[
                        "check_type"
                    ],
                    "critical": check[
                        "critical"
                    ],
                    "last_result": check[
                        "last_result"
                    ],
                    "last_checked": check[
                        "last_checked"
                    ],
                    "consecutive_failures": (
                        check[
                            "consecutive_"
                            "failures"
                        ]
                    ),
                }

            return {
                "status": (
                    self._overall_status
                ),
                "uptime_since": (
                    self._started_at
                ),
                "checks": check_details,
                "stats": dict(
                    self._stats
                ),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }

    def get_summary(
        self,
    ) -> dict[str, Any]:
        """Ozet getirir."""
        try:
            return {
                "status": (
                    self._overall_status
                ),
                "total_checks": len(
                    self._checks
                ),
                "uptime_since": (
                    self._started_at
                ),
                "stats": dict(
                    self._stats
                ),
                "retrieved": True,
            }
        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }
