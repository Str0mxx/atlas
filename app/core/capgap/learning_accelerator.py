"""ATLAS Ogrenme Hizlandirici modulu.

Hizli yetenek edinimi, transfer ogrenme,
kalip yeniden kullanimi, kisayol tespiti, verimlilik.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class LearningAccelerator:
    """Ogrenme hizlandirici.

    Yetenek edinimini hizlandirir.

    Attributes:
        _patterns: Ogrenilmis kalipler.
        _shortcuts: Bulunan kisayollar.
    """

    def __init__(self) -> None:
        """Ogrenme hizlandiriciyi baslatir."""
        self._patterns: dict[
            str, dict[str, Any]
        ] = {}
        self._shortcuts: dict[
            str, dict[str, Any]
        ] = {}
        self._transfers: list[
            dict[str, Any]
        ] = []
        self._stats = {
            "patterns_learned": 0,
            "shortcuts_found": 0,
            "transfers": 0,
        }

        logger.info(
            "LearningAccelerator baslatildi",
        )

    def learn_pattern(
        self,
        pattern_name: str,
        capability: str,
        steps: list[str],
        success_rate: float = 1.0,
    ) -> dict[str, Any]:
        """Kalip ogrenir.

        Args:
            pattern_name: Kalip adi.
            capability: Ilgili yetenek.
            steps: Adimlar.
            success_rate: Basari orani.

        Returns:
            Ogrenme bilgisi.
        """
        self._patterns[pattern_name] = {
            "name": pattern_name,
            "capability": capability,
            "steps": steps,
            "success_rate": success_rate,
            "usage_count": 0,
            "learned_at": time.time(),
        }
        self._stats["patterns_learned"] += 1

        return {
            "pattern": pattern_name,
            "learned": True,
            "steps": len(steps),
        }

    def find_similar_pattern(
        self,
        capability: str,
    ) -> dict[str, Any] | None:
        """Benzer kalip bulur.

        Args:
            capability: Yetenek adi.

        Returns:
            Benzer kalip veya None.
        """
        cap_lower = capability.lower()

        best_match = None
        best_score = 0.0

        for name, pattern in (
            self._patterns.items()
        ):
            pat_cap = pattern[
                "capability"
            ].lower()

            # Kelime eslesmesi
            cap_words = set(
                cap_lower.split("_"),
            )
            pat_words = set(
                pat_cap.split("_"),
            )
            common = cap_words & pat_words
            total = cap_words | pat_words

            if total:
                score = (
                    len(common) / len(total)
                )
            else:
                score = 0.0

            if score > best_score:
                best_score = score
                best_match = pattern

        if best_match and best_score > 0.2:
            return {
                "pattern": best_match["name"],
                "similarity": round(
                    best_score, 2,
                ),
                "steps": best_match["steps"],
                "success_rate": best_match[
                    "success_rate"
                ],
            }

        return None

    def transfer_learning(
        self,
        source_capability: str,
        target_capability: str,
    ) -> dict[str, Any]:
        """Transfer ogrenme uygular.

        Args:
            source_capability: Kaynak yetenek.
            target_capability: Hedef yetenek.

        Returns:
            Transfer bilgisi.
        """
        # Kaynak kaliplari bul
        source_patterns = [
            p for p in self._patterns.values()
            if p["capability"]
            == source_capability
        ]

        if not source_patterns:
            return {
                "transfer": False,
                "reason": "no_source_patterns",
            }

        transferred_steps = []
        for pattern in source_patterns:
            for step in pattern["steps"]:
                adapted = step.replace(
                    source_capability,
                    target_capability,
                )
                transferred_steps.append(
                    adapted,
                )

        transfer = {
            "source": source_capability,
            "target": target_capability,
            "steps_transferred": len(
                transferred_steps,
            ),
            "adapted_steps": (
                transferred_steps
            ),
            "estimated_speedup": round(
                min(
                    len(source_patterns) * 0.3,
                    0.8,
                ),
                2,
            ),
            "transferred_at": time.time(),
        }

        self._transfers.append(transfer)
        self._stats["transfers"] += 1

        return {
            "transfer": True,
            **transfer,
        }

    def reuse_pattern(
        self,
        pattern_name: str,
        target_capability: str,
    ) -> dict[str, Any]:
        """Kalip yeniden kullanir.

        Args:
            pattern_name: Kalip adi.
            target_capability: Hedef yetenek.

        Returns:
            Yeniden kullanim bilgisi.
        """
        pattern = self._patterns.get(
            pattern_name,
        )
        if not pattern:
            return {
                "error": "pattern_not_found",
            }

        pattern["usage_count"] += 1

        adapted_steps = []
        for step in pattern["steps"]:
            adapted = step.replace(
                pattern["capability"],
                target_capability,
            )
            adapted_steps.append(adapted)

        return {
            "pattern": pattern_name,
            "reused": True,
            "adapted_steps": adapted_steps,
            "usage_count": pattern[
                "usage_count"
            ],
        }

    def detect_shortcut(
        self,
        capability: str,
        current_steps: list[str],
    ) -> dict[str, Any]:
        """Kisayol tespit eder.

        Args:
            capability: Yetenek adi.
            current_steps: Mevcut adimlar.

        Returns:
            Kisayol bilgisi.
        """
        shortcuts = []

        # Benzer kaliplardan kisayol bul
        similar = self.find_similar_pattern(
            capability,
        )
        if similar:
            sim_steps = similar["steps"]
            if len(sim_steps) < len(
                current_steps,
            ):
                shortcuts.append({
                    "type": "pattern_reuse",
                    "source": similar[
                        "pattern"
                    ],
                    "savings": (
                        len(current_steps)
                        - len(sim_steps)
                    ),
                    "steps": sim_steps,
                })

        # Tekrar eden adim tespiti
        seen = set()
        duplicates = []
        for step in current_steps:
            if step in seen:
                duplicates.append(step)
            seen.add(step)

        if duplicates:
            shortcuts.append({
                "type": "duplicate_removal",
                "duplicates": duplicates,
                "savings": len(duplicates),
            })

        if shortcuts:
            self._shortcuts[capability] = {
                "shortcuts": shortcuts,
                "found_at": time.time(),
            }
            self._stats[
                "shortcuts_found"
            ] += len(shortcuts)

        return {
            "capability": capability,
            "shortcuts": shortcuts,
            "count": len(shortcuts),
            "total_savings": sum(
                s.get("savings", 0)
                for s in shortcuts
            ),
        }

    def get_efficiency_report(
        self,
    ) -> dict[str, Any]:
        """Verimlilik raporu.

        Returns:
            Verimlilik bilgisi.
        """
        total_usage = sum(
            p["usage_count"]
            for p in self._patterns.values()
        )
        avg_success = 0.0
        if self._patterns:
            avg_success = sum(
                p["success_rate"]
                for p in self._patterns.values()
            ) / len(self._patterns)

        return {
            "patterns_learned": (
                self._stats["patterns_learned"]
            ),
            "shortcuts_found": (
                self._stats["shortcuts_found"]
            ),
            "transfers": (
                self._stats["transfers"]
            ),
            "total_pattern_usage": total_usage,
            "avg_success_rate": round(
                avg_success, 2,
            ),
        }

    @property
    def pattern_count(self) -> int:
        """Kalip sayisi."""
        return len(self._patterns)

    @property
    def transfer_count(self) -> int:
        """Transfer sayisi."""
        return self._stats["transfers"]
