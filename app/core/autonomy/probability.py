"""ATLAS Bayesci ag ve olasiliksal cikarsama modulu.

Belief'ler uzerinde olasiliksal guncelleme, kosullu olasilik
tablolari ve kanit yayilimi saglar.
"""

import logging
from typing import Any

import numpy as np
from scipy.special import logsumexp

from app.models.probability import (
    ConditionalProbability,
    Evidence,
    PosteriorResult,
    PriorBelief,
)

logger = logging.getLogger("atlas.autonomy.probability")


class BayesianNetwork:
    """Bayesci ag sinifi.

    Degiskenler arasi bagimliliklari modelleyerek
    kanit geldikce posterior olasiliklari gunceller.

    Attributes:
        nodes: Degisken tanimlari (isim -> olasi durumlar).
        priors: On inanc olasiliklari (isim -> PriorBelief).
        cpts: Kosullu olasilik tablolari (cocuk -> ConditionalProbability).
        evidence_history: Islenmis kanitlar listesi.
    """

    def __init__(self) -> None:
        """Bos Bayesci agi baslatir."""
        self.nodes: dict[str, list[str]] = {}
        self.priors: dict[str, PriorBelief] = {}
        self.cpts: dict[str, ConditionalProbability] = {}
        self.evidence_history: list[Evidence] = []
        logger.info("BayesianNetwork olusturuldu")

    def add_node(self, name: str, states: list[str]) -> None:
        """Aga degisken dugumu ekler.

        Args:
            name: Degisken adi.
            states: Olasi durum listesi (orn: ["high", "low"]).
        """
        self.nodes[name] = list(states)
        logger.info("Dugum eklendi: %s (%d durum)", name, len(states))

    def set_prior(self, prior: PriorBelief) -> None:
        """Degiskenin on inanc dagilimini ayarlar.

        Args:
            prior: On inanc nesnesi.

        Raises:
            ValueError: Olasiliklar 1'e toplamiyorsa.
        """
        total = sum(prior.probabilities.values())
        if abs(total - 1.0) > 1e-6:
            msg = (
                f"Prior olasiliklari 1'e toplanmali: "
                f"{prior.variable} toplam={total:.6f}"
            )
            raise ValueError(msg)
        self.priors[prior.variable] = prior
        logger.info("Prior ayarlandi: %s", prior.variable)

    def set_cpt(self, cpt: ConditionalProbability) -> None:
        """Kosullu olasilik tablosunu ayarlar.

        Args:
            cpt: Kosullu olasilik tablosu.

        Raises:
            ValueError: Tablo satirlari 1'e toplamiyorsa.
        """
        for parent_state, child_probs in cpt.table.items():
            total = sum(child_probs.values())
            if abs(total - 1.0) > 1e-6:
                msg = (
                    f"CPT satiri 1'e toplanmali: "
                    f"{cpt.child}|{parent_state} toplam={total:.6f}"
                )
                raise ValueError(msg)
        self.cpts[cpt.child] = cpt
        logger.info(
            "CPT ayarlandi: %s | %s", cpt.child, cpt.parents,
        )

    def update_posterior(
        self,
        variable: str,
        evidence: list[Evidence],
    ) -> PosteriorResult:
        """Kanit geldikten sonra posterior olasiliklari hesaplar.

        Bayes teoremi uygulayarak prior'dan posterior'a gecer.
        Numerik kararlilik icin log-space hesaplama yapar.

        Args:
            variable: Guncellenen degisken.
            evidence: Gozlenen kanit listesi.

        Returns:
            Posterior hesaplama sonucu.
        """
        # Prior'i al
        prior = self.priors.get(variable)
        if prior is None:
            # Uniform prior varsay
            states = self.nodes.get(variable, [])
            if not states:
                return PosteriorResult(
                    variable=variable,
                    prior={},
                    posterior={},
                )
            uniform_prob = 1.0 / len(states)
            prior_probs = {s: uniform_prob for s in states}
        else:
            prior_probs = dict(prior.probabilities)

        states = list(prior_probs.keys())
        if not states:
            return PosteriorResult(
                variable=variable, prior={}, posterior={},
            )

        # Log-space'de prior
        log_prior = np.array([
            np.log(max(prior_probs[s], 1e-300)) for s in states
        ])

        # Her kanit icin likelihood hesapla
        log_likelihood_total = np.zeros(len(states))
        evidence_names: list[str] = []

        for ev in evidence:
            evidence_names.append(ev.observed_value)
            self.evidence_history.append(ev)

            # CPT'den likelihood al
            cpt = self.cpts.get(variable)
            if cpt is not None and ev.variable in cpt.parents:
                for i, state in enumerate(states):
                    cpt_row = cpt.table.get(ev.observed_value, {})
                    likelihood = cpt_row.get(state, 1.0 / len(states))
                    log_likelihood_total[i] += np.log(
                        max(likelihood, 1e-300),
                    ) * ev.confidence
            elif ev.variable == variable:
                # Dogrudan kanit: gozlenen duruma yuksek olasilik
                for i, state in enumerate(states):
                    if state == ev.observed_value:
                        log_likelihood_total[i] += np.log(
                            0.9 * ev.confidence + 0.1 * (1 - ev.confidence),
                        )
                    else:
                        remaining = len(states) - 1
                        if remaining > 0:
                            log_likelihood_total[i] += np.log(
                                max(
                                    (1 - 0.9 * ev.confidence) / remaining,
                                    1e-300,
                                ),
                            )

        # Posterior = prior * likelihood (log-space)
        log_unnormalized = log_prior + log_likelihood_total
        log_evidence = logsumexp(log_unnormalized)
        log_posterior = log_unnormalized - log_evidence

        posterior_probs = {
            states[i]: float(np.exp(log_posterior[i]))
            for i in range(len(states))
        }

        # Normalize (numerik hatalari duzelt)
        posterior_probs = self._normalize(posterior_probs)

        return PosteriorResult(
            variable=variable,
            prior=prior_probs,
            posterior=posterior_probs,
            evidence_used=evidence_names,
            log_likelihood=float(log_evidence),
        )

    def propagate_evidence(
        self,
        evidence: Evidence,
    ) -> dict[str, PosteriorResult]:
        """Kaniti tum bagli degiskenlere yayar.

        Args:
            evidence: Yayilacak kanit.

        Returns:
            Guncellenen tum degiskenlerin posterior sonuclari.
        """
        results: dict[str, PosteriorResult] = {}

        # Gozlenen degiskenin kendisini guncelle
        if evidence.variable in self.nodes:
            result = self.update_posterior(
                evidence.variable, [evidence],
            )
            results[evidence.variable] = result

        # Cocuk degiskenleri guncelle (bu degisken ebeveynse)
        for child_name, cpt in self.cpts.items():
            if evidence.variable in cpt.parents:
                result = self.update_posterior(
                    child_name, [evidence],
                )
                results[child_name] = result

        return results

    def get_probability(
        self,
        variable: str,
        state: str,
    ) -> float:
        """Degiskenin belirli durumda olma olasiligini dondurur.

        Args:
            variable: Degisken adi.
            state: Sorgulanan durum.

        Returns:
            Olasilik degeri [0.0, 1.0].
        """
        prior = self.priors.get(variable)
        if prior is None:
            states = self.nodes.get(variable, [])
            if not states or state not in states:
                return 0.0
            return 1.0 / len(states)
        return prior.probabilities.get(state, 0.0)

    def get_joint_probability(
        self,
        variables: dict[str, str],
    ) -> float:
        """Birlesik olasilik hesaplar.

        Bagimsizlik varsayimi altinda birlesik olasilik:
        P(A, B) = P(A) * P(B) (bagimsiz durumda)
        P(A, B) = P(B|A) * P(A) (CPT varsa)

        Args:
            variables: Degisken -> durum eslesmesi.

        Returns:
            Birlesik olasilik degeri.
        """
        if not variables:
            return 0.0

        joint = 1.0
        processed: set[str] = set()

        for var_name, var_state in variables.items():
            if var_name in processed:
                continue

            # CPT varsa kosullu olasilik kullan
            cpt = self.cpts.get(var_name)
            if cpt is not None:
                # Ebeveyn durumlarini bul
                parent_states: list[str] = []
                for parent in cpt.parents:
                    if parent in variables:
                        parent_states.append(variables[parent])
                if parent_states:
                    parent_key = ",".join(parent_states)
                    cpt_row = cpt.table.get(parent_key, {})
                    joint *= cpt_row.get(var_state, 0.0)
                    processed.add(var_name)
                    continue

            # Bagimsiz olasilik
            joint *= self.get_probability(var_name, var_state)
            processed.add(var_name)

        return joint

    def _normalize(self, probs: dict[str, float]) -> dict[str, float]:
        """Olasiliklari 1'e normalize eder.

        Args:
            probs: Normalize edilecek olasiliklar.

        Returns:
            Normalize edilmis olasiliklar.
        """
        total = sum(probs.values())
        if total <= 0:
            # Uniform dagitim
            n = len(probs)
            return {k: 1.0 / n for k in probs} if n > 0 else {}
        return {k: v / total for k, v in probs.items()}

    def _log_normalize(self, log_probs: np.ndarray) -> np.ndarray:
        """Log-space'de normalize eder (numerik kararlilik).

        Args:
            log_probs: Log-olasilik dizisi.

        Returns:
            Normalize edilmis log-olasiliklar.
        """
        return log_probs - logsumexp(log_probs)

    def snapshot(self) -> dict[str, Any]:
        """Mevcut ag durumunu dondurur."""
        return {
            "nodes": dict(self.nodes),
            "priors": {
                k: dict(v.probabilities)
                for k, v in self.priors.items()
            },
            "cpts": list(self.cpts.keys()),
            "evidence_count": len(self.evidence_history),
        }
