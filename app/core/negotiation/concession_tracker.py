"""ATLAS Taviz Takipçisi modülü.

Taviz geçmişi, örüntü analizi,
kalan alan, karşılıklılık takibi,
kırmızı çizgi izleme.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class ConcessionTracker:
    """Taviz takipçisi.

    Müzakere tavizlerini takip eder.

    Attributes:
        _concessions: Taviz kayıtları.
        _red_lines: Kırmızı çizgiler.
    """

    def __init__(self) -> None:
        """Takipçisini başlatır."""
        self._concessions: list[
            dict[str, Any]
        ] = []
        self._red_lines: dict[
            str, float
        ] = {}
        self._parties: dict[
            str, list[dict[str, Any]]
        ] = {}
        self._counter = 0
        self._stats = {
            "concessions_tracked": 0,
            "patterns_analyzed": 0,
            "red_lines_set": 0,
        }

        logger.info(
            "ConcessionTracker baslatildi",
        )

    def record_concession(
        self,
        party: str,
        concession_type: str = "price",
        original: float = 0.0,
        conceded: float = 0.0,
        description: str = "",
    ) -> dict[str, Any]:
        """Taviz kaydeder.

        Args:
            party: Taraf.
            concession_type: Taviz tipi.
            original: Orijinal değer.
            conceded: Taviz değeri.
            description: Açıklama.

        Returns:
            Taviz bilgisi.
        """
        self._counter += 1
        cid = f"conc_{self._counter}"

        magnitude = round(
            abs(original - conceded), 2,
        )
        percent = round(
            magnitude
            / max(abs(original), 0.01)
            * 100, 2,
        ) if original != 0 else 0.0

        record = {
            "concession_id": cid,
            "party": party,
            "type": concession_type,
            "original": original,
            "conceded": conceded,
            "magnitude": magnitude,
            "percent": percent,
            "description": description,
            "timestamp": time.time(),
        }
        self._concessions.append(record)

        if party not in self._parties:
            self._parties[party] = []
        self._parties[party].append(record)

        self._stats[
            "concessions_tracked"
        ] += 1

        return {
            "concession_id": cid,
            "magnitude": magnitude,
            "percent": percent,
            "recorded": True,
        }

    def analyze_pattern(
        self,
        party: str = "",
    ) -> dict[str, Any]:
        """Örüntü analizi yapar.

        Args:
            party: Taraf filtresi.

        Returns:
            Örüntü bilgisi.
        """
        concessions = (
            self._parties.get(party, [])
            if party
            else self._concessions
        )

        if not concessions:
            return {
                "pattern": "none",
                "count": 0,
                "analyzed": False,
            }

        magnitudes = [
            c["magnitude"]
            for c in concessions
        ]
        percents = [
            c["percent"]
            for c in concessions
        ]

        avg_magnitude = round(
            sum(magnitudes)
            / len(magnitudes), 2,
        )
        avg_percent = round(
            sum(percents) / len(percents),
            2,
        )

        # Taviz trendi
        if len(magnitudes) >= 2:
            if magnitudes[-1] < magnitudes[0]:
                trend = "decreasing"
            elif (
                magnitudes[-1] > magnitudes[0]
            ):
                trend = "increasing"
            else:
                trend = "stable"
        else:
            trend = "insufficient_data"

        # Tip dağılımı
        type_counts: dict[str, int] = {}
        for c in concessions:
            t = c["type"]
            type_counts[t] = (
                type_counts.get(t, 0) + 1
            )

        self._stats[
            "patterns_analyzed"
        ] += 1

        return {
            "pattern": trend,
            "count": len(concessions),
            "avg_magnitude": avg_magnitude,
            "avg_percent": avg_percent,
            "by_type": type_counts,
            "party": party or "all",
            "analyzed": True,
        }

    def get_remaining_room(
        self,
        current_position: float,
        minimum: float,
    ) -> dict[str, Any]:
        """Kalan alanı hesaplar.

        Args:
            current_position: Mevcut pozisyon.
            minimum: Minimum kabul.

        Returns:
            Kalan alan bilgisi.
        """
        remaining = round(
            abs(
                current_position - minimum
            ), 2,
        )
        remaining_percent = round(
            remaining
            / max(
                abs(current_position), 0.01,
            )
            * 100, 1,
        )

        # Toplam verilen taviz
        total_given = sum(
            c["magnitude"]
            for c in self._concessions
        )

        urgency = (
            "critical"
            if remaining_percent < 5
            else "tight"
            if remaining_percent < 15
            else "moderate"
            if remaining_percent < 30
            else "comfortable"
        )

        return {
            "remaining": remaining,
            "remaining_percent": (
                remaining_percent
            ),
            "total_given": round(
                total_given, 2,
            ),
            "urgency": urgency,
            "at_limit": remaining_percent < 2,
        }

    def track_reciprocity(
        self,
    ) -> dict[str, Any]:
        """Karşılıklılık takibi yapar.

        Returns:
            Karşılıklılık bilgisi.
        """
        if not self._parties:
            return {
                "balanced": True,
                "ratio": 1.0,
                "parties": {},
            }

        party_totals: dict[
            str, float
        ] = {}
        for party, concessions in (
            self._parties.items()
        ):
            party_totals[party] = round(
                sum(
                    c["magnitude"]
                    for c in concessions
                ), 2,
            )

        values = list(
            party_totals.values(),
        )
        if len(values) >= 2:
            max_val = max(values)
            min_val = min(values)
            ratio = round(
                min_val
                / max(max_val, 0.01), 2,
            )
            balanced = ratio >= 0.7
        else:
            ratio = 1.0
            balanced = True

        return {
            "balanced": balanced,
            "ratio": ratio,
            "parties": party_totals,
        }

    def set_red_line(
        self,
        dimension: str,
        value: float,
    ) -> dict[str, Any]:
        """Kırmızı çizgi belirler.

        Args:
            dimension: Boyut.
            value: Değer.

        Returns:
            Kırmızı çizgi bilgisi.
        """
        self._red_lines[dimension] = value
        self._stats["red_lines_set"] += 1

        return {
            "dimension": dimension,
            "value": value,
            "set": True,
        }

    def check_red_line(
        self,
        dimension: str,
        current_value: float,
    ) -> dict[str, Any]:
        """Kırmızı çizgi kontrolü yapar.

        Args:
            dimension: Boyut.
            current_value: Mevcut değer.

        Returns:
            Kontrol bilgisi.
        """
        if dimension not in self._red_lines:
            return {
                "dimension": dimension,
                "violated": False,
                "has_red_line": False,
            }

        red_line = self._red_lines[
            dimension
        ]
        violated = current_value < red_line
        proximity = round(
            abs(current_value - red_line), 2,
        )
        warning = (
            proximity
            < abs(red_line) * 0.1
        )

        return {
            "dimension": dimension,
            "red_line": red_line,
            "current": current_value,
            "violated": violated,
            "proximity": proximity,
            "warning": warning or violated,
            "has_red_line": True,
        }

    @property
    def concession_count(self) -> int:
        """Taviz sayısı."""
        return self._stats[
            "concessions_tracked"
        ]

    @property
    def red_line_count(self) -> int:
        """Kırmızı çizgi sayısı."""
        return self._stats[
            "red_lines_set"
        ]
