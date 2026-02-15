"""ATLAS Plan Uretici modulu.

Fark hesaplama, degisiklik onizleme,
maliyet tahmini, risk degerlendirmesi
ve onay is akisi.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class PlanGenerator:
    """Plan uretici.

    IaC degisiklik planlari olusturur.

    Attributes:
        _plans: Uretilmis planlar.
        _cost_estimates: Maliyet tahminleri.
    """

    def __init__(self) -> None:
        """Ureticiy baslatir."""
        self._plans: dict[
            str, dict[str, Any]
        ] = {}
        self._cost_rates: dict[
            str, float
        ] = {}
        self._risk_rules: dict[
            str, dict[str, Any]
        ] = {}
        self._stats = {
            "plans": 0,
            "approved": 0,
            "rejected": 0,
        }

        logger.info(
            "PlanGenerator baslatildi",
        )

    def generate(
        self,
        plan_id: str,
        desired: dict[str, dict[str, Any]],
        current: dict[str, dict[str, Any]]
            | None = None,
    ) -> dict[str, Any]:
        """Plan uretir.

        Args:
            plan_id: Plan ID.
            desired: Istenen durum.
            current: Mevcut durum.

        Returns:
            Plan bilgisi.
        """
        cur = current or {}
        changes: list[dict[str, Any]] = []

        # Olusturulacaklar
        for key, res in desired.items():
            if key not in cur:
                changes.append({
                    "action": "create",
                    "resource": key,
                    "properties": res,
                })
            else:
                # Guncelleme kontrolu
                if res != cur[key]:
                    changes.append({
                        "action": "update",
                        "resource": key,
                        "old": cur[key],
                        "new": res,
                    })

        # Silinecekler
        for key in cur:
            if key not in desired:
                changes.append({
                    "action": "delete",
                    "resource": key,
                })

        creates = sum(
            1 for c in changes
            if c["action"] == "create"
        )
        updates = sum(
            1 for c in changes
            if c["action"] == "update"
        )
        deletes = sum(
            1 for c in changes
            if c["action"] == "delete"
        )

        # Maliyet tahmini
        cost = self._estimate_cost(changes)

        # Risk degerlendirmesi
        risk = self._assess_risk(changes)

        plan = {
            "plan_id": plan_id,
            "changes": changes,
            "summary": {
                "creates": creates,
                "updates": updates,
                "deletes": deletes,
                "total": len(changes),
            },
            "estimated_cost": cost,
            "risk": risk,
            "status": "pending",
            "created_at": time.time(),
        }

        self._plans[plan_id] = plan
        self._stats["plans"] += 1

        return plan

    def _estimate_cost(
        self,
        changes: list[dict[str, Any]],
    ) -> float:
        """Maliyet tahmin eder.

        Args:
            changes: Degisiklikler.

        Returns:
            Tahmini maliyet.
        """
        total = 0.0
        for change in changes:
            res = change["resource"]
            res_type = res.split(".")[0] if "." in res else res
            rate = self._cost_rates.get(
                res_type, 0.0,
            )
            if change["action"] == "create":
                total += rate
            elif change["action"] == "update":
                total += rate * 0.1
        return round(total, 2)

    def _assess_risk(
        self,
        changes: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Risk degerlendirir.

        Args:
            changes: Degisiklikler.

        Returns:
            Risk bilgisi.
        """
        score = 0
        warnings: list[str] = []

        for change in changes:
            if change["action"] == "delete":
                score += 30
                warnings.append(
                    f"Deletion: {change['resource']}",
                )
            elif change["action"] == "update":
                score += 10

            # Ozel kurallar
            res = change["resource"]
            for rule_name, rule in (
                self._risk_rules.items()
            ):
                pattern = rule.get("pattern", "")
                if pattern and pattern in res:
                    score += rule.get("score", 0)
                    if rule.get("warning"):
                        warnings.append(
                            rule["warning"],
                        )

        if score >= 80:
            level = "critical"
        elif score >= 50:
            level = "high"
        elif score >= 20:
            level = "medium"
        else:
            level = "low"

        return {
            "score": min(score, 100),
            "level": level,
            "warnings": warnings,
        }

    def set_cost_rate(
        self,
        resource_type: str,
        monthly_cost: float,
    ) -> None:
        """Maliyet oranini ayarlar.

        Args:
            resource_type: Kaynak tipi.
            monthly_cost: Aylik maliyet.
        """
        self._cost_rates[resource_type] = (
            monthly_cost
        )

    def add_risk_rule(
        self,
        name: str,
        pattern: str,
        score: int,
        warning: str = "",
    ) -> dict[str, Any]:
        """Risk kurali ekler.

        Args:
            name: Kural adi.
            pattern: Eslesme kalip.
            score: Risk puani.
            warning: Uyari mesaji.

        Returns:
            Kural bilgisi.
        """
        self._risk_rules[name] = {
            "pattern": pattern,
            "score": score,
            "warning": warning,
        }
        return {"name": name, "score": score}

    def approve(
        self,
        plan_id: str,
        approver: str = "",
    ) -> dict[str, Any]:
        """Plani onaylar.

        Args:
            plan_id: Plan ID.
            approver: Onaylayan.

        Returns:
            Onay bilgisi.
        """
        plan = self._plans.get(plan_id)
        if not plan:
            return {"error": "not_found"}

        plan["status"] = "approved"
        plan["approved_by"] = approver
        plan["approved_at"] = time.time()
        self._stats["approved"] += 1

        return {
            "plan_id": plan_id,
            "status": "approved",
        }

    def reject(
        self,
        plan_id: str,
        reason: str = "",
    ) -> dict[str, Any]:
        """Plani reddeder.

        Args:
            plan_id: Plan ID.
            reason: Sebep.

        Returns:
            Red bilgisi.
        """
        plan = self._plans.get(plan_id)
        if not plan:
            return {"error": "not_found"}

        plan["status"] = "rejected"
        plan["reject_reason"] = reason
        self._stats["rejected"] += 1

        return {
            "plan_id": plan_id,
            "status": "rejected",
        }

    def get_plan(
        self,
        plan_id: str,
    ) -> dict[str, Any] | None:
        """Plan getirir.

        Args:
            plan_id: Plan ID.

        Returns:
            Plan bilgisi veya None.
        """
        return self._plans.get(plan_id)

    def get_changes(
        self,
        plan_id: str,
    ) -> list[dict[str, Any]]:
        """Plan degisikliklerini getirir.

        Args:
            plan_id: Plan ID.

        Returns:
            Degisiklik listesi.
        """
        plan = self._plans.get(plan_id)
        if not plan:
            return []
        return list(plan["changes"])

    @property
    def plan_count(self) -> int:
        """Plan sayisi."""
        return len(self._plans)

    @property
    def approved_count(self) -> int:
        """Onaylanan sayisi."""
        return self._stats["approved"]

    @property
    def rejected_count(self) -> int:
        """Reddedilen sayisi."""
        return self._stats["rejected"]

    @property
    def cost_rate_count(self) -> int:
        """Maliyet orani sayisi."""
        return len(self._cost_rates)

    @property
    def risk_rule_count(self) -> int:
        """Risk kurali sayisi."""
        return len(self._risk_rules)
