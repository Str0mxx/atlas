"""ATLAS Felaket Planlayici modulu.

DR planlari, RTO/RPO hedefleri,
runbook'lar, iletisim listeleri
ve eskalasyon.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class DisasterPlanner:
    """Felaket planlayici.

    Felaket kurtarma planlarini yonetir.

    Attributes:
        _plans: DR planlari.
        _contacts: Iletisim listeleri.
    """

    def __init__(self) -> None:
        """Planlayiciyi baslatir."""
        self._plans: dict[
            str, dict[str, Any]
        ] = {}
        self._contacts: dict[
            str, dict[str, Any]
        ] = {}
        self._runbooks: dict[
            str, dict[str, Any]
        ] = {}
        self._escalation_levels: list[
            dict[str, Any]
        ] = []
        self._stats = {
            "plans": 0,
            "drills": 0,
            "activations": 0,
        }

        logger.info(
            "DisasterPlanner baslatildi",
        )

    def create_plan(
        self,
        plan_id: str,
        name: str,
        rto_minutes: int = 60,
        rpo_minutes: int = 15,
        severity: str = "high",
        description: str = "",
    ) -> dict[str, Any]:
        """DR plani olusturur.

        Args:
            plan_id: Plan ID.
            name: Plan adi.
            rto_minutes: RTO (dakika).
            rpo_minutes: RPO (dakika).
            severity: Ciddiyet.
            description: Aciklama.

        Returns:
            Plan bilgisi.
        """
        self._plans[plan_id] = {
            "name": name,
            "rto_minutes": rto_minutes,
            "rpo_minutes": rpo_minutes,
            "severity": severity,
            "description": description,
            "status": "active",
            "steps": [],
            "created_at": time.time(),
            "last_tested": None,
        }

        self._stats["plans"] += 1

        return {
            "plan_id": plan_id,
            "name": name,
            "rto": rto_minutes,
            "rpo": rpo_minutes,
        }

    def get_plan(
        self,
        plan_id: str,
    ) -> dict[str, Any] | None:
        """DR plani getirir.

        Args:
            plan_id: Plan ID.

        Returns:
            Plan bilgisi veya None.
        """
        return self._plans.get(plan_id)

    def remove_plan(
        self,
        plan_id: str,
    ) -> bool:
        """DR plani kaldirir.

        Args:
            plan_id: Plan ID.

        Returns:
            Basarili mi.
        """
        if plan_id in self._plans:
            del self._plans[plan_id]
            return True
        return False

    def add_step(
        self,
        plan_id: str,
        step_name: str,
        action: str = "",
        responsible: str = "",
        timeout_minutes: int = 10,
    ) -> dict[str, Any]:
        """Plana adim ekler.

        Args:
            plan_id: Plan ID.
            step_name: Adim adi.
            action: Eylem.
            responsible: Sorumlu.
            timeout_minutes: Zaman asimi.

        Returns:
            Adim bilgisi.
        """
        plan = self._plans.get(plan_id)
        if not plan:
            return {"error": "plan_not_found"}

        step = {
            "name": step_name,
            "action": action,
            "responsible": responsible,
            "timeout_minutes": timeout_minutes,
            "order": len(plan["steps"]) + 1,
        }
        plan["steps"].append(step)

        return {
            "plan_id": plan_id,
            "step": step_name,
            "order": step["order"],
        }

    def add_contact(
        self,
        contact_id: str,
        name: str,
        role: str = "",
        phone: str = "",
        email: str = "",
        priority: int = 5,
    ) -> dict[str, Any]:
        """Iletisim ekler.

        Args:
            contact_id: Iletisim ID.
            name: Isim.
            role: Rol.
            phone: Telefon.
            email: E-posta.
            priority: Oncelik.

        Returns:
            Iletisim bilgisi.
        """
        self._contacts[contact_id] = {
            "name": name,
            "role": role,
            "phone": phone,
            "email": email,
            "priority": priority,
        }

        return {
            "contact_id": contact_id,
            "name": name,
        }

    def remove_contact(
        self,
        contact_id: str,
    ) -> bool:
        """Iletisim kaldirir.

        Args:
            contact_id: Iletisim ID.

        Returns:
            Basarili mi.
        """
        if contact_id in self._contacts:
            del self._contacts[contact_id]
            return True
        return False

    def get_contacts(
        self,
        role: str | None = None,
    ) -> list[dict[str, Any]]:
        """Iletisimleri getirir.

        Args:
            role: Rol filtresi.

        Returns:
            Iletisim listesi.
        """
        contacts = [
            {"contact_id": cid, **c}
            for cid, c in self._contacts.items()
        ]
        if role:
            contacts = [
                c for c in contacts
                if c.get("role") == role
            ]
        contacts.sort(
            key=lambda x: x["priority"],
        )
        return contacts

    def create_runbook(
        self,
        runbook_id: str,
        title: str,
        steps: list[str],
        plan_id: str = "",
    ) -> dict[str, Any]:
        """Runbook olusturur.

        Args:
            runbook_id: Runbook ID.
            title: Baslik.
            steps: Adimlar.
            plan_id: Iliskili plan ID.

        Returns:
            Runbook bilgisi.
        """
        self._runbooks[runbook_id] = {
            "title": title,
            "steps": list(steps),
            "plan_id": plan_id,
            "created_at": time.time(),
        }

        return {
            "runbook_id": runbook_id,
            "steps_count": len(steps),
        }

    def get_runbook(
        self,
        runbook_id: str,
    ) -> dict[str, Any] | None:
        """Runbook getirir.

        Args:
            runbook_id: Runbook ID.

        Returns:
            Runbook bilgisi veya None.
        """
        return self._runbooks.get(runbook_id)

    def set_escalation(
        self,
        levels: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Eskalasyon seviyeleri ayarlar.

        Args:
            levels: Seviye listesi.

        Returns:
            Eskalasyon bilgisi.
        """
        self._escalation_levels = list(levels)
        return {
            "levels": len(levels),
        }

    def get_escalation_path(
        self,
        severity: str = "high",
    ) -> list[dict[str, Any]]:
        """Eskalasyon yolunu getirir.

        Args:
            severity: Ciddiyet.

        Returns:
            Eskalasyon yolu.
        """
        sev_order = {
            "low": 1,
            "medium": 2,
            "high": 3,
            "critical": 4,
            "catastrophic": 5,
        }
        sev_val = sev_order.get(severity, 3)

        return [
            level for level
            in self._escalation_levels
            if level.get("min_severity", 1)
            <= sev_val
        ]

    def activate_plan(
        self,
        plan_id: str,
    ) -> dict[str, Any]:
        """DR planini aktive eder.

        Args:
            plan_id: Plan ID.

        Returns:
            Aktivasyon bilgisi.
        """
        plan = self._plans.get(plan_id)
        if not plan:
            return {"error": "plan_not_found"}

        plan["status"] = "activated"
        plan["activated_at"] = time.time()
        self._stats["activations"] += 1

        return {
            "plan_id": plan_id,
            "status": "activated",
            "steps": len(plan["steps"]),
        }

    def list_plans(
        self,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        """DR planlarini listeler.

        Args:
            status: Durum filtresi.

        Returns:
            Plan listesi.
        """
        plans = [
            {"plan_id": pid, **p}
            for pid, p in self._plans.items()
        ]
        if status:
            plans = [
                p for p in plans
                if p.get("status") == status
            ]
        return plans

    @property
    def plan_count(self) -> int:
        """Plan sayisi."""
        return len(self._plans)

    @property
    def contact_count(self) -> int:
        """Iletisim sayisi."""
        return len(self._contacts)

    @property
    def runbook_count(self) -> int:
        """Runbook sayisi."""
        return len(self._runbooks)

    @property
    def escalation_level_count(self) -> int:
        """Eskalasyon seviye sayisi."""
        return len(self._escalation_levels)

    @property
    def activation_count(self) -> int:
        """Aktivasyon sayisi."""
        return self._stats["activations"]
