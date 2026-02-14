"""ATLAS Oruntu Madencisi modulu.

Basari oruntu cikarma, basarisizlik
desen tespiti, korelasyon kesfetme,
trend belirleme ve kumeleme analizi.
"""

import logging
from collections import Counter
from typing import Any

from app.models.adaptive import (
    ExperienceRecord,
    OutcomeType,
    PatternRecord,
    PatternType,
)

logger = logging.getLogger(__name__)


class PatternMiner:
    """Oruntu madencisi.

    Deneyimlerden oruntuler cikarir
    ve anlamli iliskiler kesfeder.

    Attributes:
        _patterns: Kesfedilen oruntuler.
        _min_support: Min destek sayisi.
        _min_confidence: Min guven esigi.
    """

    def __init__(
        self,
        min_support: int = 3,
        min_confidence: float = 0.6,
    ) -> None:
        """Oruntu madencisini baslatir.

        Args:
            min_support: Min destek sayisi.
            min_confidence: Min guven esigi.
        """
        self._patterns: list[PatternRecord] = []
        self._min_support = max(1, min_support)
        self._min_confidence = max(0.0, min(1.0, min_confidence))

        logger.info(
            "PatternMiner baslatildi "
            "(support=%d, confidence=%.2f)",
            self._min_support, self._min_confidence,
        )

    def mine_success_patterns(
        self,
        experiences: list[ExperienceRecord],
    ) -> list[PatternRecord]:
        """Basari oruntuleri cikarir.

        Args:
            experiences: Deneyim listesi.

        Returns:
            Kesfedilen oruntuler.
        """
        successes = [
            e for e in experiences
            if e.outcome == OutcomeType.SUCCESS
        ]
        return self._extract_patterns(
            successes, PatternType.SUCCESS,
        )

    def mine_failure_patterns(
        self,
        experiences: list[ExperienceRecord],
    ) -> list[PatternRecord]:
        """Basarisizlik oruntuleri cikarir.

        Args:
            experiences: Deneyim listesi.

        Returns:
            Kesfedilen oruntuler.
        """
        failures = [
            e for e in experiences
            if e.outcome == OutcomeType.FAILURE
        ]
        return self._extract_patterns(
            failures, PatternType.FAILURE,
        )

    def discover_correlations(
        self,
        experiences: list[ExperienceRecord],
    ) -> list[PatternRecord]:
        """Korelasyonlari kesfeder.

        Args:
            experiences: Deneyim listesi.

        Returns:
            Korelasyon oruntuleri.
        """
        patterns: list[PatternRecord] = []
        if len(experiences) < self._min_support:
            return patterns

        # Tag-outcome korelasyonu
        tag_outcomes: dict[str, list[str]] = {}
        for exp in experiences:
            for tag in exp.tags:
                if tag not in tag_outcomes:
                    tag_outcomes[tag] = []
                tag_outcomes[tag].append(exp.outcome.value)

        for tag, outcomes in tag_outcomes.items():
            if len(outcomes) < self._min_support:
                continue

            counter = Counter(outcomes)
            total = len(outcomes)
            for outcome, count in counter.items():
                confidence = count / total
                if confidence >= self._min_confidence:
                    pattern = PatternRecord(
                        pattern_type=PatternType.CORRELATION,
                        description=(
                            f"tag:{tag} -> {outcome} "
                            f"({confidence:.0%})"
                        ),
                        confidence=confidence,
                        support=count,
                        features={
                            "tag": tag,
                            "outcome": outcome,
                            "total": total,
                        },
                    )
                    patterns.append(pattern)
                    self._patterns.append(pattern)

        return patterns

    def identify_trends(
        self,
        experiences: list[ExperienceRecord],
        window: int = 10,
    ) -> list[PatternRecord]:
        """Trendleri belirler.

        Args:
            experiences: Deneyim listesi.
            window: Pencere boyutu.

        Returns:
            Trend oruntuleri.
        """
        patterns: list[PatternRecord] = []
        if len(experiences) < window * 2:
            return patterns

        # Odul trendini kontrol et
        early = experiences[:window]
        recent = experiences[-window:]

        early_avg = (
            sum(e.reward for e in early) / len(early)
        )
        recent_avg = (
            sum(e.reward for e in recent) / len(recent)
        )

        diff = recent_avg - early_avg
        if abs(diff) > 0.1:
            direction = "improving" if diff > 0 else "declining"
            pattern = PatternRecord(
                pattern_type=PatternType.TREND,
                description=(
                    f"Performans trendi: {direction} "
                    f"({early_avg:.2f} -> {recent_avg:.2f})"
                ),
                confidence=min(1.0, abs(diff)),
                support=len(experiences),
                features={
                    "direction": direction,
                    "early_avg": early_avg,
                    "recent_avg": recent_avg,
                    "diff": diff,
                },
            )
            patterns.append(pattern)
            self._patterns.append(pattern)

        return patterns

    def cluster_experiences(
        self,
        experiences: list[ExperienceRecord],
    ) -> list[PatternRecord]:
        """Deneyimleri kumeler.

        Args:
            experiences: Deneyim listesi.

        Returns:
            Kume oruntuleri.
        """
        patterns: list[PatternRecord] = []
        if not experiences:
            return patterns

        # Aksiyon bazli kumeleme
        clusters: dict[str, list[ExperienceRecord]] = {}
        for exp in experiences:
            key = exp.action
            if key not in clusters:
                clusters[key] = []
            clusters[key].append(exp)

        for action, cluster in clusters.items():
            if len(cluster) < self._min_support:
                continue

            avg_reward = (
                sum(e.reward for e in cluster) / len(cluster)
            )
            success_rate = sum(
                1 for e in cluster
                if e.outcome == OutcomeType.SUCCESS
            ) / len(cluster)

            pattern = PatternRecord(
                pattern_type=PatternType.CLUSTER,
                description=(
                    f"Kume: {action} "
                    f"(n={len(cluster)}, "
                    f"basari={success_rate:.0%})"
                ),
                confidence=success_rate,
                support=len(cluster),
                features={
                    "action": action,
                    "avg_reward": avg_reward,
                    "success_rate": success_rate,
                    "count": len(cluster),
                },
            )
            patterns.append(pattern)
            self._patterns.append(pattern)

        return patterns

    def _extract_patterns(
        self,
        experiences: list[ExperienceRecord],
        pattern_type: PatternType,
    ) -> list[PatternRecord]:
        """Oruntuleri cikarir.

        Args:
            experiences: Deneyim listesi.
            pattern_type: Oruntu turu.

        Returns:
            Oruntuler.
        """
        patterns: list[PatternRecord] = []
        if not experiences:
            return patterns

        # Aksiyon frekansi
        action_counts = Counter(e.action for e in experiences)

        for action, count in action_counts.items():
            if count < self._min_support:
                continue

            related = [
                e for e in experiences if e.action == action
            ]
            avg_reward = (
                sum(e.reward for e in related) / len(related)
            )
            tags = Counter(
                t for e in related for t in e.tags
            )
            top_tags = [
                t for t, _ in tags.most_common(3)
            ]

            confidence = count / len(experiences)
            pattern = PatternRecord(
                pattern_type=pattern_type,
                description=(
                    f"{pattern_type.value}: {action} "
                    f"(n={count}, reward={avg_reward:.2f})"
                ),
                confidence=confidence,
                support=count,
                features={
                    "action": action,
                    "avg_reward": avg_reward,
                    "top_tags": top_tags,
                },
            )
            patterns.append(pattern)
            self._patterns.append(pattern)

        return patterns

    def get_patterns(
        self,
        pattern_type: PatternType | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Oruntuleri getirir.

        Args:
            pattern_type: Tur filtresi.
            limit: Maks kayit.

        Returns:
            Oruntu listesi.
        """
        patterns = self._patterns
        if pattern_type:
            patterns = [
                p for p in patterns
                if p.pattern_type == pattern_type
            ]
        return [
            {
                "pattern_id": p.pattern_id,
                "type": p.pattern_type.value,
                "description": p.description,
                "confidence": p.confidence,
                "support": p.support,
            }
            for p in patterns[-limit:]
        ]

    @property
    def pattern_count(self) -> int:
        """Oruntu sayisi."""
        return len(self._patterns)
