"""ATLAS Dolandırıcılık Örüntüsü Eşleştirici.

Bilinen kalıplar, kural eşleştirme,
imza tespiti, bulanık eşleştirme,
kalıp kütüphanesi.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class FraudPatternMatcher:
    """Dolandırıcılık örüntüsü eşleştirici.

    Bilinen dolandırıcılık kalıplarını eşler.

    Attributes:
        _patterns: Kalıp kütüphanesi.
        _rules: Kural kayıtları.
    """

    def __init__(self) -> None:
        """Eşleştiriciyi başlatır."""
        self._patterns: dict[
            str, dict[str, Any]
        ] = {}
        self._rules: dict[
            str, dict[str, Any]
        ] = {}
        self._matches: list[
            dict[str, Any]
        ] = []
        self._counter = 0
        self._stats = {
            "patterns_registered": 0,
            "matches_found": 0,
        }

        logger.info(
            "FraudPatternMatcher "
            "baslatildi",
        )

    def register_pattern(
        self,
        name: str,
        indicators: list[str]
        | None = None,
        severity: str = "medium",
        description: str = "",
    ) -> dict[str, Any]:
        """Kalıp kaydeder.

        Args:
            name: Kalıp adı.
            indicators: Göstergeler.
            severity: Ciddiyet.
            description: Açıklama.

        Returns:
            Kayıt bilgisi.
        """
        self._counter += 1
        pid = f"pat_{self._counter}"
        indicators = indicators or []

        self._patterns[name] = {
            "pattern_id": pid,
            "name": name,
            "indicators": indicators,
            "severity": severity,
            "description": description,
        }
        self._stats[
            "patterns_registered"
        ] += 1

        return {
            "pattern_id": pid,
            "name": name,
            "indicators": len(indicators),
            "registered": True,
        }

    def match_known_pattern(
        self,
        signals: list[str]
        | None = None,
    ) -> dict[str, Any]:
        """Bilinen kalıp eşler.

        Args:
            signals: Sinyaller.

        Returns:
            Eşleşme bilgisi.
        """
        signals = signals or []
        signal_set = set(
            s.lower() for s in signals
        )
        matches = []

        for name, pat in (
            self._patterns.items()
        ):
            indicators = set(
                i.lower()
                for i in pat["indicators"]
            )
            overlap = (
                signal_set & indicators
            )
            if overlap:
                match_pct = round(
                    len(overlap)
                    / len(indicators) * 100,
                    1,
                )
                matches.append({
                    "pattern": name,
                    "severity": pat[
                        "severity"
                    ],
                    "match_pct": match_pct,
                    "matched_indicators": (
                        list(overlap)
                    ),
                })

        if matches:
            self._stats[
                "matches_found"
            ] += len(matches)

        return {
            "matches": matches,
            "match_count": len(matches),
            "matched": len(matches) > 0,
        }

    def add_rule(
        self,
        name: str,
        condition: str = "",
        threshold: float = 0.0,
        action: str = "alert",
    ) -> dict[str, Any]:
        """Kural ekler.

        Args:
            name: Kural adı.
            condition: Koşul.
            threshold: Eşik.
            action: Eylem.

        Returns:
            Kural bilgisi.
        """
        self._counter += 1
        rid = f"rule_{self._counter}"

        self._rules[name] = {
            "rule_id": rid,
            "name": name,
            "condition": condition,
            "threshold": threshold,
            "action": action,
        }

        return {
            "rule_id": rid,
            "name": name,
            "added": True,
        }

    def match_rules(
        self,
        data: dict[str, float]
        | None = None,
    ) -> dict[str, Any]:
        """Kural eşleştirme yapar.

        Args:
            data: Veri.

        Returns:
            Eşleşme bilgisi.
        """
        data = data or {}
        triggered = []

        for name, rule in (
            self._rules.items()
        ):
            cond = rule["condition"]
            if cond in data:
                if (
                    data[cond]
                    > rule["threshold"]
                ):
                    triggered.append({
                        "rule": name,
                        "value": data[cond],
                        "threshold": rule[
                            "threshold"
                        ],
                        "action": rule[
                            "action"
                        ],
                    })

        return {
            "triggered": triggered,
            "trigger_count": len(triggered),
            "matched": len(triggered) > 0,
        }

    def detect_signature(
        self,
        event_sequence: list[str]
        | None = None,
    ) -> dict[str, Any]:
        """İmza tespiti yapar.

        Args:
            event_sequence: Olay dizisi.

        Returns:
            Tespit bilgisi.
        """
        event_sequence = (
            event_sequence or []
        )
        detected = []

        for name, pat in (
            self._patterns.items()
        ):
            indicators = pat["indicators"]
            if not indicators:
                continue
            # Sıralı alt dizi kontrolü
            idx = 0
            for event in event_sequence:
                if (
                    idx < len(indicators)
                    and event.lower()
                    == indicators[
                        idx
                    ].lower()
                ):
                    idx += 1
            if idx == len(indicators):
                detected.append({
                    "pattern": name,
                    "severity": pat[
                        "severity"
                    ],
                })

        return {
            "detected": detected,
            "detection_count": len(
                detected,
            ),
            "found": len(detected) > 0,
        }

    def fuzzy_match(
        self,
        text: str,
        min_similarity: float = 0.5,
    ) -> dict[str, Any]:
        """Bulanık eşleştirme yapar.

        Args:
            text: Metin.
            min_similarity: Min benzerlik.

        Returns:
            Eşleşme bilgisi.
        """
        text_words = set(
            text.lower().split()
        )
        matches = []

        for name, pat in (
            self._patterns.items()
        ):
            pat_words = set(
                w.lower()
                for ind in pat["indicators"]
                for w in ind.split()
            )
            if not pat_words:
                continue

            common = text_words & pat_words
            similarity = (
                len(common) / len(pat_words)
            )

            if similarity >= min_similarity:
                matches.append({
                    "pattern": name,
                    "similarity": round(
                        similarity, 2,
                    ),
                    "common_words": list(
                        common,
                    ),
                })

        return {
            "matches": matches,
            "match_count": len(matches),
            "matched": len(matches) > 0,
        }

    @property
    def pattern_count(self) -> int:
        """Kalıp sayısı."""
        return self._stats[
            "patterns_registered"
        ]

    @property
    def match_count(self) -> int:
        """Eşleşme sayısı."""
        return self._stats[
            "matches_found"
        ]
