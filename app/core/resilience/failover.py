"""ATLAS failover yonetim modulu.

Primary/secondary servis yedeklemesi, saglik kontrolleri,
otomatik failover ve circuit breaker pattern saglar.
"""

import asyncio
import logging
import time
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable

from pydantic import BaseModel, Field

from app.config import settings

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    """Circuit breaker durum tanimlari."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class ServiceHealth(BaseModel):
    """Servis saglik durumu.

    Attributes:
        name: Servis adi.
        is_primary: Birincil servis mi.
        status: Saglik durumu (healthy/degraded/down).
        last_check: Son kontrol zamani.
        failure_count: Ardisik hata sayisi.
        circuit_state: Circuit breaker durumu.
    """

    name: str
    is_primary: bool = True
    status: str = "healthy"
    last_check: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
    failure_count: int = 0
    circuit_state: CircuitState = CircuitState.CLOSED


class CircuitBreaker:
    """Circuit breaker sinifi.

    Ardisik hatalar esik degerini asinca devreyi acar,
    belirli bir sure sonra test moduna gecer.

    Attributes:
        failure_threshold: Devreyi acmak icin ardisik hata esigi.
        recovery_timeout: Devre acik kaldiktan sonra test suresi (sn).
        half_open_max_calls: Test modunda izin verilen cagri sayisi.
    """

    def __init__(
        self,
        failure_threshold: int | None = None,
        recovery_timeout: int | None = None,
        half_open_max_calls: int = 3,
    ) -> None:
        """CircuitBreaker'i baslatir.

        Args:
            failure_threshold: Hata esigi (varsayilan: settings'ten).
            recovery_timeout: Kurtarma suresi (varsayilan: settings'ten).
            half_open_max_calls: Test modu maks. cagri.
        """
        self.failure_threshold = (
            failure_threshold or settings.circuit_breaker_failure_threshold
        )
        self.recovery_timeout = (
            recovery_timeout or settings.circuit_breaker_recovery_timeout
        )
        self.half_open_max_calls = half_open_max_calls

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: float = 0
        self._half_open_calls = 0

    @property
    def state(self) -> CircuitState:
        """Guncel circuit breaker durumu.

        OPEN durumda recovery_timeout gecmisse HALF_OPEN'a gecer.

        Returns:
            Circuit breaker durumu.
        """
        if self._state == CircuitState.OPEN:
            elapsed = time.monotonic() - self._last_failure_time
            if elapsed >= self.recovery_timeout:
                self._state = CircuitState.HALF_OPEN
                self._half_open_calls = 0
                logger.info("Circuit breaker HALF_OPEN'a gecti")
        return self._state

    async def execute(
        self,
        func: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Fonksiyonu circuit breaker korumasi altinda calistirir.

        Args:
            func: Calistirilacak fonksiyon (async veya sync).
            *args: Fonksiyon argumanlari.
            **kwargs: Fonksiyon keyword argumanlari.

        Returns:
            Fonksiyon sonucu.

        Raises:
            RuntimeError: Circuit OPEN durumda.
            Exception: Fonksiyon hatasi (HALF_OPEN'da devreyi acar).
        """
        current_state = self.state

        if current_state == CircuitState.OPEN:
            raise RuntimeError(
                "Circuit breaker OPEN — istek engellendi",
            )

        if current_state == CircuitState.HALF_OPEN:
            if self._half_open_calls >= self.half_open_max_calls:
                raise RuntimeError(
                    "Circuit breaker HALF_OPEN — maks. test cagrisi asildi",
                )
            self._half_open_calls += 1

        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            self.record_success()
            return result
        except Exception as exc:
            self.record_failure()
            raise exc

    def record_success(self) -> None:
        """Basarili cagriyi kaydeder. Devreyi kapatir."""
        self._failure_count = 0
        if self._state != CircuitState.CLOSED:
            logger.info("Circuit breaker CLOSED'a gecti (basarili)")
        self._state = CircuitState.CLOSED
        self._half_open_calls = 0

    def record_failure(self) -> None:
        """Basarisiz cagriyi kaydeder. Esik asilirsa devreyi acar."""
        self._failure_count += 1
        self._last_failure_time = time.monotonic()

        if self._failure_count >= self.failure_threshold:
            self._state = CircuitState.OPEN
            logger.warning(
                "Circuit breaker OPEN'a gecti (%d ardisik hata)",
                self._failure_count,
            )
        elif self._state == CircuitState.HALF_OPEN:
            self._state = CircuitState.OPEN
            logger.warning("Circuit breaker HALF_OPEN'dan OPEN'a gecti")

    def reset(self) -> None:
        """Circuit breaker'i sifirlar."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._half_open_calls = 0
        logger.info("Circuit breaker sifirlandi")


class FailoverManager:
    """Failover yonetim sinifi.

    Servisleri kaydeder, sagliklarini izler ve
    birincil servis basarisiz olursa yedege gecer.

    Attributes:
        health_check_interval: Saglik kontrolu araligi (saniye).
    """

    def __init__(
        self,
        health_check_interval: int | None = None,
    ) -> None:
        """FailoverManager'i baslatir.

        Args:
            health_check_interval: Saglik kontrolu araligi (saniye).
        """
        self.health_check_interval = (
            health_check_interval or settings.offline_health_check_interval
        )
        self._services: dict[str, dict[str, Any]] = {}
        self._fallback_map: dict[str, str] = {}
        self._health_status: dict[str, ServiceHealth] = {}
        self._circuit_breakers: dict[str, CircuitBreaker] = {}
        self._task: asyncio.Task[None] | None = None
        self._running = False

        logger.info(
            "FailoverManager olusturuldu (aralik=%ds)",
            self.health_check_interval,
        )

    def register_service(
        self,
        name: str,
        health_check_fn: Callable[..., Any],
        is_primary: bool = True,
    ) -> None:
        """Servis kaydeder.

        Args:
            name: Servis adi.
            health_check_fn: Saglik kontrolu fonksiyonu (async, bool dondurur).
            is_primary: Birincil servis mi.
        """
        self._services[name] = {
            "health_check_fn": health_check_fn,
            "is_primary": is_primary,
        }
        self._health_status[name] = ServiceHealth(
            name=name, is_primary=is_primary,
        )
        self._circuit_breakers[name] = CircuitBreaker()
        logger.info(
            "Servis kaydedildi: %s (primary=%s)", name, is_primary,
        )

    def register_fallback(self, primary: str, fallback: str) -> None:
        """Birincil servis icin yedek tanimlar.

        Args:
            primary: Birincil servis adi.
            fallback: Yedek servis adi.
        """
        self._fallback_map[primary] = fallback
        logger.info("Fallback tanimlandi: %s -> %s", primary, fallback)

    async def check_all_services(self) -> dict[str, ServiceHealth]:
        """Tum servislerin sagligini kontrol eder.

        Returns:
            Servis adi -> saglik durumu eslesmesi.
        """
        for name in self._services:
            await self.check_service(name)
        return dict(self._health_status)

    async def check_service(self, name: str) -> ServiceHealth:
        """Tek bir servisin sagligini kontrol eder.

        Args:
            name: Servis adi.

        Returns:
            Servis saglik durumu.

        Raises:
            KeyError: Servis bulunamadi.
        """
        if name not in self._services:
            raise KeyError(f"Servis bulunamadi: {name}")

        health_fn = self._services[name]["health_check_fn"]
        health = self._health_status[name]

        try:
            if asyncio.iscoroutinefunction(health_fn):
                is_healthy = await health_fn()
            else:
                is_healthy = health_fn()

            if is_healthy:
                health.status = "healthy"
                health.failure_count = 0
                self._circuit_breakers[name].record_success()
            else:
                health.status = "degraded"
                health.failure_count += 1
                self._circuit_breakers[name].record_failure()
        except Exception:
            health.status = "down"
            health.failure_count += 1
            self._circuit_breakers[name].record_failure()

        health.last_check = datetime.now(timezone.utc)
        health.circuit_state = self._circuit_breakers[name].state
        return health

    async def execute_with_failover(
        self,
        service: str,
        func: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Fonksiyonu failover destegiyle calistirir.

        Birincil servis basarisiz olursa yedege gecer.

        Args:
            service: Servis adi.
            func: Calistirilacak fonksiyon.
            *args: Fonksiyon argumanlari.
            **kwargs: Fonksiyon keyword argumanlari.

        Returns:
            Fonksiyon sonucu.

        Raises:
            RuntimeError: Hem birincil hem yedek basarisiz.
        """
        # Birincil dene
        try:
            cb = self._circuit_breakers.get(service)
            if cb:
                return await cb.execute(func, *args, **kwargs)
            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            return func(*args, **kwargs)
        except Exception as primary_exc:
            logger.warning(
                "Birincil servis basarisiz (%s): %s", service, primary_exc,
            )

        # Yedek dene
        fallback = self._fallback_map.get(service)
        if fallback and fallback in self._circuit_breakers:
            try:
                cb = self._circuit_breakers[fallback]
                return await cb.execute(func, *args, **kwargs)
            except Exception as fallback_exc:
                logger.error(
                    "Yedek servis de basarisiz (%s): %s",
                    fallback, fallback_exc,
                )
                raise RuntimeError(
                    f"Hem {service} hem {fallback} basarisiz",
                ) from fallback_exc

        raise RuntimeError(
            f"Servis basarisiz ve yedek tanimli degil: {service}",
        )

    async def start(self) -> None:
        """Periyodik saglik kontrolu baslatir."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(
            self._health_loop(),
            name="failover_health_check",
        )
        logger.info("FailoverManager baslatildi")

    async def stop(self) -> None:
        """Saglik kontrolu durdurur."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None
        logger.info("FailoverManager durduruldu")

    async def _health_loop(self) -> None:
        """Periyodik saglik kontrol dongusu."""
        while self._running:
            try:
                await self.check_all_services()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Failover saglik kontrolu hatasi: %s", exc)

            try:
                await asyncio.sleep(self.health_check_interval)
            except asyncio.CancelledError:
                break

    def get_service_status(self) -> dict[str, ServiceHealth]:
        """Tum servislerin saglik durumunu dondurur.

        Returns:
            Servis adi -> saglik durumu eslesmesi.
        """
        return dict(self._health_status)
