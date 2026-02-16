"""ATLAS Yanlış Pozitif Filtresi modülü.

FP tespiti, geri bildirim öğrenme,
kural iyileştirme, eşik ayarlama,
doğruluk takibi.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class FalsePositiveFilter:
    """Yanlış pozitif filtresi.

    Yanlış alarmları filtreler ve öğrenir.

    Attributes:
        _feedback: Geri bildirim kayıtları.
        _accuracy: Doğruluk kayıtları.
    """

    def __init__(self) -> None:
        """Filtreyi başlatır."""
        self._feedback: list[
            dict[str, Any]
        ] = []
        self._whitelist: set[str] = set()
        self._thresholds: dict[
            str, float
        ] = {}
        self._counter = 0
        self._stats = {
            "fps_detected": 0,
            "accuracy_checks": 0,
            "total_alerts": 0,
            "true_positives": 0,
        }

        logger.info(
            "FalsePositiveFilter "
            "baslatildi",
        )

    def check_false_positive(
        self,
        alert_id: str,
        entity: str = "",
        score: float = 0.0,
        context: dict[str, Any]
        | None = None,
    ) -> dict[str, Any]:
        """FP kontrolü yapar.

        Args:
            alert_id: Uyarı ID.
            entity: Varlık.
            score: Puan.
            context: Bağlam.

        Returns:
            FP bilgisi.
        """
        self._stats["total_alerts"] += 1

        # Beyaz listede mi?
        if entity in self._whitelist:
            self._stats[
                "fps_detected"
            ] += 1
            return {
                "alert_id": alert_id,
                "is_fp": True,
                "reason": "whitelisted",
            }

        # Eşik altında mı?
        category_threshold = (
            self._thresholds.get(
                "default", 30.0,
            )
        )
        if score < category_threshold:
            self._stats[
                "fps_detected"
            ] += 1
            return {
                "alert_id": alert_id,
                "is_fp": True,
                "reason": "below_threshold",
            }

        self._stats[
            "true_positives"
        ] += 1
        return {
            "alert_id": alert_id,
            "is_fp": False,
            "reason": "above_threshold",
        }

    def learn_from_feedback(
        self,
        alert_id: str,
        was_fp: bool,
        entity: str = "",
    ) -> dict[str, Any]:
        """Geri bildirimden öğrenir.

        Args:
            alert_id: Uyarı ID.
            was_fp: FP miydi.
            entity: Varlık.

        Returns:
            Öğrenme bilgisi.
        """
        self._feedback.append({
            "alert_id": alert_id,
            "was_fp": was_fp,
            "entity": entity,
            "timestamp": time.time(),
        })

        # FP ise beyaz listeye ekle
        if was_fp and entity:
            fp_count = sum(
                1 for f in self._feedback
                if f["entity"] == entity
                and f["was_fp"]
            )
            if fp_count >= 3:
                self._whitelist.add(entity)

        return {
            "alert_id": alert_id,
            "was_fp": was_fp,
            "entity_whitelisted": (
                entity in self._whitelist
            ),
            "learned": True,
        }

    def refine_rules(
        self,
    ) -> dict[str, Any]:
        """Kuralları iyileştirir.

        Returns:
            İyileştirme bilgisi.
        """
        if not self._feedback:
            return {
                "refined": False,
                "reason": "No feedback",
            }

        total = len(self._feedback)
        fps = sum(
            1 for f in self._feedback
            if f["was_fp"]
        )
        fp_rate = round(
            fps / total * 100, 1,
        )

        # FP oranı yüksekse eşiği yükselt
        adjustment = 0.0
        if fp_rate > 30:
            adjustment = 5.0
            current = self._thresholds.get(
                "default", 30.0,
            )
            self._thresholds["default"] = (
                current + adjustment
            )

        return {
            "total_feedback": total,
            "fp_count": fps,
            "fp_rate": fp_rate,
            "threshold_adjustment": (
                adjustment
            ),
            "refined": True,
        }

    def tune_threshold(
        self,
        category: str = "default",
        value: float = 30.0,
    ) -> dict[str, Any]:
        """Eşik ayarlar.

        Args:
            category: Kategori.
            value: Değer.

        Returns:
            Ayarlama bilgisi.
        """
        old = self._thresholds.get(
            category, 30.0,
        )
        self._thresholds[category] = value

        return {
            "category": category,
            "old_threshold": old,
            "new_threshold": value,
            "tuned": True,
        }

    def track_accuracy(
        self,
    ) -> dict[str, Any]:
        """Doğruluk takibi yapar.

        Returns:
            Doğruluk bilgisi.
        """
        total = self._stats["total_alerts"]
        tp = self._stats["true_positives"]
        fp = self._stats["fps_detected"]

        precision = round(
            tp / (tp + fp) * 100, 1,
        ) if (tp + fp) > 0 else 100.0

        self._stats[
            "accuracy_checks"
        ] += 1

        return {
            "total_alerts": total,
            "true_positives": tp,
            "false_positives": fp,
            "precision": precision,
            "tracked": True,
        }

    @property
    def fp_count(self) -> int:
        """FP sayısı."""
        return self._stats["fps_detected"]

    @property
    def accuracy(self) -> float:
        """Doğruluk."""
        tp = self._stats["true_positives"]
        fp = self._stats["fps_detected"]
        return round(
            tp / (tp + fp) * 100, 1,
        ) if (tp + fp) > 0 else 100.0
