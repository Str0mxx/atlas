"""
Yedek yonlendirici modulu.

Hata tespiti, otomatik yedek,
yeniden deneme mantigi, devre kesici,
kurtarma yonetimi.
"""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class FallbackRouter:
    """Yedek yonlendirici.

    Attributes:
        _routes: Yedek rotalari.
        _circuit_breakers: Devre kesiciler.
        _retry_history: Deneme gecmisi.
        _stats: Istatistikler.
    """

    CIRCUIT_STATES: list[str] = [
        "closed",
        "open",
        "half_open",
    ]

    def __init__(
        self,
        max_retries: int = 3,
        circuit_threshold: int = 5,
        recovery_timeout: int = 60,
    ) -> None:
        """Yonlendiriciyi baslatir.

        Args:
            max_retries: Maks deneme.
            circuit_threshold: Devre esigi.
            recovery_timeout: Kurtarma sure.
        """
        self._max_retries = max_retries
        self._circuit_threshold = (
            circuit_threshold
        )
        self._recovery_timeout = (
            recovery_timeout
        )
        self._routes: dict[
            str, list[str]
        ] = {}
        self._circuit_breakers: dict[
            str, dict
        ] = {}
        self._retry_history: list[
            dict
        ] = []
        self._stats: dict[str, int] = {
            "routes_configured": 0,
            "fallbacks_triggered": 0,
            "retries_attempted": 0,
            "circuits_opened": 0,
            "successful_recoveries": 0,
        }
        logger.info(
            "FallbackRouter baslatildi"
        )

    @property
    def open_circuits(self) -> int:
        """Acik devre sayisi."""
        return sum(
            1
            for cb in (
                self._circuit_breakers
                .values()
            )
            if cb["state"] == "open"
        )

    def configure_route(
        self,
        primary_model: str = "",
        fallback_chain: (
            list[str] | None
        ) = None,
    ) -> dict[str, Any]:
        """Yedek rotasi yapilandirir.

        Args:
            primary_model: Birincil model.
            fallback_chain: Yedek zinciri.

        Returns:
            Rota bilgisi.
        """
        try:
            chain = fallback_chain or []
            self._routes[
                primary_model
            ] = chain

            # Her model icin devre kesici
            for m in [
                primary_model
            ] + chain:
                if m not in (
                    self._circuit_breakers
                ):
                    self._circuit_breakers[
                        m
                    ] = {
                        "model_id": m,
                        "state": "closed",
                        "failure_count": 0,
                        "last_failure": None,
                        "last_success": None,
                    }

            self._stats[
                "routes_configured"
            ] += 1

            return {
                "primary": primary_model,
                "chain_length": len(chain),
                "configured": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "configured": False,
                "error": str(e),
            }

    def route_request(
        self,
        primary_model: str = "",
        simulate_failure: bool = False,
    ) -> dict[str, Any]:
        """Istegi yonlendirir.

        Args:
            primary_model: Birincil model.
            simulate_failure: Hata simule.

        Returns:
            Yonlendirme bilgisi.
        """
        try:
            rid = f"rt_{uuid4()!s:.8}"

            # Birincil model dene
            if not simulate_failure and (
                self._is_available(
                    primary_model
                )
            ):
                self._record_success(
                    primary_model
                )
                return {
                    "request_id": rid,
                    "routed_to": (
                        primary_model
                    ),
                    "is_fallback": False,
                    "attempt": 1,
                    "routed": True,
                }

            # Hata kaydet
            self._record_failure(
                primary_model
            )

            # Yedek zinciri dene
            chain = self._routes.get(
                primary_model, []
            )
            for i, fallback in enumerate(
                chain
            ):
                if self._is_available(
                    fallback
                ):
                    self._record_success(
                        fallback
                    )
                    self._stats[
                        "fallbacks_triggered"
                    ] += 1

                    return {
                        "request_id": rid,
                        "routed_to": fallback,
                        "is_fallback": True,
                        "attempt": i + 2,
                        "original": (
                            primary_model
                        ),
                        "routed": True,
                    }

                self._record_failure(
                    fallback
                )

            return {
                "request_id": rid,
                "routed": False,
                "error": (
                    "Tum modeller basarisiz"
                ),
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "routed": False,
                "error": str(e),
            }

    def _is_available(
        self,
        model_id: str,
    ) -> bool:
        """Model uygun mu kontrol."""
        cb = self._circuit_breakers.get(
            model_id
        )
        if not cb:
            return True
        return cb["state"] != "open"

    def _record_failure(
        self,
        model_id: str,
    ) -> None:
        """Hata kaydeder."""
        cb = self._circuit_breakers.get(
            model_id
        )
        if not cb:
            return

        cb["failure_count"] += 1
        cb["last_failure"] = (
            datetime.now(
                timezone.utc
            ).isoformat()
        )
        self._stats[
            "retries_attempted"
        ] += 1

        if (
            cb["failure_count"]
            >= self._circuit_threshold
        ):
            cb["state"] = "open"
            self._stats[
                "circuits_opened"
            ] += 1

        self._retry_history.append({
            "model_id": model_id,
            "result": "failure",
            "timestamp": (
                datetime.now(
                    timezone.utc
                ).isoformat()
            ),
        })

    def _record_success(
        self,
        model_id: str,
    ) -> None:
        """Basari kaydeder."""
        cb = self._circuit_breakers.get(
            model_id
        )
        if not cb:
            return

        cb["last_success"] = (
            datetime.now(
                timezone.utc
            ).isoformat()
        )

        if cb["state"] == "half_open":
            cb["state"] = "closed"
            cb["failure_count"] = 0
            self._stats[
                "successful_recoveries"
            ] += 1

    def reset_circuit(
        self,
        model_id: str = "",
    ) -> dict[str, Any]:
        """Devre kesiciyi sifirlar.

        Args:
            model_id: Model ID.

        Returns:
            Sifirlama bilgisi.
        """
        try:
            cb = (
                self._circuit_breakers.get(
                    model_id
                )
            )
            if not cb:
                return {
                    "reset": False,
                    "error": (
                        "Model bulunamadi"
                    ),
                }

            cb["state"] = "closed"
            cb["failure_count"] = 0

            return {
                "model_id": model_id,
                "state": "closed",
                "reset": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "reset": False,
                "error": str(e),
            }

    def half_open_circuit(
        self,
        model_id: str = "",
    ) -> dict[str, Any]:
        """Devreyi yari acar.

        Args:
            model_id: Model ID.

        Returns:
            Durum bilgisi.
        """
        try:
            cb = (
                self._circuit_breakers.get(
                    model_id
                )
            )
            if not cb:
                return {
                    "updated": False,
                    "error": (
                        "Model bulunamadi"
                    ),
                }

            cb["state"] = "half_open"
            return {
                "model_id": model_id,
                "state": "half_open",
                "updated": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "updated": False,
                "error": str(e),
            }

    def get_circuit_status(
        self,
        model_id: str = "",
    ) -> dict[str, Any]:
        """Devre durumu getirir.

        Args:
            model_id: Model ID.

        Returns:
            Devre durumu.
        """
        try:
            cb = (
                self._circuit_breakers.get(
                    model_id
                )
            )
            if not cb:
                return {
                    "retrieved": False,
                    "error": (
                        "Model bulunamadi"
                    ),
                }

            return {
                **cb,
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
                "total_routes": len(
                    self._routes
                ),
                "total_circuits": len(
                    self._circuit_breakers
                ),
                "open_circuits": (
                    self.open_circuits
                ),
                "retry_history": len(
                    self._retry_history
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
