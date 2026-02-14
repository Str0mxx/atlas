"""ATLAS Bilgi Damitici modulu.

Genelleme cikarma, orneklerden kural
olusturma, hipotez dogrulama, bilgi
rafine etme ve eski bilgi budama.
"""

import logging
from collections import Counter
from typing import Any

from app.models.adaptive import (
    ExperienceRecord,
    KnowledgeRule,
    OutcomeType,
)

logger = logging.getLogger(__name__)


class KnowledgeDistiller:
    """Bilgi damitici.

    Deneyimlerden genel kurallar cikarir,
    dogrular ve surekli rafine eder.

    Attributes:
        _rules: Bilgi kurallari.
        _hypotheses: Test edilen hipotezler.
        _min_evidence: Min kanit sayisi.
    """

    def __init__(
        self,
        min_evidence: int = 3,
    ) -> None:
        """Bilgi damiticiyi baslatir.

        Args:
            min_evidence: Min kanit sayisi.
        """
        self._rules: dict[str, KnowledgeRule] = {}
        self._hypotheses: list[dict[str, Any]] = []
        self._min_evidence = max(1, min_evidence)
        self._pruned_count = 0

        logger.info(
            "KnowledgeDistiller baslatildi (min_evidence=%d)",
            self._min_evidence,
        )

    def extract_generalizations(
        self,
        experiences: list[ExperienceRecord],
    ) -> list[KnowledgeRule]:
        """Genellemeler cikarir.

        Args:
            experiences: Deneyim listesi.

        Returns:
            Olusturulan kurallar.
        """
        rules: list[KnowledgeRule] = []
        if not experiences:
            return rules

        # Aksiyon-sonuc iliskilerini topla
        action_outcomes: dict[str, list[OutcomeType]] = {}
        for exp in experiences:
            if exp.action not in action_outcomes:
                action_outcomes[exp.action] = []
            action_outcomes[exp.action].append(exp.outcome)

        for action, outcomes in action_outcomes.items():
            if len(outcomes) < self._min_evidence:
                continue

            counter = Counter(o.value for o in outcomes)
            total = len(outcomes)
            dominant = counter.most_common(1)[0]
            confidence = dominant[1] / total

            if confidence >= 0.6:
                rule = KnowledgeRule(
                    condition=f"action={action}",
                    action=f"expect_{dominant[0]}",
                    confidence=confidence,
                    usage_count=total,
                )
                self._rules[rule.rule_id] = rule
                rules.append(rule)

        return rules

    def create_rule(
        self,
        condition: str,
        action: str,
        confidence: float = 0.5,
    ) -> KnowledgeRule:
        """Kural olusturur.

        Args:
            condition: Kosul.
            action: Aksiyon.
            confidence: Guven degeri.

        Returns:
            Olusturulan kural.
        """
        rule = KnowledgeRule(
            condition=condition,
            action=action,
            confidence=max(0.0, min(1.0, confidence)),
        )
        self._rules[rule.rule_id] = rule
        return rule

    def validate_hypothesis(
        self,
        hypothesis: str,
        evidence_for: int,
        evidence_against: int,
    ) -> dict[str, Any]:
        """Hipotez dogrular.

        Args:
            hypothesis: Hipotez ifadesi.
            evidence_for: Destekleyen kanit.
            evidence_against: Karsi kanit.

        Returns:
            Dogrulama sonucu.
        """
        total = evidence_for + evidence_against
        if total == 0:
            result = {
                "hypothesis": hypothesis,
                "supported": False,
                "confidence": 0.0,
                "verdict": "insufficient_evidence",
            }
            self._hypotheses.append(result)
            return result

        confidence = evidence_for / total
        sufficient = total >= self._min_evidence
        supported = confidence >= 0.6 and sufficient

        verdict = "supported" if supported else "rejected"
        if not sufficient:
            verdict = "insufficient_evidence"

        result = {
            "hypothesis": hypothesis,
            "supported": supported,
            "confidence": confidence,
            "evidence_for": evidence_for,
            "evidence_against": evidence_against,
            "verdict": verdict,
        }
        self._hypotheses.append(result)

        # Desteklenen hipotezi kurala cevir
        if supported:
            self.create_rule(
                condition=hypothesis,
                action="validated_hypothesis",
                confidence=confidence,
            )

        return result

    def refine_rule(
        self,
        rule_id: str,
        new_confidence: float,
        additional_evidence: int = 1,
    ) -> bool:
        """Kurali rafine eder.

        Args:
            rule_id: Kural ID.
            new_confidence: Yeni guven degeri.
            additional_evidence: Ek kanit sayisi.

        Returns:
            Basarili ise True.
        """
        rule = self._rules.get(rule_id)
        if not rule:
            return False

        # Agirlikli ortalama
        old_weight = rule.usage_count
        new_weight = additional_evidence
        total_weight = old_weight + new_weight

        rule.confidence = (
            rule.confidence * old_weight
            + new_confidence * new_weight
        ) / total_weight
        rule.usage_count = total_weight
        return True

    def prune_outdated(
        self,
        min_confidence: float = 0.3,
        min_usage: int = 0,
    ) -> int:
        """Eski/zayif kurallari budar.

        Args:
            min_confidence: Min guven esigi.
            min_usage: Min kullanim sayisi.

        Returns:
            Budanan kural sayisi.
        """
        to_prune = [
            rid for rid, rule in self._rules.items()
            if rule.confidence < min_confidence
            or (min_usage > 0 and rule.usage_count < min_usage)
        ]
        for rid in to_prune:
            self._rules[rid].valid = False
            del self._rules[rid]

        self._pruned_count += len(to_prune)
        return len(to_prune)

    def invalidate_rule(
        self,
        rule_id: str,
    ) -> bool:
        """Kurali gecersiz kilar.

        Args:
            rule_id: Kural ID.

        Returns:
            Basarili ise True.
        """
        rule = self._rules.get(rule_id)
        if not rule:
            return False
        rule.valid = False
        del self._rules[rule_id]
        return True

    def get_rules(
        self,
        min_confidence: float = 0.0,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Kurallari getirir.

        Args:
            min_confidence: Min guven filtresi.
            limit: Maks kayit.

        Returns:
            Kural listesi.
        """
        rules = [
            r for r in self._rules.values()
            if r.confidence >= min_confidence and r.valid
        ]
        rules.sort(key=lambda r: r.confidence, reverse=True)
        return [
            {
                "rule_id": r.rule_id,
                "condition": r.condition,
                "action": r.action,
                "confidence": r.confidence,
                "usage_count": r.usage_count,
            }
            for r in rules[:limit]
        ]

    def get_rule(
        self,
        rule_id: str,
    ) -> dict[str, Any] | None:
        """Kural bilgisi getirir.

        Args:
            rule_id: Kural ID.

        Returns:
            Kural bilgisi veya None.
        """
        r = self._rules.get(rule_id)
        if not r:
            return None
        return {
            "rule_id": r.rule_id,
            "condition": r.condition,
            "action": r.action,
            "confidence": r.confidence,
            "usage_count": r.usage_count,
            "valid": r.valid,
        }

    @property
    def rule_count(self) -> int:
        """Gecerli kural sayisi."""
        return len(self._rules)

    @property
    def hypothesis_count(self) -> int:
        """Hipotez sayisi."""
        return len(self._hypotheses)

    @property
    def pruned_count(self) -> int:
        """Budanan kural sayisi."""
        return self._pruned_count
