"""
LLM yonlendirici orkestrator modulu.

Tam LLM orkestrasyon, analiz-sec-
yonlendir-yedek pipeline,
coklu saglayici, analitik.
"""

import logging
from typing import Any

from .cost_per_token_tracker import (
    CostPerTokenTracker,
)
from .fallback_router import (
    FallbackRouter,
)
from .latency_optimizer import (
    LatencyOptimizer,
)
from .model_performance_comparator import (
    ModelPerformanceComparator,
)
from .model_registry import ModelRegistry
from .model_selector import ModelSelector
from .provider_health_monitor import (
    ProviderHealthMonitor,
)
from .task_complexity_analyzer import (
    TaskComplexityAnalyzer,
)

logger = logging.getLogger(__name__)


class LLMRouterOrchestrator:
    """LLM yonlendirici orkestrator.

    Analyze -> Select -> Route -> Fallback
    pipeline ile coklu saglayici
    desteği ve analitik.

    Attributes:
        registry: Model kayit defteri.
        analyzer: Karmasiklik analizcisi.
        selector: Model secici.
        router: Yedek yonlendirici.
        cost_tracker: Maliyet takipci.
        latency: Gecikme optimizasyonu.
        comparator: Performans karsilast.
        health: Saglik izleyici.
    """

    def __init__(
        self,
        default_provider: str = "",
        cost_optimization: bool = True,
        auto_fallback: bool = True,
        latency_threshold_ms: int = 5000,
    ) -> None:
        """Orkestratoru baslatir.

        Args:
            default_provider: Varsayilan.
            cost_optimization: Maliyet opt.
            auto_fallback: Oto yedek.
            latency_threshold_ms: Gecikme.
        """
        self._default_provider = (
            default_provider
        )
        self._cost_optimization = (
            cost_optimization
        )
        self._auto_fallback = auto_fallback
        self._latency_threshold = (
            latency_threshold_ms
        )

        self.registry = ModelRegistry()
        self.analyzer = (
            TaskComplexityAnalyzer()
        )
        self.selector = ModelSelector()
        self.router = FallbackRouter()
        self.cost_tracker = (
            CostPerTokenTracker()
        )
        self.latency = LatencyOptimizer(
            default_timeout_ms=(
                latency_threshold_ms
            ),
        )
        self.comparator = (
            ModelPerformanceComparator()
        )
        self.health = (
            ProviderHealthMonitor()
        )

        logger.info(
            "LLMRouterOrchestrator "
            "baslatildi"
        )

    def route_task(
        self,
        task_text: str = "",
        context: str = "",
        required_capabilities: (
            list[str] | None
        ) = None,
        preferred_provider: str = "",
        max_cost_per_1k: float = 0.0,
        strategy: str = "balanced",
    ) -> dict[str, Any]:
        """Gorevi yonlendirir.

        Analyze -> Select -> Route pipeline.

        Args:
            task_text: Gorev metni.
            context: Baglam.
            required_capabilities: Gerekler.
            preferred_provider: Tercih.
            max_cost_per_1k: Maks maliyet.
            strategy: Strateji.

        Returns:
            Yonlendirme sonucu.
        """
        try:
            # 1. Karmasiklik analizi
            analysis = (
                self.analyzer
                .analyze_complexity(
                    task_text=task_text,
                    context=context,
                )
            )

            if not analysis.get(
                "analyzed"
            ):
                return {
                    "routed": False,
                    "error": (
                        "Analiz basarisiz"
                    ),
                }

            complexity = analysis[
                "complexity_score"
            ]

            # Strateji ayarla
            if self._cost_optimization:
                if complexity <= 0.3:
                    strategy = (
                        "lowest_cost"
                    )

            # 2. Uygun modeller bul
            provider = (
                preferred_provider
                or self._default_provider
            )
            models_result = (
                self.registry
                .find_by_capability(
                    provider=provider,
                )
            )

            available = []
            if models_result.get(
                "retrieved"
            ):
                available = (
                    models_result["models"]
                )

            if not available:
                # Tum modeller
                all_m = (
                    self.registry
                    .find_by_capability()
                )
                if all_m.get("retrieved"):
                    available = all_m[
                        "models"
                    ]

            if not available:
                return {
                    "routed": False,
                    "error": (
                        "Uygun model yok"
                    ),
                }

            # 3. Model sec
            selection = (
                self.selector.select_model(
                    available_models=(
                        available
                    ),
                    required_capabilities=(
                        required_capabilities
                    ),
                    strategy=strategy,
                    max_cost_per_1k=(
                        max_cost_per_1k
                    ),
                    complexity_score=(
                        complexity
                    ),
                )
            )

            if not selection.get(
                "selected"
            ):
                return {
                    "routed": False,
                    "error": (
                        "Model secilemedi"
                    ),
                }

            selected_model = selection[
                "model_id"
            ]

            # 4. Yonlendir (fallback ile)
            if self._auto_fallback:
                route_result = (
                    self.router
                    .route_request(
                        primary_model=(
                            selected_model
                        ),
                    )
                )

                if route_result.get(
                    "routed"
                ):
                    final_model = (
                        route_result[
                            "routed_to"
                        ]
                    )
                else:
                    final_model = (
                        selected_model
                    )
            else:
                final_model = (
                    selected_model
                )

            # Kullanim artir
            self.registry.increment_usage(
                final_model
            )

            return {
                "model_id": final_model,
                "complexity_score": (
                    complexity
                ),
                "complexity_level": (
                    analysis[
                        "complexity_level"
                    ]
                ),
                "domain": analysis[
                    "domain"
                ],
                "strategy": strategy,
                "selection_score": (
                    selection["score"]
                ),
                "estimated_tokens": (
                    analysis[
                        "estimated_tokens"
                    ]
                ),
                "routed": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "routed": False,
                "error": str(e),
            }

    def record_completion(
        self,
        model_id: str = "",
        provider: str = "",
        input_tokens: int = 0,
        output_tokens: int = 0,
        latency_ms: float = 0.0,
        input_cost_per_1k: float = 0.0,
        output_cost_per_1k: float = 0.0,
        quality_score: float = 0.0,
        task_id: str = "",
        task_domain: str = "",
        success: bool = True,
    ) -> dict[str, Any]:
        """Tamamlanma kaydeder.

        Args:
            model_id: Model ID.
            provider: Saglayici.
            input_tokens: Girdi token.
            output_tokens: Cikti token.
            latency_ms: Gecikme.
            input_cost_per_1k: Girdi mali.
            output_cost_per_1k: Cikti mali.
            quality_score: Kalite puani.
            task_id: Gorev ID.
            task_domain: Alan.
            success: Basarili mi.

        Returns:
            Kayit bilgisi.
        """
        try:
            # Maliyet kaydi
            cost_result = (
                self.cost_tracker
                .record_usage(
                    model_id=model_id,
                    provider=provider,
                    input_tokens=(
                        input_tokens
                    ),
                    output_tokens=(
                        output_tokens
                    ),
                    input_cost_per_1k=(
                        input_cost_per_1k
                    ),
                    output_cost_per_1k=(
                        output_cost_per_1k
                    ),
                    task_id=task_id,
                )
            )

            # Gecikme kaydi
            self.latency.record_latency(
                model_id=model_id,
                provider=provider,
                latency_ms=latency_ms,
                input_tokens=input_tokens,
                output_tokens=(
                    output_tokens
                ),
                success=success,
                task_id=task_id,
            )

            # Kalite kaydi
            if quality_score > 0:
                self.comparator\
                    .evaluate_response(
                    model_id=model_id,
                    task_id=task_id,
                    task_domain=(
                        task_domain
                    ),
                    overall_score=(
                        quality_score
                    ),
                )

            # Saglik kaydi
            self.health.record_request(
                provider_id=provider,
                success=success,
                tokens_used=(
                    input_tokens
                    + output_tokens
                ),
            )

            return {
                "model_id": model_id,
                "total_cost": (
                    cost_result.get(
                        "total_cost", 0
                    )
                ),
                "latency_ms": latency_ms,
                "recorded": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "recorded": False,
                "error": str(e),
            }

    def setup_provider(
        self,
        provider_id: str = "",
        name: str = "",
        base_url: str = "",
        api_type: str = "rest",
        auth_type: str = "api_key",
        rate_limit_rpm: int = 60,
        rate_limit_tpm: int = 100000,
        models: (
            list[dict] | None
        ) = None,
    ) -> dict[str, Any]:
        """Saglayici kurulumu.

        Args:
            provider_id: Saglayici ID.
            name: Saglayici adi.
            base_url: Temel URL.
            api_type: API tipi.
            auth_type: Auth tipi.
            rate_limit_rpm: RPM limiti.
            rate_limit_tpm: TPM limiti.
            models: Modeller.

        Returns:
            Kurulum bilgisi.
        """
        try:
            # Kayit defterine ekle
            self.registry.register_provider(
                name=provider_id,
                api_type=api_type,
                base_url=base_url,
                auth_type=auth_type,
                rate_limit=rate_limit_rpm,
            )

            # Saglik izleyiciye ekle
            self.health.register_provider(
                provider_id=provider_id,
                name=name,
                base_url=base_url,
                rate_limit_rpm=(
                    rate_limit_rpm
                ),
                rate_limit_tpm=(
                    rate_limit_tpm
                ),
            )

            # Modelleri kaydet
            registered = 0
            for m in (models or []):
                result = (
                    self.registry
                    .register_model(
                        model_id=m.get(
                            "model_id", ""
                        ),
                        provider=(
                            provider_id
                        ),
                        name=m.get(
                            "name", ""
                        ),
                        capabilities=(
                            m.get(
                                "capabilities"
                            )
                        ),
                        max_tokens=m.get(
                            "max_tokens",
                            4096,
                        ),
                        input_cost_per_1k=(
                            m.get(
                                "input_cost"
                                "_per_1k",
                                0.0,
                            )
                        ),
                        output_cost_per_1k=(
                            m.get(
                                "output_cost"
                                "_per_1k",
                                0.0,
                            )
                        ),
                        context_window=(
                            m.get(
                                "context"
                                "_window",
                                4096,
                            )
                        ),
                    )
                )
                if result.get(
                    "registered"
                ):
                    registered += 1

            return {
                "provider_id": (
                    provider_id
                ),
                "models_registered": (
                    registered
                ),
                "setup": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "setup": False,
                "error": str(e),
            }

    def get_analytics(
        self,
    ) -> dict[str, Any]:
        """Analitik getirir."""
        try:
            cost_summary = (
                self.cost_tracker
                .get_summary()
            )
            latency_summary = (
                self.latency.get_summary()
            )
            perf_summary = (
                self.comparator
                .get_summary()
            )
            health_summary = (
                self.health.get_summary()
            )
            registry_summary = (
                self.registry.get_summary()
            )

            return {
                "registry": (
                    registry_summary
                ),
                "cost": cost_summary,
                "latency": latency_summary,
                "performance": (
                    perf_summary
                ),
                "health": health_summary,
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
                "default_provider": (
                    self._default_provider
                ),
                "cost_optimization": (
                    self._cost_optimization
                ),
                "auto_fallback": (
                    self._auto_fallback
                ),
                "latency_threshold_ms": (
                    self._latency_threshold
                ),
                "total_models": (
                    self.registry
                    .model_count
                ),
                "total_cost": (
                    self.cost_tracker
                    .total_cost
                ),
                "cache_hit_rate": (
                    self.latency
                    .cache_hit_rate
                ),
                "healthy_providers": (
                    self.health
                    .healthy_count
                ),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }
