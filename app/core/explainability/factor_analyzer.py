"""ATLAS Faktor Analizcisi modulu.

Anahtar faktorler, faktor agirliklari,
katki analizi, hassasiyet analizi, karsi-olgusal.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class FactorAnalyzer:
    """Faktor analizcisi.

    Karar faktorlerini analiz eder.

    Attributes:
        _analyses: Analiz kayitlari.
        _factors: Faktor kayitlari.
    """

    def __init__(self) -> None:
        """Faktor analizcisini baslatir."""
        self._analyses: dict[
            str, dict[str, Any]
        ] = {}
        self._factors: dict[
            str, list[dict[str, Any]]
        ] = {}
        self._stats = {
            "analyzed": 0,
        }

        logger.info(
            "FactorAnalyzer baslatildi",
        )

    def analyze_factors(
        self,
        decision_id: str,
        factors: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Faktor analizi yapar.

        Args:
            decision_id: Karar ID.
            factors: Faktor listesi
                [{name, value, weight}].

        Returns:
            Analiz sonucu.
        """
        if not factors:
            return {
                "decision_id": decision_id,
                "factors": [],
                "key_factors": [],
            }

        analyzed = []
        total_weight = sum(
            f.get("weight", 1.0)
            for f in factors
        )

        for f in factors:
            weight = f.get("weight", 1.0)
            value = f.get("value", 0.0)
            contribution = (
                weight * value / max(
                    total_weight, 0.001,
                )
            )

            influence = "neutral"
            if contribution > 0.2:
                influence = "positive"
            elif contribution > 0.5:
                influence = "critical"
            elif contribution < -0.2:
                influence = "negative"

            analyzed.append({
                "name": f.get("name", ""),
                "value": value,
                "weight": weight,
                "weight_pct": round(
                    weight / max(
                        total_weight, 0.001,
                    ) * 100, 1,
                ),
                "contribution": round(
                    contribution, 4,
                ),
                "influence": influence,
            })

        analyzed.sort(
            key=lambda x: abs(
                x["contribution"],
            ),
            reverse=True,
        )

        key_factors = [
            f for f in analyzed
            if abs(f["contribution"]) > 0.1
        ]

        self._factors[decision_id] = analyzed
        self._analyses[decision_id] = {
            "decision_id": decision_id,
            "factor_count": len(analyzed),
            "key_factor_count": len(key_factors),
            "analyzed_at": time.time(),
        }
        self._stats["analyzed"] += 1

        return {
            "decision_id": decision_id,
            "factors": analyzed,
            "key_factors": key_factors,
            "total_weight": round(
                total_weight, 4,
            ),
        }

    def get_key_factors(
        self,
        decision_id: str,
        top_n: int = 5,
    ) -> list[dict[str, Any]]:
        """Anahtar faktorleri getirir.

        Args:
            decision_id: Karar ID.
            top_n: En onemli N faktor.

        Returns:
            Anahtar faktorler.
        """
        factors = self._factors.get(
            decision_id, [],
        )
        return factors[:top_n]

    def calculate_weights(
        self,
        factors: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Faktor agirliklarini hesaplar.

        Args:
            factors: Faktor listesi.

        Returns:
            Agirlik bilgisi.
        """
        total = sum(
            f.get("weight", 1.0)
            for f in factors
        )

        weights = {}
        for f in factors:
            name = f.get("name", "")
            w = f.get("weight", 1.0)
            weights[name] = round(
                w / max(total, 0.001) * 100, 1,
            )

        return {
            "weights": weights,
            "total": round(total, 4),
            "factor_count": len(factors),
        }

    def contribution_analysis(
        self,
        decision_id: str,
    ) -> dict[str, Any]:
        """Katki analizi yapar.

        Args:
            decision_id: Karar ID.

        Returns:
            Katki analizi.
        """
        factors = self._factors.get(
            decision_id, [],
        )
        if not factors:
            return {
                "decision_id": decision_id,
                "contributions": {},
            }

        contributions = {}
        for f in factors:
            contributions[f["name"]] = {
                "contribution": f["contribution"],
                "weight_pct": f["weight_pct"],
                "influence": f["influence"],
            }

        return {
            "decision_id": decision_id,
            "contributions": contributions,
            "factor_count": len(factors),
        }

    def sensitivity_analysis(
        self,
        decision_id: str,
        factor_name: str,
        variations: list[float] | None = None,
    ) -> dict[str, Any]:
        """Hassasiyet analizi yapar.

        Args:
            decision_id: Karar ID.
            factor_name: Faktor adi.
            variations: Varyasyonlar.

        Returns:
            Hassasiyet bilgisi.
        """
        factors = self._factors.get(
            decision_id, [],
        )

        target = None
        for f in factors:
            if f["name"] == factor_name:
                target = f
                break

        if not target:
            return {
                "error": "factor_not_found",
            }

        if variations is None:
            variations = [
                -0.5, -0.25, 0.0, 0.25, 0.5,
            ]

        base_value = target["value"]
        results = []

        for var in variations:
            new_value = base_value * (1 + var)
            new_contribution = (
                target["weight"]
                * new_value
                / max(
                    sum(
                        f["weight"]
                        for f in factors
                    ),
                    0.001,
                )
            )
            results.append({
                "variation": var,
                "new_value": round(
                    new_value, 4,
                ),
                "contribution": round(
                    new_contribution, 4,
                ),
                "change": round(
                    new_contribution
                    - target["contribution"],
                    4,
                ),
            })

        return {
            "decision_id": decision_id,
            "factor": factor_name,
            "base_value": base_value,
            "sensitivity": results,
            "is_sensitive": any(
                abs(r["change"]) > 0.05
                for r in results
            ),
        }

    def counterfactual_factors(
        self,
        decision_id: str,
        target_outcome: str = "opposite",
    ) -> dict[str, Any]:
        """Karsi-olgusal faktor analizi.

        Args:
            decision_id: Karar ID.
            target_outcome: Hedef sonuc.

        Returns:
            Karsi-olgusal bilgisi.
        """
        factors = self._factors.get(
            decision_id, [],
        )
        if not factors:
            return {
                "decision_id": decision_id,
                "changes_needed": [],
            }

        changes = []
        for f in factors:
            if abs(f["contribution"]) > 0.1:
                changes.append({
                    "factor": f["name"],
                    "current_value": f["value"],
                    "suggested_change": (
                        "increase"
                        if f["contribution"] < 0
                        else "decrease"
                    ),
                    "impact": abs(
                        f["contribution"],
                    ),
                })

        changes.sort(
            key=lambda x: x["impact"],
            reverse=True,
        )

        return {
            "decision_id": decision_id,
            "target": target_outcome,
            "changes_needed": changes,
            "min_changes": min(
                len(changes), 1,
            ),
        }

    @property
    def analysis_count(self) -> int:
        """Analiz sayisi."""
        return self._stats["analyzed"]
