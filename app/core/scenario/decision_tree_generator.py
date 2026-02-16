"""ATLAS Karar Ağacı Üretici.

Ağaç oluşturma, seçenek haritalama,
sonuç projeksiyonu, yol analizi, görselleştirme.
"""

import logging
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class DecisionTreeGenerator:
    """Karar ağacı üretici.

    Karar ağaçları oluşturur, seçenekleri
    haritalandırır ve sonuçları projekte eder.

    Attributes:
        _trees: Ağaç kayıtları.
        _stats: İstatistikler.
    """

    def __init__(self) -> None:
        """Üreticiyi başlatır."""
        self._trees: dict[
            str, dict
        ] = {}
        self._stats = {
            "trees_created": 0,
            "paths_analyzed": 0,
        }
        logger.info(
            "DecisionTreeGenerator "
            "baslatildi",
        )

    @property
    def tree_count(self) -> int:
        """Ağaç sayısı."""
        return self._stats[
            "trees_created"
        ]

    @property
    def path_count(self) -> int:
        """Analiz edilen yol sayısı."""
        return self._stats[
            "paths_analyzed"
        ]

    def build_tree(
        self,
        decision_name: str,
        options: list[str]
        | None = None,
    ) -> dict[str, Any]:
        """Karar ağacı oluşturur.

        Args:
            decision_name: Karar adı.
            options: Seçenekler.

        Returns:
            Ağaç bilgisi.
        """
        if options is None:
            options = []

        tid = f"dt_{str(uuid4())[:8]}"
        self._trees[tid] = {
            "name": decision_name,
            "options": {
                o: {
                    "outcomes": [],
                    "probability": 0.0,
                    "value": 0.0,
                }
                for o in options
            },
        }
        self._stats[
            "trees_created"
        ] += 1

        return {
            "tree_id": tid,
            "decision": decision_name,
            "option_count": len(options),
            "built": True,
        }

    def map_option(
        self,
        tree_id: str,
        option: str,
        probability: float = 0.5,
        expected_value: float = 0.0,
        outcomes: list[str]
        | None = None,
    ) -> dict[str, Any]:
        """Seçenek haritalandırır.

        Args:
            tree_id: Ağaç kimliği.
            option: Seçenek adı.
            probability: Olasılık.
            expected_value: Beklenen değer.
            outcomes: Olası sonuçlar.

        Returns:
            Haritalama bilgisi.
        """
        if outcomes is None:
            outcomes = []

        if tree_id in self._trees:
            self._trees[tree_id][
                "options"
            ][option] = {
                "outcomes": outcomes,
                "probability": probability,
                "value": expected_value,
            }

        return {
            "tree_id": tree_id,
            "option": option,
            "probability": probability,
            "expected_value": expected_value,
            "outcome_count": len(outcomes),
            "mapped": True,
        }

    def project_outcome(
        self,
        tree_id: str,
        option: str,
        probability: float = 0.5,
        payoff: float = 0.0,
        cost: float = 0.0,
    ) -> dict[str, Any]:
        """Sonuç projeksiyonu yapar.

        Args:
            tree_id: Ağaç kimliği.
            option: Seçenek adı.
            probability: Olasılık.
            payoff: Kazanç.
            cost: Maliyet.

        Returns:
            Projeksiyon bilgisi.
        """
        expected = round(
            probability * payoff
            - (1 - probability) * cost,
            2,
        )

        net_payoff = round(
            payoff - cost, 2,
        )

        return {
            "tree_id": tree_id,
            "option": option,
            "expected_value": expected,
            "net_payoff": net_payoff,
            "risk_adjusted": round(
                expected * probability, 2,
            ),
            "projected": True,
        }

    def analyze_path(
        self,
        tree_id: str,
        path: list[str]
        | None = None,
        probabilities: list[float]
        | None = None,
        values: list[float]
        | None = None,
    ) -> dict[str, Any]:
        """Yol analizi yapar.

        Args:
            tree_id: Ağaç kimliği.
            path: Yol düğümleri.
            probabilities: Olasılıklar.
            values: Değerler.

        Returns:
            Yol analizi bilgisi.
        """
        if path is None:
            path = []
        if probabilities is None:
            probabilities = []
        if values is None:
            values = []

        combined_prob = 1.0
        for p in probabilities:
            combined_prob *= p
        combined_prob = round(
            combined_prob, 4,
        )

        total_value = round(
            sum(values), 2,
        )
        expected = round(
            combined_prob * total_value,
            2,
        )

        self._stats[
            "paths_analyzed"
        ] += 1

        return {
            "tree_id": tree_id,
            "path_length": len(path),
            "combined_probability": (
                combined_prob
            ),
            "total_value": total_value,
            "expected_value": expected,
            "analyzed": True,
        }

    def visualize(
        self,
        tree_id: str,
    ) -> dict[str, Any]:
        """Ağacı görselleştirir.

        Args:
            tree_id: Ağaç kimliği.

        Returns:
            Görselleştirme bilgisi.
        """
        tree = self._trees.get(tree_id)

        if tree is None:
            return {
                "tree_id": tree_id,
                "found": False,
            }

        options = tree["options"]
        nodes = 1 + len(options)
        for opt in options.values():
            nodes += len(
                opt.get("outcomes", []),
            )

        return {
            "tree_id": tree_id,
            "name": tree["name"],
            "node_count": nodes,
            "option_count": len(options),
            "format": "text",
            "visualized": True,
        }
