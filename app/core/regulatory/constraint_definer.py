"""ATLAS Kısıt Tanımlayıcı modulu.

Sert kısıtlar, yumuşak kısıtlar,
zamansal kısıtlar, koşullu kısıtlar, öncelik seviyeleri.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class ConstraintDefiner:
    """Kısıt tanımlayıcı.

    Kısıtları tanımlar ve yönetir.

    Attributes:
        _constraints: Kısıt kayıtları.
    """

    def __init__(self) -> None:
        """Tanımlayıcıyı başlatır."""
        self._constraints: dict[
            str, dict[str, Any]
        ] = {}
        self._counter = 0
        self._stats = {
            "defined": 0,
        }

        logger.info(
            "ConstraintDefiner baslatildi",
        )

    def define_hard_constraint(
        self,
        name: str,
        condition: str,
        description: str = "",
    ) -> dict[str, Any]:
        """Sert kısıt tanımlar.

        Args:
            name: Kısıt adı.
            condition: Koşul ifadesi.
            description: Açıklama.

        Returns:
            Tanımlama bilgisi.
        """
        return self._add_constraint(
            name, "hard", condition,
            description, priority=10,
        )

    def define_soft_constraint(
        self,
        name: str,
        condition: str,
        priority: int = 5,
        description: str = "",
    ) -> dict[str, Any]:
        """Yumuşak kısıt tanımlar.

        Args:
            name: Kısıt adı.
            condition: Koşul ifadesi.
            priority: Öncelik (1-10).
            description: Açıklama.

        Returns:
            Tanımlama bilgisi.
        """
        return self._add_constraint(
            name, "soft", condition,
            description, priority=priority,
        )

    def define_temporal_constraint(
        self,
        name: str,
        condition: str,
        start_time: float | None = None,
        end_time: float | None = None,
        description: str = "",
    ) -> dict[str, Any]:
        """Zamansal kısıt tanımlar.

        Args:
            name: Kısıt adı.
            condition: Koşul ifadesi.
            start_time: Başlangıç zamanı.
            end_time: Bitiş zamanı.
            description: Açıklama.

        Returns:
            Tanımlama bilgisi.
        """
        result = self._add_constraint(
            name, "temporal", condition,
            description, priority=7,
        )
        cid = result["constraint_id"]
        self._constraints[cid][
            "start_time"
        ] = start_time
        self._constraints[cid][
            "end_time"
        ] = end_time
        return result

    def define_conditional_constraint(
        self,
        name: str,
        condition: str,
        trigger: str = "",
        description: str = "",
    ) -> dict[str, Any]:
        """Koşullu kısıt tanımlar.

        Args:
            name: Kısıt adı.
            condition: Koşul ifadesi.
            trigger: Tetikleyici.
            description: Açıklama.

        Returns:
            Tanımlama bilgisi.
        """
        result = self._add_constraint(
            name, "conditional", condition,
            description, priority=6,
        )
        cid = result["constraint_id"]
        self._constraints[cid][
            "trigger"
        ] = trigger
        return result

    def _add_constraint(
        self,
        name: str,
        constraint_type: str,
        condition: str,
        description: str,
        priority: int,
    ) -> dict[str, Any]:
        """Kısıt ekler (iç metot).

        Args:
            name: Kısıt adı.
            constraint_type: Kısıt tipi.
            condition: Koşul.
            description: Açıklama.
            priority: Öncelik.

        Returns:
            Ekleme bilgisi.
        """
        self._counter += 1
        cid = f"cst_{self._counter}"

        self._constraints[cid] = {
            "constraint_id": cid,
            "name": name,
            "constraint_type": constraint_type,
            "condition": condition,
            "description": description,
            "priority": max(
                1, min(10, priority),
            ),
            "active": True,
            "created_at": time.time(),
        }
        self._stats["defined"] += 1

        return {
            "constraint_id": cid,
            "name": name,
            "constraint_type": constraint_type,
            "priority": priority,
            "defined": True,
        }

    def get_constraint(
        self,
        constraint_id: str,
    ) -> dict[str, Any]:
        """Kısıt getirir.

        Args:
            constraint_id: Kısıt ID.

        Returns:
            Kısıt bilgisi.
        """
        c = self._constraints.get(
            constraint_id,
        )
        if not c:
            return {
                "error": "constraint_not_found",
            }
        return dict(c)

    def evaluate_constraint(
        self,
        constraint_id: str,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Kısıt değerlendirir.

        Args:
            constraint_id: Kısıt ID.
            context: Değerlendirme bağlamı.

        Returns:
            Değerlendirme bilgisi.
        """
        c = self._constraints.get(
            constraint_id,
        )
        if not c:
            return {
                "error": "constraint_not_found",
            }

        if not c["active"]:
            return {
                "constraint_id": constraint_id,
                "satisfied": True,
                "reason": "inactive",
            }

        # Zamansal kontrol
        if c["constraint_type"] == "temporal":
            now = time.time()
            start = c.get("start_time")
            end = c.get("end_time")
            if start and now < start:
                return {
                    "constraint_id": (
                        constraint_id
                    ),
                    "satisfied": True,
                    "reason": "not_yet_active",
                }
            if end and now > end:
                return {
                    "constraint_id": (
                        constraint_id
                    ),
                    "satisfied": True,
                    "reason": "expired",
                }

        # Koşul değerlendirme
        condition = c["condition"]
        satisfied = self._check_condition(
            condition, context,
        )

        return {
            "constraint_id": constraint_id,
            "constraint_type": c[
                "constraint_type"
            ],
            "satisfied": satisfied,
            "priority": c["priority"],
            "is_hard": (
                c["constraint_type"] == "hard"
            ),
        }

    def _check_condition(
        self,
        condition: str,
        context: dict[str, Any],
    ) -> bool:
        """Koşul kontrol eder.

        Args:
            condition: Koşul ifadesi.
            context: Bağlam.

        Returns:
            Koşul sonucu.
        """
        # Basit anahtar-değer kontrolü
        # "key=value" formatı
        if "=" in condition and "!" not in condition:
            parts = condition.split("=", 1)
            key = parts[0].strip()
            val = parts[1].strip()
            return str(
                context.get(key, ""),
            ) == val

        # "key!=value" formatı
        if "!=" in condition:
            parts = condition.split("!=", 1)
            key = parts[0].strip()
            val = parts[1].strip()
            return str(
                context.get(key, ""),
            ) != val

        # Anahtar varlık kontrolü
        return condition in context

    def list_constraints(
        self,
        constraint_type: str | None = None,
        active_only: bool = True,
    ) -> list[dict[str, Any]]:
        """Kısıtları listeler.

        Args:
            constraint_type: Tip filtresi.
            active_only: Sadece aktif.

        Returns:
            Kısıt listesi.
        """
        results = []
        for c in self._constraints.values():
            if active_only and not c["active"]:
                continue
            if constraint_type and (
                c["constraint_type"]
                != constraint_type
            ):
                continue
            results.append({
                "constraint_id": c[
                    "constraint_id"
                ],
                "name": c["name"],
                "constraint_type": c[
                    "constraint_type"
                ],
                "priority": c["priority"],
            })

        results.sort(
            key=lambda x: x["priority"],
            reverse=True,
        )
        return results

    def deactivate_constraint(
        self,
        constraint_id: str,
    ) -> dict[str, Any]:
        """Kısıt deaktifleştirir.

        Args:
            constraint_id: Kısıt ID.

        Returns:
            Deaktivasyon bilgisi.
        """
        c = self._constraints.get(
            constraint_id,
        )
        if not c:
            return {
                "error": "constraint_not_found",
            }
        c["active"] = False
        return {
            "constraint_id": constraint_id,
            "deactivated": True,
        }

    @property
    def constraint_count(self) -> int:
        """Kısıt sayısı."""
        return self._stats["defined"]
