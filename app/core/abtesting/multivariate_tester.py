"""ATLAS Çok Değişkenli Test modülü.

Çoklu değişken, etkileşim etkileri,
faktöriyel tasarım, optimizasyon,
karmaşıklık yönetimi.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class MultivariateTester:
    """Çok değişkenli test yöneticisi.

    Çok değişkenli testleri yönetir.

    Attributes:
        _tests: Test kayıtları.
        _factors: Faktör kayıtları.
    """

    def __init__(self) -> None:
        """Test yöneticisini başlatır."""
        self._tests: dict[
            str, dict[str, Any]
        ] = {}
        self._factors: dict[
            str, list[dict[str, Any]]
        ] = {}
        self._counter = 0
        self._stats = {
            "tests_created": 0,
            "optimizations": 0,
        }

        logger.info(
            "MultivariateTester "
            "baslatildi",
        )

    def define_variables(
        self,
        test_id: str,
        variables: dict[str, list[str]]
        | None = None,
    ) -> dict[str, Any]:
        """Değişkenler tanımlar.

        Args:
            test_id: Test kimliği.
            variables: Değişkenler.

        Returns:
            Tanımlama bilgisi.
        """
        variables = variables or {}

        total_combos = 1
        for levels in variables.values():
            total_combos *= len(levels)

        self._tests[test_id] = {
            "test_id": test_id,
            "variables": variables,
            "total_combinations": (
                total_combos
            ),
            "status": "draft",
            "timestamp": time.time(),
        }

        self._stats[
            "tests_created"
        ] += 1

        return {
            "test_id": test_id,
            "variable_count": len(
                variables,
            ),
            "total_combinations": (
                total_combos
            ),
            "defined": True,
        }

    def analyze_interactions(
        self,
        test_id: str,
        results: list[dict[str, Any]]
        | None = None,
    ) -> dict[str, Any]:
        """Etkileşim etkileri analiz eder.

        Args:
            test_id: Test kimliği.
            results: Sonuçlar.

        Returns:
            Analiz bilgisi.
        """
        results = results or []
        test = self._tests.get(test_id)
        if not test:
            return {
                "test_id": test_id,
                "found": False,
            }

        variables = test.get(
            "variables", {},
        )
        interactions = []

        var_names = list(variables.keys())
        for i, v1 in enumerate(var_names):
            for v2 in var_names[i + 1:]:
                interactions.append({
                    "variables": [v1, v2],
                    "strength": round(
                        0.5
                        * len(results)
                        / max(
                            len(var_names),
                            1,
                        ),
                        2,
                    ),
                    "significant": (
                        len(results) > 10
                    ),
                })

        return {
            "test_id": test_id,
            "interactions": interactions,
            "interaction_count": len(
                interactions,
            ),
            "analyzed": True,
        }

    def factorial_design(
        self,
        test_id: str,
        fractional: bool = False,
    ) -> dict[str, Any]:
        """Faktöriyel tasarım yapar.

        Args:
            test_id: Test kimliği.
            fractional: Kısmi tasarım.

        Returns:
            Tasarım bilgisi.
        """
        test = self._tests.get(test_id)
        if not test:
            return {
                "test_id": test_id,
                "found": False,
            }

        variables = test.get(
            "variables", {},
        )
        total = test.get(
            "total_combinations", 0,
        )

        if fractional and total > 8:
            run_count = max(
                total // 2, 4,
            )
            design_type = "fractional"
        else:
            run_count = total
            design_type = "full"

        combinations: list[
            dict[str, str]
        ] = []
        var_items = list(
            variables.items(),
        )

        if var_items:
            self._generate_combos(
                var_items, 0, {},
                combinations,
            )

        if fractional:
            combinations = combinations[
                :run_count
            ]

        return {
            "test_id": test_id,
            "design_type": design_type,
            "run_count": len(combinations),
            "combinations": combinations,
            "designed": True,
        }

    def _generate_combos(
        self,
        var_items: list[
            tuple[str, list[str]]
        ],
        idx: int,
        current: dict[str, str],
        results: list[dict[str, str]],
    ) -> None:
        """Kombinasyonları üretir."""
        if idx >= len(var_items):
            results.append(
                dict(current),
            )
            return

        name, levels = var_items[idx]
        for level in levels:
            current[name] = level
            self._generate_combos(
                var_items,
                idx + 1,
                current,
                results,
            )

    def optimize(
        self,
        test_id: str,
        results: list[dict[str, Any]]
        | None = None,
        metric: str = "conversion",
    ) -> dict[str, Any]:
        """Optimizasyon yapar.

        Args:
            test_id: Test kimliği.
            results: Sonuçlar.
            metric: Metrik.

        Returns:
            Optimizasyon bilgisi.
        """
        results = results or []

        if not results:
            return {
                "test_id": test_id,
                "optimized": False,
                "reason": "No results",
            }

        best = max(
            results,
            key=lambda r: r.get(
                metric, 0,
            ),
        )

        self._stats[
            "optimizations"
        ] += 1

        return {
            "test_id": test_id,
            "best_combination": best,
            "metric": metric,
            "best_value": best.get(
                metric, 0,
            ),
            "optimized": True,
        }

    def manage_complexity(
        self,
        test_id: str,
        max_combinations: int = 16,
    ) -> dict[str, Any]:
        """Karmaşıklık yönetimi yapar.

        Args:
            test_id: Test kimliği.
            max_combinations: Maks kombinasyon.

        Returns:
            Yönetim bilgisi.
        """
        test = self._tests.get(test_id)
        if not test:
            return {
                "test_id": test_id,
                "found": False,
            }

        total = test.get(
            "total_combinations", 0,
        )

        if total > max_combinations:
            recommendation = "fractional"
            feasible = False
        else:
            recommendation = "full"
            feasible = True

        return {
            "test_id": test_id,
            "total_combinations": total,
            "max_allowed": max_combinations,
            "feasible": feasible,
            "recommendation": (
                recommendation
            ),
            "managed": True,
        }

    @property
    def test_count(self) -> int:
        """Test sayısı."""
        return self._stats[
            "tests_created"
        ]

    @property
    def optimization_count(self) -> int:
        """Optimizasyon sayısı."""
        return self._stats[
            "optimizations"
        ]
