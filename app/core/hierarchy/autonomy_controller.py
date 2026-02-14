"""ATLAS Otonomi Kontrolcusu modulu.

Agent basina otonomi seviyeleri, bagimsiz hareket,
izin isteme, raporlama ve dinamik otonomi ayarlama.
"""

import logging
from typing import Any

from app.models.hierarchy import (
    AgentNode,
    AutonomyLevel,
)

logger = logging.getLogger(__name__)

# Otonomi siralamasi
_AUTONOMY_ORDER: dict[AutonomyLevel, int] = {
    AutonomyLevel.FULL: 4,
    AutonomyLevel.HIGH: 3,
    AutonomyLevel.MEDIUM: 2,
    AutonomyLevel.LOW: 1,
    AutonomyLevel.NONE: 0,
}

# Aksiyon risk seviyeleri
_ACTION_RISK: dict[str, str] = {
    "read": "low",
    "analyze": "low",
    "log": "low",
    "cache_clear": "low",
    "notify": "medium",
    "update": "medium",
    "create": "medium",
    "delete": "high",
    "deploy": "high",
    "restart": "high",
    "budget_change": "critical",
    "database_modify": "critical",
    "production_change": "critical",
}


class AutonomyController:
    """Otonomi kontrol sistemi.

    Her agent icin otonomi seviyesini yonetir,
    ne zaman bagimsiz hareket edecegi, izin isteyecegi
    veya rapor verecegini belirler.

    Attributes:
        _agent_autonomy: Agent otonomi haritasi.
        _action_log: Aksiyon gecmisi.
        _performance_history: Performans gecmisi.
    """

    def __init__(
        self,
        default_level: AutonomyLevel = AutonomyLevel.MEDIUM,
    ) -> None:
        """Otonomi kontrolcusunu baslatir.

        Args:
            default_level: Varsayilan otonomi seviyesi.
        """
        self._default_level = default_level
        self._agent_autonomy: dict[str, AutonomyLevel] = {}
        self._action_log: list[dict[str, Any]] = []
        self._performance_history: dict[str, list[bool]] = {}

        logger.info(
            "AutonomyController baslatildi (default=%s)",
            default_level.value,
        )

    def set_autonomy(
        self, agent_id: str, level: AutonomyLevel,
    ) -> None:
        """Otonomi seviyesini ayarlar.

        Args:
            agent_id: Agent ID.
            level: Otonomi seviyesi.
        """
        old = self._agent_autonomy.get(agent_id, self._default_level)
        self._agent_autonomy[agent_id] = level
        logger.info(
            "Otonomi degisti: %s (%s -> %s)",
            agent_id, old.value, level.value,
        )

    def get_autonomy(self, agent_id: str) -> AutonomyLevel:
        """Otonomi seviyesini getirir.

        Args:
            agent_id: Agent ID.

        Returns:
            AutonomyLevel degeri.
        """
        return self._agent_autonomy.get(agent_id, self._default_level)

    def can_act_independently(
        self, agent_id: str, action: str,
    ) -> bool:
        """Bagimsiz hareket edebilir mi kontrol eder.

        Args:
            agent_id: Agent ID.
            action: Aksiyon adi.

        Returns:
            Bagimsiz hareket edebiliyorsa True.
        """
        level = self.get_autonomy(agent_id)
        level_value = _AUTONOMY_ORDER.get(level, 2)
        risk = _ACTION_RISK.get(action, "medium")

        if level == AutonomyLevel.FULL:
            return True

        if level == AutonomyLevel.NONE:
            return False

        if risk == "low":
            return level_value >= 1  # LOW ve ustu
        elif risk == "medium":
            return level_value >= 2  # MEDIUM ve ustu
        elif risk == "high":
            return level_value >= 3  # HIGH ve ustu
        else:  # critical
            return level_value >= 4  # Sadece FULL

        return False

    def should_ask_permission(
        self, agent_id: str, action: str,
    ) -> bool:
        """Izin istenmesi gerekiyor mu.

        Args:
            agent_id: Agent ID.
            action: Aksiyon adi.

        Returns:
            Izin gerekiyorsa True.
        """
        return not self.can_act_independently(agent_id, action)

    def should_report(
        self, agent_id: str, action: str,
    ) -> bool:
        """Rapor verilmesi gerekiyor mu.

        Args:
            agent_id: Agent ID.
            action: Aksiyon adi.

        Returns:
            Rapor gerekiyorsa True.
        """
        level = self.get_autonomy(agent_id)
        risk = _ACTION_RISK.get(action, "medium")

        # NONE: her sey raporlanir
        if level == AutonomyLevel.NONE:
            return True

        # FULL: sadece critical raporlanir
        if level == AutonomyLevel.FULL:
            return risk == "critical"

        # Digerleri: medium ve ustu raporlanir
        return risk in ("medium", "high", "critical")

    def record_action(
        self,
        agent_id: str,
        action: str,
        success: bool,
        autonomous: bool = True,
    ) -> None:
        """Aksiyon kaydeder.

        Args:
            agent_id: Agent ID.
            action: Aksiyon adi.
            success: Basarili mi.
            autonomous: Otonom mu.
        """
        self._action_log.append({
            "agent_id": agent_id,
            "action": action,
            "success": success,
            "autonomous": autonomous,
        })

        # Performans gecmisi
        if agent_id not in self._performance_history:
            self._performance_history[agent_id] = []
        self._performance_history[agent_id].append(success)

        # Son 50 kayit tut
        if len(self._performance_history[agent_id]) > 50:
            self._performance_history[agent_id] = (
                self._performance_history[agent_id][-50:]
            )

    def adjust_autonomy(self, agent_id: str) -> AutonomyLevel:
        """Performansa gore otonomiyi dinamik ayarlar.

        Args:
            agent_id: Agent ID.

        Returns:
            Yeni AutonomyLevel.
        """
        history = self._performance_history.get(agent_id, [])
        if len(history) < 5:
            return self.get_autonomy(agent_id)

        # Son 10 aksiyonun basari orani
        recent = history[-10:]
        success_rate = sum(1 for s in recent if s) / len(recent)

        current = self.get_autonomy(agent_id)
        current_value = _AUTONOMY_ORDER.get(current, 2)

        # Basari yuksekse otonomi artir
        if success_rate >= 0.9 and current_value < 4:
            new_value = current_value + 1
        # Basari dusukse otonomi azalt
        elif success_rate < 0.5 and current_value > 0:
            new_value = current_value - 1
        else:
            return current

        # Deger -> seviye
        value_to_level = {v: k for k, v in _AUTONOMY_ORDER.items()}
        new_level = value_to_level.get(new_value, current)

        self.set_autonomy(agent_id, new_level)
        return new_level

    def get_action_history(
        self, agent_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Aksiyon gecmisini getirir.

        Args:
            agent_id: Agent filtresi.

        Returns:
            Aksiyon listesi.
        """
        if agent_id:
            return [
                a for a in self._action_log
                if a["agent_id"] == agent_id
            ]
        return list(self._action_log)

    def get_success_rate(self, agent_id: str) -> float:
        """Basari oranini getirir.

        Args:
            agent_id: Agent ID.

        Returns:
            Basari orani (0-1).
        """
        history = self._performance_history.get(agent_id, [])
        if not history:
            return 0.0
        return sum(1 for s in history if s) / len(history)

    @property
    def managed_agents(self) -> int:
        """Yonetilen agent sayisi."""
        return len(self._agent_autonomy)

    @property
    def total_actions(self) -> int:
        """Toplam aksiyon sayisi."""
        return len(self._action_log)
