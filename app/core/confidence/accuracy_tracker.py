"""ATLAS Dogruluk Takibi modulu.

Karar sonuclari, dogruluk gecmisi,
trend analizi, alan dogrulugu, kalibrasyon kontrolu.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class AccuracyTracker:
    """Dogruluk takipcisi.

    Karar dogruluklarini izler.

    Attributes:
        _records: Dogruluk kayitlari.
        _domain_records: Alan bazli kayitlar.
    """

    def __init__(self) -> None:
        """Dogruluk takipcisini baslatir."""
        self._records: list[
            dict[str, Any]
        ] = []
        self._domain_records: dict[
            str, list[dict[str, Any]]
        ] = {}
        self._predictions: dict[
            str, dict[str, Any]
        ] = {}
        self._stats = {
            "total": 0,
            "correct": 0,
            "incorrect": 0,
        }

        logger.info(
            "AccuracyTracker baslatildi",
        )

    def record_prediction(
        self,
        prediction_id: str,
        confidence: float,
        predicted_outcome: str,
        domain: str = "",
    ) -> dict[str, Any]:
        """Tahmin kaydeder.

        Args:
            prediction_id: Tahmin ID.
            confidence: Guven puani.
            predicted_outcome: Tahmini sonuc.
            domain: Alan.

        Returns:
            Kayit bilgisi.
        """
        self._predictions[prediction_id] = {
            "prediction_id": prediction_id,
            "confidence": confidence,
            "predicted_outcome": predicted_outcome,
            "domain": domain,
            "timestamp": time.time(),
            "resolved": False,
        }

        return {
            "prediction_id": prediction_id,
            "recorded": True,
        }

    def record_outcome(
        self,
        prediction_id: str,
        actual_outcome: str,
    ) -> dict[str, Any]:
        """Gercek sonucu kaydeder.

        Args:
            prediction_id: Tahmin ID.
            actual_outcome: Gercek sonuc.

        Returns:
            Dogruluk bilgisi.
        """
        pred = self._predictions.get(prediction_id)
        if not pred:
            return {"error": "prediction_not_found"}

        correct = (
            pred["predicted_outcome"]
            == actual_outcome
        )
        pred["actual_outcome"] = actual_outcome
        pred["correct"] = correct
        pred["resolved"] = True

        record = {
            "prediction_id": prediction_id,
            "confidence": pred["confidence"],
            "correct": correct,
            "domain": pred["domain"],
            "timestamp": time.time(),
        }

        self._records.append(record)
        self._stats["total"] += 1
        if correct:
            self._stats["correct"] += 1
        else:
            self._stats["incorrect"] += 1

        domain = pred["domain"]
        if domain:
            if domain not in self._domain_records:
                self._domain_records[domain] = []
            self._domain_records[domain].append(
                record,
            )

        return {
            "prediction_id": prediction_id,
            "correct": correct,
            "accuracy": self.overall_accuracy,
        }

    def get_accuracy(
        self,
        domain: str | None = None,
    ) -> float:
        """Dogruluk oranini getirir.

        Args:
            domain: Alan filtresi.

        Returns:
            Dogruluk orani.
        """
        if domain:
            records = self._domain_records.get(
                domain, [],
            )
        else:
            records = self._records

        if not records:
            return 0.0

        correct = sum(
            1 for r in records if r["correct"]
        )
        return round(correct / len(records), 4)

    def get_accuracy_history(
        self,
        window: int = 20,
        domain: str | None = None,
    ) -> list[float]:
        """Dogruluk gecmisini getirir.

        Args:
            window: Pencere boyutu.
            domain: Alan filtresi.

        Returns:
            Dogruluk listesi.
        """
        if domain:
            records = self._domain_records.get(
                domain, [],
            )
        else:
            records = self._records

        if not records:
            return []

        result = []
        for i in range(
            0, len(records), max(1, window // 5),
        ):
            chunk = records[
                max(0, i - window):i + 1
            ]
            if chunk:
                acc = sum(
                    1 for r in chunk if r["correct"]
                ) / len(chunk)
                result.append(round(acc, 4))

        return result

    def analyze_trend(
        self,
        domain: str | None = None,
    ) -> dict[str, Any]:
        """Trend analizi yapar.

        Args:
            domain: Alan filtresi.

        Returns:
            Trend bilgisi.
        """
        if domain:
            records = self._domain_records.get(
                domain, [],
            )
        else:
            records = self._records

        if len(records) < 4:
            return {
                "trend": "insufficient_data",
                "count": len(records),
            }

        mid = len(records) // 2
        first_half = records[:mid]
        second_half = records[mid:]

        first_acc = (
            sum(1 for r in first_half if r["correct"])
            / len(first_half)
        )
        second_acc = (
            sum(1 for r in second_half if r["correct"])
            / len(second_half)
        )

        diff = second_acc - first_acc
        if diff > 0.1:
            trend = "improving"
        elif diff < -0.1:
            trend = "declining"
        else:
            trend = "stable"

        return {
            "trend": trend,
            "first_half_accuracy": round(
                first_acc, 4,
            ),
            "second_half_accuracy": round(
                second_acc, 4,
            ),
            "change": round(diff, 4),
        }

    def get_domain_accuracy(
        self,
    ) -> dict[str, float]:
        """Tum alan dogruluklarini getirir.

        Returns:
            Alan dogruluk haritasi.
        """
        result = {}
        for domain, records in (
            self._domain_records.items()
        ):
            if records:
                correct = sum(
                    1
                    for r in records
                    if r["correct"]
                )
                result[domain] = round(
                    correct / len(records), 4,
                )
        return result

    def check_calibration(
        self,
        bins: int = 5,
    ) -> dict[str, Any]:
        """Kalibrasyon kontrol eder.

        Args:
            bins: Kutu sayisi.

        Returns:
            Kalibrasyon bilgisi.
        """
        if len(self._records) < 10:
            return {
                "status": "insufficient_data",
                "count": len(self._records),
            }

        bin_data: dict[
            int, dict[str, Any]
        ] = {}
        for r in self._records:
            b = min(
                bins - 1,
                int(r["confidence"] * bins),
            )
            if b not in bin_data:
                bin_data[b] = {
                    "total": 0,
                    "correct": 0,
                    "confidence_sum": 0.0,
                }
            bin_data[b]["total"] += 1
            if r["correct"]:
                bin_data[b]["correct"] += 1
            bin_data[b]["confidence_sum"] += (
                r["confidence"]
            )

        # Brier score
        brier = sum(
            (r["confidence"] - (1.0 if r["correct"] else 0.0)) ** 2
            for r in self._records
        ) / len(self._records)

        calibration_error = 0.0
        bin_count = 0
        for data in bin_data.values():
            if data["total"] > 0:
                avg_conf = (
                    data["confidence_sum"]
                    / data["total"]
                )
                actual_acc = (
                    data["correct"] / data["total"]
                )
                calibration_error += abs(
                    avg_conf - actual_acc,
                )
                bin_count += 1

        avg_error = (
            calibration_error / bin_count
            if bin_count > 0
            else 0.0
        )

        if avg_error < 0.1:
            status = "well_calibrated"
        elif brier > 0.25:
            # Genel conf cok mu yuksek?
            avg_conf = sum(
                r["confidence"]
                for r in self._records
            ) / len(self._records)
            overall_acc = self.overall_accuracy
            if avg_conf > overall_acc + 0.1:
                status = "overconfident"
            elif avg_conf < overall_acc - 0.1:
                status = "underconfident"
            else:
                status = "needs_recalibration"
        else:
            status = "well_calibrated"

        return {
            "status": status,
            "brier_score": round(brier, 4),
            "calibration_error": round(
                avg_error, 4,
            ),
            "sample_count": len(self._records),
        }

    @property
    def overall_accuracy(self) -> float:
        """Genel dogruluk."""
        total = self._stats["total"]
        if total == 0:
            return 0.0
        return round(
            self._stats["correct"] / total, 4,
        )

    @property
    def record_count(self) -> int:
        """Kayit sayisi."""
        return len(self._records)

    @property
    def domain_count(self) -> int:
        """Alan sayisi."""
        return len(self._domain_records)
