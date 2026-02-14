"""ATLAS Akil Yurutme Motoru modulu.

Mantiksal, analojik, nedensel, abduktif
ve meta akil yurutme yetenekleri.
"""

import logging
from typing import Any

from app.models.unified import ReasoningChain, ReasoningType

logger = logging.getLogger(__name__)


class ReasoningEngine:
    """Akil yurutme motoru.

    Farkli akil yurutme turleriyle
    sonuc cikarir ve zincir olusturur.

    Attributes:
        _chains: Akil yurutme zincirleri.
        _rules: Mantik kurallari.
        _analogies: Benzetme katalogu.
        _causal_links: Nedensel baglantilar.
    """

    def __init__(self, max_depth: int = 10) -> None:
        """Akil yurutme motorunu baslatir.

        Args:
            max_depth: Maks zincirleme derinligi.
        """
        self._chains: dict[str, ReasoningChain] = {}
        self._rules: dict[str, dict[str, Any]] = {}
        self._analogies: list[dict[str, Any]] = []
        self._causal_links: list[dict[str, Any]] = []
        self._max_depth = max_depth

        logger.info("ReasoningEngine baslatildi (depth=%d)", max_depth)

    def reason_logically(
        self,
        premises: list[str],
        rules: list[str] | None = None,
    ) -> ReasoningChain:
        """Mantiksal akil yurutme yapar.

        Args:
            premises: Onculler.
            rules: Uygulanacak kurallar.

        Returns:
            ReasoningChain nesnesi.
        """
        steps = []
        applied_rules = []

        for premise in premises:
            steps.append({
                "type": "premise",
                "content": premise,
            })

        # Kural uygula
        for rule_name in (rules or []):
            rule = self._rules.get(rule_name)
            if rule:
                steps.append({
                    "type": "rule_application",
                    "rule": rule_name,
                    "description": rule.get("description", ""),
                })
                applied_rules.append(rule_name)

        # Sonuc cikar
        conclusion = f"Sonuc: {len(premises)} oncul, {len(applied_rules)} kural"
        if premises:
            conclusion = f"{premises[-1]} (dogrulanmis)"

        chain = ReasoningChain(
            reasoning_type=ReasoningType.LOGICAL,
            premises=premises,
            conclusion=conclusion,
            steps=steps,
            confidence=min(0.9, 0.5 + len(premises) * 0.1),
            metadata={"rules_applied": applied_rules},
        )
        self._chains[chain.chain_id] = chain

        logger.info("Mantiksal akil yurutme: %s", chain.chain_id)
        return chain

    def reason_analogically(
        self,
        source_domain: str,
        target_domain: str,
        mappings: dict[str, str] | None = None,
    ) -> ReasoningChain:
        """Analojik akil yurutme yapar.

        Args:
            source_domain: Kaynak alan.
            target_domain: Hedef alan.
            mappings: Alan eslestirmeleri.

        Returns:
            ReasoningChain nesnesi.
        """
        effective_mappings = mappings or {}

        steps = [
            {"type": "source", "domain": source_domain},
            {"type": "target", "domain": target_domain},
            {"type": "mapping", "pairs": effective_mappings},
        ]

        # Benzetme katalogundan eslesme ara
        similarity = 0.3
        for analogy in self._analogies:
            if (analogy.get("source") == source_domain
                    or analogy.get("target") == target_domain):
                similarity = max(similarity, analogy.get("strength", 0.5))

        conclusion = (
            f"{source_domain} -> {target_domain}: "
            f"{len(effective_mappings)} eslestirme"
        )

        chain = ReasoningChain(
            reasoning_type=ReasoningType.ANALOGICAL,
            premises=[source_domain, target_domain],
            conclusion=conclusion,
            steps=steps,
            confidence=round(similarity, 3),
        )
        self._chains[chain.chain_id] = chain

        return chain

    def reason_causally(
        self,
        cause: str,
        observed_effects: list[str] | None = None,
    ) -> ReasoningChain:
        """Nedensel akil yurutme yapar.

        Args:
            cause: Neden.
            observed_effects: Gozlenen etkiler.

        Returns:
            ReasoningChain nesnesi.
        """
        effects = observed_effects or []
        steps = [{"type": "cause", "content": cause}]

        # Nedensel baglanti ara
        predicted_effects = []
        for link in self._causal_links:
            if link.get("cause") == cause:
                predicted_effects.append(link.get("effect", ""))
                steps.append({
                    "type": "causal_link",
                    "effect": link.get("effect"),
                    "strength": link.get("strength", 0.5),
                })

        for effect in effects:
            steps.append({
                "type": "observed_effect",
                "content": effect,
            })

        verified = set(predicted_effects) & set(effects)
        confidence = (
            len(verified) / max(len(predicted_effects), 1)
            if predicted_effects else 0.5
        )

        chain = ReasoningChain(
            reasoning_type=ReasoningType.CAUSAL,
            premises=[cause] + effects,
            conclusion=f"{cause} -> {len(effects)} etki",
            steps=steps,
            confidence=round(min(1.0, confidence), 3),
        )
        self._chains[chain.chain_id] = chain

        return chain

    def reason_abductively(
        self,
        observations: list[str],
        hypotheses: list[str] | None = None,
    ) -> ReasoningChain:
        """Abduktif akil yurutme yapar (en iyi aciklama).

        Args:
            observations: Gozlemler.
            hypotheses: Hipotez adaylari.

        Returns:
            ReasoningChain nesnesi.
        """
        candidates = hypotheses or []
        steps = []

        for obs in observations:
            steps.append({"type": "observation", "content": obs})

        # Hipotezleri degerlendir
        scored = []
        for hyp in candidates:
            # Basit skor: gozlem sayisina dayali
            score = round(min(1.0, 0.3 + len(observations) * 0.1), 3)
            scored.append({"hypothesis": hyp, "score": score})
            steps.append({
                "type": "hypothesis",
                "content": hyp,
                "score": score,
            })

        scored.sort(key=lambda h: h["score"], reverse=True)
        best = scored[0] if scored else {"hypothesis": "belirsiz", "score": 0.3}

        chain = ReasoningChain(
            reasoning_type=ReasoningType.ABDUCTIVE,
            premises=observations,
            conclusion=f"En iyi aciklama: {best['hypothesis']}",
            steps=steps,
            confidence=best["score"],
            metadata={"all_hypotheses": scored},
        )
        self._chains[chain.chain_id] = chain

        return chain

    def meta_reason(
        self,
        chain_ids: list[str],
    ) -> ReasoningChain:
        """Meta akil yurutme yapar (akilyurutme hakkinda).

        Args:
            chain_ids: Degerlendirilecek zincir ID'leri.

        Returns:
            Meta akil yurutme zinciri.
        """
        evaluated = []
        steps = []
        total_confidence = 0.0

        for cid in chain_ids:
            chain = self._chains.get(cid)
            if chain:
                evaluated.append({
                    "chain_id": cid,
                    "type": chain.reasoning_type.value,
                    "confidence": chain.confidence,
                    "conclusion": chain.conclusion,
                })
                total_confidence += chain.confidence
                steps.append({
                    "type": "evaluate",
                    "chain_id": cid,
                    "reasoning_type": chain.reasoning_type.value,
                    "confidence": chain.confidence,
                })

        avg_conf = (
            total_confidence / len(evaluated) if evaluated else 0.0
        )

        # En guvenilir sonucu sec
        best = max(evaluated, key=lambda e: e["confidence"]) if evaluated else None
        conclusion = (
            f"Meta analiz: {best['conclusion']} (en guvenilir)"
            if best else "Yeterli veri yok"
        )

        chain = ReasoningChain(
            reasoning_type=ReasoningType.META,
            premises=[e["chain_id"] for e in evaluated],
            conclusion=conclusion,
            steps=steps,
            confidence=round(avg_conf, 3),
            metadata={"evaluated": evaluated},
        )
        self._chains[chain.chain_id] = chain

        return chain

    def add_rule(
        self,
        name: str,
        condition: str,
        consequence: str,
        description: str = "",
    ) -> None:
        """Mantik kurali ekler.

        Args:
            name: Kural adi.
            condition: Kosul.
            consequence: Sonuc.
            description: Aciklama.
        """
        self._rules[name] = {
            "condition": condition,
            "consequence": consequence,
            "description": description,
        }

    def add_analogy(
        self,
        source: str,
        target: str,
        strength: float = 0.5,
    ) -> None:
        """Benzetme katalogu ekler.

        Args:
            source: Kaynak alan.
            target: Hedef alan.
            strength: Guc (0-1).
        """
        self._analogies.append({
            "source": source,
            "target": target,
            "strength": max(0.0, min(1.0, strength)),
        })

    def add_causal_link(
        self,
        cause: str,
        effect: str,
        strength: float = 0.5,
    ) -> None:
        """Nedensel baglanti ekler.

        Args:
            cause: Neden.
            effect: Etki.
            strength: Guc.
        """
        self._causal_links.append({
            "cause": cause,
            "effect": effect,
            "strength": max(0.0, min(1.0, strength)),
        })

    def get_chain(self, chain_id: str) -> ReasoningChain | None:
        """Zinciri getirir.

        Args:
            chain_id: Zincir ID.

        Returns:
            ReasoningChain veya None.
        """
        return self._chains.get(chain_id)

    def get_chains_by_type(
        self,
        reasoning_type: ReasoningType,
    ) -> list[ReasoningChain]:
        """Ture gore zincirleri getirir.

        Args:
            reasoning_type: Akil yurutme turu.

        Returns:
            Zincir listesi.
        """
        return [
            c for c in self._chains.values()
            if c.reasoning_type == reasoning_type
        ]

    @property
    def total_chains(self) -> int:
        """Toplam zincir sayisi."""
        return len(self._chains)

    @property
    def rule_count(self) -> int:
        """Kural sayisi."""
        return len(self._rules)

    @property
    def analogy_count(self) -> int:
        """Benzetme sayisi."""
        return len(self._analogies)

    @property
    def causal_link_count(self) -> int:
        """Nedensel baglanti sayisi."""
        return len(self._causal_links)
