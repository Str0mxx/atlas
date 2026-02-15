"""ATLAS Sonuc Tespiti modulu.

Basari/basarisizlik tespiti, metrik degisimi,
yan etki tespiti, gecikmeli sonuclar, korelasyon.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class OutcomeDetector:
    """Sonuc tespitcisi.

    Aksiyon sonuclarini tespit eder.

    Attributes:
        _outcomes: Sonuc kayitlari.
        _metric_baselines: Metrik temelleri.
    """

    def __init__(
        self,
        detection_timeout: int = 300,
    ) -> None:
        """Sonuc tespitcisini baslatir.

        Args:
            detection_timeout: Tespit zaman asimi (sn).
        """
        self._outcomes: dict[
            str, dict[str, Any]
        ] = {}
        self._action_outcomes: dict[
            str, list[str]
        ] = {}
        self._metric_baselines: dict[
            str, float
        ] = {}
        self._metric_current: dict[
            str, float
        ] = {}
        self._side_effects: list[
            dict[str, Any]
        ] = []
        self._pending_detections: dict[
            str, dict[str, Any]
        ] = {}
        self._detection_timeout = detection_timeout
        self._stats = {
            "detected": 0,
            "success": 0,
            "failure": 0,
            "timeout": 0,
        }

        logger.info(
            "OutcomeDetector baslatildi",
        )

    def detect_outcome(
        self,
        action_id: str,
        outcome_type: str = "unknown",
        metrics: dict[str, Any] | None = None,
        confidence: float = 1.0,
    ) -> dict[str, Any]:
        """Sonucu tespit eder.

        Args:
            action_id: Aksiyon ID.
            outcome_type: Sonuc tipi.
            metrics: Metrikler.
            confidence: Guven.

        Returns:
            Tespit bilgisi.
        """
        outcome_id = f"out_{action_id}_{int(time.time())}"
        now = time.time()

        outcome = {
            "outcome_id": outcome_id,
            "action_id": action_id,
            "outcome_type": outcome_type,
            "metrics": metrics or {},
            "confidence": confidence,
            "detected_at": now,
            "side_effects": [],
        }

        self._outcomes[outcome_id] = outcome

        if action_id not in self._action_outcomes:
            self._action_outcomes[action_id] = []
        self._action_outcomes[action_id].append(
            outcome_id,
        )

        self._stats["detected"] += 1
        if outcome_type == "success":
            self._stats["success"] += 1
        elif outcome_type == "failure":
            self._stats["failure"] += 1

        return {
            "outcome_id": outcome_id,
            "action_id": action_id,
            "outcome_type": outcome_type,
            "confidence": confidence,
        }

    def check_metric_change(
        self,
        metric_name: str,
        current_value: float,
        threshold: float = 0.1,
    ) -> dict[str, Any]:
        """Metrik degisimini kontrol eder.

        Args:
            metric_name: Metrik adi.
            current_value: Guncel deger.
            threshold: Esik degeri.

        Returns:
            Degisim bilgisi.
        """
        baseline = self._metric_baselines.get(
            metric_name,
        )
        self._metric_current[metric_name] = (
            current_value
        )

        if baseline is None:
            self._metric_baselines[metric_name] = (
                current_value
            )
            return {
                "metric": metric_name,
                "changed": False,
                "reason": "baseline_set",
            }

        if baseline == 0:
            change_pct = (
                100.0 if current_value != 0 else 0.0
            )
        else:
            change_pct = abs(
                (current_value - baseline) / baseline,
            )

        changed = change_pct >= threshold

        return {
            "metric": metric_name,
            "baseline": baseline,
            "current": current_value,
            "change_pct": round(change_pct * 100, 1),
            "changed": changed,
            "direction": (
                "up"
                if current_value > baseline
                else "down"
                if current_value < baseline
                else "flat"
            ),
        }

    def detect_side_effect(
        self,
        action_id: str,
        effect_type: str,
        description: str = "",
        severity: str = "low",
    ) -> dict[str, Any]:
        """Yan etkiyi tespit eder.

        Args:
            action_id: Aksiyon ID.
            effect_type: Etki tipi.
            description: Aciklama.
            severity: Ciddiyet.

        Returns:
            Yan etki bilgisi.
        """
        effect = {
            "action_id": action_id,
            "effect_type": effect_type,
            "description": description,
            "severity": severity,
            "detected_at": time.time(),
        }

        self._side_effects.append(effect)

        # Aksiyonun sonuclarina ekle
        outcomes = self._action_outcomes.get(
            action_id, [],
        )
        for oid in outcomes:
            outcome = self._outcomes.get(oid)
            if outcome:
                outcome["side_effects"].append(
                    effect,
                )

        return {
            "action_id": action_id,
            "effect_type": effect_type,
            "severity": severity,
            "recorded": True,
        }

    def register_delayed_detection(
        self,
        action_id: str,
        check_after: int = 60,
        expected_metric: str = "",
    ) -> dict[str, Any]:
        """Gecikmeli tespit kaydeder.

        Args:
            action_id: Aksiyon ID.
            check_after: Kontrol suresi (sn).
            expected_metric: Beklenen metrik.

        Returns:
            Kayit bilgisi.
        """
        self._pending_detections[action_id] = {
            "action_id": action_id,
            "check_after": check_after,
            "expected_metric": expected_metric,
            "registered_at": time.time(),
            "status": "pending",
        }

        return {
            "action_id": action_id,
            "check_after": check_after,
            "status": "registered",
        }

    def check_pending_detections(
        self,
    ) -> list[dict[str, Any]]:
        """Bekleyen tespitleri kontrol eder.

        Returns:
            Kontrol sonuclari.
        """
        now = time.time()
        results = []

        for aid, det in list(
            self._pending_detections.items(),
        ):
            elapsed = now - det["registered_at"]

            if elapsed >= det["check_after"]:
                metric = det.get("expected_metric")
                if metric and metric in self._metric_current:
                    results.append({
                        "action_id": aid,
                        "status": "checked",
                        "metric_value": (
                            self._metric_current[metric]
                        ),
                    })
                else:
                    results.append({
                        "action_id": aid,
                        "status": "timeout",
                    })
                    self._stats["timeout"] += 1

                det["status"] = "checked"

            elif elapsed >= self._detection_timeout:
                det["status"] = "expired"
                self._stats["timeout"] += 1
                results.append({
                    "action_id": aid,
                    "status": "expired",
                })

        return results

    def correlate_outcomes(
        self,
        action_ids: list[str],
    ) -> dict[str, Any]:
        """Sonuclari iliskilendirir.

        Args:
            action_ids: Aksiyon ID listesi.

        Returns:
            Korelasyon bilgisi.
        """
        outcomes_data = []
        for aid in action_ids:
            oids = self._action_outcomes.get(
                aid, [],
            )
            for oid in oids:
                outcome = self._outcomes.get(oid)
                if outcome:
                    outcomes_data.append(outcome)

        if len(outcomes_data) < 2:
            return {
                "correlation": "insufficient_data",
                "count": len(outcomes_data),
            }

        types = [
            o["outcome_type"]
            for o in outcomes_data
        ]
        success_count = types.count("success")
        failure_count = types.count("failure")
        total = len(types)

        success_rate = success_count / total

        return {
            "total_outcomes": total,
            "success_rate": round(
                success_rate, 2,
            ),
            "success_count": success_count,
            "failure_count": failure_count,
            "pattern": (
                "mostly_success"
                if success_rate > 0.7
                else "mostly_failure"
                if success_rate < 0.3
                else "mixed"
            ),
        }

    def get_outcomes(
        self,
        action_id: str,
    ) -> list[dict[str, Any]]:
        """Aksiyonun sonuclarini getirir.

        Args:
            action_id: Aksiyon ID.

        Returns:
            Sonuc listesi.
        """
        oids = self._action_outcomes.get(
            action_id, [],
        )
        return [
            dict(self._outcomes[oid])
            for oid in oids
            if oid in self._outcomes
        ]

    def set_baseline(
        self,
        metric_name: str,
        value: float,
    ) -> None:
        """Metrik temelini ayarlar.

        Args:
            metric_name: Metrik adi.
            value: Temel deger.
        """
        self._metric_baselines[metric_name] = value

    @property
    def outcome_count(self) -> int:
        """Sonuc sayisi."""
        return len(self._outcomes)

    @property
    def side_effect_count(self) -> int:
        """Yan etki sayisi."""
        return len(self._side_effects)

    @property
    def pending_count(self) -> int:
        """Bekleyen tespit sayisi."""
        return sum(
            1
            for d in self._pending_detections.values()
            if d["status"] == "pending"
        )
