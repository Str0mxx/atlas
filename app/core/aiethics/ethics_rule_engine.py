"""
Etik kural motoru modulu.

Kural tanimlama, kural degerlendirme,
ihlal tespiti, ciddiyet puanlama,
istisna yonetimi.
"""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class EthicsRuleEngine:
    """Etik kural motoru.

    Attributes:
        _rules: Kurallar.
        _evaluations: Degerlendirmeler.
        _exceptions: Istisnalar.
        _stats: Istatistikler.
    """

    RULE_CATEGORIES: list[str] = [
        "fairness",
        "transparency",
        "accountability",
        "privacy",
        "safety",
        "autonomy",
        "beneficence",
        "non_maleficence",
    ]

    SEVERITY_LEVELS: list[str] = [
        "info",
        "warning",
        "violation",
        "critical",
    ]

    def __init__(self) -> None:
        """Motoru baslatir."""
        self._rules: dict[
            str, dict
        ] = {}
        self._evaluations: dict[
            str, dict
        ] = {}
        self._exceptions: dict[
            str, dict
        ] = {}
        self._stats: dict[str, int] = {
            "rules_defined": 0,
            "evaluations_done": 0,
            "violations_found": 0,
            "exceptions_granted": 0,
        }
        logger.info(
            "EthicsRuleEngine baslatildi"
        )

    @property
    def rule_count(self) -> int:
        """Kural sayisi."""
        return len(self._rules)

    def define_rule(
        self,
        name: str = "",
        category: str = "",
        description: str = "",
        condition: str = "",
        severity: str = "warning",
        threshold: float = 0.0,
        metadata: dict | None = None,
    ) -> dict[str, Any]:
        """Kural tanimlar.

        Args:
            name: Ad.
            category: Kategori.
            description: Aciklama.
            condition: Kosul.
            severity: Ciddiyet.
            threshold: Esik.
            metadata: Ek veri.

        Returns:
            Tanimlama bilgisi.
        """
        try:
            rid = f"erul_{uuid4()!s:.8}"
            self._rules[rid] = {
                "rule_id": rid,
                "name": name,
                "category": category,
                "description": description,
                "condition": condition,
                "severity": severity,
                "threshold": threshold,
                "active": True,
                "metadata": metadata or {},
                "created_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
            }
            self._stats[
                "rules_defined"
            ] += 1
            return {
                "rule_id": rid,
                "defined": True,
            }
        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "defined": False,
                "error": str(e),
            }

    def evaluate(
        self,
        context: dict | None = None,
        rule_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        """Kurallari degerlendirir.

        Args:
            context: Baglam verisi.
            rule_ids: Kural filtreleri.

        Returns:
            Degerlendirme bilgisi.
        """
        try:
            eid = f"eevl_{uuid4()!s:.8}"
            ctx = context or {}
            violations: list[dict] = []
            passed: list[str] = []

            rules_to_check = (
                self._rules
            )
            if rule_ids:
                rules_to_check = {
                    k: v
                    for k, v in self._rules.items()
                    if k in rule_ids
                }

            for rule in (
                rules_to_check.values()
            ):
                if not rule["active"]:
                    continue

                # Istisna kontrolu
                if self._has_exception(
                    rule["rule_id"]
                ):
                    passed.append(
                        rule["rule_id"]
                    )
                    continue

                # Kural degerlendirme
                result = (
                    self._evaluate_rule(
                        rule, ctx
                    )
                )

                if result["violated"]:
                    violations.append({
                        "rule_id": rule[
                            "rule_id"
                        ],
                        "rule_name": rule[
                            "name"
                        ],
                        "category": rule[
                            "category"
                        ],
                        "severity": rule[
                            "severity"
                        ],
                        "detail": result.get(
                            "detail", ""
                        ),
                        "score": result.get(
                            "score", 0.0
                        ),
                    })
                else:
                    passed.append(
                        rule["rule_id"]
                    )

            self._evaluations[eid] = {
                "evaluation_id": eid,
                "violations": violations,
                "passed": passed,
                "context": {
                    k: str(v)[:100]
                    for k, v in ctx.items()
                },
                "evaluated_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
            }

            self._stats[
                "evaluations_done"
            ] += 1
            self._stats[
                "violations_found"
            ] += len(violations)

            return {
                "evaluation_id": eid,
                "violations": violations,
                "violation_count": len(
                    violations
                ),
                "passed_count": len(passed),
                "compliant": (
                    len(violations) == 0
                ),
                "evaluated": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "evaluated": False,
                "error": str(e),
            }

    def _evaluate_rule(
        self,
        rule: dict,
        context: dict,
    ) -> dict[str, Any]:
        """Tek kural degerlendirir."""
        cond = rule.get("condition", "")
        threshold = rule.get(
            "threshold", 0.0
        )

        # Basit kosul degerlendirme
        if cond == "bias_score":
            val = context.get(
                "bias_score", 0.0
            )
            if val > threshold:
                return {
                    "violated": True,
                    "detail": (
                        f"Onyargi puani "
                        f"{val} > {threshold}"
                    ),
                    "score": val,
                }
        elif cond == "fairness_score":
            val = context.get(
                "fairness_score", 1.0
            )
            if val < threshold:
                return {
                    "violated": True,
                    "detail": (
                        f"Adalet puani "
                        f"{val} < {threshold}"
                    ),
                    "score": 1.0 - val,
                }
        elif cond == "disparity_ratio":
            val = context.get(
                "disparity_ratio", 1.0
            )
            if val < threshold:
                return {
                    "violated": True,
                    "detail": (
                        f"Esitsizlik orani "
                        f"{val} < {threshold}"
                    ),
                    "score": 1.0 - val,
                }
        elif cond == "transparency":
            val = context.get(
                "transparency_score", 1.0
            )
            if val < threshold:
                return {
                    "violated": True,
                    "detail": (
                        f"Seffaflik puani "
                        f"{val} < {threshold}"
                    ),
                    "score": 1.0 - val,
                }
        elif cond:
            # Genel anahtar kontrolu
            val = context.get(cond)
            if val is not None:
                if isinstance(
                    val, (int, float)
                ):
                    if val > threshold:
                        return {
                            "violated": True,
                            "detail": (
                                f"{cond}={val}"
                                f" > {threshold}"
                            ),
                            "score": float(
                                val
                            ),
                        }

        return {"violated": False}

    def _has_exception(
        self, rule_id: str
    ) -> bool:
        """Istisna kontrolu."""
        for exc in (
            self._exceptions.values()
        ):
            if (
                exc["rule_id"] == rule_id
                and exc["active"]
            ):
                return True
        return False

    def grant_exception(
        self,
        rule_id: str = "",
        reason: str = "",
        granted_by: str = "",
    ) -> dict[str, Any]:
        """Istisna verir.

        Args:
            rule_id: Kural ID.
            reason: Neden.
            granted_by: Veren.

        Returns:
            Istisna bilgisi.
        """
        try:
            if rule_id not in self._rules:
                return {
                    "granted": False,
                    "error": (
                        "Kural bulunamadi"
                    ),
                }

            eid = f"exc_{uuid4()!s:.8}"
            self._exceptions[eid] = {
                "exception_id": eid,
                "rule_id": rule_id,
                "reason": reason,
                "granted_by": granted_by,
                "active": True,
                "granted_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
            }
            self._stats[
                "exceptions_granted"
            ] += 1
            return {
                "exception_id": eid,
                "granted": True,
            }
        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "granted": False,
                "error": str(e),
            }

    def revoke_exception(
        self, exception_id: str = ""
    ) -> dict[str, Any]:
        """Istisnayi iptal eder.

        Args:
            exception_id: Istisna ID.

        Returns:
            Iptal bilgisi.
        """
        try:
            exc = self._exceptions.get(
                exception_id
            )
            if not exc:
                return {
                    "revoked": False,
                    "error": (
                        "Istisna bulunamadi"
                    ),
                }
            exc["active"] = False
            return {
                "exception_id": (
                    exception_id
                ),
                "revoked": True,
            }
        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "revoked": False,
                "error": str(e),
            }

    def toggle_rule(
        self,
        rule_id: str = "",
        active: bool = True,
    ) -> dict[str, Any]:
        """Kural aktif/pasif yapar.

        Args:
            rule_id: Kural ID.
            active: Durum.

        Returns:
            Guncelleme bilgisi.
        """
        try:
            rule = self._rules.get(rule_id)
            if not rule:
                return {
                    "toggled": False,
                    "error": (
                        "Kural bulunamadi"
                    ),
                }
            rule["active"] = active
            return {
                "rule_id": rule_id,
                "active": active,
                "toggled": True,
            }
        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "toggled": False,
                "error": str(e),
            }

    def get_summary(
        self,
    ) -> dict[str, Any]:
        """Ozet getirir."""
        try:
            return {
                "total_rules": len(
                    self._rules
                ),
                "total_evaluations": len(
                    self._evaluations
                ),
                "total_exceptions": len(
                    self._exceptions
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
