"""ATLAS Regresyon Tespitcisi modulu.

Temel karsilastirma, performans
regresyonu, davranis degisikligi,
gorsel regresyon ve uyari uretimi.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class RegressionDetector:
    """Regresyon tespitcisi.

    Regresyonlari tespit eder ve
    uyari uretir.

    Attributes:
        _baselines: Temel degerler.
        _regressions: Tespit edilen regresyonlar.
    """

    def __init__(
        self,
        tolerance: float = 0.1,
    ) -> None:
        """Regresyon tespitcisini baslatir.

        Args:
            tolerance: Tolerans yuzdesi.
        """
        self._tolerance = tolerance
        self._baselines: dict[
            str, dict[str, Any]
        ] = {}
        self._regressions: list[
            dict[str, Any]
        ] = []
        self._alerts: list[
            dict[str, Any]
        ] = []

        logger.info(
            "RegressionDetector baslatildi",
        )

    def set_baseline(
        self,
        name: str,
        metrics: dict[str, float],
    ) -> dict[str, Any]:
        """Temel deger ayarlar.

        Args:
            name: Metrik adi.
            metrics: Degerler.

        Returns:
            Temel deger bilgisi.
        """
        baseline = {
            "name": name,
            "metrics": metrics,
            "created_at": time.time(),
        }
        self._baselines[name] = baseline
        return baseline

    def compare_with_baseline(
        self,
        name: str,
        current: dict[str, float],
    ) -> dict[str, Any]:
        """Temel degerle karsilastirir.

        Args:
            name: Metrik adi.
            current: Mevcut degerler.

        Returns:
            Karsilastirma sonucu.
        """
        baseline = self._baselines.get(name)
        if not baseline:
            return {
                "found": False,
                "regressions": [],
            }

        base_metrics = baseline["metrics"]
        regressions = []
        improvements = []

        for key, cur_val in current.items():
            base_val = base_metrics.get(key)
            if base_val is None or base_val == 0:
                continue

            change = (cur_val - base_val) / abs(
                base_val
            )

            if change > self._tolerance:
                regressions.append({
                    "metric": key,
                    "baseline": base_val,
                    "current": cur_val,
                    "change_pct": round(
                        change * 100, 2,
                    ),
                })
            elif change < -self._tolerance:
                improvements.append({
                    "metric": key,
                    "baseline": base_val,
                    "current": cur_val,
                    "change_pct": round(
                        change * 100, 2,
                    ),
                })

        if regressions:
            for reg in regressions:
                reg_record = {
                    "name": name,
                    **reg,
                    "detected_at": time.time(),
                }
                self._regressions.append(
                    reg_record,
                )

        return {
            "found": True,
            "regressions": regressions,
            "improvements": improvements,
            "has_regression": len(regressions) > 0,
        }

    def detect_performance_regression(
        self,
        name: str,
        current_ms: float,
        baseline_ms: float | None = None,
    ) -> dict[str, Any]:
        """Performans regresyonu tespit eder.

        Args:
            name: Test adi.
            current_ms: Mevcut sure (ms).
            baseline_ms: Temel sure (ms).

        Returns:
            Tespit sonucu.
        """
        if baseline_ms is None:
            bl = self._baselines.get(name)
            if bl and "response_time" in bl["metrics"]:
                baseline_ms = bl["metrics"][
                    "response_time"
                ]

        if baseline_ms is None or baseline_ms == 0:
            return {
                "regression": False,
                "reason": "no_baseline",
            }

        change = (
            (current_ms - baseline_ms)
            / baseline_ms
        )
        is_regression = change > self._tolerance

        result = {
            "name": name,
            "regression": is_regression,
            "baseline_ms": baseline_ms,
            "current_ms": current_ms,
            "change_pct": round(change * 100, 2),
        }

        if is_regression:
            self._regressions.append({
                "name": name,
                "metric": "response_time",
                "baseline": baseline_ms,
                "current": current_ms,
                "change_pct": round(
                    change * 100, 2,
                ),
                "detected_at": time.time(),
            })
            self._generate_alert(
                f"Performance regression: {name}",
                "performance",
                result,
            )

        return result

    def detect_behavior_change(
        self,
        name: str,
        expected_output: Any,
        actual_output: Any,
    ) -> dict[str, Any]:
        """Davranis degisikligi tespit eder.

        Args:
            name: Test adi.
            expected_output: Beklenen cikti.
            actual_output: Gercek cikti.

        Returns:
            Tespit sonucu.
        """
        changed = expected_output != actual_output

        result = {
            "name": name,
            "changed": changed,
            "expected": expected_output,
            "actual": actual_output,
        }

        if changed:
            self._regressions.append({
                "name": name,
                "metric": "behavior",
                "expected": str(expected_output),
                "actual": str(actual_output),
                "detected_at": time.time(),
            })
            self._generate_alert(
                f"Behavior change: {name}",
                "behavior",
                result,
            )

        return result

    def _generate_alert(
        self,
        message: str,
        alert_type: str,
        data: dict[str, Any],
    ) -> None:
        """Uyari uretir.

        Args:
            message: Uyari mesaji.
            alert_type: Uyari tipi.
            data: Veri.
        """
        self._alerts.append({
            "message": message,
            "type": alert_type,
            "data": data,
            "timestamp": time.time(),
        })

    def get_regressions(
        self,
    ) -> list[dict[str, Any]]:
        """Regresyonlari getirir.

        Returns:
            Regresyon listesi.
        """
        return list(self._regressions)

    def get_alerts(
        self,
    ) -> list[dict[str, Any]]:
        """Uyarilari getirir.

        Returns:
            Uyari listesi.
        """
        return list(self._alerts)

    def clear_regressions(self) -> int:
        """Regresyonlari temizler.

        Returns:
            Temizlenen sayi.
        """
        count = len(self._regressions)
        self._regressions = []
        self._alerts = []
        return count

    @property
    def regression_count(self) -> int:
        """Regresyon sayisi."""
        return len(self._regressions)

    @property
    def alert_count(self) -> int:
        """Uyari sayisi."""
        return len(self._alerts)

    @property
    def baseline_count(self) -> int:
        """Temel deger sayisi."""
        return len(self._baselines)
