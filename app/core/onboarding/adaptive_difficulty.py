"""ATLAS Adaptif Zorluk modülü.

Performans analizi, zorluk ayarlama,
meydan okuma optimizasyonu,
hayal kırıklığı önleme,
etkileşim maksimizasyonu.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class AdaptiveDifficulty:
    """Adaptif zorluk yöneticisi.

    Zorluğu performansa göre ayarlar.

    Attributes:
        _profiles: Kullanıcı profilleri.
        _history: Performans geçmişi.
    """

    def __init__(self) -> None:
        """Yöneticiyi başlatır."""
        self._profiles: dict[
            str, dict[str, Any]
        ] = {}
        self._history: dict[
            str, list[dict[str, Any]]
        ] = {}
        self._stats = {
            "adjustments_made": 0,
            "frustrations_prevented": 0,
        }

        logger.info(
            "AdaptiveDifficulty "
            "baslatildi",
        )

    def analyze_performance(
        self,
        user_id: str,
        scores: list[float]
        | None = None,
    ) -> dict[str, Any]:
        """Performans analizi yapar.

        Args:
            user_id: Kullanıcı kimliği.
            scores: Puanlar.

        Returns:
            Analiz bilgisi.
        """
        scores = scores or []

        if not scores:
            return {
                "user_id": user_id,
                "avg_score": 0.0,
                "trend": "unknown",
                "analyzed": True,
            }

        avg = sum(scores) / len(scores)

        if len(scores) >= 3:
            recent = scores[-3:]
            if (
                recent[-1] > recent[0]
            ):
                trend = "improving"
            elif (
                recent[-1] < recent[0]
            ):
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "insufficient_data"

        self._profiles[user_id] = {
            "avg_score": avg,
            "trend": trend,
            "score_count": len(scores),
            "current_difficulty": (
                self._profiles.get(
                    user_id, {},
                ).get(
                    "current_difficulty",
                    "medium",
                )
            ),
        }

        return {
            "user_id": user_id,
            "avg_score": avg,
            "trend": trend,
            "score_count": len(scores),
            "analyzed": True,
        }

    def adjust_difficulty(
        self,
        user_id: str,
        current_score: float = 0.0,
    ) -> dict[str, Any]:
        """Zorluk ayarlar.

        Args:
            user_id: Kullanıcı kimliği.
            current_score: Güncel puan.

        Returns:
            Ayar bilgisi.
        """
        profile = self._profiles.get(
            user_id, {},
        )
        current = profile.get(
            "current_difficulty", "medium",
        )

        levels = [
            "easy", "medium",
            "hard", "expert",
        ]
        idx = levels.index(current)

        if current_score >= 90 and idx < 3:
            new_level = levels[idx + 1]
        elif (
            current_score < 40 and idx > 0
        ):
            new_level = levels[idx - 1]
        else:
            new_level = current

        changed = new_level != current

        if user_id not in self._profiles:
            self._profiles[user_id] = {}
        self._profiles[user_id][
            "current_difficulty"
        ] = new_level

        if changed:
            self._stats[
                "adjustments_made"
            ] += 1

        return {
            "user_id": user_id,
            "previous": current,
            "new_level": new_level,
            "changed": changed,
            "adjusted": True,
        }

    def optimize_challenge(
        self,
        user_id: str,
    ) -> dict[str, Any]:
        """Meydan okuma optimizasyonu.

        Args:
            user_id: Kullanıcı kimliği.

        Returns:
            Optimizasyon bilgisi.
        """
        profile = self._profiles.get(
            user_id, {},
        )
        avg = profile.get("avg_score", 50)
        trend = profile.get(
            "trend", "stable",
        )

        if trend == "improving":
            strategy = "increase_gradually"
        elif trend == "declining":
            strategy = "reduce_and_support"
        else:
            strategy = "maintain_current"

        target_score = 70.0

        return {
            "user_id": user_id,
            "strategy": strategy,
            "target_score": target_score,
            "current_avg": avg,
            "optimized": True,
        }

    def prevent_frustration(
        self,
        user_id: str,
        consecutive_failures: int = 0,
        threshold: int = 3,
    ) -> dict[str, Any]:
        """Hayal kırıklığı önler.

        Args:
            user_id: Kullanıcı kimliği.
            consecutive_failures: Ardışık
                başarısızlık.
            threshold: Eşik.

        Returns:
            Önleme bilgisi.
        """
        frustrated = (
            consecutive_failures
            >= threshold
        )

        actions = []
        if frustrated:
            actions.append(
                "reduce_difficulty",
            )
            actions.append(
                "offer_hint",
            )
            actions.append(
                "provide_encouragement",
            )
            self._stats[
                "frustrations_prevented"
            ] += 1

        return {
            "user_id": user_id,
            "frustrated": frustrated,
            "consecutive_failures": (
                consecutive_failures
            ),
            "actions": actions,
            "prevented": frustrated,
        }

    def maximize_engagement(
        self,
        user_id: str,
    ) -> dict[str, Any]:
        """Etkileşim maksimizasyonu.

        Args:
            user_id: Kullanıcı kimliği.

        Returns:
            Maksimizasyon bilgisi.
        """
        profile = self._profiles.get(
            user_id, {},
        )
        avg = profile.get("avg_score", 50)
        trend = profile.get(
            "trend", "stable",
        )

        recommendations = []

        if avg > 85:
            recommendations.append(
                "introduce_bonus_challenges",
            )
        if trend == "declining":
            recommendations.append(
                "gamification_boost",
            )
        if avg < 50:
            recommendations.append(
                "peer_support",
            )

        if not recommendations:
            recommendations.append(
                "continue_current_path",
            )

        return {
            "user_id": user_id,
            "recommendations": (
                recommendations
            ),
            "engagement_score": min(
                100, avg * 1.2,
            ),
            "maximized": True,
        }

    @property
    def adjustment_count(self) -> int:
        """Ayarlama sayısı."""
        return self._stats[
            "adjustments_made"
        ]

    @property
    def prevention_count(self) -> int:
        """Önleme sayısı."""
        return self._stats[
            "frustrations_prevented"
        ]
