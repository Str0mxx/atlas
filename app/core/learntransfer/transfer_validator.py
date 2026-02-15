"""ATLAS Transfer Dogrulayici modulu.

Uygulanabilirlik kontrolu, risk degerlendirme,
catisma tespiti, performans tahmini, guvenlik dogrulama.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class TransferValidator:
    """Transfer dogrulayici.

    Transfer uygulanabilirligini dogrular.

    Attributes:
        _validations: Dogrulama kayitlari.
        _stats: Istatistikler.
    """

    def __init__(self) -> None:
        """Transfer dogrulayiciyi baslatir."""
        self._validations: dict[
            str, dict[str, Any]
        ] = {}
        self._counter = 0
        self._stats = {
            "validated": 0,
            "approved": 0,
            "rejected": 0,
        }

        logger.info(
            "TransferValidator baslatildi",
        )

    def validate_transfer(
        self,
        knowledge: dict[str, Any],
        target_system: str,
        target_context: dict[str, Any],
    ) -> dict[str, Any]:
        """Transfer dogrular.

        Args:
            knowledge: Transfer bilgisi.
            target_system: Hedef sistem.
            target_context: Hedef baglam.

        Returns:
            Dogrulama sonucu.
        """
        self._counter += 1
        vid = f"val_{self._counter}"

        checks = []

        # Uygulanabilirlik
        applicability = (
            self._check_applicability(
                knowledge, target_context,
            )
        )
        checks.append(applicability)

        # Risk degerlendirme
        risk = self._assess_risk(
            knowledge, target_context,
        )
        checks.append(risk)

        # Catisma tespiti
        conflict = self._detect_conflicts(
            knowledge, target_context,
        )
        checks.append(conflict)

        # Performans tahmini
        performance = (
            self._predict_performance(
                knowledge,
            )
        )
        checks.append(performance)

        # Guvenlik
        safety = self._validate_safety(
            knowledge,
        )
        checks.append(safety)

        all_passed = all(
            c["passed"] for c in checks
        )
        risk_level = risk.get(
            "risk_level", "unknown",
        )

        validation = {
            "validation_id": vid,
            "knowledge_id": knowledge.get(
                "knowledge_id", "",
            ),
            "target_system": target_system,
            "approved": all_passed,
            "risk_level": risk_level,
            "checks": checks,
            "check_count": len(checks),
            "passed_count": sum(
                1 for c in checks
                if c["passed"]
            ),
            "validated_at": time.time(),
        }

        self._validations[vid] = validation
        self._stats["validated"] += 1
        if all_passed:
            self._stats["approved"] += 1
        else:
            self._stats["rejected"] += 1

        return validation

    def _check_applicability(
        self,
        knowledge: dict[str, Any],
        target_context: dict[str, Any],
    ) -> dict[str, Any]:
        """Uygulanabilirlik kontrolu.

        Args:
            knowledge: Bilgi.
            target_context: Hedef baglam.

        Returns:
            Kontrol sonucu.
        """
        k_type = knowledge.get(
            "knowledge_type", "",
        )
        supported = target_context.get(
            "supported_types",
            [
                "pattern", "rule", "heuristic",
                "model", "strategy", "lesson",
            ],
        )

        applicable = k_type in supported

        return {
            "check": "applicability",
            "passed": applicable,
            "details": (
                "Knowledge type applicable"
                if applicable
                else (
                    f"Type '{k_type}' not "
                    f"supported"
                )
            ),
        }

    def _assess_risk(
        self,
        knowledge: dict[str, Any],
        target_context: dict[str, Any],
    ) -> dict[str, Any]:
        """Risk degerlendirmesi.

        Args:
            knowledge: Bilgi.
            target_context: Hedef baglam.

        Returns:
            Risk sonucu.
        """
        confidence = knowledge.get(
            "confidence", 0.0,
        )
        is_critical = target_context.get(
            "is_critical", False,
        )

        if confidence >= 0.8:
            risk_level = "low"
        elif confidence >= 0.5:
            risk_level = "medium"
        else:
            risk_level = "high"

        if is_critical and risk_level != "low":
            risk_level = "critical"

        passed = risk_level in ("low", "medium")

        return {
            "check": "risk_assessment",
            "passed": passed,
            "risk_level": risk_level,
            "confidence": confidence,
            "details": (
                f"Risk level: {risk_level}"
            ),
        }

    def _detect_conflicts(
        self,
        knowledge: dict[str, Any],
        target_context: dict[str, Any],
    ) -> dict[str, Any]:
        """Catisma tespiti.

        Args:
            knowledge: Bilgi.
            target_context: Hedef baglam.

        Returns:
            Catisma sonucu.
        """
        conflicts = []
        k_rules = knowledge.get("rules", [])
        existing_rules = target_context.get(
            "existing_rules", [],
        )

        k_outcomes = {
            str(r.get("condition", "")): r.get(
                "outcome", "",
            )
            for r in k_rules
            if isinstance(r, dict)
        }
        e_outcomes = {
            str(r.get("condition", "")): r.get(
                "outcome", "",
            )
            for r in existing_rules
            if isinstance(r, dict)
        }

        for cond, outcome in k_outcomes.items():
            if (
                cond in e_outcomes
                and e_outcomes[cond] != outcome
            ):
                conflicts.append({
                    "condition": cond,
                    "source_outcome": outcome,
                    "target_outcome": (
                        e_outcomes[cond]
                    ),
                })

        return {
            "check": "conflict_detection",
            "passed": len(conflicts) == 0,
            "conflicts": conflicts,
            "conflict_count": len(conflicts),
            "details": (
                "No conflicts"
                if not conflicts
                else (
                    f"{len(conflicts)} "
                    f"conflict(s) found"
                )
            ),
        }

    def _predict_performance(
        self,
        knowledge: dict[str, Any],
    ) -> dict[str, Any]:
        """Performans tahmini.

        Args:
            knowledge: Bilgi.

        Returns:
            Tahmin sonucu.
        """
        confidence = knowledge.get(
            "confidence", 0.0,
        )
        # Basit tahmin: guven * beklenen etki
        predicted_impact = round(
            confidence * 0.8, 3,
        )
        passed = predicted_impact >= 0.2

        return {
            "check": "performance_prediction",
            "passed": passed,
            "predicted_impact": (
                predicted_impact
            ),
            "details": (
                f"Predicted impact: "
                f"{predicted_impact}"
            ),
        }

    def _validate_safety(
        self,
        knowledge: dict[str, Any],
    ) -> dict[str, Any]:
        """Guvenlik dogrulama.

        Args:
            knowledge: Bilgi.

        Returns:
            Guvenlik sonucu.
        """
        content = knowledge.get("content", {})

        # Tehlikeli icerikleri kontrol et
        dangerous = [
            "delete_all", "drop_table",
            "rm_rf", "format_disk",
        ]

        has_danger = any(
            d in str(content).lower()
            for d in dangerous
        )

        return {
            "check": "safety_validation",
            "passed": not has_danger,
            "details": (
                "Safe to transfer"
                if not has_danger
                else "Dangerous content detected"
            ),
        }

    def get_validation(
        self,
        validation_id: str,
    ) -> dict[str, Any]:
        """Dogrulama getirir.

        Args:
            validation_id: Dogrulama ID.

        Returns:
            Dogrulama bilgisi.
        """
        v = self._validations.get(
            validation_id,
        )
        if not v:
            return {
                "error": (
                    "validation_not_found"
                ),
            }
        return dict(v)

    @property
    def validation_count(self) -> int:
        """Dogrulama sayisi."""
        return self._stats["validated"]

    @property
    def approval_rate(self) -> float:
        """Onay orani."""
        total = self._stats["validated"]
        if total == 0:
            return 0.0
        return round(
            self._stats["approved"]
            / total * 100, 1,
        )
