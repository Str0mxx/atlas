"""ATLAS Karar Entegratouru modulu.

Tum karar sistemlerini birlestirir:
BDI + Olasiliksal + RL + Duygusal.
Catisma cozumu, sentez ve aciklama.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from app.models.unified import DecisionSource, IntegratedDecision

logger = logging.getLogger(__name__)

_SOURCE_WEIGHTS: dict[DecisionSource, float] = {
    DecisionSource.BDI: 0.25,
    DecisionSource.PROBABILISTIC: 0.20,
    DecisionSource.REINFORCEMENT: 0.20,
    DecisionSource.EMOTIONAL: 0.10,
    DecisionSource.RULE_BASED: 0.15,
    DecisionSource.CONSENSUS: 0.10,
}


class DecisionIntegrator:
    """Karar entegratouru.

    Farkli karar kaynaklarindan gelen
    onerileri birlestirir ve sentezler.

    Attributes:
        _decisions: Entegre kararlar.
        _source_weights: Kaynak agirliklari.
        _proposals: Karar onerileri.
        _conflicts: Catisma kayitlari.
    """

    def __init__(self) -> None:
        """Karar entegratorunu baslatir."""
        self._decisions: dict[str, IntegratedDecision] = {}
        self._source_weights = dict(_SOURCE_WEIGHTS)
        self._proposals: dict[str, list[dict[str, Any]]] = {}
        self._conflicts: list[dict[str, Any]] = []

        logger.info("DecisionIntegrator baslatildi")

    def add_proposal(
        self,
        question: str,
        source: DecisionSource,
        action: str,
        confidence: float = 0.5,
        reasoning: str = "",
    ) -> str:
        """Karar onerisi ekler.

        Args:
            question: Soru/karar noktasi.
            source: Kaynak sistem.
            action: Onerilen aksiyon.
            confidence: Guven (0-1).
            reasoning: Gerekce.

        Returns:
            Soru ID.
        """
        proposal = {
            "source": source.value,
            "action": action,
            "confidence": max(0.0, min(1.0, confidence)),
            "reasoning": reasoning,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._proposals.setdefault(question, []).append(proposal)

        return question

    def synthesize(
        self,
        question: str,
    ) -> IntegratedDecision | None:
        """Karar sentezi yapar.

        Args:
            question: Soru/karar noktasi.

        Returns:
            IntegratedDecision veya None.
        """
        proposals = self._proposals.get(question)
        if not proposals:
            return None

        # Her onerinin agirlikli puanini hesapla
        scored: dict[str, float] = {}
        sources_map: dict[str, list[DecisionSource]] = {}

        for p in proposals:
            action = p["action"]
            src = DecisionSource(p["source"])
            weight = self._source_weights.get(src, 0.1)
            score = p["confidence"] * weight

            scored[action] = scored.get(action, 0.0) + score
            sources_map.setdefault(action, []).append(src)

        # En iyi aksiyonu sec
        best_action = max(scored, key=scored.get)  # type: ignore[arg-type]
        alternatives = [a for a in scored if a != best_action]

        # Catisma tespiti
        if len(scored) > 1:
            values = list(scored.values())
            top_two = sorted(values, reverse=True)[:2]
            if len(top_two) == 2 and top_two[0] - top_two[1] < 0.05:
                self._conflicts.append({
                    "question": question,
                    "options": dict(scored),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })

        # Toplam guven
        total_weight = sum(
            self._source_weights.get(DecisionSource(p["source"]), 0.1)
            for p in proposals
        )
        overall_confidence = round(
            scored[best_action] / max(total_weight, 0.01), 3,
        )
        overall_confidence = min(1.0, overall_confidence)

        # Aciklama olustur
        explanation = self._generate_explanation(
            question, best_action, proposals, scored,
        )

        decision = IntegratedDecision(
            question=question,
            chosen_action=best_action,
            sources=sources_map.get(best_action, []),
            confidence=overall_confidence,
            reasoning=proposals[0].get("reasoning", ""),
            alternatives=alternatives,
            explanation=explanation,
        )
        self._decisions[decision.decision_id] = decision

        logger.info(
            "Karar sentezi: %s -> %s (conf=%.2f)",
            question, best_action, overall_confidence,
        )
        return decision

    def resolve_conflict(
        self,
        question: str,
        chosen_action: str,
        reason: str = "",
    ) -> IntegratedDecision | None:
        """Catismayi cozer.

        Args:
            question: Soru.
            chosen_action: Secilen aksiyon.
            reason: Gerekce.

        Returns:
            IntegratedDecision veya None.
        """
        proposals = self._proposals.get(question)
        if not proposals:
            return None

        sources = [
            DecisionSource(p["source"])
            for p in proposals if p["action"] == chosen_action
        ]

        decision = IntegratedDecision(
            question=question,
            chosen_action=chosen_action,
            sources=sources,
            confidence=0.9,
            reasoning=reason,
            explanation=f"Manuel cozum: {reason}",
        )
        self._decisions[decision.decision_id] = decision

        return decision

    def set_source_weight(
        self,
        source: DecisionSource,
        weight: float,
    ) -> None:
        """Kaynak agirligini ayarlar.

        Args:
            source: Kaynak.
            weight: Agirlik (0-1).
        """
        self._source_weights[source] = max(0.0, min(1.0, weight))

    def get_source_weight(
        self,
        source: DecisionSource,
    ) -> float:
        """Kaynak agirligini getirir.

        Args:
            source: Kaynak.

        Returns:
            Agirlik.
        """
        return self._source_weights.get(source, 0.1)

    def _generate_explanation(
        self,
        question: str,
        chosen: str,
        proposals: list[dict[str, Any]],
        scores: dict[str, float],
    ) -> str:
        """Karar aciklamasi olusturur.

        Args:
            question: Soru.
            chosen: Secilen aksiyon.
            proposals: Oneriler.
            scores: Puanlar.

        Returns:
            Aciklama metni.
        """
        supporting = [
            p["source"] for p in proposals if p["action"] == chosen
        ]
        return (
            f"'{chosen}' secildi. "
            f"Destekleyenler: {', '.join(supporting)}. "
            f"Puan: {scores[chosen]:.3f}."
        )

    def get_decision(
        self,
        decision_id: str,
    ) -> IntegratedDecision | None:
        """Karar getirir.

        Args:
            decision_id: Karar ID.

        Returns:
            IntegratedDecision veya None.
        """
        return self._decisions.get(decision_id)

    def get_proposals(
        self,
        question: str,
    ) -> list[dict[str, Any]]:
        """Onerileri getirir.

        Args:
            question: Soru.

        Returns:
            Oneri listesi.
        """
        return list(self._proposals.get(question, []))

    def get_conflicts(self) -> list[dict[str, Any]]:
        """Catismalari getirir.

        Returns:
            Catisma listesi.
        """
        return list(self._conflicts)

    @property
    def total_decisions(self) -> int:
        """Toplam karar sayisi."""
        return len(self._decisions)

    @property
    def total_proposals(self) -> int:
        """Toplam oneri sayisi."""
        return sum(len(v) for v in self._proposals.values())

    @property
    def conflict_count(self) -> int:
        """Catisma sayisi."""
        return len(self._conflicts)
