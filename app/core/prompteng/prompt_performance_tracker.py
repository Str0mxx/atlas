"""
Prompt performans takip modulu.

Basari orani takibi, kalite metrikleri,
prompt basi maliyet, gecikme takibi,
iyilestirme trendleri.
"""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class PromptPerformanceTracker:
    """Prompt performans takipçisi.

    Attributes:
        _records: Performans kayitlari.
        _prompts: Takip edilen promptlar.
        _trends: Trend verileri.
        _stats: Istatistikler.
    """

    METRICS: list[str] = [
        "success_rate",
        "quality_score",
        "latency_ms",
        "cost_per_call",
        "token_efficiency",
        "user_satisfaction",
    ]

    def __init__(self) -> None:
        """Takipciyi baslatir."""
        self._records: list[dict] = []
        self._prompts: dict[
            str, dict
        ] = {}
        self._trends: dict[
            str, list[dict]
        ] = {}
        self._stats: dict[str, int] = {
            "records_tracked": 0,
            "prompts_monitored": 0,
            "trends_analyzed": 0,
            "alerts_generated": 0,
        }
        logger.info(
            "PromptPerformanceTracker "
            "baslatildi"
        )

    @property
    def record_count(self) -> int:
        """Kayit sayisi."""
        return len(self._records)

    def register_prompt(
        self,
        name: str = "",
        prompt_text: str = "",
        model: str = "",
        domain: str = "",
        version: int = 1,
    ) -> dict[str, Any]:
        """Promptu takibe alir.

        Args:
            name: Prompt adi.
            prompt_text: Prompt metni.
            model: Model.
            domain: Alan.
            version: Versiyon.

        Returns:
            Kayit bilgisi.
        """
        try:
            pid = f"pp_{uuid4()!s:.8}"

            self._prompts[pid] = {
                "prompt_id": pid,
                "name": name,
                "prompt_text": prompt_text,
                "model": model,
                "domain": domain,
                "version": version,
                "total_calls": 0,
                "successes": 0,
                "total_latency": 0.0,
                "total_cost": 0.0,
                "total_tokens": 0,
                "quality_scores": [],
                "created_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
            }

            self._trends[pid] = []
            self._stats[
                "prompts_monitored"
            ] += 1

            return {
                "prompt_id": pid,
                "name": name,
                "registered": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "registered": False,
                "error": str(e),
            }

    def record_execution(
        self,
        prompt_id: str = "",
        success: bool = True,
        quality_score: float = 0.0,
        latency_ms: float = 0.0,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cost: float = 0.0,
        metadata: dict | None = None,
    ) -> dict[str, Any]:
        """Calistirma kaydeder.

        Args:
            prompt_id: Prompt ID.
            success: Basarili mi.
            quality_score: Kalite puani.
            latency_ms: Gecikme ms.
            input_tokens: Giris tokenlari.
            output_tokens: Cikis tokenlari.
            cost: Maliyet.
            metadata: Ek veri.

        Returns:
            Kayit bilgisi.
        """
        try:
            prompt = self._prompts.get(
                prompt_id
            )
            if not prompt:
                return {
                    "recorded": False,
                    "error": (
                        "Prompt bulunamadi"
                    ),
                }

            total_tokens = (
                input_tokens + output_tokens
            )
            now = datetime.now(
                timezone.utc
            ).isoformat()

            record = {
                "prompt_id": prompt_id,
                "success": success,
                "quality_score": (
                    quality_score
                ),
                "latency_ms": latency_ms,
                "input_tokens": input_tokens,
                "output_tokens": (
                    output_tokens
                ),
                "total_tokens": total_tokens,
                "cost": cost,
                "metadata": metadata or {},
                "recorded_at": now,
            }
            self._records.append(record)

            # Prompt istatistikleri
            prompt["total_calls"] += 1
            if success:
                prompt["successes"] += 1
            prompt["total_latency"] += (
                latency_ms
            )
            prompt["total_cost"] += cost
            prompt["total_tokens"] += (
                total_tokens
            )
            if quality_score > 0:
                prompt[
                    "quality_scores"
                ].append(quality_score)

            # Trend verisi
            self._trends[prompt_id].append({
                "success": success,
                "quality": quality_score,
                "latency": latency_ms,
                "cost": cost,
                "tokens": total_tokens,
                "at": now,
            })

            self._stats[
                "records_tracked"
            ] += 1

            return {
                "prompt_id": prompt_id,
                "total_calls": prompt[
                    "total_calls"
                ],
                "recorded": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "recorded": False,
                "error": str(e),
            }

    def get_metrics(
        self,
        prompt_id: str = "",
    ) -> dict[str, Any]:
        """Metrikleri getirir.

        Args:
            prompt_id: Prompt ID.

        Returns:
            Metrik bilgisi.
        """
        try:
            prompt = self._prompts.get(
                prompt_id
            )
            if not prompt:
                return {
                    "retrieved": False,
                    "error": (
                        "Prompt bulunamadi"
                    ),
                }

            calls = prompt["total_calls"]
            if calls == 0:
                return {
                    "prompt_id": prompt_id,
                    "total_calls": 0,
                    "retrieved": True,
                }

            success_rate = (
                prompt["successes"] / calls
            )
            avg_latency = (
                prompt["total_latency"]
                / calls
            )
            avg_cost = (
                prompt["total_cost"] / calls
            )
            avg_tokens = (
                prompt["total_tokens"]
                / calls
            )

            scores = prompt[
                "quality_scores"
            ]
            avg_quality = (
                sum(scores) / len(scores)
                if scores
                else 0.0
            )

            # Token verimliligi
            efficiency = 0.0
            if avg_tokens > 0:
                efficiency = (
                    avg_quality / avg_tokens
                    * 1000
                )

            return {
                "prompt_id": prompt_id,
                "name": prompt["name"],
                "total_calls": calls,
                "success_rate": round(
                    success_rate, 4
                ),
                "avg_quality": round(
                    avg_quality, 4
                ),
                "avg_latency_ms": round(
                    avg_latency, 2
                ),
                "avg_cost": round(
                    avg_cost, 6
                ),
                "avg_tokens": round(
                    avg_tokens, 1
                ),
                "token_efficiency": round(
                    efficiency, 4
                ),
                "total_cost": round(
                    prompt["total_cost"], 4
                ),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }

    def get_trend(
        self,
        prompt_id: str = "",
        window: int = 10,
    ) -> dict[str, Any]:
        """Trend verisini getirir.

        Args:
            prompt_id: Prompt ID.
            window: Pencere boyutu.

        Returns:
            Trend bilgisi.
        """
        try:
            trend_data = self._trends.get(
                prompt_id
            )
            if trend_data is None:
                return {
                    "retrieved": False,
                    "error": (
                        "Prompt bulunamadi"
                    ),
                }

            if len(trend_data) < 2:
                return {
                    "prompt_id": prompt_id,
                    "data_points": len(
                        trend_data
                    ),
                    "trend": "insufficient",
                    "retrieved": True,
                }

            # Son window kayitlari
            recent = trend_data[-window:]

            # Kalite trendi
            qualities = [
                d["quality"]
                for d in recent
                if d["quality"] > 0
            ]

            if len(qualities) >= 2:
                first_half = qualities[
                    : len(qualities) // 2
                ]
                second_half = qualities[
                    len(qualities) // 2 :
                ]

                avg_first = (
                    sum(first_half)
                    / len(first_half)
                )
                avg_second = (
                    sum(second_half)
                    / len(second_half)
                )

                if avg_second > (
                    avg_first * 1.05
                ):
                    quality_trend = (
                        "improving"
                    )
                elif avg_second < (
                    avg_first * 0.95
                ):
                    quality_trend = (
                        "declining"
                    )
                else:
                    quality_trend = "stable"
            else:
                quality_trend = (
                    "insufficient"
                )

            # Basari trendi
            successes = [
                d["success"] for d in recent
            ]
            success_rate = (
                sum(successes)
                / len(successes)
                if successes
                else 0.0
            )

            self._stats[
                "trends_analyzed"
            ] += 1

            return {
                "prompt_id": prompt_id,
                "data_points": len(recent),
                "quality_trend": (
                    quality_trend
                ),
                "success_rate": round(
                    success_rate, 4
                ),
                "avg_quality": round(
                    (
                        sum(qualities)
                        / len(qualities)
                    )
                    if qualities
                    else 0.0,
                    4,
                ),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }

    def compare_prompts(
        self,
        prompt_ids: (
            list[str] | None
        ) = None,
    ) -> dict[str, Any]:
        """Promptlari karsilastirir.

        Args:
            prompt_ids: Karsilastirilacaklar.

        Returns:
            Karsilastirma bilgisi.
        """
        try:
            ids = prompt_ids or []
            comparisons = []

            for pid in ids:
                metrics = self.get_metrics(
                    prompt_id=pid
                )
                if metrics.get("retrieved"):
                    comparisons.append(
                        metrics
                    )

            if not comparisons:
                return {
                    "comparisons": [],
                    "compared": True,
                }

            # En iyi bul
            best_quality = max(
                comparisons,
                key=lambda x: x.get(
                    "avg_quality", 0
                ),
            )
            best_cost = min(
                comparisons,
                key=lambda x: x.get(
                    "avg_cost", float("inf")
                ),
            )

            return {
                "comparisons": comparisons,
                "best_quality": (
                    best_quality["prompt_id"]
                ),
                "best_cost": (
                    best_cost["prompt_id"]
                ),
                "count": len(comparisons),
                "compared": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "compared": False,
                "error": str(e),
            }

    def get_alerts(
        self,
        success_threshold: float = 0.8,
        quality_threshold: float = 0.5,
    ) -> dict[str, Any]:
        """Uyarilari getirir.

        Args:
            success_threshold: Basari esigi.
            quality_threshold: Kalite esigi.

        Returns:
            Uyari bilgisi.
        """
        try:
            alerts = []

            for pid, prompt in (
                self._prompts.items()
            ):
                calls = prompt["total_calls"]
                if calls < 5:
                    continue

                sr = (
                    prompt["successes"]
                    / calls
                )
                if sr < success_threshold:
                    alerts.append({
                        "prompt_id": pid,
                        "name": prompt["name"],
                        "alert": (
                            "low_success_rate"
                        ),
                        "value": round(
                            sr, 4
                        ),
                        "threshold": (
                            success_threshold
                        ),
                    })

                scores = prompt[
                    "quality_scores"
                ]
                if scores:
                    avg_q = sum(scores) / len(
                        scores
                    )
                    if (
                        avg_q
                        < quality_threshold
                    ):
                        alerts.append({
                            "prompt_id": pid,
                            "name": prompt[
                                "name"
                            ],
                            "alert": (
                                "low_quality"
                            ),
                            "value": round(
                                avg_q, 4
                            ),
                            "threshold": (
                                quality_threshold
                            ),
                        })

            self._stats[
                "alerts_generated"
            ] += len(alerts)

            return {
                "alerts": alerts,
                "count": len(alerts),
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
            total_calls = sum(
                p["total_calls"]
                for p in (
                    self._prompts.values()
                )
            )
            total_cost = sum(
                p["total_cost"]
                for p in (
                    self._prompts.values()
                )
            )

            return {
                "total_prompts": len(
                    self._prompts
                ),
                "total_records": len(
                    self._records
                ),
                "total_calls": total_calls,
                "total_cost": round(
                    total_cost, 4
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
