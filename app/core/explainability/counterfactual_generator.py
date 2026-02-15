"""ATLAS Karsi-Olgusal Uretici modulu.

Ya-olsaydi senaryolari, minimal degisiklikler,
alternatif sonuclar, hassasiyet sinirlari, eyleme donuk icerikler.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class CounterfactualGenerator:
    """Karsi-olgusal uretici.

    Karsi-olgusal senaryolar uretir.

    Attributes:
        _counterfactuals: Karsi-olgusal kayitlari.
        _scenarios: Senaryo kayitlari.
    """

    def __init__(self) -> None:
        """Karsi-olgusal ureticiyi baslatir."""
        self._counterfactuals: dict[
            str, list[dict[str, Any]]
        ] = {}
        self._scenarios: list[
            dict[str, Any]
        ] = []
        self._stats = {
            "generated": 0,
        }

        logger.info(
            "CounterfactualGenerator "
            "baslatildi",
        )

    def generate_what_if(
        self,
        decision_id: str,
        factor_name: str,
        original_value: float,
        new_value: float,
        factors: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Ya-olsaydi senaryosu uretir.

        Args:
            decision_id: Karar ID.
            factor_name: Faktor adi.
            original_value: Orijinal deger.
            new_value: Yeni deger.
            factors: Tum faktorler.

        Returns:
            Senaryo bilgisi.
        """
        change_pct = 0.0
        if original_value != 0:
            change_pct = (
                (new_value - original_value)
                / abs(original_value) * 100
            )

        # Yeni sonucu tahmin et
        total_weight = sum(
            f.get("weight", 1.0)
            for f in factors
        )

        original_score = 0.0
        new_score = 0.0
        for f in factors:
            w = f.get("weight", 1.0)
            v = f.get("value", 0.0)
            original_score += w * v
            if f.get("name") == factor_name:
                new_score += w * new_value
            else:
                new_score += w * v

        if total_weight > 0:
            original_score /= total_weight
            new_score /= total_weight

        outcome_change = (
            "same"
            if abs(new_score - original_score)
            < 0.01
            else (
                "better"
                if new_score > original_score
                else "worse"
            )
        )

        scenario = {
            "decision_id": decision_id,
            "type": "what_if",
            "factor": factor_name,
            "original_value": original_value,
            "new_value": new_value,
            "change_pct": round(change_pct, 1),
            "original_score": round(
                original_score, 4,
            ),
            "new_score": round(new_score, 4),
            "outcome_change": outcome_change,
            "generated_at": time.time(),
        }

        if decision_id not in (
            self._counterfactuals
        ):
            self._counterfactuals[
                decision_id
            ] = []
        self._counterfactuals[
            decision_id
        ].append(scenario)
        self._scenarios.append(scenario)
        self._stats["generated"] += 1

        return scenario

    def find_minimal_change(
        self,
        decision_id: str,
        factors: list[dict[str, Any]],
        target_change: str = "opposite",
    ) -> dict[str, Any]:
        """Minimal degisiklik bulur.

        Args:
            decision_id: Karar ID.
            factors: Faktorler.
            target_change: Hedef degisiklik.

        Returns:
            Minimal degisiklik bilgisi.
        """
        if not factors:
            return {
                "decision_id": decision_id,
                "changes": [],
            }

        # En etkili faktoru bul
        sorted_factors = sorted(
            factors,
            key=lambda f: abs(
                f.get("weight", 0)
                * f.get("value", 0),
            ),
            reverse=True,
        )

        changes = []
        for f in sorted_factors[:3]:
            name = f.get("name", "")
            value = f.get("value", 0.0)

            if target_change == "opposite":
                new_val = -value if value != 0 else 1.0
            else:
                new_val = value * 1.5

            changes.append({
                "factor": name,
                "current_value": value,
                "required_value": round(
                    new_val, 4,
                ),
                "change_magnitude": round(
                    abs(new_val - value), 4,
                ),
            })

        changes.sort(
            key=lambda x: x[
                "change_magnitude"
            ],
        )

        result = {
            "decision_id": decision_id,
            "target": target_change,
            "changes": changes,
            "minimal_change": (
                changes[0] if changes else None
            ),
            "generated_at": time.time(),
        }

        self._scenarios.append(result)
        self._stats["generated"] += 1

        return result

    def generate_alternatives(
        self,
        decision_id: str,
        factors: list[dict[str, Any]],
        num_alternatives: int = 3,
    ) -> dict[str, Any]:
        """Alternatif sonuclar uretir.

        Args:
            decision_id: Karar ID.
            factors: Faktorler.
            num_alternatives: Alternatif sayisi.

        Returns:
            Alternatif sonuclar.
        """
        alternatives = []

        for i in range(num_alternatives):
            modified = []
            multiplier = 1.0 + (i + 1) * 0.2

            for f in factors:
                new_val = (
                    f.get("value", 0.0)
                    * multiplier
                )
                modified.append({
                    "name": f.get("name", ""),
                    "original": f.get(
                        "value", 0.0,
                    ),
                    "modified": round(
                        new_val, 4,
                    ),
                })

            total_weight = sum(
                f.get("weight", 1.0)
                for f in factors
            )
            score = 0.0
            for j, f in enumerate(factors):
                w = f.get("weight", 1.0)
                score += w * modified[j][
                    "modified"
                ]
            if total_weight > 0:
                score /= total_weight

            alternatives.append({
                "alternative_id": i + 1,
                "multiplier": multiplier,
                "factors": modified,
                "score": round(score, 4),
            })

        result = {
            "decision_id": decision_id,
            "alternatives": alternatives,
            "count": len(alternatives),
            "generated_at": time.time(),
        }

        self._scenarios.append(result)
        self._stats["generated"] += 1

        return result

    def sensitivity_bounds(
        self,
        decision_id: str,
        factor_name: str,
        factors: list[dict[str, Any]],
        threshold: float = 0.0,
    ) -> dict[str, Any]:
        """Hassasiyet sinirlarini belirler.

        Args:
            decision_id: Karar ID.
            factor_name: Faktor adi.
            factors: Faktorler.
            threshold: Sonuc esigi.

        Returns:
            Sinir bilgisi.
        """
        target = None
        for f in factors:
            if f.get("name") == factor_name:
                target = f
                break

        if not target:
            return {"error": "factor_not_found"}

        value = target.get("value", 0.0)
        weight = target.get("weight", 1.0)

        total_weight = sum(
            f.get("weight", 1.0)
            for f in factors
        )

        # Alt ve ust sinirlari bul
        lower_bound = value - abs(value) * 0.5
        upper_bound = value + abs(value) * 0.5

        if value == 0:
            lower_bound = -1.0
            upper_bound = 1.0

        result = {
            "decision_id": decision_id,
            "factor": factor_name,
            "current_value": value,
            "lower_bound": round(
                lower_bound, 4,
            ),
            "upper_bound": round(
                upper_bound, 4,
            ),
            "sensitivity": round(
                weight / max(
                    total_weight, 0.001,
                ),
                4,
            ),
            "generated_at": time.time(),
        }

        self._scenarios.append(result)
        self._stats["generated"] += 1

        return result

    def actionable_insights(
        self,
        decision_id: str,
        factors: list[dict[str, Any]],
        target: str = "improve",
    ) -> dict[str, Any]:
        """Eyleme donuk icerikler uretir.

        Args:
            decision_id: Karar ID.
            factors: Faktorler.
            target: Hedef (improve/maintain).

        Returns:
            Icerik bilgisi.
        """
        insights = []

        sorted_factors = sorted(
            factors,
            key=lambda f: abs(
                f.get("contribution",
                       f.get("weight", 0)
                       * f.get("value", 0)),
            ),
            reverse=True,
        )

        for f in sorted_factors:
            name = f.get("name", "")
            value = f.get("value", 0.0)
            weight = f.get("weight", 1.0)

            if target == "improve":
                if value < 0.5:
                    action = "increase"
                    priority = "high"
                else:
                    action = "maintain"
                    priority = "low"
            else:
                action = "monitor"
                priority = (
                    "high" if weight > 0.5
                    else "medium"
                )

            insights.append({
                "factor": name,
                "action": action,
                "priority": priority,
                "current_value": value,
                "impact": round(
                    weight * value, 4,
                ),
            })

        result = {
            "decision_id": decision_id,
            "target": target,
            "insights": insights,
            "count": len(insights),
            "generated_at": time.time(),
        }

        self._scenarios.append(result)
        self._stats["generated"] += 1

        return result

    def get_counterfactuals(
        self,
        decision_id: str,
    ) -> list[dict[str, Any]]:
        """Karsi-olgusallari getirir.

        Args:
            decision_id: Karar ID.

        Returns:
            Karsi-olgusal listesi.
        """
        return list(
            self._counterfactuals.get(
                decision_id, [],
            ),
        )

    @property
    def generated_count(self) -> int:
        """Uretilen sayisi."""
        return self._stats["generated"]
