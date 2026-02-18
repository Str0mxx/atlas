"""
Gecikme izleyici modülü.

Yanıt süreleri, yüzdelik takibi,
yavaş endpointler, trend analizi,
baseline karşılaştırma.
"""

import logging
import math
from typing import Any

logger = logging.getLogger(__name__)


class LatencyMonitor:
    """Gecikme izleyici.

    Attributes:
        _endpoints: Endpoint kayıtları.
        _measurements: Ölçümler.
        _stats: İstatistikler.
    """

    def __init__(self) -> None:
        """İzleyiciyi başlatır."""
        self._endpoints: list[dict] = []
        self._measurements: list[dict] = []
        self._stats: dict[str, int] = {
            "endpoints_tracked": 0,
            "measurements_recorded": 0,
        }
        logger.info(
            "LatencyMonitor baslatildi"
        )

    @property
    def endpoint_count(self) -> int:
        """Endpoint sayısı."""
        return len(self._endpoints)

    def track_endpoint(
        self,
        name: str = "",
        path: str = "",
        baseline_ms: float = 100.0,
    ) -> dict[str, Any]:
        """Endpoint takibe alır.

        Args:
            name: Endpoint adı.
            path: Endpoint yolu.
            baseline_ms: Baz süre (ms).

        Returns:
            Takip bilgisi.
        """
        try:
            record = {
                "name": name,
                "path": path,
                "baseline_ms": baseline_ms,
                "measurements": [],
            }
            self._endpoints.append(record)
            self._stats[
                "endpoints_tracked"
            ] += 1

            return {
                "name": name,
                "path": path,
                "baseline_ms": baseline_ms,
                "tracked": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "tracked": False,
                "error": str(e),
            }

    def record_response_time(
        self,
        endpoint_name: str = "",
        response_ms: float = 0.0,
        status_code: int = 200,
    ) -> dict[str, Any]:
        """Yanıt süresi kaydeder.

        Args:
            endpoint_name: Endpoint adı.
            response_ms: Yanıt süresi (ms).
            status_code: HTTP durum kodu.

        Returns:
            Kayıt bilgisi.
        """
        try:
            endpoint = None
            for ep in self._endpoints:
                if ep["name"] == endpoint_name:
                    endpoint = ep
                    break

            if not endpoint:
                return {
                    "recorded": False,
                    "error": "endpoint_not_found",
                }

            measurement = {
                "response_ms": response_ms,
                "status_code": status_code,
            }
            endpoint["measurements"].append(
                measurement
            )
            self._measurements.append({
                "endpoint": endpoint_name,
                **measurement,
            })
            self._stats[
                "measurements_recorded"
            ] += 1

            baseline = endpoint["baseline_ms"]
            if response_ms > baseline * 3:
                performance = "very_slow"
            elif response_ms > baseline * 1.5:
                performance = "slow"
            elif response_ms > baseline:
                performance = "acceptable"
            else:
                performance = "fast"

            return {
                "endpoint": endpoint_name,
                "response_ms": response_ms,
                "baseline_ms": baseline,
                "performance": performance,
                "recorded": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "recorded": False,
                "error": str(e),
            }

    def get_percentiles(
        self,
        endpoint_name: str = "",
    ) -> dict[str, Any]:
        """Yüzdelik değerleri getirir.

        Args:
            endpoint_name: Endpoint adı.

        Returns:
            Yüzdelik bilgisi.
        """
        try:
            endpoint = None
            for ep in self._endpoints:
                if ep["name"] == endpoint_name:
                    endpoint = ep
                    break

            if not endpoint:
                return {
                    "calculated": False,
                    "error": "endpoint_not_found",
                }

            times = sorted(
                m["response_ms"]
                for m in endpoint[
                    "measurements"
                ]
            )

            if not times:
                return {
                    "endpoint": endpoint_name,
                    "sample_count": 0,
                    "calculated": True,
                }

            def percentile(
                data: list, p: float
            ) -> float:
                idx = (
                    p / 100.0
                    * (len(data) - 1)
                )
                lower = int(math.floor(idx))
                upper = int(math.ceil(idx))
                if lower == upper:
                    return data[lower]
                frac = idx - lower
                return (
                    data[lower] * (1 - frac)
                    + data[upper] * frac
                )

            return {
                "endpoint": endpoint_name,
                "sample_count": len(times),
                "p50": round(
                    percentile(times, 50), 1
                ),
                "p90": round(
                    percentile(times, 90), 1
                ),
                "p95": round(
                    percentile(times, 95), 1
                ),
                "p99": round(
                    percentile(times, 99), 1
                ),
                "min_ms": round(
                    min(times), 1
                ),
                "max_ms": round(
                    max(times), 1
                ),
                "avg_ms": round(
                    sum(times) / len(times), 1
                ),
                "calculated": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "calculated": False,
                "error": str(e),
            }

    def find_slow_endpoints(
        self,
        threshold_ms: float = 500.0,
    ) -> dict[str, Any]:
        """Yavaş endpointleri bulur.

        Args:
            threshold_ms: Eşik (ms).

        Returns:
            Yavaş endpoint bilgisi.
        """
        try:
            slow = []
            for ep in self._endpoints:
                times = [
                    m["response_ms"]
                    for m in ep["measurements"]
                ]
                if not times:
                    continue

                avg = sum(times) / len(times)
                if avg > threshold_ms:
                    slow.append({
                        "name": ep["name"],
                        "path": ep["path"],
                        "avg_ms": round(
                            avg, 1
                        ),
                        "max_ms": round(
                            max(times), 1
                        ),
                        "samples": len(times),
                        "over_threshold_pct": round(
                            sum(
                                1 for t in times
                                if t > threshold_ms
                            )
                            / len(times)
                            * 100,
                            1,
                        ),
                    })

            slow.sort(
                key=lambda s: s["avg_ms"],
                reverse=True,
            )

            return {
                "slow_endpoints": slow,
                "slow_count": len(slow),
                "threshold_ms": threshold_ms,
                "total_endpoints": len(
                    self._endpoints
                ),
                "found": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "found": False,
                "error": str(e),
            }

    def analyze_trend(
        self,
        endpoint_name: str = "",
        window: int = 10,
    ) -> dict[str, Any]:
        """Trend analizi yapar.

        Args:
            endpoint_name: Endpoint adı.
            window: Pencere boyutu.

        Returns:
            Trend bilgisi.
        """
        try:
            endpoint = None
            for ep in self._endpoints:
                if ep["name"] == endpoint_name:
                    endpoint = ep
                    break

            if not endpoint:
                return {
                    "analyzed": False,
                    "error": "endpoint_not_found",
                }

            times = [
                m["response_ms"]
                for m in endpoint[
                    "measurements"
                ]
            ]

            if len(times) < 2:
                return {
                    "endpoint": endpoint_name,
                    "trend": "insufficient_data",
                    "analyzed": True,
                }

            recent = times[-window:]
            first_half = recent[
                :len(recent) // 2
            ]
            second_half = recent[
                len(recent) // 2:
            ]

            avg_first = (
                sum(first_half)
                / len(first_half)
            )
            avg_second = (
                sum(second_half)
                / len(second_half)
            )

            change_pct = (
                (avg_second - avg_first)
                / avg_first * 100.0
            ) if avg_first > 0 else 0.0

            if change_pct > 20:
                trend = "degrading"
            elif change_pct < -20:
                trend = "improving"
            else:
                trend = "stable"

            return {
                "endpoint": endpoint_name,
                "trend": trend,
                "change_percent": round(
                    change_pct, 1
                ),
                "recent_avg_ms": round(
                    avg_second, 1
                ),
                "previous_avg_ms": round(
                    avg_first, 1
                ),
                "window": window,
                "analyzed": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "analyzed": False,
                "error": str(e),
            }

    def compare_baseline(
        self,
        endpoint_name: str = "",
    ) -> dict[str, Any]:
        """Baseline karşılaştırma yapar.

        Args:
            endpoint_name: Endpoint adı.

        Returns:
            Karşılaştırma bilgisi.
        """
        try:
            endpoint = None
            for ep in self._endpoints:
                if ep["name"] == endpoint_name:
                    endpoint = ep
                    break

            if not endpoint:
                return {
                    "compared": False,
                    "error": "endpoint_not_found",
                }

            times = [
                m["response_ms"]
                for m in endpoint[
                    "measurements"
                ]
            ]

            if not times:
                return {
                    "endpoint": endpoint_name,
                    "compared": True,
                    "samples": 0,
                }

            baseline = endpoint["baseline_ms"]
            avg = sum(times) / len(times)
            deviation = (
                (avg - baseline)
                / baseline * 100.0
            ) if baseline > 0 else 0.0

            above_baseline = sum(
                1 for t in times
                if t > baseline
            )

            if deviation > 50:
                verdict = "significantly_worse"
            elif deviation > 20:
                verdict = "worse"
            elif deviation > -10:
                verdict = "within_range"
            else:
                verdict = "better"

            return {
                "endpoint": endpoint_name,
                "baseline_ms": baseline,
                "current_avg_ms": round(
                    avg, 1
                ),
                "deviation_percent": round(
                    deviation, 1
                ),
                "above_baseline_pct": round(
                    above_baseline
                    / len(times) * 100,
                    1,
                ),
                "verdict": verdict,
                "compared": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "compared": False,
                "error": str(e),
            }
