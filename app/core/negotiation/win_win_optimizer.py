"""ATLAS Kazan-Kazan Optimizasyonu modülü.

Değer yaratma, ilgi hizalama,
takas analizi, Pareto optimizasyonu,
yaratıcı çözümler.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class WinWinOptimizer:
    """Kazan-kazan optimizasyonu.

    Her iki taraf için değer yaratır.

    Attributes:
        _solutions: Çözüm kayıtları.
        _interests: İlgi haritası.
    """

    def __init__(self) -> None:
        """Optimizasyonu başlatır."""
        self._solutions: list[
            dict[str, Any]
        ] = []
        self._interests: dict[
            str, list[str]
        ] = {}
        self._tradeoffs: list[
            dict[str, Any]
        ] = []
        self._counter = 0
        self._stats = {
            "values_created": 0,
            "alignments_found": 0,
            "tradeoffs_analyzed": 0,
            "solutions_generated": 0,
        }

        logger.info(
            "WinWinOptimizer baslatildi",
        )

    def create_value(
        self,
        our_strengths: list[str],
        their_needs: list[str],
        our_needs: list[str] | None = None,
        their_strengths: (
            list[str] | None
        ) = None,
    ) -> dict[str, Any]:
        """Değer yaratır.

        Args:
            our_strengths: Güçlü yanlarımız.
            their_needs: Onların ihtiyaçları.
            our_needs: Bizim ihtiyaçlarımız.
            their_strengths: Onların güçleri.

        Returns:
            Değer bilgisi.
        """
        self._counter += 1
        vid = f"value_{self._counter}"

        our_needs = our_needs or []
        their_strengths = (
            their_strengths or []
        )

        # Eşleşme bul
        matches = [
            s for s in our_strengths
            if s in their_needs
        ]

        reverse_matches = [
            s for s in their_strengths
            if s in our_needs
        ]

        synergies = len(matches) + len(
            reverse_matches,
        )
        potential = (
            "high" if synergies >= 3
            else "medium" if synergies >= 1
            else "low"
        )

        self._stats["values_created"] += 1

        return {
            "value_id": vid,
            "matches": matches,
            "reverse_matches": (
                reverse_matches
            ),
            "synergies": synergies,
            "potential": potential,
            "created": True,
        }

    def align_interests(
        self,
        party_a: str,
        interests_a: list[str],
        party_b: str,
        interests_b: list[str],
    ) -> dict[str, Any]:
        """İlgi hizalama yapar.

        Args:
            party_a: Taraf A.
            interests_a: A ilgileri.
            party_b: Taraf B.
            interests_b: B ilgileri.

        Returns:
            Hizalama bilgisi.
        """
        self._interests[party_a] = (
            interests_a
        )
        self._interests[party_b] = (
            interests_b
        )

        # Ortak ilgiler
        common = list(
            set(interests_a)
            & set(interests_b)
        )

        # Benzersiz ilgiler
        unique_a = list(
            set(interests_a)
            - set(interests_b)
        )
        unique_b = list(
            set(interests_b)
            - set(interests_a)
        )

        alignment = round(
            len(common)
            / max(
                len(
                    set(interests_a)
                    | set(interests_b)
                ), 1,
            )
            * 100, 1,
        )

        compatibility = (
            "high" if alignment >= 60
            else "medium"
            if alignment >= 30
            else "low"
        )

        self._stats[
            "alignments_found"
        ] += 1

        return {
            "common": common,
            "unique_a": unique_a,
            "unique_b": unique_b,
            "alignment_percent": alignment,
            "compatibility": compatibility,
        }

    def analyze_tradeoff(
        self,
        dimension_a: str,
        value_a_gives: float,
        value_a_gets: float,
        dimension_b: str,
        value_b_gives: float,
        value_b_gets: float,
    ) -> dict[str, Any]:
        """Takas analizi yapar.

        Args:
            dimension_a: Boyut A.
            value_a_gives: A veriyor.
            value_a_gets: A alıyor.
            dimension_b: Boyut B.
            value_b_gives: B veriyor.
            value_b_gets: B alıyor.

        Returns:
            Takas bilgisi.
        """
        self._counter += 1
        tid = f"trade_{self._counter}"

        net_a = round(
            value_a_gets - value_a_gives, 2,
        )
        net_b = round(
            value_b_gets - value_b_gives, 2,
        )
        total_value = round(
            net_a + net_b, 2,
        )

        fair = abs(net_a - net_b) < max(
            abs(net_a), abs(net_b), 1,
        ) * 0.3

        tradeoff = {
            "tradeoff_id": tid,
            "dimension_a": dimension_a,
            "dimension_b": dimension_b,
            "net_a": net_a,
            "net_b": net_b,
            "total_value": total_value,
            "fair": fair,
            "win_win": (
                net_a > 0 and net_b > 0
            ),
            "timestamp": time.time(),
        }
        self._tradeoffs.append(tradeoff)
        self._stats[
            "tradeoffs_analyzed"
        ] += 1

        return tradeoff

    def find_pareto_optimal(
        self,
        options: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Pareto optimal çözümler bulur.

        Args:
            options: Seçenekler.

        Returns:
            Pareto bilgisi.
        """
        if not options:
            return {
                "optimal": [],
                "count": 0,
            }

        # Pareto dominansı kontrolü
        optimal = []
        for i, opt_a in enumerate(options):
            dominated = False
            for j, opt_b in enumerate(
                options,
            ):
                if i == j:
                    continue
                a_val = opt_a.get(
                    "value_a", 0,
                )
                a_val_b = opt_a.get(
                    "value_b", 0,
                )
                b_val = opt_b.get(
                    "value_a", 0,
                )
                b_val_b = opt_b.get(
                    "value_b", 0,
                )
                if (
                    b_val >= a_val
                    and b_val_b >= a_val_b
                    and (
                        b_val > a_val
                        or b_val_b > a_val_b
                    )
                ):
                    dominated = True
                    break
            if not dominated:
                optimal.append(opt_a)

        return {
            "optimal": optimal,
            "count": len(optimal),
            "total_options": len(options),
            "efficiency": round(
                len(optimal)
                / max(len(options), 1)
                * 100, 1,
            ),
        }

    def generate_creative_solution(
        self,
        deadlock_issue: str,
        party_a_priority: str = "",
        party_b_priority: str = "",
    ) -> dict[str, Any]:
        """Yaratıcı çözüm üretir.

        Args:
            deadlock_issue: Tıkanıklık konusu.
            party_a_priority: A önceliği.
            party_b_priority: B önceliği.

        Returns:
            Çözüm bilgisi.
        """
        self._counter += 1
        sid = f"solution_{self._counter}"

        solutions = []

        # Fark buysa bölme
        solutions.append({
            "type": "split",
            "description": (
                f"Split {deadlock_issue} "
                "into phases"
            ),
        })

        # Farklı boyutlarda takas
        if (
            party_a_priority
            and party_b_priority
        ):
            solutions.append({
                "type": "trade",
                "description": (
                    f"Trade {party_a_priority}"
                    f" for {party_b_priority}"
                ),
            })

        # Yeni değer yaratma
        solutions.append({
            "type": "expand",
            "description": (
                "Expand the pie with "
                "new value opportunities"
            ),
        })

        # Koşullu anlaşma
        solutions.append({
            "type": "contingent",
            "description": (
                "Contingent agreement "
                "based on outcomes"
            ),
        })

        record = {
            "solution_id": sid,
            "issue": deadlock_issue,
            "solutions": solutions,
            "count": len(solutions),
            "timestamp": time.time(),
        }
        self._solutions.append(record)
        self._stats[
            "solutions_generated"
        ] += 1

        return {
            "solution_id": sid,
            "solutions": solutions,
            "count": len(solutions),
            "generated": True,
        }

    @property
    def solution_count(self) -> int:
        """Çözüm sayısı."""
        return self._stats[
            "solutions_generated"
        ]

    @property
    def tradeoff_count(self) -> int:
        """Takas sayısı."""
        return self._stats[
            "tradeoffs_analyzed"
        ]
