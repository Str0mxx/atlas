"""ATLAS Otomasyon Kural Motoru modülü.

Kural tanımlama, tetikleme koşulları,
aksiyon yürütme, zamanlama,
zincirleme.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class AutomationRuleEngine:
    """Otomasyon kural motoru.

    IoT otomasyon kurallarını yönetir.

    Attributes:
        _rules: Kural kayıtları.
        _executions: Yürütme kayıtları.
    """

    def __init__(self) -> None:
        """Motoru başlatır."""
        self._rules: dict[
            str, dict[str, Any]
        ] = {}
        self._executions: list[
            dict[str, Any]
        ] = []
        self._counter = 0
        self._stats = {
            "rules_defined": 0,
            "rules_executed": 0,
        }

        logger.info(
            "AutomationRuleEngine "
            "baslatildi",
        )

    def define_rule(
        self,
        name: str,
        trigger_type: str = "threshold",
        condition: dict[str, Any]
        | None = None,
        action: dict[str, Any]
        | None = None,
    ) -> dict[str, Any]:
        """Kural tanımlar.

        Args:
            name: Kural adı.
            trigger_type: Tetikleyici tipi.
            condition: Koşul.
            action: Aksiyon.

        Returns:
            Tanım bilgisi.
        """
        condition = condition or {}
        action = action or {}
        self._counter += 1
        rid = f"rule_{self._counter}"

        self._rules[rid] = {
            "rule_id": rid,
            "name": name,
            "trigger_type": trigger_type,
            "condition": condition,
            "action": action,
            "enabled": True,
            "created_at": time.time(),
        }

        self._stats["rules_defined"] += 1

        return {
            "rule_id": rid,
            "name": name,
            "trigger_type": trigger_type,
            "defined": True,
        }

    def check_trigger(
        self,
        rule_id: str,
        current_value: float = 0.0,
    ) -> dict[str, Any]:
        """Tetikleme koşulu kontrol eder.

        Args:
            rule_id: Kural kimliği.
            current_value: Güncel değer.

        Returns:
            Kontrol bilgisi.
        """
        rule = self._rules.get(rule_id)
        if not rule:
            return {
                "rule_id": rule_id,
                "found": False,
            }

        if not rule["enabled"]:
            return {
                "rule_id": rule_id,
                "triggered": False,
                "reason": "disabled",
                "checked": True,
            }

        condition = rule["condition"]
        op = condition.get(
            "operator", "gt",
        )
        threshold = condition.get(
            "threshold", 0,
        )

        if op == "gt":
            triggered = (
                current_value > threshold
            )
        elif op == "lt":
            triggered = (
                current_value < threshold
            )
        elif op == "eq":
            triggered = (
                current_value == threshold
            )
        else:
            triggered = False

        return {
            "rule_id": rule_id,
            "triggered": triggered,
            "current_value": current_value,
            "threshold": threshold,
            "checked": True,
        }

    def execute_action(
        self,
        rule_id: str,
    ) -> dict[str, Any]:
        """Aksiyon yürütür.

        Args:
            rule_id: Kural kimliği.

        Returns:
            Yürütme bilgisi.
        """
        rule = self._rules.get(rule_id)
        if not rule:
            return {
                "rule_id": rule_id,
                "found": False,
            }

        action = rule["action"]
        execution = {
            "rule_id": rule_id,
            "action": action,
            "status": "executed",
            "timestamp": time.time(),
        }
        self._executions.append(execution)
        self._stats[
            "rules_executed"
        ] += 1

        return {
            "rule_id": rule_id,
            "action": action.get(
                "type", "unknown",
            ),
            "executed": True,
        }

    def schedule_rule(
        self,
        rule_id: str,
        cron: str = "",
        interval_seconds: int = 0,
    ) -> dict[str, Any]:
        """Kural zamanlar.

        Args:
            rule_id: Kural kimliği.
            cron: Cron ifadesi.
            interval_seconds: Aralık (sn).

        Returns:
            Zamanlama bilgisi.
        """
        rule = self._rules.get(rule_id)
        if not rule:
            return {
                "rule_id": rule_id,
                "found": False,
            }

        rule["schedule"] = {
            "cron": cron,
            "interval": interval_seconds,
        }
        rule["trigger_type"] = "schedule"

        return {
            "rule_id": rule_id,
            "schedule_type": (
                "cron" if cron
                else "interval"
            ),
            "scheduled": True,
        }

    def chain_rules(
        self,
        rule_ids: list[str]
        | None = None,
    ) -> dict[str, Any]:
        """Kuralları zincirler.

        Args:
            rule_ids: Kural kimlikleri.

        Returns:
            Zincirleme bilgisi.
        """
        rule_ids = rule_ids or []
        self._counter += 1
        cid = f"chain_{self._counter}"

        valid = [
            rid for rid in rule_ids
            if rid in self._rules
        ]

        for i, rid in enumerate(valid[:-1]):
            self._rules[rid][
                "next_rule"
            ] = valid[i + 1]

        return {
            "chain_id": cid,
            "rules": valid,
            "length": len(valid),
            "chained": True,
        }

    @property
    def rule_count(self) -> int:
        """Kural sayısı."""
        return self._stats[
            "rules_defined"
        ]

    @property
    def execution_count(self) -> int:
        """Yürütme sayısı."""
        return self._stats[
            "rules_executed"
        ]
