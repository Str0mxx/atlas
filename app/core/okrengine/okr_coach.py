"""
OKR Coach - OKR koçluğu ve en iyi pratikler modülü.

Bu modül OKR yazımı, takibi, hizalama konularında koçluk sağlar,
yaygın tuzakları uyarır ve eğitim materyalleri sunar.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class OKRCoach:
    """
    OKR koçu - OKR yazımı, iyileştirme, uyarı ve eğitim için yardımcı.

    Attributes:
        _tips: Koçluk ipuçları listesi
        _stats: Koçluk oturum istatistikleri
    """

    def __init__(self) -> None:
        """OKRCoach başlatıcı."""
        self._tips: list[str] = [
            "focus_on_outcomes",
            "be_specific_and_measurable",
            "align_with_strategy",
            "regular_check_ins",
            "celebrate_progress"
        ]
        self._stats: dict[str, int] = {
            "coaching_sessions": 0
        }
        logger.info("OKRCoach initialized")

    @property
    def session_count(self) -> int:
        """
        Toplam koçluk oturum sayısını döndürür.

        Returns:
            Koçluk oturum sayısı
        """
        return self._stats["coaching_sessions"]

    def suggest_best_practices(self, area: str = "general") -> dict[str, Any]:
        """
        Belirli bir alan için OKR en iyi pratiklerini önerir.

        Args:
            area: Pratik alanı (writing/tracking/alignment/general)

        Returns:
            En iyi pratikler bilgisi içeren sözlük
        """
        try:
            practices_map: dict[str, list[str]] = {
                "writing": [
                    "start_with_verbs",
                    "be_specific",
                    "set_measurable_targets",
                    "limit_3_5_krs"
                ],
                "tracking": [
                    "weekly_checkins",
                    "update_confidence",
                    "document_blockers",
                    "celebrate_wins"
                ],
                "alignment": [
                    "cascade_from_top",
                    "cross_team_review",
                    "regular_alignment_checks"
                ],
                "general": [
                    "focus_on_outcomes",
                    "stretch_but_achievable",
                    "transparent_scoring",
                    "learn_from_misses"
                ]
            }

            practices = practices_map.get(area, ["focus_on_outcomes"])

            # İstatistikleri güncelle
            self._stats["coaching_sessions"] += 1

            result = {
                "area": area,
                "practices": practices,
                "practice_count": len(practices),
                "suggested": True
            }

            logger.info(
                f"Best practices suggested for area '{area}': {len(practices)} practices"
            )

            return result

        except Exception as e:
            logger.error(f"Error suggesting best practices: {e}")
            return {
                "area": area,
                "practices": [],
                "practice_count": 0,
                "suggested": False,
                "error": str(e)
            }

    def assist_writing(
        self,
        draft_objective: str = "",
        draft_kr: str = ""
    ) -> dict[str, Any]:
        """
        OKR yazımında yardımcı olur ve taslağı değerlendirir.

        Args:
            draft_objective: Taslak Objective metni
            draft_kr: Taslak Key Result metni

        Returns:
            Yazım değerlendirmesi ve sorunlar içeren sözlük
        """
        try:
            issues: list[str] = []

            # Objective kontrolü
            if len(draft_objective) < 10:
                issues.append("objective_too_short")

            # Key Result kontrolü
            if not draft_kr:
                issues.append("missing_key_result")

            # Ölçülebilirlik kontrolü
            if draft_kr and not any(c.isdigit() for c in draft_kr):
                issues.append("kr_not_measurable")

            # Kalite değerlendirmesi
            if not issues:
                quality = "good"
            elif len(issues) == 1:
                quality = "needs_work"
            else:
                quality = "poor"

            # İstatistikleri güncelle
            self._stats["coaching_sessions"] += 1

            result = {
                "draft_objective": draft_objective,
                "draft_kr": draft_kr,
                "issues": issues,
                "issue_count": len(issues),
                "quality": quality,
                "assisted": True
            }

            logger.info(
                f"Writing assistance provided: quality={quality}, issues={len(issues)}"
            )

            return result

        except Exception as e:
            logger.error(f"Error assisting writing: {e}")
            return {
                "draft_objective": draft_objective,
                "draft_kr": draft_kr,
                "issues": [],
                "issue_count": 0,
                "quality": "unknown",
                "assisted": False,
                "error": str(e)
            }

    def suggest_improvements(
        self,
        score: float = 50.0,
        kr_count: int = 3,
        confidence: float = 0.5
    ) -> dict[str, Any]:
        """
        Mevcut OKR durumuna göre iyileştirme önerileri sunar.

        Args:
            score: Mevcut OKR skoru (0-100)
            kr_count: Key Result sayısı
            confidence: Güven seviyesi (0.0-1.0)

        Returns:
            İyileştirme önerileri içeren sözlük
        """
        try:
            tips: list[str] = []

            # Skor bazlı öneriler
            if score < 40:
                tips.append("lower_targets_or_increase_effort")

            # KR sayısı bazlı öneriler
            if kr_count > 5:
                tips.append("reduce_kr_count_for_focus")
            if kr_count < 2:
                tips.append("add_more_key_results")

            # Güven bazlı öneriler
            if confidence < 0.3:
                tips.append("reassess_feasibility")

            # Yüksek performans önerisi
            if score > 90:
                tips.append("set_more_ambitious_targets")

            # Genel durum
            if not tips:
                tips.append("on_track_keep_going")

            # İstatistikleri güncelle
            self._stats["coaching_sessions"] += 1

            result = {
                "tips": tips,
                "tip_count": len(tips),
                "score": score,
                "kr_count": kr_count,
                "confidence": confidence,
                "improved": True
            }

            logger.info(
                f"Improvements suggested: {len(tips)} tips for score={score:.1f}"
            )

            return result

        except Exception as e:
            logger.error(f"Error suggesting improvements: {e}")
            return {
                "tips": [],
                "tip_count": 0,
                "score": score,
                "kr_count": kr_count,
                "confidence": confidence,
                "improved": False,
                "error": str(e)
            }

    def warn_pitfalls(
        self,
        objective_count: int = 5,
        avg_kr_per_obj: float = 3.0,
        scoring_method: str = "simple_average"
    ) -> dict[str, Any]:
        """
        Yaygın OKR tuzakları konusunda uyarır.

        Args:
            objective_count: Toplam Objective sayısı
            avg_kr_per_obj: Objective başına ortalama KR sayısı
            scoring_method: Puanlama yöntemi

        Returns:
            Uyarılar ve risk seviyesi içeren sözlük
        """
        try:
            warnings: list[str] = []

            # Objective sayısı kontrolü
            if objective_count > 7:
                warnings.append("too_many_objectives")

            # KR sayısı kontrolü
            if avg_kr_per_obj > 5:
                warnings.append("too_many_krs_per_objective")
            if avg_kr_per_obj < 1:
                warnings.append("insufficient_key_results")

            # Puanlama yöntemi kontrolü
            if scoring_method == "binary":
                warnings.append("binary_scoring_loses_nuance")

            # Genel durum
            if not warnings:
                warnings.append("no_major_pitfalls")

            # Risk seviyesi belirleme
            if len(warnings) > 2:
                risk_level = "high"
            elif len(warnings) > 0 and warnings[0] != "no_major_pitfalls":
                risk_level = "medium"
            else:
                risk_level = "low"

            # İstatistikleri güncelle
            self._stats["coaching_sessions"] += 1

            result = {
                "warnings": warnings,
                "warning_count": len(warnings),
                "risk_level": risk_level,
                "warned": True
            }

            logger.info(
                f"Pitfalls warned: {len(warnings)} warnings, risk_level={risk_level}"
            )

            return result

        except Exception as e:
            logger.error(f"Error warning pitfalls: {e}")
            return {
                "warnings": [],
                "warning_count": 0,
                "risk_level": "unknown",
                "warned": False,
                "error": str(e)
            }

    def provide_training(
        self,
        topic: str = "okr_basics",
        level: str = "beginner"
    ) -> dict[str, Any]:
        """
        OKR eğitim materyalleri sağlar.

        Args:
            topic: Eğitim konusu (okr_basics/advanced_okrs/leadership)
            level: Seviye (beginner/intermediate/advanced)

        Returns:
            Eğitim modülleri ve süre bilgisi içeren sözlük
        """
        try:
            modules_map: dict[str, list[str]] = {
                "okr_basics": [
                    "what_are_okrs",
                    "objective_vs_kr",
                    "scoring_system"
                ],
                "advanced_okrs": [
                    "cascading",
                    "cross_functional",
                    "stretch_goals",
                    "cfrs"
                ],
                "leadership": [
                    "setting_company_okrs",
                    "coaching_teams",
                    "review_facilitation"
                ]
            }

            modules = modules_map.get(topic, ["okr_overview"])
            duration_hours = len(modules) * 0.5

            # İstatistikleri güncelle
            self._stats["coaching_sessions"] += 1

            result = {
                "topic": topic,
                "level": level,
                "modules": modules,
                "module_count": len(modules),
                "duration_hours": duration_hours,
                "training_ready": True
            }

            logger.info(
                f"Training provided: topic={topic}, level={level}, "
                f"{len(modules)} modules, {duration_hours}h"
            )

            return result

        except Exception as e:
            logger.error(f"Error providing training: {e}")
            return {
                "topic": topic,
                "level": level,
                "modules": [],
                "module_count": 0,
                "duration_hours": 0.0,
                "training_ready": False,
                "error": str(e)
            }
