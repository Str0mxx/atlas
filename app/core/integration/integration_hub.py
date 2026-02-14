"""ATLAS Entegrasyon Merkezi modulu.

Merkezi entegrasyon noktasi, servis
orkestrasyonu, birlesmis API, izleme
ve analitik.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from app.models.integration import (
    AuthType,
    IntegrationSnapshot,
    ProtocolType,
    ServiceStatus,
    SyncMode,
)

from app.core.integration.api_connector import APIConnector
from app.core.integration.auth_handler import AuthHandler
from app.core.integration.data_sync import DataSync
from app.core.integration.error_handler import IntegrationErrorHandler
from app.core.integration.rate_limiter import RateLimiter
from app.core.integration.response_cache import ResponseCache
from app.core.integration.service_registry import ExternalServiceRegistry
from app.core.integration.webhook_manager import WebhookManager

logger = logging.getLogger(__name__)


class IntegrationHub:
    """Entegrasyon merkezi.

    Tum entegrasyon alt sistemlerini
    birlestiren orkestrator.

    Attributes:
        _connector: API baglayici.
        _auth: Kimlik dogrulama.
        _webhooks: Webhook yoneticisi.
        _sync: Veri senkronizasyonu.
        _registry: Servis kaydi.
        _limiter: Hiz sinirlandirici.
        _cache: Yanit onbellegi.
        _errors: Hata yoneticisi.
    """

    def __init__(
        self,
        default_timeout: int = 30,
        max_retries: int = 3,
        cache_enabled: bool = True,
        rate_limit_default: int = 100,
    ) -> None:
        """Entegrasyon merkezini baslatir.

        Args:
            default_timeout: Varsayilan zaman asimi.
            max_retries: Maks yeniden deneme.
            cache_enabled: Onbellek aktif mi.
            rate_limit_default: Varsayilan hiz limiti.
        """
        self._connector = APIConnector(
            default_timeout=default_timeout,
        )
        self._auth = AuthHandler()
        self._webhooks = WebhookManager(max_retries=max_retries)
        self._sync = DataSync()
        self._registry = ExternalServiceRegistry()
        self._limiter = RateLimiter(
            default_limit=rate_limit_default,
        )
        self._cache = ResponseCache()
        self._errors = IntegrationErrorHandler(
            max_retries=max_retries,
        )

        self._cache_enabled = cache_enabled
        self._started_at = datetime.now(timezone.utc)
        self._total_requests = 0

        logger.info(
            "IntegrationHub baslatildi "
            "(timeout=%d, retries=%d, cache=%s)",
            default_timeout, max_retries, cache_enabled,
        )

    def register_service(
        self,
        name: str,
        url: str,
        protocol: ProtocolType = ProtocolType.REST,
        auth_type: AuthType = AuthType.NONE,
        credentials: dict[str, str] | None = None,
        rate_limit: int | None = None,
    ) -> dict[str, Any]:
        """Servis kaydeder ve yapilandirir.

        Args:
            name: Servis adi.
            url: Servis URL.
            protocol: Protokol.
            auth_type: Dogrulama turu.
            credentials: Kimlik bilgileri.
            rate_limit: Hiz limiti.

        Returns:
            Kayit sonucu.
        """
        # Registry'ye ekle
        self._registry.register_service(name, url)

        # API connector yapilandir
        self._connector.configure_service(
            name, url, protocol,
        )

        # Auth ayarla
        if auth_type != AuthType.NONE and credentials:
            self._auth.register_credentials(
                name, auth_type, credentials,
            )

        # Rate limit ayarla
        if rate_limit:
            self._limiter.set_limit(name, rate_limit)

        return {
            "service": name,
            "url": url,
            "protocol": protocol.value,
            "auth_type": auth_type.value,
            "registered": True,
        }

    def request(
        self,
        service: str,
        method: str = "GET",
        endpoint: str = "/",
        data: dict[str, Any] | None = None,
        use_cache: bool = True,
        priority: int = 0,
    ) -> dict[str, Any]:
        """Birlesmis API istegi yapar.

        Args:
            service: Servis adi.
            method: HTTP metodu.
            endpoint: Endpoint.
            data: Istek verisi.
            use_cache: Onbellek kullan.
            priority: Oncelik.

        Returns:
            Yanit.
        """
        self._total_requests += 1

        # Failover kontrol
        active_service = self._registry.get_active_service(service)

        # Rate limit kontrol
        limit_check = self._limiter.check_limit(
            active_service, priority,
        )
        if not limit_check["allowed"]:
            return {
                "success": False,
                "error": "Rate limit asildi",
                "retry_after": limit_check.get(
                    "retry_after_seconds", 60,
                ),
            }

        # Cache kontrol (sadece GET)
        cache_key = f"{active_service}:{method}:{endpoint}"
        if (self._cache_enabled and use_cache
                and method.upper() == "GET"):
            cached = self._cache.get(cache_key, active_service)
            if cached is not None:
                return {
                    "success": True,
                    "data": cached,
                    "cached": True,
                    "service": active_service,
                }

        # Auth basliklar
        headers = self._auth.get_auth_headers(active_service)

        # Istek yap
        result = self._connector.rest_request(
            active_service, method, endpoint,
            data=data,
        )
        self._limiter.record_request(active_service)

        # Basarili ise cache'le
        if result.get("success") and method.upper() == "GET":
            if self._cache_enabled and use_cache:
                self._cache.set(
                    cache_key,
                    result.get("response", {}),
                    active_service,
                )

        # Saglik guncelle
        self._registry.check_health(
            active_service,
            is_healthy=result.get("success", False),
        )

        result["service"] = active_service
        result["cached"] = False
        return result

    def sync_data(
        self,
        source: str,
        target: str,
        data: list[dict[str, Any]],
        mode: SyncMode = SyncMode.DELTA,
    ) -> dict[str, Any]:
        """Veri senkronize eder.

        Args:
            source: Kaynak.
            target: Hedef.
            data: Veriler.
            mode: Sync modu.

        Returns:
            Sync sonucu.
        """
        if mode == SyncMode.FULL:
            record = self._sync.full_sync(source, target, data)
        elif mode == SyncMode.DELTA:
            record = self._sync.delta_sync(source, target, data)
        else:
            record = self._sync.delta_sync(source, target, data)

        return {
            "sync_id": record.sync_id,
            "mode": mode.value,
            "records_synced": record.records_synced,
            "success": record.success,
        }

    def process_webhook(
        self,
        event_type: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Webhook isler.

        Args:
            event_type: Olay turu.
            payload: Veri yuku.

        Returns:
            Isleme sonucu.
        """
        return self._webhooks.process_incoming(
            event_type, payload,
        )

    def get_service_health(
        self,
        service: str = "",
    ) -> dict[str, Any]:
        """Servis sagligini getirir.

        Args:
            service: Servis filtresi.

        Returns:
            Saglik bilgisi.
        """
        if service:
            svc = self._registry.get_service(service)
            if not svc:
                return {"error": "Servis bulunamadi"}
            return {
                "service": service,
                "status": svc["status"],
                "check_count": svc["check_count"],
                "failure_count": svc["failure_count"],
            }

        services = self._registry.discover_services()
        return {
            "total": len(services),
            "active": self._registry.active_count,
            "services": [
                {
                    "name": s["name"],
                    "status": s["status"],
                }
                for s in services
            ],
        }

    def get_snapshot(self) -> IntegrationSnapshot:
        """Entegrasyon goruntusu getirir.

        Returns:
            IntegrationSnapshot nesnesi.
        """
        uptime = (
            datetime.now(timezone.utc) - self._started_at
        ).total_seconds()

        cache_stats = self._cache.get_stats()

        return IntegrationSnapshot(
            total_services=self._registry.service_count,
            active_services=self._registry.active_count,
            total_requests=self._total_requests,
            total_errors=self._errors.error_count,
            cache_hit_rate=cache_stats["hit_rate"],
            avg_latency_ms=0.0,
            webhooks_processed=self._webhooks.event_count,
            syncs_completed=self._sync.sync_count,
            uptime_seconds=round(uptime, 2),
        )

    # Alt sistem erisimi
    @property
    def connector(self) -> APIConnector:
        """API baglayici."""
        return self._connector

    @property
    def auth(self) -> AuthHandler:
        """Kimlik dogrulama."""
        return self._auth

    @property
    def webhooks(self) -> WebhookManager:
        """Webhook yoneticisi."""
        return self._webhooks

    @property
    def sync(self) -> DataSync:
        """Veri senkronizasyonu."""
        return self._sync

    @property
    def registry(self) -> ExternalServiceRegistry:
        """Servis kaydi."""
        return self._registry

    @property
    def limiter(self) -> RateLimiter:
        """Hiz sinirlandirici."""
        return self._limiter

    @property
    def cache(self) -> ResponseCache:
        """Yanit onbellegi."""
        return self._cache

    @property
    def errors(self) -> IntegrationErrorHandler:
        """Hata yoneticisi."""
        return self._errors

    @property
    def total_requests(self) -> int:
        """Toplam istek sayisi."""
        return self._total_requests
