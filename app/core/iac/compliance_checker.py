"""ATLAS IaC Uyumluluk Denetcisi modulu.

Politika dogrulama, guvenlik kurallari,
en iyi uygulamalar, ozel kurallar
ve raporlama.
"""

import logging
import time
from typing import Any, Callable

logger = logging.getLogger(__name__)


class IaCComplianceChecker:
    """IaC uyumluluk denetcisi.

    Politika ve guvenlik denetimi yapar.

    Attributes:
        _policies: Politikalar.
        _results: Denetim sonuclari.
    """

    def __init__(self) -> None:
        """Denetciyi baslatir."""
        self._policies: dict[
            str, dict[str, Any]
        ] = {}
        self._custom_rules: dict[
            str, Callable[..., bool]
        ] = {}
        self._results: list[
            dict[str, Any]
        ] = []
        self._exemptions: dict[
            str, dict[str, Any]
        ] = {}
        self._stats = {
            "checks": 0,
            "passed": 0,
            "failed": 0,
            "warnings": 0,
        }

        logger.info(
            "IaCComplianceChecker baslatildi",
        )

    def add_policy(
        self,
        name: str,
        rules: list[dict[str, Any]],
        severity: str = "medium",
        description: str = "",
        category: str = "general",
    ) -> dict[str, Any]:
        """Politika ekler.

        Args:
            name: Politika adi.
            rules: Kural listesi.
            severity: Ciddiyet.
            description: Aciklama.
            category: Kategori.

        Returns:
            Politika bilgisi.
        """
        self._policies[name] = {
            "rules": rules,
            "severity": severity,
            "description": description,
            "category": category,
            "enabled": True,
            "created_at": time.time(),
        }

        return {
            "name": name,
            "rules_count": len(rules),
        }

    def remove_policy(
        self,
        name: str,
    ) -> bool:
        """Politika kaldirir.

        Args:
            name: Politika adi.

        Returns:
            Basarili mi.
        """
        if name in self._policies:
            del self._policies[name]
            return True
        return False

    def enable_policy(
        self,
        name: str,
    ) -> bool:
        """Politikayi etkinlestirir.

        Args:
            name: Politika adi.

        Returns:
            Basarili mi.
        """
        policy = self._policies.get(name)
        if not policy:
            return False
        policy["enabled"] = True
        return True

    def disable_policy(
        self,
        name: str,
    ) -> bool:
        """Politikayi devre disi birakir.

        Args:
            name: Politika adi.

        Returns:
            Basarili mi.
        """
        policy = self._policies.get(name)
        if not policy:
            return False
        policy["enabled"] = False
        return True

    def add_custom_rule(
        self,
        name: str,
        check_fn: Callable[..., bool],
    ) -> None:
        """Ozel kural ekler.

        Args:
            name: Kural adi.
            check_fn: Kontrol fonksiyonu.
        """
        self._custom_rules[name] = check_fn

    def add_exemption(
        self,
        resource_key: str,
        policy_name: str,
        reason: str = "",
    ) -> dict[str, Any]:
        """Muafiyet ekler.

        Args:
            resource_key: Kaynak anahtari.
            policy_name: Politika adi.
            reason: Sebep.

        Returns:
            Muafiyet bilgisi.
        """
        ex_key = (
            f"{resource_key}:{policy_name}"
        )
        self._exemptions[ex_key] = {
            "resource": resource_key,
            "policy": policy_name,
            "reason": reason,
            "granted_at": time.time(),
        }

        return {
            "resource": resource_key,
            "policy": policy_name,
            "status": "exempted",
        }

    def check(
        self,
        resource_key: str,
        resource_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Kaynak uyumlulugunun denetler.

        Args:
            resource_key: Kaynak anahtari.
            resource_data: Kaynak verisi.

        Returns:
            Denetim sonucu.
        """
        self._stats["checks"] += 1
        violations: list[dict[str, Any]] = []
        warnings: list[dict[str, Any]] = []

        for pname, policy in (
            self._policies.items()
        ):
            if not policy["enabled"]:
                continue

            # Muafiyet kontrolu
            ex_key = (
                f"{resource_key}:{pname}"
            )
            if ex_key in self._exemptions:
                continue

            for rule in policy["rules"]:
                passed = self._evaluate_rule(
                    rule, resource_data,
                )
                if not passed:
                    entry = {
                        "policy": pname,
                        "rule": rule.get(
                            "name",
                            rule.get("field", ""),
                        ),
                        "severity": policy[
                            "severity"
                        ],
                        "message": rule.get(
                            "message", "",
                        ),
                    }

                    if policy["severity"] in (
                        "low",
                        "info",
                    ):
                        warnings.append(entry)
                        self._stats[
                            "warnings"
                        ] += 1
                    else:
                        violations.append(entry)
                        self._stats[
                            "failed"
                        ] += 1

        # Ozel kurallar
        for rname, check_fn in (
            self._custom_rules.items()
        ):
            try:
                if not check_fn(resource_data):
                    violations.append({
                        "policy": "custom",
                        "rule": rname,
                        "severity": "medium",
                    })
                    self._stats["failed"] += 1
            except Exception:
                pass

        compliant = len(violations) == 0

        if compliant:
            self._stats["passed"] += 1

        result = {
            "resource": resource_key,
            "compliant": compliant,
            "violations": violations,
            "warnings": warnings,
            "checked_at": time.time(),
        }

        self._results.append(result)

        return result

    def _evaluate_rule(
        self,
        rule: dict[str, Any],
        data: dict[str, Any],
    ) -> bool:
        """Kurali degerlendirir.

        Args:
            rule: Kural tanimu.
            data: Kaynak verisi.

        Returns:
            Gecti mi.
        """
        field = rule.get("field", "")
        operator = rule.get("operator", "exists")
        expected = rule.get("value")

        actual = data.get(field)

        if operator == "exists":
            return actual is not None
        elif operator == "equals":
            return actual == expected
        elif operator == "not_equals":
            return actual != expected
        elif operator == "contains":
            return (
                expected in actual
                if actual
                else False
            )
        elif operator == "in":
            return actual in (expected or [])
        elif operator == "not_in":
            return actual not in (
                expected or []
            )
        elif operator == "min":
            return (
                actual >= expected
                if actual is not None
                else False
            )
        elif operator == "max":
            return (
                actual <= expected
                if actual is not None
                else False
            )

        return True

    def check_all(
        self,
        resources: dict[
            str, dict[str, Any]
        ],
    ) -> dict[str, Any]:
        """Tum kaynaklari denetler.

        Args:
            resources: Kaynaklar.

        Returns:
            Toplu denetim sonucu.
        """
        results: list[dict[str, Any]] = []
        compliant_count = 0
        violation_count = 0

        for key, data in resources.items():
            result = self.check(key, data)
            results.append(result)
            if result["compliant"]:
                compliant_count += 1
            else:
                violation_count += len(
                    result["violations"],
                )

        return {
            "total": len(results),
            "compliant": compliant_count,
            "non_compliant": (
                len(results) - compliant_count
            ),
            "violations": violation_count,
            "results": results,
        }

    def get_report(self) -> dict[str, Any]:
        """Uyumluluk raporu olusturur.

        Returns:
            Rapor.
        """
        by_severity: dict[str, int] = {}
        by_policy: dict[str, int] = {}

        for result in self._results:
            for v in result.get(
                "violations", []
            ):
                sev = v.get("severity", "medium")
                by_severity[sev] = (
                    by_severity.get(sev, 0) + 1
                )
                pol = v.get("policy", "unknown")
                by_policy[pol] = (
                    by_policy.get(pol, 0) + 1
                )

        return {
            "total_checks": (
                self._stats["checks"]
            ),
            "passed": self._stats["passed"],
            "failed": self._stats["failed"],
            "warnings": (
                self._stats["warnings"]
            ),
            "by_severity": by_severity,
            "by_policy": by_policy,
            "timestamp": time.time(),
        }

    def get_results(
        self,
        limit: int = 50,
        compliant_only: bool = False,
    ) -> list[dict[str, Any]]:
        """Sonuclari getirir.

        Args:
            limit: Limit.
            compliant_only: Sadece uyumlu.

        Returns:
            Sonuc listesi.
        """
        results = self._results[-limit:]
        if compliant_only:
            results = [
                r for r in results
                if r.get("compliant")
            ]
        return results

    @property
    def policy_count(self) -> int:
        """Politika sayisi."""
        return len(self._policies)

    @property
    def custom_rule_count(self) -> int:
        """Ozel kural sayisi."""
        return len(self._custom_rules)

    @property
    def exemption_count(self) -> int:
        """Muafiyet sayisi."""
        return len(self._exemptions)

    @property
    def check_count(self) -> int:
        """Denetim sayisi."""
        return self._stats["checks"]

    @property
    def result_count(self) -> int:
        """Sonuc sayisi."""
        return len(self._results)
