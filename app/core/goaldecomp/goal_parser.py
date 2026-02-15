"""ATLAS Hedef Ayristirici modulu.

Dogal dil parse, niyet cikarimi,
basari kriterleri, kisit tespiti, belirsizlik cozumu.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class GoalParser:
    """Hedef ayristirici.

    Dogal dil hedeflerini yapisal forma donusturur.

    Attributes:
        _parsed: Parse edilmis hedefler.
        _stats: Istatistikler.
    """

    def __init__(self) -> None:
        """Hedef ayristiriciyi baslatir."""
        self._parsed: dict[
            str, dict[str, Any]
        ] = {}
        self._intent_keywords: dict[
            str, list[str]
        ] = {
            "create": [
                "create", "build", "make",
                "develop", "generate", "add",
            ],
            "improve": [
                "improve", "optimize", "enhance",
                "upgrade", "boost", "increase",
            ],
            "fix": [
                "fix", "repair", "resolve",
                "debug", "patch", "correct",
            ],
            "analyze": [
                "analyze", "investigate",
                "examine", "study", "research",
            ],
            "monitor": [
                "monitor", "track", "watch",
                "observe", "check",
            ],
            "deploy": [
                "deploy", "release", "launch",
                "publish", "ship",
            ],
        }
        self._stats = {
            "parsed": 0,
        }

        logger.info("GoalParser baslatildi")

    def parse_goal(
        self,
        goal_id: str,
        description: str,
    ) -> dict[str, Any]:
        """Hedefi parse eder.

        Args:
            goal_id: Hedef ID.
            description: Hedef aciklamasi.

        Returns:
            Parse sonucu.
        """
        words = description.lower().split()

        # Niyet cikarimi
        intent = self._extract_intent(words)

        # Basari kriterleri
        criteria = self._extract_criteria(
            description,
        )

        # Kisitlar
        constraints = (
            self._identify_constraints(
                description,
            )
        )

        # Belirsizlik tespiti
        ambiguities = (
            self._detect_ambiguities(
                description,
            )
        )

        parsed = {
            "goal_id": goal_id,
            "description": description,
            "intent": intent,
            "success_criteria": criteria,
            "constraints": constraints,
            "ambiguities": ambiguities,
            "word_count": len(words),
            "is_clear": len(ambiguities) == 0,
            "parsed_at": time.time(),
        }

        self._parsed[goal_id] = parsed
        self._stats["parsed"] += 1

        return parsed

    def _extract_intent(
        self,
        words: list[str],
    ) -> str:
        """Niyet cikarir.

        Args:
            words: Kelime listesi.

        Returns:
            Tespit edilen niyet.
        """
        for intent, keywords in (
            self._intent_keywords.items()
        ):
            for kw in keywords:
                if kw in words:
                    return intent
        return "general"

    def _extract_criteria(
        self,
        description: str,
    ) -> list[str]:
        """Basari kriterleri cikarir.

        Args:
            description: Hedef aciklamasi.

        Returns:
            Kriter listesi.
        """
        criteria = []
        lower = description.lower()

        # Sayisal hedefler
        criteria_indicators = [
            "must", "should", "need",
            "require", "ensure", "achieve",
            "reach", "maintain",
        ]
        for indicator in criteria_indicators:
            if indicator in lower:
                criteria.append(
                    f"{indicator}_based_criterion",
                )
                break

        # Varsayilan kriter
        if not criteria:
            criteria.append(
                "task_completion",
            )

        return criteria

    def _identify_constraints(
        self,
        description: str,
    ) -> list[str]:
        """Kisitlari tespit eder.

        Args:
            description: Hedef aciklamasi.

        Returns:
            Kisit listesi.
        """
        constraints = []
        lower = description.lower()

        constraint_patterns = {
            "time": [
                "deadline", "by", "before",
                "within", "hours", "days",
            ],
            "budget": [
                "budget", "cost", "spend",
                "price", "cheap",
            ],
            "quality": [
                "quality", "reliable",
                "stable", "secure", "safe",
            ],
            "scope": [
                "only", "limited", "specific",
                "exclude", "without",
            ],
        }

        for ctype, patterns in (
            constraint_patterns.items()
        ):
            for p in patterns:
                if p in lower:
                    constraints.append(ctype)
                    break

        return constraints

    def _detect_ambiguities(
        self,
        description: str,
    ) -> list[str]:
        """Belirsizlikleri tespit eder.

        Args:
            description: Hedef aciklamasi.

        Returns:
            Belirsizlik listesi.
        """
        ambiguities = []
        lower = description.lower()

        # Cok kisa hedef
        if len(description.split()) < 3:
            ambiguities.append(
                "too_brief",
            )

        # Belirsiz kelimeler
        vague_words = [
            "somehow", "maybe", "probably",
            "something", "stuff", "things",
            "etc", "whatever",
        ]
        for vw in vague_words:
            if vw in lower:
                ambiguities.append(
                    f"vague_term:{vw}",
                )

        return ambiguities

    def resolve_ambiguity(
        self,
        goal_id: str,
        clarifications: dict[str, str],
    ) -> dict[str, Any]:
        """Belirsizlik cozer.

        Args:
            goal_id: Hedef ID.
            clarifications: Aciklamalar.

        Returns:
            Cozum bilgisi.
        """
        parsed = self._parsed.get(goal_id)
        if not parsed:
            return {
                "error": "goal_not_found",
            }

        # Cozulen belirsizlikleri kaldir
        remaining = [
            a for a in parsed["ambiguities"]
            if a not in clarifications
        ]
        parsed["ambiguities"] = remaining
        parsed["is_clear"] = (
            len(remaining) == 0
        )
        parsed["clarifications"] = (
            clarifications
        )

        return {
            "goal_id": goal_id,
            "resolved": len(clarifications),
            "remaining": len(remaining),
            "is_clear": parsed["is_clear"],
        }

    def get_parsed(
        self,
        goal_id: str,
    ) -> dict[str, Any]:
        """Parse sonucu getirir.

        Args:
            goal_id: Hedef ID.

        Returns:
            Parse bilgisi.
        """
        p = self._parsed.get(goal_id)
        if not p:
            return {
                "error": "goal_not_found",
            }
        return dict(p)

    @property
    def parse_count(self) -> int:
        """Parse sayisi."""
        return self._stats["parsed"]
