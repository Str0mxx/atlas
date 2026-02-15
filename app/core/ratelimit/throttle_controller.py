"""ATLAS Kisma Kontrolcusu modulu.

Adaptif kisma, yuk tabanli,
oncelik, geri basinc, devre entegrasyonu.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class ThrottleController:
    """Kisma kontrolcusu.

    Yuk durumuna gore trafigi kisitlar.

    Attributes:
        _rules: Kisma kurallari.
        _circuits: Devre durumlari.
    """

    def __init__(
        self,
        default_mode: str = "none",
        load_threshold: float = 0.8,
        backpressure_threshold: float = 0.9,
    ) -> None:
        """Kisma kontrolcusunu baslatir.

        Args:
            default_mode: Varsayilan mod.
            load_threshold: Yuk esigi.
            backpressure_threshold: Geri basinc esigi.
        """
        self._rules: dict[
            str, dict[str, Any]
        ] = {}
        self._circuits: dict[
            str, dict[str, Any]
        ] = {}
        self._load_history: list[
            dict[str, Any]
        ] = []
        self._default_mode = default_mode
        self._load_threshold = load_threshold
        self._backpressure_threshold = (
            backpressure_threshold
        )
        self._current_load = 0.0
        self._stats = {
            "throttled": 0,
            "passed": 0,
            "backpressure_events": 0,
        }

        logger.info(
            "ThrottleController baslatildi",
        )

    def add_rule(
        self,
        rule_id: str,
        mode: str = "soft",
        threshold: float = 0.8,
        delay_ms: int = 0,
        priority: int = 5,
        target: str = "*",
    ) -> dict[str, Any]:
        """Kisma kurali ekler.

        Args:
            rule_id: Kural ID.
            mode: Kisma modu.
            threshold: Esik.
            delay_ms: Gecikme (ms).
            priority: Oncelik.
            target: Hedef.

        Returns:
            Kural bilgisi.
        """
        self._rules[rule_id] = {
            "rule_id": rule_id,
            "mode": mode,
            "threshold": threshold,
            "delay_ms": delay_ms,
            "priority": priority,
            "target": target,
            "active": True,
            "triggered_count": 0,
            "created_at": time.time(),
        }

        return {
            "rule_id": rule_id,
            "mode": mode,
            "status": "added",
        }

    def remove_rule(
        self,
        rule_id: str,
    ) -> bool:
        """Kisma kurali kaldirir.

        Args:
            rule_id: Kural ID.

        Returns:
            Basarili mi.
        """
        if rule_id not in self._rules:
            return False
        del self._rules[rule_id]
        return True

    def check(
        self,
        target: str = "*",
        priority: int = 5,
    ) -> dict[str, Any]:
        """Kisma kontrolu yapar.

        Args:
            target: Hedef.
            priority: Istek onceligi.

        Returns:
            Kontrol sonucu.
        """
        # Geri basinc kontrolu
        if (
            self._current_load
            >= self._backpressure_threshold
        ):
            self._stats["backpressure_events"] += 1
            self._stats["throttled"] += 1
            return {
                "allowed": False,
                "reason": "backpressure",
                "load": self._current_load,
                "delay_ms": 0,
            }

        # Kural kontrolu
        for rule in sorted(
            self._rules.values(),
            key=lambda r: r["priority"],
            reverse=True,
        ):
            if not rule["active"]:
                continue

            if (
                rule["target"] != "*"
                and rule["target"] != target
            ):
                continue

            if (
                self._current_load
                >= rule["threshold"]
            ):
                rule["triggered_count"] += 1

                if rule["mode"] == "hard":
                    self._stats["throttled"] += 1
                    return {
                        "allowed": False,
                        "reason": "hard_throttle",
                        "rule_id": rule["rule_id"],
                        "load": self._current_load,
                        "delay_ms": 0,
                    }

                if rule["mode"] == "soft":
                    self._stats["passed"] += 1
                    return {
                        "allowed": True,
                        "throttled": True,
                        "rule_id": rule["rule_id"],
                        "delay_ms": rule["delay_ms"],
                        "load": self._current_load,
                    }

                if rule["mode"] == "adaptive":
                    load_factor = (
                        self._current_load
                        / max(rule["threshold"], 0.01)
                    )
                    delay = int(
                        rule["delay_ms"]
                        * load_factor,
                    )
                    self._stats["passed"] += 1
                    return {
                        "allowed": True,
                        "throttled": True,
                        "rule_id": rule["rule_id"],
                        "delay_ms": delay,
                        "load": self._current_load,
                    }

        # Devre kontrolu
        circuit = self._circuits.get(target)
        if circuit and circuit["state"] == "open":
            self._stats["throttled"] += 1
            return {
                "allowed": False,
                "reason": "circuit_open",
                "target": target,
                "delay_ms": 0,
            }

        self._stats["passed"] += 1
        return {
            "allowed": True,
            "throttled": False,
            "delay_ms": 0,
            "load": self._current_load,
        }

    def update_load(
        self,
        load: float,
    ) -> dict[str, Any]:
        """Yuk bilgisini gunceller.

        Args:
            load: Yuk (0.0-1.0).

        Returns:
            Yuk durumu.
        """
        self._current_load = max(
            0.0, min(1.0, load),
        )
        self._load_history.append({
            "load": self._current_load,
            "timestamp": time.time(),
        })

        # Gecmisi sinirla
        if len(self._load_history) > 1000:
            self._load_history = (
                self._load_history[-1000:]
            )

        return {
            "load": self._current_load,
            "threshold": self._load_threshold,
            "backpressure": (
                self._current_load
                >= self._backpressure_threshold
            ),
        }

    def set_circuit(
        self,
        target: str,
        state: str = "closed",
    ) -> dict[str, Any]:
        """Devre durumunu ayarlar.

        Args:
            target: Hedef.
            state: Durum (open/closed/half_open).

        Returns:
            Devre durumu.
        """
        self._circuits[target] = {
            "state": state,
            "updated_at": time.time(),
        }

        return {
            "target": target,
            "state": state,
        }

    def get_rule(
        self,
        rule_id: str,
    ) -> dict[str, Any] | None:
        """Kural bilgisi getirir.

        Args:
            rule_id: Kural ID.

        Returns:
            Kural bilgisi veya None.
        """
        return self._rules.get(rule_id)

    def get_load_history(
        self,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Yuk gecmisini getirir.

        Args:
            limit: Limit.

        Returns:
            Yuk gecmisi.
        """
        return self._load_history[-limit:]

    def list_rules(
        self,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Kurallari listeler.

        Args:
            limit: Limit.

        Returns:
            Kural listesi.
        """
        items = list(self._rules.values())
        return items[-limit:]

    @property
    def rule_count(self) -> int:
        """Kural sayisi."""
        return len(self._rules)

    @property
    def current_load(self) -> float:
        """Mevcut yuk."""
        return self._current_load

    @property
    def throttled_count(self) -> int:
        """Kistirilan sayisi."""
        return self._stats["throttled"]

    @property
    def passed_count(self) -> int:
        """Gecen sayisi."""
        return self._stats["passed"]
