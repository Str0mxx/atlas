"""ATLAS Kayma Tespiti modulu.

Veri kaymasi, kavram kaymasi,
ozellik kaymasi, alarm uretimi
ve yeniden egitim tetikleyicileri.
"""

import logging
import math
import time
from typing import Any

logger = logging.getLogger(__name__)


class DriftDetector:
    """Kayma tespitcisi.

    Veri ve model kaymasini tespit eder.

    Attributes:
        _baselines: Referans dagilimlari.
        _alerts: Alarmlar.
    """

    def __init__(
        self,
        threshold: float = 0.05,
    ) -> None:
        """Tespitciyi baslatir.

        Args:
            threshold: Kayma esigi.
        """
        self._threshold = threshold
        self._baselines: dict[
            str, dict[str, Any]
        ] = {}
        self._alerts: list[
            dict[str, Any]
        ] = []
        self._drift_history: list[
            dict[str, Any]
        ] = []
        self._retrain_triggers: dict[
            str, dict[str, Any]
        ] = {}

        logger.info(
            "DriftDetector baslatildi: "
            "threshold=%f",
            threshold,
        )

    def set_baseline(
        self,
        feature: str,
        values: list[float],
    ) -> dict[str, Any]:
        """Referans dagilimini ayarlar.

        Args:
            feature: Ozellik adi.
            values: Referans degerler.

        Returns:
            Referans bilgisi.
        """
        if not values:
            return {"error": "empty_values"}

        n = len(values)
        mean = sum(values) / n
        variance = sum(
            (v - mean) ** 2 for v in values
        ) / n
        std = math.sqrt(variance) if variance > 0 else 1.0

        self._baselines[feature] = {
            "mean": mean,
            "std": std,
            "min": min(values),
            "max": max(values),
            "count": n,
            "set_at": time.time(),
        }

        return {
            "feature": feature,
            "mean": mean,
            "std": std,
        }

    def detect_data_drift(
        self,
        feature: str,
        values: list[float],
    ) -> dict[str, Any]:
        """Veri kaymasini tespit eder.

        Args:
            feature: Ozellik adi.
            values: Yeni degerler.

        Returns:
            Kayma sonucu.
        """
        baseline = self._baselines.get(feature)
        if not baseline or not values:
            return {
                "feature": feature,
                "drift_detected": False,
                "reason": "no_baseline",
            }

        n = len(values)
        new_mean = sum(values) / n
        new_variance = sum(
            (v - new_mean) ** 2 for v in values
        ) / n
        new_std = math.sqrt(
            new_variance,
        ) if new_variance > 0 else 1.0

        # Z-score tabanli kayma tespiti
        base_std = baseline["std"]
        if base_std == 0:
            base_std = 1.0
        z_score = abs(
            new_mean - baseline["mean"]
        ) / base_std

        # KL divergence yaklasimlama
        kl_approx = 0.0
        if new_std > 0 and base_std > 0:
            kl_approx = (
                math.log(new_std / base_std)
                + (base_std ** 2
                   + (baseline["mean"] - new_mean) ** 2)
                / (2 * new_std ** 2)
                - 0.5
            )
            kl_approx = abs(kl_approx)

        drift_score = (z_score + kl_approx) / 2
        detected = drift_score > self._threshold

        result = {
            "feature": feature,
            "drift_detected": detected,
            "drift_score": drift_score,
            "z_score": z_score,
            "kl_divergence": kl_approx,
            "threshold": self._threshold,
            "baseline_mean": baseline["mean"],
            "current_mean": new_mean,
            "timestamp": time.time(),
        }

        self._drift_history.append(result)

        if detected:
            self._generate_alert(
                feature, "data", drift_score,
            )

        return result

    def detect_concept_drift(
        self,
        model_id: str,
        recent_accuracy: list[float],
        window: int = 10,
    ) -> dict[str, Any]:
        """Kavram kaymasini tespit eder.

        Args:
            model_id: Model ID.
            recent_accuracy: Son dogruluk degerleri.
            window: Pencere boyutu.

        Returns:
            Kayma sonucu.
        """
        if len(recent_accuracy) < window:
            return {
                "model_id": model_id,
                "drift_detected": False,
                "reason": "insufficient_data",
            }

        # Erken ve gec pencere ortalamasi
        mid = len(recent_accuracy) // 2
        early = recent_accuracy[:mid]
        late = recent_accuracy[mid:]

        early_mean = sum(early) / len(early)
        late_mean = sum(late) / len(late)
        decline = early_mean - late_mean

        detected = decline > self._threshold

        result = {
            "model_id": model_id,
            "drift_detected": detected,
            "early_accuracy": early_mean,
            "late_accuracy": late_mean,
            "decline": decline,
            "threshold": self._threshold,
            "timestamp": time.time(),
        }

        self._drift_history.append(result)

        if detected:
            self._generate_alert(
                model_id, "concept", decline,
            )
            self._trigger_retrain(model_id)

        return result

    def detect_feature_drift(
        self,
        features: dict[str, list[float]],
    ) -> dict[str, Any]:
        """Ozellik kaymasini toplu tespit eder.

        Args:
            features: Ozellik-deger eslesmesi.

        Returns:
            Toplu kayma sonucu.
        """
        results: dict[str, dict[str, Any]] = {}
        drifted: list[str] = []

        for feature, values in features.items():
            r = self.detect_data_drift(
                feature, values,
            )
            results[feature] = r
            if r.get("drift_detected"):
                drifted.append(feature)

        return {
            "features_checked": len(features),
            "features_drifted": len(drifted),
            "drifted_features": drifted,
            "results": results,
        }

    def _generate_alert(
        self,
        source: str,
        drift_type: str,
        score: float,
    ) -> None:
        """Alarm uretir.

        Args:
            source: Kaynak.
            drift_type: Kayma tipi.
            score: Skor.
        """
        self._alerts.append({
            "source": source,
            "drift_type": drift_type,
            "score": score,
            "severity": (
                "high" if score > 0.3
                else "medium"
                if score > 0.1
                else "low"
            ),
            "timestamp": time.time(),
        })

    def _trigger_retrain(
        self,
        model_id: str,
    ) -> None:
        """Yeniden egitim tetikler.

        Args:
            model_id: Model ID.
        """
        self._retrain_triggers[model_id] = {
            "model_id": model_id,
            "triggered_at": time.time(),
            "status": "pending",
        }

    def get_alerts(
        self,
        drift_type: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Alarmlari getirir.

        Args:
            drift_type: Kayma tipi filtresi.
            limit: Limit.

        Returns:
            Alarm listesi.
        """
        alerts = self._alerts
        if drift_type:
            alerts = [
                a for a in alerts
                if a["drift_type"] == drift_type
            ]
        return alerts[-limit:]

    def get_retrain_triggers(
        self,
    ) -> dict[str, dict[str, Any]]:
        """Yeniden egitim tetikleyicilerini getirir.

        Returns:
            Tetikleyiciler.
        """
        return dict(self._retrain_triggers)

    def should_retrain(
        self,
        model_id: str,
    ) -> bool:
        """Yeniden egitim gerekli mi.

        Args:
            model_id: Model ID.

        Returns:
            Gerekli mi.
        """
        trigger = self._retrain_triggers.get(
            model_id,
        )
        return (
            trigger is not None
            and trigger["status"] == "pending"
        )

    def acknowledge_retrain(
        self,
        model_id: str,
    ) -> bool:
        """Yeniden egitimi onaylar.

        Args:
            model_id: Model ID.

        Returns:
            Basarili mi.
        """
        trigger = self._retrain_triggers.get(
            model_id,
        )
        if trigger:
            trigger["status"] = "acknowledged"
            return True
        return False

    @property
    def baseline_count(self) -> int:
        """Referans sayisi."""
        return len(self._baselines)

    @property
    def alert_count(self) -> int:
        """Alarm sayisi."""
        return len(self._alerts)

    @property
    def drift_count(self) -> int:
        """Tespit edilen kayma sayisi."""
        return sum(
            1 for d in self._drift_history
            if d.get("drift_detected")
        )

    @property
    def history_count(self) -> int:
        """Gecmis sayisi."""
        return len(self._drift_history)
