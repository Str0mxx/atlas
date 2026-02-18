"""
Anahtar saglik puani modulu.

Saglik puanlama, yas faktoru,
kullanim faktoru, yetki faktoru,
genel degerlendirme.
"""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class KeyHealthScore:
    """Anahtar saglik puani.

    Attributes:
        _scores: Puan kayitlari.
        _assessments: Degerlendirmeler.
        _weights: Faktor agirliklari.
        _stats: Istatistikler.
    """

    HEALTH_GRADES: list[str] = [
        "excellent",
        "good",
        "fair",
        "poor",
        "critical",
    ]

    FACTORS: list[str] = [
        "age",
        "usage",
        "permission",
        "rotation",
        "anomaly",
    ]

    def __init__(self) -> None:
        """Puanlayiciyi baslatir."""
        self._scores: dict[
            str, dict
        ] = {}
        self._assessments: list[dict] = []
        self._weights: dict[
            str, float
        ] = {
            "age": 0.2,
            "usage": 0.25,
            "permission": 0.2,
            "rotation": 0.2,
            "anomaly": 0.15,
        }
        self._thresholds: dict[
            str, dict
        ] = {
            "excellent": {
                "min": 90, "max": 100
            },
            "good": {
                "min": 70, "max": 89
            },
            "fair": {
                "min": 50, "max": 69
            },
            "poor": {
                "min": 30, "max": 49
            },
            "critical": {
                "min": 0, "max": 29
            },
        }
        self._stats: dict[str, int] = {
            "scores_calculated": 0,
            "assessments_run": 0,
            "critical_keys": 0,
            "excellent_keys": 0,
        }
        logger.info(
            "KeyHealthScore baslatildi"
        )

    @property
    def scored_count(self) -> int:
        """Puanlanan anahtar sayisi."""
        return len(self._scores)

    def set_weights(
        self,
        weights: dict[str, float] | None = None,
    ) -> dict[str, Any]:
        """Faktor agirliklarini ayarlar.

        Args:
            weights: Yeni agirliklar.

        Returns:
            Ayar bilgisi.
        """
        try:
            w = weights or {}
            for k, v in w.items():
                if k in self._weights:
                    self._weights[k] = v

            total = sum(
                self._weights.values()
            )

            return {
                "weights": dict(
                    self._weights
                ),
                "total": round(total, 2),
                "updated": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "updated": False,
                "error": str(e),
            }

    def calculate_age_score(
        self,
        age_days: int = 0,
        max_age_days: int = 365,
    ) -> float:
        """Yas puani hesaplar.

        Args:
            age_days: Yas (gun).
            max_age_days: Max yas.

        Returns:
            Puan (0-100).
        """
        if age_days <= 0:
            return 100.0
        if age_days >= max_age_days:
            return 0.0
        ratio = age_days / max_age_days
        return round(
            (1 - ratio) * 100, 1
        )

    def calculate_usage_score(
        self,
        total_usage: int = 0,
        error_count: int = 0,
        days_since_last_use: int = 0,
    ) -> float:
        """Kullanim puani hesaplar.

        Args:
            total_usage: Toplam kullanim.
            error_count: Hata sayisi.
            days_since_last_use: Son kullanim.

        Returns:
            Puan (0-100).
        """
        score = 100.0

        # Hic kullanilmamis
        if total_usage == 0:
            return 30.0

        # Hata orani
        if total_usage > 0:
            error_rate = (
                error_count
                / total_usage
            )
            if error_rate > 0.5:
                score -= 40
            elif error_rate > 0.2:
                score -= 20
            elif error_rate > 0.1:
                score -= 10

        # Son kullanim
        if days_since_last_use > 90:
            score -= 30
        elif days_since_last_use > 30:
            score -= 15

        return max(round(score, 1), 0.0)

    def calculate_permission_score(
        self,
        total_scopes: int = 0,
        used_scopes: int = 0,
        has_admin: bool = False,
    ) -> float:
        """Yetki puani hesaplar.

        Args:
            total_scopes: Toplam kapsam.
            used_scopes: Kullanilan kapsam.
            has_admin: Admin yetkisi var mi.

        Returns:
            Puan (0-100).
        """
        score = 100.0

        if total_scopes == 0:
            return 100.0

        # Kullanilmayan kapsam
        unused = total_scopes - used_scopes
        if unused > 0:
            penalty = min(
                unused * 10, 40
            )
            score -= penalty

        # Admin yetkisi
        if has_admin:
            score -= 20

        # Cok fazla kapsam
        if total_scopes > 10:
            score -= 15
        elif total_scopes > 5:
            score -= 5

        return max(round(score, 1), 0.0)

    def calculate_rotation_score(
        self,
        days_since_rotation: int = 0,
        rotation_policy_days: int = 90,
        rotation_count: int = 0,
    ) -> float:
        """Rotasyon puani hesaplar.

        Args:
            days_since_rotation: Son rotasyon.
            rotation_policy_days: Politika.
            rotation_count: Rotasyon sayisi.

        Returns:
            Puan (0-100).
        """
        score = 100.0

        if rotation_policy_days <= 0:
            return 50.0

        ratio = (
            days_since_rotation
            / rotation_policy_days
        )

        if ratio > 2.0:
            score = 10.0
        elif ratio > 1.5:
            score = 30.0
        elif ratio > 1.0:
            score = 50.0
        elif ratio > 0.8:
            score = 70.0
        else:
            score = 100.0

        # Hic rotate edilmemis
        if rotation_count == 0:
            score = min(score, 60.0)

        return round(score, 1)

    def calculate_anomaly_score(
        self,
        anomaly_count: int = 0,
        critical_anomalies: int = 0,
    ) -> float:
        """Anomali puani hesaplar.

        Args:
            anomaly_count: Anomali sayisi.
            critical_anomalies: Kritik.

        Returns:
            Puan (0-100).
        """
        score = 100.0

        if critical_anomalies > 0:
            score -= min(
                critical_anomalies * 30,
                60,
            )

        non_critical = (
            anomaly_count
            - critical_anomalies
        )
        if non_critical > 0:
            score -= min(
                non_critical * 10, 30
            )

        return max(round(score, 1), 0.0)

    def calculate_health(
        self,
        key_id: str = "",
        age_days: int = 0,
        total_usage: int = 0,
        error_count: int = 0,
        days_since_last_use: int = 0,
        total_scopes: int = 0,
        used_scopes: int = 0,
        has_admin: bool = False,
        days_since_rotation: int = 0,
        rotation_policy_days: int = 90,
        rotation_count: int = 0,
        anomaly_count: int = 0,
        critical_anomalies: int = 0,
    ) -> dict[str, Any]:
        """Genel saglik hesaplar.

        Args:
            key_id: Anahtar ID.
            age_days: Yas.
            total_usage: Kullanim.
            error_count: Hata.
            days_since_last_use: Son kullanim.
            total_scopes: Kapsam.
            used_scopes: Kullanilan kapsam.
            has_admin: Admin.
            days_since_rotation: Rotasyon.
            rotation_policy_days: Politika.
            rotation_count: Rotasyon sayisi.
            anomaly_count: Anomali.
            critical_anomalies: Kritik.

        Returns:
            Saglik bilgisi.
        """
        try:
            self._stats[
                "scores_calculated"
            ] += 1

            # Faktor puanlari
            factors = {
                "age": (
                    self.calculate_age_score(
                        age_days
                    )
                ),
                "usage": (
                    self.calculate_usage_score(
                        total_usage,
                        error_count,
                        days_since_last_use,
                    )
                ),
                "permission": (
                    self.calculate_permission_score(
                        total_scopes,
                        used_scopes,
                        has_admin,
                    )
                ),
                "rotation": (
                    self.calculate_rotation_score(
                        days_since_rotation,
                        rotation_policy_days,
                        rotation_count,
                    )
                ),
                "anomaly": (
                    self.calculate_anomaly_score(
                        anomaly_count,
                        critical_anomalies,
                    )
                ),
            }

            # Agirlikli ortalama
            total = sum(
                factors[f]
                * self._weights[f]
                for f in self.FACTORS
            )
            overall = round(total, 1)

            # Derece
            grade = "critical"
            for g, t in (
                self._thresholds.items()
            ):
                if (
                    t["min"]
                    <= overall
                    <= t["max"]
                ):
                    grade = g
                    break

            if grade == "critical":
                self._stats[
                    "critical_keys"
                ] += 1
            elif grade == "excellent":
                self._stats[
                    "excellent_keys"
                ] += 1

            result = {
                "key_id": key_id,
                "overall_score": overall,
                "grade": grade,
                "factors": factors,
                "weights": dict(
                    self._weights
                ),
                "calculated_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
                "calculated": True,
            }
            self._scores[key_id] = result

            return result

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "calculated": False,
                "error": str(e),
            }

    def assess_fleet(
        self,
        key_data: (
            list[dict] | None
        ) = None,
    ) -> dict[str, Any]:
        """Tum anahtarlari degerlendirir.

        Args:
            key_data: Anahtar verileri.

        Returns:
            Degerlendirme bilgisi.
        """
        try:
            self._stats[
                "assessments_run"
            ] += 1
            keys = key_data or []
            results: list[dict] = []
            grade_dist: dict[
                str, int
            ] = {}

            for kd in keys:
                r = self.calculate_health(
                    **kd
                )
                results.append(r)
                g = r.get(
                    "grade", "critical"
                )
                grade_dist[g] = (
                    grade_dist.get(g, 0)
                    + 1
                )

            scores = [
                r["overall_score"]
                for r in results
                if r.get("calculated")
            ]
            avg = (
                round(
                    sum(scores)
                    / len(scores),
                    1,
                )
                if scores
                else 0.0
            )

            assessment = {
                "total_keys": len(keys),
                "average_score": avg,
                "grade_distribution": (
                    grade_dist
                ),
                "lowest_score": (
                    min(scores)
                    if scores
                    else 0
                ),
                "highest_score": (
                    max(scores)
                    if scores
                    else 0
                ),
                "assessed": True,
            }
            self._assessments.append(
                assessment
            )

            return assessment

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "assessed": False,
                "error": str(e),
            }

    def get_score(
        self,
        key_id: str = "",
    ) -> dict[str, Any]:
        """Puan getirir.

        Args:
            key_id: Anahtar ID.

        Returns:
            Puan bilgisi.
        """
        try:
            score = self._scores.get(
                key_id
            )
            if not score:
                return {
                    "found": False,
                    "error": (
                        "Puan bulunamadi"
                    ),
                }

            return {
                **score,
                "found": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "found": False,
                "error": str(e),
            }

    def get_summary(
        self,
    ) -> dict[str, Any]:
        """Ozet getirir."""
        try:
            scores = [
                s["overall_score"]
                for s in self._scores.values()
                if "overall_score" in s
            ]
            avg = (
                round(
                    sum(scores)
                    / len(scores),
                    1,
                )
                if scores
                else 0.0
            )

            return {
                "total_scored": len(
                    self._scores
                ),
                "average_score": avg,
                "total_assessments": len(
                    self._assessments
                ),
                "weights": dict(
                    self._weights
                ),
                "stats": dict(self._stats),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }
