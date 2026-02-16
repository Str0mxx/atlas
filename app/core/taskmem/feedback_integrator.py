"""ATLAS Geri Bildirim Entegratörü modülü.

Açık geri bildirim, örtük sinyaller,
düzeltme öğrenme, memnuniyet takibi,
iyileştirme eşleme.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class TaskFeedbackIntegrator:
    """Geri bildirim entegratörü.

    Geri bildirimleri toplar ve entegre eder.

    Attributes:
        _feedbacks: Geri bildirim kayıtları.
        _corrections: Düzeltme kayıtları.
    """

    def __init__(self) -> None:
        """Entegratörü başlatır."""
        self._feedbacks: list[
            dict[str, Any]
        ] = []
        self._corrections: list[
            dict[str, Any]
        ] = []
        self._satisfaction: list[float] = []
        self._improvements: list[
            dict[str, Any]
        ] = []
        self._counter = 0
        self._stats = {
            "explicit_feedbacks": 0,
            "implicit_signals": 0,
            "corrections": 0,
            "improvements_mapped": 0,
        }

        logger.info(
            "TaskFeedbackIntegrator "
            "baslatildi",
        )

    def record_explicit(
        self,
        task_id: str,
        rating: float,
        comment: str = "",
        category: str = "general",
    ) -> dict[str, Any]:
        """Açık geri bildirim kaydeder.

        Args:
            task_id: Görev ID.
            rating: Puan (0-5).
            comment: Yorum.
            category: Kategori.

        Returns:
            Kayıt bilgisi.
        """
        self._counter += 1
        fid = f"fb_{self._counter}"

        rating = max(0.0, min(5.0, rating))

        feedback = {
            "feedback_id": fid,
            "task_id": task_id,
            "type": "explicit",
            "rating": rating,
            "comment": comment,
            "category": category,
            "timestamp": time.time(),
        }
        self._feedbacks.append(feedback)
        self._satisfaction.append(rating)
        self._stats[
            "explicit_feedbacks"
        ] += 1

        return {
            "feedback_id": fid,
            "task_id": task_id,
            "rating": rating,
            "recorded": True,
        }

    def record_implicit(
        self,
        task_id: str,
        signal_type: str,
        value: Any = None,
    ) -> dict[str, Any]:
        """Örtük sinyal kaydeder.

        Args:
            task_id: Görev ID.
            signal_type: Sinyal tipi.
            value: Değer.

        Returns:
            Kayıt bilgisi.
        """
        self._counter += 1
        fid = f"imp_{self._counter}"

        # Örtük sinyalden puan çıkar
        signal_scores = {
            "accepted": 4.0,
            "modified": 3.0,
            "rejected": 1.0,
            "repeated": 4.5,
            "ignored": 2.0,
            "quick_approve": 5.0,
        }
        inferred_score = signal_scores.get(
            signal_type, 3.0,
        )

        feedback = {
            "feedback_id": fid,
            "task_id": task_id,
            "type": "implicit",
            "signal_type": signal_type,
            "value": value,
            "inferred_score": inferred_score,
            "timestamp": time.time(),
        }
        self._feedbacks.append(feedback)
        self._satisfaction.append(
            inferred_score,
        )
        self._stats[
            "implicit_signals"
        ] += 1

        return {
            "feedback_id": fid,
            "signal_type": signal_type,
            "inferred_score": inferred_score,
            "recorded": True,
        }

    def record_correction(
        self,
        task_id: str,
        original: str,
        corrected: str,
        field: str = "",
    ) -> dict[str, Any]:
        """Düzeltme kaydeder.

        Args:
            task_id: Görev ID.
            original: Orijinal.
            corrected: Düzeltilmiş.
            field: Alan.

        Returns:
            Kayıt bilgisi.
        """
        self._counter += 1
        cid = f"cor_{self._counter}"

        correction = {
            "correction_id": cid,
            "task_id": task_id,
            "original": original,
            "corrected": corrected,
            "field": field,
            "timestamp": time.time(),
        }
        self._corrections.append(correction)
        self._stats["corrections"] += 1

        return {
            "correction_id": cid,
            "task_id": task_id,
            "field": field,
            "recorded": True,
        }

    def get_satisfaction_score(
        self,
    ) -> dict[str, Any]:
        """Memnuniyet puanını döndürür.

        Returns:
            Puan bilgisi.
        """
        if not self._satisfaction:
            return {
                "score": 0.0,
                "count": 0,
                "trend": "insufficient_data",
            }

        avg = sum(self._satisfaction) / len(
            self._satisfaction,
        )

        # Trend
        if len(self._satisfaction) >= 5:
            recent = self._satisfaction[-5:]
            older = self._satisfaction[-10:-5]
            if older:
                recent_avg = sum(recent) / len(
                    recent,
                )
                older_avg = sum(older) / len(
                    older,
                )
                trend = (
                    "improving"
                    if recent_avg > older_avg
                    else "declining"
                    if recent_avg < older_avg
                    else "stable"
                )
            else:
                trend = "stable"
        else:
            trend = "insufficient_data"

        return {
            "score": round(avg, 2),
            "count": len(
                self._satisfaction,
            ),
            "trend": trend,
        }

    def map_improvements(
        self,
    ) -> dict[str, Any]:
        """İyileştirmeleri eşler.

        Returns:
            İyileştirme bilgisi.
        """
        improvements = []

        # Düzeltmelerden öğren
        field_corrections: dict[
            str, int
        ] = {}
        for corr in self._corrections:
            f = corr["field"] or "general"
            field_corrections[f] = (
                field_corrections.get(f, 0)
                + 1
            )

        for field, count in (
            field_corrections.items()
        ):
            if count >= 2:
                improvements.append({
                    "area": field,
                    "issue": (
                        "frequent_corrections"
                    ),
                    "count": count,
                    "priority": (
                        "high"
                        if count >= 5
                        else "medium"
                    ),
                })

        # Düşük puanlı alanlar
        low_rated = [
            f for f in self._feedbacks
            if f.get("rating", 5) < 3
            and f["type"] == "explicit"
        ]
        categories: dict[str, int] = {}
        for fb in low_rated:
            cat = fb.get(
                "category", "general",
            )
            categories[cat] = (
                categories.get(cat, 0) + 1
            )

        for cat, count in categories.items():
            improvements.append({
                "area": cat,
                "issue": "low_satisfaction",
                "count": count,
                "priority": (
                    "high"
                    if count >= 3
                    else "medium"
                ),
            })

        self._improvements = improvements
        self._stats[
            "improvements_mapped"
        ] = len(improvements)

        return {
            "improvements": improvements,
            "count": len(improvements),
        }

    def get_feedbacks(
        self,
        task_id: str | None = None,
        feedback_type: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Geri bildirimleri getirir."""
        results = self._feedbacks
        if task_id:
            results = [
                f for f in results
                if f["task_id"] == task_id
            ]
        if feedback_type:
            results = [
                f for f in results
                if f["type"] == feedback_type
            ]
        return list(results[-limit:])

    @property
    def feedback_count(self) -> int:
        """Geri bildirim sayısı."""
        return len(self._feedbacks)

    @property
    def correction_count(self) -> int:
        """Düzeltme sayısı."""
        return len(self._corrections)
