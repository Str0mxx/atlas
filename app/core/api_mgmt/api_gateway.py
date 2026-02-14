"""ATLAS API Gateway modulu.

Tam gateway islevseligi, guvenlik
entegrasyonu, onbellekleme, izleme
ve yapilandirma.
"""

import logging
import time
from typing import Any

from app.core.api_mgmt.api_registry import (
    APIRegistry,
)
from app.core.api_mgmt.request_router import (
    RequestRouter,
)
from app.core.api_mgmt.rate_limiter import (
    APIRateLimiter,
)
from app.core.api_mgmt.request_validator import (
    RequestValidator,
)
from app.core.api_mgmt.response_transformer import (
    ResponseTransformer,
)
from app.core.api_mgmt.api_versioner import (
    APIVersioner,
)
from app.core.api_mgmt.documentation_generator import (
    DocumentationGenerator,
)
from app.core.api_mgmt.analytics_collector import (
    APIAnalyticsCollector,
)

logger = logging.getLogger(__name__)


class APIGateway:
    """API Gateway orkestratoru.

    Tum API yonetim bilesenlerini
    koordine eder.

    Attributes:
        registry: API kayit defteri.
        router: Istek yonlendirici.
        rate_limiter: Hiz sinirlandirici.
        validator: Istek dogrulayici.
        transformer: Yanit donusturucu.
        versioner: API surumleyici.
        docs: Dokumantasyon ureticisi.
        analytics: Analitik toplayici.
    """

    def __init__(
        self,
        gateway_name: str = "ATLAS Gateway",
    ) -> None:
        """API Gateway baslatir.

        Args:
            gateway_name: Gateway adi.
        """
        self._name = gateway_name
        self._started_at = time.time()

        self.registry = APIRegistry()
        self.router = RequestRouter()
        self.rate_limiter = APIRateLimiter()
        self.validator = RequestValidator()
        self.transformer = ResponseTransformer()
        self.versioner = APIVersioner()
        self.docs = DocumentationGenerator()
        self.analytics = APIAnalyticsCollector()

        self._middleware: list[
            dict[str, Any]
        ] = []
        self._cors_config: dict[str, Any] = {}

        logger.info(
            "APIGateway baslatildi: %s",
            gateway_name,
        )

    def handle_request(
        self,
        path: str,
        method: str = "GET",
        headers: dict[str, str] | None = None,
        body: Any = None,
        params: dict[str, Any] | None = None,
        client_id: str = "",
    ) -> dict[str, Any]:
        """Istegi isle.

        Args:
            path: Istek yolu.
            method: HTTP metodu.
            headers: Basliklar.
            body: Istek govdesi.
            params: Sorgu parametreleri.
            client_id: Istemci ID.

        Returns:
            Islem sonucu.
        """
        start_time = time.time()
        headers = headers or {}
        params = params or {}

        # 1. Hiz siniri kontrolu
        rate_key = client_id or "anonymous"
        rate_result = self.rate_limiter.check(
            rate_key,
        )
        if not rate_result["allowed"]:
            elapsed = (
                time.time() - start_time
            ) * 1000
            self.analytics.record_request(
                endpoint=path,
                method=method,
                status_code=429,
                response_time=elapsed,
                client_id=client_id,
            )
            return {
                "status_code": 429,
                "body": {
                    "error": "rate_limit_exceeded",
                },
                "headers": {
                    "X-RateLimit-Remaining": str(
                        rate_result["remaining"],
                    ),
                },
            }

        # 2. Surum cozumleme
        request_info = {
            "path": path,
            "headers": headers,
            "params": params,
        }
        version = self.versioner.resolve_version(
            request_info,
        )

        # 3. Rota cozumleme
        route_result = self.router.resolve(
            path=path,
            method=method,
            version=version or None,
        )

        if not route_result.get("resolved"):
            elapsed = (
                time.time() - start_time
            ) * 1000
            self.analytics.record_request(
                endpoint=path,
                method=method,
                status_code=404,
                response_time=elapsed,
                client_id=client_id,
            )
            return {
                "status_code": 404,
                "body": {"error": "not_found"},
                "headers": {},
            }

        # 4. Basarili yanit
        elapsed = (
            time.time() - start_time
        ) * 1000
        self.analytics.record_request(
            endpoint=path,
            method=method,
            status_code=200,
            response_time=elapsed,
            client_id=client_id,
        )

        response_body = {
            "target": route_result["target"],
            "version": route_result.get(
                "version", "",
            ),
        }

        # Yaniti sar
        wrapped = self.transformer.wrap_response(
            data=response_body,
            status="success",
        )

        return {
            "status_code": 200,
            "body": wrapped,
            "headers": {
                "X-RateLimit-Remaining": str(
                    rate_result["remaining"],
                ),
                "X-Gateway": self._name,
            },
        }

    def register_api(
        self,
        name: str,
        base_url: str,
        version: str = "v1",
        endpoints: list[str] | None = None,
    ) -> dict[str, Any]:
        """API kaydeder ve rotalar ekler.

        Args:
            name: API adi.
            base_url: Temel URL.
            version: Surum.
            endpoints: Endpointler.

        Returns:
            Kayit bilgisi.
        """
        # Registry'ye kaydet
        api = self.registry.register(
            name=name,
            base_path=base_url,
            version=version,
        )

        # Endpointleri ekle
        eps = endpoints or []
        for ep in eps:
            self.registry.add_endpoint(
                api_id=api.api_id,
                path=ep,
            )
            # Rota ekle
            self.router.add_route(
                path=ep,
                target=f"{base_url}{ep}",
                version=version,
            )
            # Dokumantasyona ekle
            self.docs.add_endpoint(
                path=ep,
                summary=f"{name} - {ep}",
            )

        # Surum kaydet
        self.versioner.register_version(
            version=version,
            description=f"{name} {version}",
            endpoints=eps,
        )

        return {
            "api": api,
            "endpoints_added": len(eps),
            "version": version,
        }

    def add_middleware(
        self,
        name: str,
        priority: int = 100,
        config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Middleware ekler.

        Args:
            name: Middleware adi.
            priority: Oncelik.
            config: Yapilandirma.

        Returns:
            Middleware bilgisi.
        """
        mw = {
            "name": name,
            "priority": priority,
            "config": config or {},
            "enabled": True,
        }
        self._middleware.append(mw)
        self._middleware.sort(
            key=lambda m: m["priority"],
        )
        return mw

    def configure_cors(
        self,
        origins: list[str] | None = None,
        methods: list[str] | None = None,
        headers: list[str] | None = None,
    ) -> dict[str, Any]:
        """CORS yapilandirir.

        Args:
            origins: Izinli kaynaklar.
            methods: Izinli metotlar.
            headers: Izinli basliklar.

        Returns:
            CORS yapisi.
        """
        self._cors_config = {
            "origins": origins or ["*"],
            "methods": methods or [
                "GET", "POST", "PUT", "DELETE",
            ],
            "headers": headers or [
                "Content-Type", "Authorization",
            ],
        }
        return self._cors_config

    def get_health(self) -> dict[str, Any]:
        """Saglik kontrolu.

        Returns:
            Saglik bilgisi.
        """
        uptime = time.time() - self._started_at
        return {
            "status": "healthy",
            "name": self._name,
            "uptime": round(uptime, 2),
            "apis": self.registry.api_count,
            "routes": self.router.route_count,
            "requests": (
                self.analytics.request_count
            ),
            "errors": (
                self.analytics.error_count
            ),
        }

    def get_analytics(self) -> dict[str, Any]:
        """Analitik ozeti.

        Returns:
            Analitik bilgisi.
        """
        return {
            "requests": (
                self.analytics.request_count
            ),
            "errors": (
                self.analytics.error_count
            ),
            "clients": (
                self.analytics.client_count
            ),
            "response_times": (
                self.analytics
                .get_response_time_stats()
            ),
            "top_endpoints": (
                self.analytics
                .get_top_endpoints(5)
            ),
            "usage_patterns": (
                self.analytics
                .get_usage_patterns()
            ),
        }

    def snapshot(self) -> dict[str, Any]:
        """Gateway durumunu dondurur.

        Returns:
            Durum bilgisi.
        """
        return {
            "name": self._name,
            "uptime": round(
                time.time() - self._started_at,
                2,
            ),
            "apis": self.registry.api_count,
            "routes": self.router.route_count,
            "rate_limits": (
                self.rate_limiter.limit_count
            ),
            "validators": (
                self.validator.schema_count
            ),
            "versions": (
                self.versioner.version_count
            ),
            "docs_endpoints": (
                self.docs.endpoint_count
            ),
            "analytics_requests": (
                self.analytics.request_count
            ),
            "middleware_count": len(
                self._middleware,
            ),
            "cors_enabled": bool(
                self._cors_config,
            ),
        }

    @property
    def name(self) -> str:
        """Gateway adi."""
        return self._name

    @property
    def middleware_count(self) -> int:
        """Middleware sayisi."""
        return len(self._middleware)

    @property
    def cors_enabled(self) -> bool:
        """CORS aktif mi."""
        return bool(self._cors_config)
