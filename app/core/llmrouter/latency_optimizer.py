"""
Gecikme optimizasyonu modulu.

Gecikme takibi, en hizli rota,
onbellekleme stratejileri, paralel
istekler, zaman asimi yonetimi.
"""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class LatencyOptimizer:
    """Gecikme optimizasyonu.

    Attributes:
        _latency_records: Gecikme kayitlari.
        _cache_entries: Onbellek girdileri.
        _timeout_config: Zaman asimi ayarlari.
        _stats: Istatistikler.
    """

    CACHE_STRATEGIES: list[str] = [
        "exact_match",
        "semantic_similarity",
        "prefix_match",
        "template_match",
    ]

    def __init__(
        self,
        default_timeout_ms: int = 30000,
        cache_ttl_seconds: int = 3600,
    ) -> None:
        """Optimizasyonu baslatir.

        Args:
            default_timeout_ms: Varsayilan timeout.
            cache_ttl_seconds: Onbellek suresi.
        """
        self._default_timeout = (
            default_timeout_ms
        )
        self._cache_ttl = cache_ttl_seconds
        self._latency_records: list[
            dict
        ] = []
        self._model_latencies: dict[
            str, list[float]
        ] = {}
        self._cache_entries: dict[
            str, dict
        ] = {}
        self._timeout_config: dict[
            str, int
        ] = {}
        self._stats: dict[str, int] = {
            "records_logged": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "timeouts_occurred": 0,
            "optimizations_made": 0,
        }
        logger.info(
            "LatencyOptimizer baslatildi"
        )

    @property
    def cache_hit_rate(self) -> float:
        """Onbellek isabet orani."""
        total = (
            self._stats["cache_hits"]
            + self._stats["cache_misses"]
        )
        if total == 0:
            return 0.0
        return round(
            self._stats["cache_hits"]
            / total,
            4,
        )

    def record_latency(
        self,
        model_id: str = "",
        provider: str = "",
        latency_ms: float = 0.0,
        input_tokens: int = 0,
        output_tokens: int = 0,
        success: bool = True,
        task_id: str = "",
    ) -> dict[str, Any]:
        """Gecikme kaydeder.

        Args:
            model_id: Model ID.
            provider: Saglayici.
            latency_ms: Gecikme (ms).
            input_tokens: Girdi token.
            output_tokens: Cikti token.
            success: Basarili mi.
            task_id: Gorev ID.

        Returns:
            Kayit bilgisi.
        """
        try:
            rid = f"lt_{uuid4()!s:.8}"

            record = {
                "record_id": rid,
                "model_id": model_id,
                "provider": provider,
                "latency_ms": latency_ms,
                "input_tokens": input_tokens,
                "output_tokens": (
                    output_tokens
                ),
                "success": success,
                "task_id": task_id,
                "recorded_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
            }
            self._latency_records.append(
                record
            )

            if model_id not in (
                self._model_latencies
            ):
                self._model_latencies[
                    model_id
                ] = []
            self._model_latencies[
                model_id
            ].append(latency_ms)

            self._stats[
                "records_logged"
            ] += 1

            # Timeout kontrol
            timeout = (
                self._timeout_config.get(
                    model_id,
                    self._default_timeout,
                )
            )
            if latency_ms > timeout:
                self._stats[
                    "timeouts_occurred"
                ] += 1

            return {
                "record_id": rid,
                "latency_ms": latency_ms,
                "recorded": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "recorded": False,
                "error": str(e),
            }

    def get_fastest_model(
        self,
        candidates: (
            list[str] | None
        ) = None,
        min_samples: int = 3,
    ) -> dict[str, Any]:
        """En hizli modeli bulur.

        Args:
            candidates: Aday modeller.
            min_samples: Min ornek sayisi.

        Returns:
            En hizli model bilgisi.
        """
        try:
            models = (
                candidates
                or list(
                    self._model_latencies
                    .keys()
                )
            )

            results = []
            for m in models:
                lats = (
                    self._model_latencies
                    .get(m, [])
                )
                if len(lats) < min_samples:
                    continue

                avg = round(
                    sum(lats) / len(lats), 2
                )
                p50 = round(
                    sorted(lats)[
                        len(lats) // 2
                    ],
                    2,
                )
                p95_idx = int(
                    len(lats) * 0.95
                )
                p95 = round(
                    sorted(lats)[
                        min(
                            p95_idx,
                            len(lats) - 1,
                        )
                    ],
                    2,
                )

                results.append({
                    "model_id": m,
                    "avg_latency_ms": avg,
                    "p50_latency_ms": p50,
                    "p95_latency_ms": p95,
                    "sample_count": (
                        len(lats)
                    ),
                })

            if not results:
                return {
                    "found": False,
                    "error": (
                        "Yeterli veri yok"
                    ),
                }

            results.sort(
                key=lambda x: x[
                    "avg_latency_ms"
                ]
            )

            return {
                "fastest": results[0][
                    "model_id"
                ],
                "rankings": results,
                "found": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "found": False,
                "error": str(e),
            }

    def cache_response(
        self,
        cache_key: str = "",
        response: str = "",
        model_id: str = "",
        strategy: str = "exact_match",
    ) -> dict[str, Any]:
        """Yaniti onbelleğe alir.

        Args:
            cache_key: Onbellek anahtari.
            response: Yanit.
            model_id: Model ID.
            strategy: Onbellek stratejisi.

        Returns:
            Onbellek bilgisi.
        """
        try:
            if strategy not in (
                self.CACHE_STRATEGIES
            ):
                return {
                    "cached": False,
                    "error": (
                        f"Gecersiz: "
                        f"{strategy}"
                    ),
                }

            self._cache_entries[
                cache_key
            ] = {
                "cache_key": cache_key,
                "response": response,
                "model_id": model_id,
                "strategy": strategy,
                "created_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
                "hit_count": 0,
            }

            return {
                "cache_key": cache_key,
                "strategy": strategy,
                "cached": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "cached": False,
                "error": str(e),
            }

    def lookup_cache(
        self,
        cache_key: str = "",
    ) -> dict[str, Any]:
        """Onbellekte arar.

        Args:
            cache_key: Anahtar.

        Returns:
            Onbellek sonucu.
        """
        try:
            entry = (
                self._cache_entries.get(
                    cache_key
                )
            )
            if entry:
                entry["hit_count"] += 1
                self._stats[
                    "cache_hits"
                ] += 1
                return {
                    "response": entry[
                        "response"
                    ],
                    "model_id": entry[
                        "model_id"
                    ],
                    "hit": True,
                }

            self._stats[
                "cache_misses"
            ] += 1
            return {"hit": False}

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "hit": False,
                "error": str(e),
            }

    def set_timeout(
        self,
        model_id: str = "",
        timeout_ms: int = 0,
    ) -> dict[str, Any]:
        """Zaman asimi ayarlar.

        Args:
            model_id: Model ID.
            timeout_ms: Zaman asimi (ms).

        Returns:
            Ayar bilgisi.
        """
        try:
            t = (
                timeout_ms
                or self._default_timeout
            )
            self._timeout_config[
                model_id
            ] = t

            return {
                "model_id": model_id,
                "timeout_ms": t,
                "set": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "set": False,
                "error": str(e),
            }

    def get_latency_stats(
        self,
        model_id: str = "",
    ) -> dict[str, Any]:
        """Model gecikme istatistikleri.

        Args:
            model_id: Model ID.

        Returns:
            Gecikme istatistikleri.
        """
        try:
            lats = (
                self._model_latencies.get(
                    model_id, []
                )
            )
            if not lats:
                return {
                    "retrieved": False,
                    "error": "Veri yok",
                }

            sorted_lats = sorted(lats)
            avg = round(
                sum(lats) / len(lats), 2
            )
            p50 = round(
                sorted_lats[
                    len(lats) // 2
                ],
                2,
            )
            p95_idx = int(
                len(lats) * 0.95
            )
            p95 = round(
                sorted_lats[
                    min(
                        p95_idx,
                        len(lats) - 1,
                    )
                ],
                2,
            )

            return {
                "model_id": model_id,
                "avg_latency_ms": avg,
                "min_latency_ms": round(
                    min(lats), 2
                ),
                "max_latency_ms": round(
                    max(lats), 2
                ),
                "p50_latency_ms": p50,
                "p95_latency_ms": p95,
                "sample_count": len(lats),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }

    def optimize_routing(
        self,
        task_latency_budget_ms: (
            float
        ) = 0.0,
    ) -> dict[str, Any]:
        """Yonlendirme optimize eder.

        Args:
            task_latency_budget_ms: Butce.

        Returns:
            Optimizasyon onerisi.
        """
        try:
            recommendations = []

            for m, lats in (
                self._model_latencies
                .items()
            ):
                if not lats:
                    continue

                avg = sum(lats) / len(lats)

                if (
                    task_latency_budget_ms
                    > 0
                    and avg
                    > task_latency_budget_ms
                ):
                    recommendations.append({
                        "model_id": m,
                        "avg_latency_ms": (
                            round(avg, 2)
                        ),
                        "action": (
                            "consider_alternative"
                        ),
                        "reason": (
                            "Butce asimi"
                        ),
                    })
                elif avg > 10000:
                    recommendations.append({
                        "model_id": m,
                        "avg_latency_ms": (
                            round(avg, 2)
                        ),
                        "action": (
                            "enable_caching"
                        ),
                        "reason": (
                            "Yuksek gecikme"
                        ),
                    })

            self._stats[
                "optimizations_made"
            ] += 1

            return {
                "recommendations": (
                    recommendations
                ),
                "total_models": len(
                    self._model_latencies
                ),
                "optimized": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "optimized": False,
                "error": str(e),
            }

    def get_summary(
        self,
    ) -> dict[str, Any]:
        """Ozet getirir."""
        try:
            return {
                "total_records": len(
                    self._latency_records
                ),
                "models_tracked": len(
                    self._model_latencies
                ),
                "cache_entries": len(
                    self._cache_entries
                ),
                "cache_hit_rate": (
                    self.cache_hit_rate
                ),
                "timeout_configs": len(
                    self._timeout_config
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
