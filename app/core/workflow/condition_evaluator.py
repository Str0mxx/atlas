"""ATLAS Kosul Degerlendirici modulu.

Boolean mantik, karsilastirma
operatorleri, veri tabanli,
zaman tabanli ve karmasik kosullar.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class ConditionEvaluator:
    """Kosul degerlendirici.

    Is akisi kosullarini degerlendirir
    ve kararlastirir.

    Attributes:
        _conditions: Kayitli kosullar.
        _evaluations: Degerlendirme gecmisi.
    """

    def __init__(self) -> None:
        """Kosul degerlendiriciyi baslatir."""
        self._conditions: dict[
            str, dict[str, Any]
        ] = {}
        self._evaluations: list[
            dict[str, Any]
        ] = []

        logger.info(
            "ConditionEvaluator baslatildi",
        )

    def register_condition(
        self,
        name: str,
        expression: str,
        config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Kosul kaydeder.

        Args:
            name: Kosul adi.
            expression: Kosul ifadesi.
            config: Yapilandirma.

        Returns:
            Kosul bilgisi.
        """
        condition = {
            "name": name,
            "expression": expression,
            "config": config or {},
        }
        self._conditions[name] = condition
        return condition

    def evaluate(
        self,
        expression: str,
        context: dict[str, Any] | None = None,
    ) -> bool:
        """Kosul degerlendirir.

        Args:
            expression: Kosul ifadesi.
            context: Baglam degiskenleri.

        Returns:
            Sonuc.
        """
        ctx = context or {}
        result = self._eval_expression(
            expression, ctx,
        )

        self._evaluations.append({
            "expression": expression,
            "context_keys": list(ctx.keys()),
            "result": result,
            "at": time.time(),
        })

        return result

    def evaluate_named(
        self,
        name: str,
        context: dict[str, Any] | None = None,
    ) -> bool:
        """Kayitli kosulu degerlendirir.

        Args:
            name: Kosul adi.
            context: Baglam.

        Returns:
            Sonuc.
        """
        condition = self._conditions.get(name)
        if not condition:
            return False
        return self.evaluate(
            condition["expression"], context,
        )

    def compare(
        self,
        left: Any,
        operator: str,
        right: Any,
    ) -> bool:
        """Karsilastirma yapar.

        Args:
            left: Sol deger.
            operator: Operator.
            right: Sag deger.

        Returns:
            Sonuc.
        """
        ops = {
            "eq": lambda a, b: a == b,
            "ne": lambda a, b: a != b,
            "gt": lambda a, b: a > b,
            "gte": lambda a, b: a >= b,
            "lt": lambda a, b: a < b,
            "lte": lambda a, b: a <= b,
            "in": lambda a, b: a in b,
            "not_in": lambda a, b: a not in b,
            "contains": lambda a, b: b in a,
        }
        op_func = ops.get(operator)
        if not op_func:
            return False
        try:
            return op_func(left, right)
        except (TypeError, ValueError):
            return False

    def evaluate_all(
        self,
        conditions: list[str],
        context: dict[str, Any] | None = None,
    ) -> bool:
        """Tum kosullari degerlendirir (AND).

        Args:
            conditions: Kosul listesi.
            context: Baglam.

        Returns:
            Hepsi True ise True.
        """
        return all(
            self.evaluate(c, context)
            for c in conditions
        )

    def evaluate_any(
        self,
        conditions: list[str],
        context: dict[str, Any] | None = None,
    ) -> bool:
        """Herhangi kosulu degerlendirir (OR).

        Args:
            conditions: Kosul listesi.
            context: Baglam.

        Returns:
            Herhangi biri True ise True.
        """
        return any(
            self.evaluate(c, context)
            for c in conditions
        )

    def check_time_condition(
        self,
        start_hour: int,
        end_hour: int,
        current_hour: int | None = None,
    ) -> bool:
        """Zaman kosulu kontrol eder.

        Args:
            start_hour: Baslangic saati.
            end_hour: Bitis saati.
            current_hour: Mevcut saat.

        Returns:
            Kosul saglaniyorsa True.
        """
        hour = current_hour
        if hour is None:
            hour = int(
                time.strftime("%H"),
            )
        if start_hour <= end_hour:
            return start_hour <= hour < end_hour
        # Gece yarisi gecisi
        return hour >= start_hour or hour < end_hour

    def _eval_expression(
        self,
        expression: str,
        context: dict[str, Any],
    ) -> bool:
        """Ifadeyi degerlendirir.

        Args:
            expression: Ifade.
            context: Baglam.

        Returns:
            Sonuc.
        """
        expr = expression.strip()

        # "true" / "false"
        if expr.lower() == "true":
            return True
        if expr.lower() == "false":
            return False

        # Karsilastirma: "field op value"
        for op in [">=", "<=", "!=", "==", ">", "<"]:
            if op in expr:
                parts = expr.split(op, 1)
                if len(parts) == 2:
                    left_key = parts[0].strip()
                    right_val = parts[1].strip()
                    left_val = context.get(
                        left_key, left_key,
                    )
                    # Sayisal donusum
                    try:
                        left_val = float(left_val)
                        right_val = float(right_val)
                    except (ValueError, TypeError):
                        pass

                    op_map = {
                        "==": "eq", "!=": "ne",
                        ">": "gt", ">=": "gte",
                        "<": "lt", "<=": "lte",
                    }
                    return self.compare(
                        left_val,
                        op_map[op],
                        right_val,
                    )

        # Degisken kontrolu
        val = context.get(expr)
        if val is not None:
            return bool(val)

        return False

    @property
    def condition_count(self) -> int:
        """Kosul sayisi."""
        return len(self._conditions)

    @property
    def evaluation_count(self) -> int:
        """Degerlendirme sayisi."""
        return len(self._evaluations)
