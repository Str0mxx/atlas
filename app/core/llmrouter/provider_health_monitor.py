"""
Saglayici saglik izleyici modulu.

Saglik kontrolleri, calisma suresi,
hata oranlari, hiz limiti izleme,
durum paneli.
"""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class ProviderHealthMonitor:
    """Saglayici saglik izleyici.

    Attributes:
        _providers: Saglayici kayitlari.
        _health_checks: Saglik kontrol.
        _incidents: Olaylar.
        _stats: Istatistikler.
    """

    HEALTH_STATES: list[str] = [
        "healthy",
        "degraded",
        "unhealthy",
        "unknown",
    ]

    def __init__(
        self,
        check_interval_sec: int = 60,
    ) -> None:
        """Izleyiciyi baslatir.

        Args:
            check_interval_sec: Kontrol.
        """
        self._check_interval = (
            check_interval_sec
        )
        self._providers: dict[
            str, dict
        ] = {}
        self._health_checks: list[
            dict
        ] = []
        self._incidents: list[dict] = []
        self._stats: dict[str, int] = {
            "checks_performed": 0,
            "incidents_detected": 0,
            "providers_registered": 0,
            "degradations_detected": 0,
        }
        logger.info(
            "ProviderHealthMonitor "
            "baslatildi"
        )

    @property
    def healthy_count(self) -> int:
        """Saglikli saglayici sayisi."""
        return sum(
            1
            for p in (
                self._providers.values()
            )
            if p["health_state"]
            == "healthy"
        )

    def register_provider(
        self,
        provider_id: str = "",
        name: str = "",
        base_url: str = "",
        rate_limit_rpm: int = 60,
        rate_limit_tpm: int = 100000,
    ) -> dict[str, Any]:
        """Saglayici kaydeder.

        Args:
            provider_id: Saglayici ID.
            name: Saglayici adi.
            base_url: Temel URL.
            rate_limit_rpm: RPM limiti.
            rate_limit_tpm: TPM limiti.

        Returns:
            Kayit bilgisi.
        """
        try:
            self._providers[
                provider_id
            ] = {
                "provider_id": provider_id,
                "name": name,
                "base_url": base_url,
                "health_state": "unknown",
                "rate_limit_rpm": (
                    rate_limit_rpm
                ),
                "rate_limit_tpm": (
                    rate_limit_tpm
                ),
                "current_rpm": 0,
                "current_tpm": 0,
                "total_requests": 0,
                "total_errors": 0,
                "error_rate": 0.0,
                "uptime_checks": 0,
                "uptime_success": 0,
                "last_check": None,
                "registered_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
            }

            self._stats[
                "providers_registered"
            ] += 1

            return {
                "provider_id": (
                    provider_id
                ),
                "registered": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "registered": False,
                "error": str(e),
            }

    def perform_health_check(
        self,
        provider_id: str = "",
        response_time_ms: float = 0.0,
        is_available: bool = True,
        error_message: str = "",
    ) -> dict[str, Any]:
        """Saglik kontrolu yapar.

        Args:
            provider_id: Saglayici ID.
            response_time_ms: Yanit suresi.
            is_available: Uygun mu.
            error_message: Hata mesaji.

        Returns:
            Kontrol sonucu.
        """
        try:
            prov = self._providers.get(
                provider_id
            )
            if not prov:
                return {
                    "checked": False,
                    "error": (
                        "Saglayici "
                        "bulunamadi"
                    ),
                }

            cid = f"hc_{uuid4()!s:.8}"
            now = datetime.now(
                timezone.utc
            ).isoformat()

            # Saglik durumunu guncelle
            prov["uptime_checks"] += 1
            if is_available:
                prov["uptime_success"] += 1

            # Durum belirle
            prev_state = prov[
                "health_state"
            ]
            if not is_available:
                prov[
                    "health_state"
                ] = "unhealthy"
            elif response_time_ms > 5000:
                prov[
                    "health_state"
                ] = "degraded"
                self._stats[
                    "degradations_detected"
                ] += 1
            else:
                prov[
                    "health_state"
                ] = "healthy"

            prov["last_check"] = now

            check = {
                "check_id": cid,
                "provider_id": (
                    provider_id
                ),
                "is_available": (
                    is_available
                ),
                "response_time_ms": (
                    response_time_ms
                ),
                "health_state": prov[
                    "health_state"
                ],
                "error_message": (
                    error_message
                ),
                "checked_at": now,
            }
            self._health_checks.append(
                check
            )

            self._stats[
                "checks_performed"
            ] += 1

            # Olay kaydi
            if (
                prev_state == "healthy"
                and prov["health_state"]
                != "healthy"
            ):
                self._record_incident(
                    provider_id,
                    prov["health_state"],
                    error_message,
                )

            return {
                "check_id": cid,
                "health_state": prov[
                    "health_state"
                ],
                "response_time_ms": (
                    response_time_ms
                ),
                "checked": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "checked": False,
                "error": str(e),
            }

    def _record_incident(
        self,
        provider_id: str,
        state: str,
        error: str,
    ) -> None:
        """Olay kaydeder."""
        self._incidents.append({
            "incident_id": (
                f"pi_{uuid4()!s:.8}"
            ),
            "provider_id": provider_id,
            "state": state,
            "error": error,
            "detected_at": (
                datetime.now(
                    timezone.utc
                ).isoformat()
            ),
            "resolved": False,
        })
        self._stats[
            "incidents_detected"
        ] += 1

    def record_request(
        self,
        provider_id: str = "",
        success: bool = True,
        tokens_used: int = 0,
        error_type: str = "",
    ) -> dict[str, Any]:
        """Istek kaydeder.

        Args:
            provider_id: Saglayici ID.
            success: Basarili mi.
            tokens_used: Kullanilan token.
            error_type: Hata tipi.

        Returns:
            Kayit bilgisi.
        """
        try:
            prov = self._providers.get(
                provider_id
            )
            if not prov:
                return {
                    "recorded": False,
                    "error": (
                        "Saglayici "
                        "bulunamadi"
                    ),
                }

            prov["total_requests"] += 1
            prov["current_rpm"] += 1
            prov[
                "current_tpm"
            ] += tokens_used

            if not success:
                prov["total_errors"] += 1

            # Hata orani guncelle
            if prov["total_requests"] > 0:
                prov["error_rate"] = round(
                    prov["total_errors"]
                    / prov[
                        "total_requests"
                    ],
                    4,
                )

            # Rate limit kontrolu
            rate_limited = False
            if (
                prov["current_rpm"]
                >= prov["rate_limit_rpm"]
            ):
                rate_limited = True
            if (
                prov["current_tpm"]
                >= prov["rate_limit_tpm"]
            ):
                rate_limited = True

            return {
                "provider_id": (
                    provider_id
                ),
                "rate_limited": (
                    rate_limited
                ),
                "error_rate": prov[
                    "error_rate"
                ],
                "recorded": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "recorded": False,
                "error": str(e),
            }

    def reset_rate_counters(
        self,
        provider_id: str = "",
    ) -> dict[str, Any]:
        """Hiz sayaclarini sifirlar.

        Args:
            provider_id: Saglayici ID.

        Returns:
            Sifirlama bilgisi.
        """
        try:
            prov = self._providers.get(
                provider_id
            )
            if not prov:
                return {
                    "reset": False,
                    "error": (
                        "Saglayici "
                        "bulunamadi"
                    ),
                }

            prov["current_rpm"] = 0
            prov["current_tpm"] = 0

            return {
                "provider_id": (
                    provider_id
                ),
                "reset": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "reset": False,
                "error": str(e),
            }

    def get_uptime(
        self,
        provider_id: str = "",
    ) -> dict[str, Any]:
        """Calisma suresi getirir.

        Args:
            provider_id: Saglayici ID.

        Returns:
            Calisma suresi.
        """
        try:
            prov = self._providers.get(
                provider_id
            )
            if not prov:
                return {
                    "retrieved": False,
                    "error": (
                        "Saglayici "
                        "bulunamadi"
                    ),
                }

            checks = prov["uptime_checks"]
            success = prov[
                "uptime_success"
            ]
            uptime = (
                round(
                    success / checks * 100,
                    2,
                )
                if checks > 0
                else 0.0
            )

            return {
                "provider_id": (
                    provider_id
                ),
                "uptime_percent": uptime,
                "total_checks": checks,
                "successful_checks": (
                    success
                ),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }

    def get_error_rates(
        self,
    ) -> dict[str, Any]:
        """Hata oranlarini getirir."""
        try:
            rates = []
            for p in (
                self._providers.values()
            ):
                rates.append({
                    "provider_id": p[
                        "provider_id"
                    ],
                    "name": p["name"],
                    "error_rate": p[
                        "error_rate"
                    ],
                    "total_requests": p[
                        "total_requests"
                    ],
                    "total_errors": p[
                        "total_errors"
                    ],
                })

            rates.sort(
                key=lambda x: x[
                    "error_rate"
                ]
            )

            return {
                "error_rates": rates,
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }

    def get_rate_limit_status(
        self,
        provider_id: str = "",
    ) -> dict[str, Any]:
        """Hiz limiti durumu getirir.

        Args:
            provider_id: Saglayici ID.

        Returns:
            Hiz limiti bilgisi.
        """
        try:
            prov = self._providers.get(
                provider_id
            )
            if not prov:
                return {
                    "retrieved": False,
                    "error": (
                        "Saglayici "
                        "bulunamadi"
                    ),
                }

            rpm_usage = (
                round(
                    prov["current_rpm"]
                    / prov["rate_limit_rpm"]
                    * 100,
                    1,
                )
                if prov["rate_limit_rpm"]
                > 0
                else 0
            )
            tpm_usage = (
                round(
                    prov["current_tpm"]
                    / prov["rate_limit_tpm"]
                    * 100,
                    1,
                )
                if prov["rate_limit_tpm"]
                > 0
                else 0
            )

            return {
                "provider_id": (
                    provider_id
                ),
                "rpm_limit": prov[
                    "rate_limit_rpm"
                ],
                "rpm_current": prov[
                    "current_rpm"
                ],
                "rpm_usage_percent": (
                    rpm_usage
                ),
                "tpm_limit": prov[
                    "rate_limit_tpm"
                ],
                "tpm_current": prov[
                    "current_tpm"
                ],
                "tpm_usage_percent": (
                    tpm_usage
                ),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }

    def get_dashboard(
        self,
    ) -> dict[str, Any]:
        """Durum paneli getirir."""
        try:
            dashboard = []
            for p in (
                self._providers.values()
            ):
                checks = p[
                    "uptime_checks"
                ]
                success = p[
                    "uptime_success"
                ]
                uptime = (
                    round(
                        success
                        / checks
                        * 100,
                        2,
                    )
                    if checks > 0
                    else 0.0
                )

                dashboard.append({
                    "provider_id": p[
                        "provider_id"
                    ],
                    "name": p["name"],
                    "health_state": p[
                        "health_state"
                    ],
                    "uptime_percent": (
                        uptime
                    ),
                    "error_rate": p[
                        "error_rate"
                    ],
                    "total_requests": p[
                        "total_requests"
                    ],
                    "last_check": p[
                        "last_check"
                    ],
                })

            return {
                "providers": dashboard,
                "total_healthy": (
                    self.healthy_count
                ),
                "total_providers": len(
                    self._providers
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
                "total_providers": len(
                    self._providers
                ),
                "healthy_providers": (
                    self.healthy_count
                ),
                "total_checks": len(
                    self._health_checks
                ),
                "total_incidents": len(
                    self._incidents
                ),
                "stats": dict(self._stats),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }
