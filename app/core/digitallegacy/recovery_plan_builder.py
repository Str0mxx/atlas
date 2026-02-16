"""
Kurtarma planı oluşturucu modülü.

Felaket senaryoları, kurtarma adımları,
öncelik sıralaması, iletişim listeleri, test takvimi.
"""

import logging
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class RecoveryPlanBuilder:
    """Kurtarma planı oluşturucu.

    Attributes:
        _plans: Plan kayıtları.
        _contacts: İletişim kayıtları.
        _stats: İstatistikler.
    """

    def __init__(self) -> None:
        """Oluşturucuyu başlatır."""
        self._plans: list[dict] = []
        self._contacts: list[dict] = []
        self._stats: dict[str, int] = {
            "plans_built": 0,
        }
        logger.info(
            "RecoveryPlanBuilder baslatildi"
        )

    @property
    def plan_count(self) -> int:
        """Plan sayısı."""
        return len(self._plans)

    def define_scenario(
        self,
        name: str = "",
        severity: str = "medium",
        description: str = "",
        probability: str = "low",
    ) -> dict[str, Any]:
        """Felaket senaryosu tanımlar.

        Args:
            name: Senaryo adı.
            severity: Ciddiyet.
            description: Açıklama.
            probability: Olasılık.

        Returns:
            Senaryo bilgisi.
        """
        try:
            sid = f"ds_{uuid4()!s:.8}"

            severity_scores = {
                "low": 1,
                "medium": 2,
                "high": 3,
                "critical": 4,
            }
            prob_scores = {
                "rare": 1,
                "low": 2,
                "medium": 3,
                "high": 4,
            }

            risk_score = (
                severity_scores.get(severity, 2)
                * prob_scores.get(probability, 2)
            )

            if risk_score >= 12:
                risk_level = "critical"
            elif risk_score >= 8:
                risk_level = "high"
            elif risk_score >= 4:
                risk_level = "medium"
            else:
                risk_level = "low"

            record = {
                "scenario_id": sid,
                "name": name,
                "severity": severity,
                "probability": probability,
                "risk_score": risk_score,
                "risk_level": risk_level,
                "steps": [],
            }
            self._plans.append(record)
            self._stats["plans_built"] += 1

            return {
                "scenario_id": sid,
                "name": name,
                "risk_score": risk_score,
                "risk_level": risk_level,
                "defined": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "defined": False,
                "error": str(e),
            }

    def add_recovery_steps(
        self,
        scenario_id: str = "",
        steps: list[str] | None = None,
    ) -> dict[str, Any]:
        """Kurtarma adımları ekler.

        Args:
            scenario_id: Senaryo ID.
            steps: Adım listesi.

        Returns:
            Adım bilgisi.
        """
        try:
            plan = None
            for p in self._plans:
                if p["scenario_id"] == scenario_id:
                    plan = p
                    break

            if not plan:
                return {
                    "added": False,
                    "error": "scenario_not_found",
                }

            step_list = steps or []
            numbered = []
            for i, s in enumerate(step_list, 1):
                numbered.append({
                    "step_num": i,
                    "action": s,
                    "status": "pending",
                })

            plan["steps"] = numbered

            return {
                "scenario_id": scenario_id,
                "step_count": len(numbered),
                "steps": numbered,
                "added": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "added": False,
                "error": str(e),
            }

    def prioritize_plans(
        self,
    ) -> dict[str, Any]:
        """Planları önceliklendirir.

        Returns:
            Öncelik bilgisi.
        """
        try:
            sorted_plans = sorted(
                self._plans,
                key=lambda p: p.get(
                    "risk_score", 0
                ),
                reverse=True,
            )

            priorities = []
            for i, p in enumerate(
                sorted_plans, 1
            ):
                priorities.append({
                    "rank": i,
                    "scenario": p["name"],
                    "risk_score": p[
                        "risk_score"
                    ],
                    "risk_level": p[
                        "risk_level"
                    ],
                })

            return {
                "priorities": priorities,
                "plan_count": len(priorities),
                "prioritized": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "prioritized": False,
                "error": str(e),
            }

    def manage_contacts(
        self,
        name: str = "",
        role: str = "",
        phone: str = "",
        email: str = "",
    ) -> dict[str, Any]:
        """İletişim listesi yönetir.

        Args:
            name: Ad.
            role: Rol.
            phone: Telefon.
            email: E-posta.

        Returns:
            İletişim bilgisi.
        """
        try:
            cid = f"ct_{uuid4()!s:.8}"

            record = {
                "contact_id": cid,
                "name": name,
                "role": role,
                "phone": phone,
                "email": email,
            }
            self._contacts.append(record)

            return {
                "contact_id": cid,
                "name": name,
                "role": role,
                "total_contacts": len(
                    self._contacts
                ),
                "added": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "added": False,
                "error": str(e),
            }

    def schedule_test(
        self,
        scenario_id: str = "",
        frequency: str = "quarterly",
    ) -> dict[str, Any]:
        """Test takvimi oluşturur.

        Args:
            scenario_id: Senaryo ID.
            frequency: Sıklık.

        Returns:
            Takvim bilgisi.
        """
        try:
            plan = None
            for p in self._plans:
                if p["scenario_id"] == scenario_id:
                    plan = p
                    break

            if not plan:
                return {
                    "scheduled": False,
                    "error": "scenario_not_found",
                }

            freq_months = {
                "monthly": 1,
                "quarterly": 3,
                "semi_annual": 6,
                "annual": 12,
            }
            interval = freq_months.get(
                frequency, 3
            )

            plan["test_schedule"] = {
                "frequency": frequency,
                "interval_months": interval,
                "last_test": None,
            }

            return {
                "scenario_id": scenario_id,
                "frequency": frequency,
                "interval_months": interval,
                "scheduled": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "scheduled": False,
                "error": str(e),
            }
