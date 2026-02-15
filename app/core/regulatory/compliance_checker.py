"""ATLAS Uyumluluk Kontrolcusu modulu.

Ön-aksiyon kontrolü, kural değerlendirme,
ihlal tespiti, şiddet değerlendirme, öneri.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class RegulatoryComplianceChecker:
    """Uyumluluk kontrolcüsü.

    Aksiyonları kurallara karşı kontrol eder.

    Attributes:
        _checks: Kontrol kayıtları.
        _violations: İhlal kayıtları.
    """

    def __init__(self) -> None:
        """Kontrolcüyü başlatır."""
        self._checks: list[
            dict[str, Any]
        ] = []
        self._violations: list[
            dict[str, Any]
        ] = []
        self._counter = 0
        self._stats = {
            "checks": 0,
            "violations": 0,
            "passed": 0,
        }

        logger.info(
            "RegulatoryComplianceChecker "
            "baslatildi",
        )

    def check_action(
        self,
        action: str,
        context: dict[str, Any],
        rules: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Aksiyonu kontrol eder.

        Args:
            action: Aksiyon adı.
            context: Aksiyon bağlamı.
            rules: Uygulanacak kurallar.

        Returns:
            Kontrol bilgisi.
        """
        self._counter += 1
        check_id = f"chk_{self._counter}"
        violations = []
        recommendations = []

        for rule in rules:
            if not rule.get("active", True):
                continue

            result = self._evaluate_rule(
                rule, action, context,
            )
            if not result["compliant"]:
                violations.append({
                    "rule_id": rule.get(
                        "rule_id", "",
                    ),
                    "rule_name": rule.get(
                        "name", "",
                    ),
                    "severity": rule.get(
                        "severity", "medium",
                    ),
                    "reason": result["reason"],
                })
                rec = self._get_recommendation(
                    rule, action,
                )
                if rec:
                    recommendations.append(rec)

        is_compliant = len(violations) == 0
        self._stats["checks"] += 1

        if is_compliant:
            self._stats["passed"] += 1
        else:
            self._stats["violations"] += len(
                violations,
            )
            for v in violations:
                self._violations.append({
                    **v,
                    "action": action,
                    "check_id": check_id,
                    "timestamp": time.time(),
                })

        check = {
            "check_id": check_id,
            "action": action,
            "compliant": is_compliant,
            "violations": violations,
            "violation_count": len(violations),
            "recommendations": recommendations,
            "timestamp": time.time(),
        }
        self._checks.append(check)

        return check

    def _evaluate_rule(
        self,
        rule: dict[str, Any],
        action: str,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Kural değerlendirir.

        Args:
            rule: Kural.
            action: Aksiyon.
            context: Bağlam.

        Returns:
            Değerlendirme bilgisi.
        """
        conditions = rule.get("conditions", {})

        # Yasaklı aksiyon kontrolü
        blocked = conditions.get(
            "blocked_actions", [],
        )
        if action in blocked:
            return {
                "compliant": False,
                "reason": "action_blocked",
            }

        # Zorunlu alan kontrolü
        required = conditions.get(
            "required_fields", [],
        )
        for field in required:
            if field not in context:
                return {
                    "compliant": False,
                    "reason": (
                        f"missing_{field}"
                    ),
                }

        # Değer limit kontrolü
        limits = conditions.get("limits", {})
        for key, limit in limits.items():
            val = context.get(key)
            if val is not None:
                if isinstance(limit, dict):
                    if (
                        "max" in limit
                        and val > limit["max"]
                    ):
                        return {
                            "compliant": False,
                            "reason": (
                                f"{key}_exceeds_max"
                            ),
                        }
                    if (
                        "min" in limit
                        and val < limit["min"]
                    ):
                        return {
                            "compliant": False,
                            "reason": (
                                f"{key}_below_min"
                            ),
                        }

        return {"compliant": True, "reason": ""}

    def _get_recommendation(
        self,
        rule: dict[str, Any],
        action: str,
    ) -> str:
        """Öneri üretir.

        Args:
            rule: İhlal edilen kural.
            action: Aksiyon.

        Returns:
            Öneri metni.
        """
        severity = rule.get(
            "severity", "medium",
        )
        name = rule.get("name", "unknown")

        if severity == "critical":
            return (
                f"CRITICAL: Action '{action}' "
                f"violates '{name}'. "
                "Do not proceed."
            )
        if severity == "high":
            return (
                f"HIGH: Review '{action}' "
                f"against '{name}' "
                "before proceeding."
            )
        return (
            f"Review '{action}' for "
            f"compliance with '{name}'."
        )

    def assess_severity(
        self,
        violations: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Şiddet değerlendirir.

        Args:
            violations: İhlaller.

        Returns:
            Değerlendirme bilgisi.
        """
        if not violations:
            return {
                "overall_severity": "none",
                "score": 0,
            }

        severity_scores = {
            "critical": 10,
            "high": 7,
            "medium": 4,
            "low": 2,
            "info": 1,
        }

        total = sum(
            severity_scores.get(
                v.get("severity", "medium"), 4,
            )
            for v in violations
        )
        max_sev = max(
            (
                v.get("severity", "medium")
                for v in violations
            ),
            key=lambda s: severity_scores.get(
                s, 0,
            ),
        )

        return {
            "overall_severity": max_sev,
            "score": total,
            "violation_count": len(violations),
        }

    def get_violations(
        self,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """İhlalleri getirir.

        Args:
            limit: Maks kayıt.

        Returns:
            İhlal listesi.
        """
        return list(self._violations[-limit:])

    def get_check_history(
        self,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Kontrol geçmişi getirir.

        Args:
            limit: Maks kayıt.

        Returns:
            Kontrol listesi.
        """
        return list(self._checks[-limit:])

    @property
    def check_count(self) -> int:
        """Kontrol sayısı."""
        return self._stats["checks"]

    @property
    def violation_count(self) -> int:
        """İhlal sayısı."""
        return self._stats["violations"]

    @property
    def compliance_rate(self) -> float:
        """Uyumluluk oranı."""
        total = self._stats["checks"]
        if total == 0:
            return 1.0
        return round(
            self._stats["passed"] / total, 3,
        )
