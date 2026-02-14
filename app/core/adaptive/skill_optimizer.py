"""ATLAS Yetenek Optimizasyonu modulu.

Performans profilleme, darbogazlari
belirleme, parametre ayarlama,
verimlilik iyilestirme ve kalite
gelistirme.
"""

import logging
from typing import Any

from app.models.adaptive import SkillLevel

logger = logging.getLogger(__name__)


class SkillOptimizer:
    """Yetenek optimizasyonu.

    Yetenekleri profiller, darbogazlari
    bulur ve optimizasyon oner.

    Attributes:
        _skills: Yetenek profilleri.
        _metrics: Performans metrikleri.
        _optimizations: Uygulanan optimizasyonlar.
    """

    def __init__(self) -> None:
        """Yetenek optimizasyonunu baslatir."""
        self._skills: dict[str, dict[str, Any]] = {}
        self._metrics: dict[str, list[float]] = {}
        self._optimizations: list[dict[str, Any]] = []
        self._bottlenecks: list[dict[str, Any]] = []

        logger.info("SkillOptimizer baslatildi")

    def register_skill(
        self,
        name: str,
        level: SkillLevel = SkillLevel.NOVICE,
        parameters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Yetenek kaydeder.

        Args:
            name: Yetenek adi.
            level: Seviye.
            parameters: Parametreler.

        Returns:
            Yetenek bilgisi.
        """
        skill = {
            "name": name,
            "level": level.value,
            "parameters": parameters or {},
            "performance_scores": [],
            "usage_count": 0,
        }
        self._skills[name] = skill
        return skill

    def record_performance(
        self,
        skill_name: str,
        score: float,
    ) -> bool:
        """Performans kaydeder.

        Args:
            skill_name: Yetenek adi.
            score: Performans skoru (0.0-1.0).

        Returns:
            Basarili ise True.
        """
        skill = self._skills.get(skill_name)
        if not skill:
            return False

        score = max(0.0, min(1.0, score))
        skill["performance_scores"].append(score)
        skill["usage_count"] += 1

        if skill_name not in self._metrics:
            self._metrics[skill_name] = []
        self._metrics[skill_name].append(score)

        # Seviye guncelle
        self._update_level(skill_name)
        return True

    def identify_bottlenecks(
        self,
        threshold: float = 0.4,
    ) -> list[dict[str, Any]]:
        """Darbogazlari belirler.

        Args:
            threshold: Esik degeri.

        Returns:
            Darbogazlar.
        """
        bottlenecks: list[dict[str, Any]] = []

        for name, skill in self._skills.items():
            scores = skill["performance_scores"]
            if not scores:
                continue

            avg = sum(scores) / len(scores)
            if avg < threshold:
                bn = {
                    "skill": name,
                    "avg_score": avg,
                    "level": skill["level"],
                    "usage_count": skill["usage_count"],
                    "suggestion": self._suggest_improvement(
                        name, avg,
                    ),
                }
                bottlenecks.append(bn)

        self._bottlenecks = bottlenecks
        return bottlenecks

    def tune_parameter(
        self,
        skill_name: str,
        param_key: str,
        new_value: Any,
    ) -> bool:
        """Parametre ayarlar.

        Args:
            skill_name: Yetenek adi.
            param_key: Parametre anahtari.
            new_value: Yeni deger.

        Returns:
            Basarili ise True.
        """
        skill = self._skills.get(skill_name)
        if not skill:
            return False

        old_value = skill["parameters"].get(param_key)
        skill["parameters"][param_key] = new_value

        self._optimizations.append({
            "skill": skill_name,
            "param": param_key,
            "old_value": old_value,
            "new_value": new_value,
        })
        return True

    def get_skill_profile(
        self,
        skill_name: str,
    ) -> dict[str, Any] | None:
        """Yetenek profili getirir.

        Args:
            skill_name: Yetenek adi.

        Returns:
            Profil bilgisi veya None.
        """
        skill = self._skills.get(skill_name)
        if not skill:
            return None

        scores = skill["performance_scores"]
        avg = sum(scores) / len(scores) if scores else 0.0
        trend = self._calc_trend(scores)

        return {
            "name": skill["name"],
            "level": skill["level"],
            "avg_score": avg,
            "trend": trend,
            "usage_count": skill["usage_count"],
            "parameters": skill["parameters"],
        }

    def get_improvement_suggestions(
        self,
    ) -> list[dict[str, Any]]:
        """Iyilestirme onerileri getirir.

        Returns:
            Oneri listesi.
        """
        suggestions: list[dict[str, Any]] = []

        for name, skill in self._skills.items():
            scores = skill["performance_scores"]
            if not scores:
                continue

            avg = sum(scores) / len(scores)
            trend = self._calc_trend(scores)

            if avg < 0.5 or trend == "declining":
                suggestions.append({
                    "skill": name,
                    "avg_score": avg,
                    "trend": trend,
                    "suggestion": self._suggest_improvement(
                        name, avg,
                    ),
                })

        return suggestions

    def _update_level(
        self,
        skill_name: str,
    ) -> None:
        """Yetenek seviyesini gunceller.

        Args:
            skill_name: Yetenek adi.
        """
        skill = self._skills.get(skill_name)
        if not skill:
            return

        scores = skill["performance_scores"]
        if len(scores) < 3:
            return

        avg = sum(scores[-10:]) / len(scores[-10:])
        levels = [
            (0.9, SkillLevel.EXPERT),
            (0.7, SkillLevel.ADVANCED),
            (0.5, SkillLevel.INTERMEDIATE),
            (0.3, SkillLevel.BEGINNER),
        ]
        for threshold, level in levels:
            if avg >= threshold:
                skill["level"] = level.value
                return
        skill["level"] = SkillLevel.NOVICE.value

    def _calc_trend(
        self,
        scores: list[float],
    ) -> str:
        """Trend hesaplar.

        Args:
            scores: Skor listesi.

        Returns:
            Trend yonu.
        """
        if len(scores) < 4:
            return "insufficient_data"

        mid = len(scores) // 2
        first_half = sum(scores[:mid]) / mid
        second_half = sum(scores[mid:]) / (len(scores) - mid)

        diff = second_half - first_half
        if diff > 0.05:
            return "improving"
        if diff < -0.05:
            return "declining"
        return "stable"

    def _suggest_improvement(
        self,
        skill_name: str,
        avg_score: float,
    ) -> str:
        """Iyilestirme onerisi uretir.

        Args:
            skill_name: Yetenek adi.
            avg_score: Ortalama skor.

        Returns:
            Oneri metni.
        """
        if avg_score < 0.2:
            return f"{skill_name}: Temel egitim gerekli"
        if avg_score < 0.4:
            return f"{skill_name}: Pratik arttirilmali"
        if avg_score < 0.6:
            return f"{skill_name}: Parametre ayarlama oneriliyor"
        return f"{skill_name}: Ileri optimizasyon"

    @property
    def skill_count(self) -> int:
        """Yetenek sayisi."""
        return len(self._skills)

    @property
    def optimization_count(self) -> int:
        """Optimizasyon sayisi."""
        return len(self._optimizations)

    @property
    def bottleneck_count(self) -> int:
        """Darbogazlar sayisi."""
        return len(self._bottlenecks)
