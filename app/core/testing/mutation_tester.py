"""ATLAS Mutasyon Testi modulu.

Kod mutasyonlari, mutasyon puanlama,
hayatta kalan mutantlar, test gucu
ve oldurme orani.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class MutationTester:
    """Mutasyon test edici.

    Kod mutasyonlari olusturur ve
    test gucunu olcer.

    Attributes:
        _mutations: Mutasyon kayitlari.
        _results: Test sonuclari.
    """

    def __init__(
        self,
        threshold: float = 0.8,
    ) -> None:
        """Mutasyon test edicisini baslatir.

        Args:
            threshold: Minimum olum orani.
        """
        self._threshold = threshold
        self._mutations: list[
            dict[str, Any]
        ] = []
        self._results: list[
            dict[str, Any]
        ] = []
        self._operators: dict[
            str, list[dict[str, str]]
        ] = {
            "arithmetic": [
                {"from": "+", "to": "-"},
                {"from": "-", "to": "+"},
                {"from": "*", "to": "/"},
                {"from": "/", "to": "*"},
            ],
            "relational": [
                {"from": "==", "to": "!="},
                {"from": "!=", "to": "=="},
                {"from": "<", "to": ">="},
                {"from": ">", "to": "<="},
                {"from": "<=", "to": ">"},
                {"from": ">=", "to": "<"},
            ],
            "logical": [
                {"from": "and", "to": "or"},
                {"from": "or", "to": "and"},
                {"from": "True", "to": "False"},
                {"from": "False", "to": "True"},
            ],
            "boundary": [
                {"from": "<", "to": "<="},
                {"from": ">", "to": ">="},
                {"from": "<=", "to": "<"},
                {"from": ">=", "to": ">"},
            ],
            "removal": [
                {"from": "return x", "to": "return None"},
            ],
        }

        logger.info(
            "MutationTester baslatildi",
        )

    def generate_mutations(
        self,
        code: str,
        mutation_type: str = "arithmetic",
    ) -> list[dict[str, Any]]:
        """Mutasyonlar uretir.

        Args:
            code: Kaynak kod.
            mutation_type: Mutasyon tipi.

        Returns:
            Mutasyon listesi.
        """
        operators = self._operators.get(
            mutation_type, [],
        )
        mutations = []

        for op in operators:
            if op["from"] in code:
                mutated = code.replace(
                    op["from"], op["to"], 1,
                )
                mutation = {
                    "id": len(self._mutations)
                    + len(mutations),
                    "type": mutation_type,
                    "original": op["from"],
                    "replacement": op["to"],
                    "mutated_code": mutated,
                    "killed": False,
                    "created_at": time.time(),
                }
                mutations.append(mutation)

        self._mutations.extend(mutations)
        return mutations

    def run_mutation(
        self,
        mutation_id: int,
        test_passed: bool,
    ) -> dict[str, Any]:
        """Mutasyon test sonucunu kaydeder.

        Args:
            mutation_id: Mutasyon ID.
            test_passed: Test gecti mi.

        Returns:
            Sonuc bilgisi.
        """
        # Test gectiyse mutant hayatta kaldi
        # Test basarisizsa mutant olduruldu
        killed = not test_passed

        # Mutasyonu guncelle
        for m in self._mutations:
            if m["id"] == mutation_id:
                m["killed"] = killed
                break

        result = {
            "mutation_id": mutation_id,
            "killed": killed,
            "test_passed": test_passed,
            "timestamp": time.time(),
        }
        self._results.append(result)
        return result

    def get_mutation_score(self) -> dict[str, Any]:
        """Mutasyon puanini hesaplar.

        Returns:
            Puan bilgisi.
        """
        total = len(self._mutations)
        killed = sum(
            1 for m in self._mutations
            if m["killed"]
        )
        survived = total - killed

        score = (
            killed / total if total > 0 else 0.0
        )

        return {
            "total": total,
            "killed": killed,
            "survived": survived,
            "score": round(score, 4),
            "meets_threshold": (
                score >= self._threshold
            ),
        }

    def get_surviving_mutants(
        self,
    ) -> list[dict[str, Any]]:
        """Hayatta kalan mutantlari getirir.

        Returns:
            Mutant listesi.
        """
        return [
            m for m in self._mutations
            if not m["killed"]
        ]

    def get_test_strength(self) -> dict[str, Any]:
        """Test gucunu hesaplar.

        Returns:
            Guc bilgisi.
        """
        score = self.get_mutation_score()
        mutation_score = score["score"]

        if mutation_score >= 0.9:
            strength = "excellent"
        elif mutation_score >= 0.8:
            strength = "good"
        elif mutation_score >= 0.6:
            strength = "moderate"
        else:
            strength = "weak"

        return {
            "mutation_score": mutation_score,
            "strength": strength,
            "total_mutations": score["total"],
            "killed": score["killed"],
            "survived": score["survived"],
        }

    def get_kill_ratio_by_type(
        self,
    ) -> dict[str, dict[str, Any]]:
        """Tipe gore olum oranini getirir.

        Returns:
            Tip bazli oranlar.
        """
        by_type: dict[str, dict[str, int]] = {}
        for m in self._mutations:
            mtype = m["type"]
            if mtype not in by_type:
                by_type[mtype] = {
                    "total": 0,
                    "killed": 0,
                }
            by_type[mtype]["total"] += 1
            if m["killed"]:
                by_type[mtype]["killed"] += 1

        result = {}
        for mtype, data in by_type.items():
            total = data["total"]
            killed = data["killed"]
            result[mtype] = {
                "total": total,
                "killed": killed,
                "ratio": round(
                    killed / total
                    if total > 0
                    else 0.0,
                    4,
                ),
            }
        return result

    def add_operator(
        self,
        mutation_type: str,
        from_str: str,
        to_str: str,
    ) -> None:
        """Mutasyon operatoru ekler.

        Args:
            mutation_type: Mutasyon tipi.
            from_str: Kaynak.
            to_str: Hedef.
        """
        if mutation_type not in self._operators:
            self._operators[mutation_type] = []
        self._operators[mutation_type].append({
            "from": from_str,
            "to": to_str,
        })

    @property
    def mutation_count(self) -> int:
        """Mutasyon sayisi."""
        return len(self._mutations)

    @property
    def killed_count(self) -> int:
        """Oldurulen mutant sayisi."""
        return sum(
            1 for m in self._mutations
            if m["killed"]
        )

    @property
    def survived_count(self) -> int:
        """Hayatta kalan sayisi."""
        return sum(
            1 for m in self._mutations
            if not m["killed"]
        )
