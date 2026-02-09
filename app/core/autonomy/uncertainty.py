"""ATLAS belirsizlik yonetimi modulu.

Guven araliklari, risk nicelestirme, senaryo analizi ve
en kotu/en iyi/beklenen durum hesaplamasi saglar.
"""

import logging
from typing import Any

import numpy as np
from scipy import stats

from app.models.probability import (
    ConfidenceInterval,
    RiskQuantification,
    ScenarioAnalysis,
)

logger = logging.getLogger("atlas.autonomy.uncertainty")


class UncertaintyManager:
    """Belirsizlik yonetim sinifi.

    Karar surecindeki belirsizligi olcer, guven araliklari
    hesaplar ve risk degerlendirmesi yapar.

    Attributes:
        default_confidence_level: Varsayilan guven duzeyi (0.95).
        risk_tolerance: Risk toleransi (0-1 arasi, 0=riskten kacinan).
    """

    def __init__(
        self,
        default_confidence_level: float = 0.95,
        risk_tolerance: float = 0.5,
    ) -> None:
        """UncertaintyManager'i baslatir.

        Args:
            default_confidence_level: Varsayilan guven duzeyi.
            risk_tolerance: Risk toleransi.
        """
        self.default_confidence_level = default_confidence_level
        self.risk_tolerance = risk_tolerance
        logger.info(
            "UncertaintyManager olusturuldu (guven=%.2f, risk_tol=%.2f)",
            default_confidence_level, risk_tolerance,
        )

    def confidence_interval(
        self,
        data: list[float] | np.ndarray,
        confidence_level: float | None = None,
    ) -> ConfidenceInterval:
        """Veri kumesi icin guven araligi hesaplar.

        Kucuk orneklerde t-dagilimi, buyuk orneklerde normal
        dagilim kullanir.

        Args:
            data: Veri noktalari.
            confidence_level: Guven duzeyi (None ise varsayilan).

        Returns:
            Hesaplanan guven araligi.
        """
        arr = np.asarray(data, dtype=float)
        level = confidence_level or self.default_confidence_level
        n = len(arr)
        mean = float(np.mean(arr))

        if n < 2:
            return ConfidenceInterval(
                lower=mean, upper=mean,
                confidence_level=level, mean=mean,
            )

        se = float(np.std(arr, ddof=1) / np.sqrt(n))

        if n < 30:
            # t-dagilimi
            lower, upper = stats.t.interval(
                level, df=n - 1, loc=mean, scale=se,
            )
        else:
            # Normal dagilim
            lower, upper = stats.norm.interval(
                level, loc=mean, scale=se,
            )

        return ConfidenceInterval(
            lower=float(lower),
            upper=float(upper),
            confidence_level=level,
            mean=mean,
        )

    def quantify_risk(
        self,
        outcomes: list[float] | np.ndarray,
        probabilities: list[float] | np.ndarray | None = None,
    ) -> RiskQuantification:
        """Risk metriklerini hesaplar.

        VaR, CVaR, kayip olasiligi ve en iyi/en kotu senaryo.

        Args:
            outcomes: Olasi sonuc degerleri.
            probabilities: Sonuc olasiliklari (None ise esit dagitim).

        Returns:
            Risk nicelestirme sonucu.
        """
        arr = np.asarray(outcomes, dtype=float)

        if len(arr) == 0:
            return RiskQuantification()

        if probabilities is not None:
            probs = np.asarray(probabilities, dtype=float)
            # Agirlikli beklenen kayip
            expected_loss = float(np.dot(arr, probs))
            # Kumulatif dagilim ile VaR
            sorted_indices = np.argsort(arr)
            sorted_outcomes = arr[sorted_indices]
            sorted_probs = probs[sorted_indices]
            cumulative = np.cumsum(sorted_probs)
            # VaR_95: %5 kumulatif esik
            var_idx = np.searchsorted(cumulative, 0.05)
            var_95 = float(sorted_outcomes[min(var_idx, len(arr) - 1)])
            # CVaR: VaR altindaki beklenen deger
            tail_mask = sorted_outcomes <= var_95
            if np.any(tail_mask):
                tail_probs = sorted_probs[tail_mask]
                tail_outcomes = sorted_outcomes[tail_mask]
                tail_sum = np.sum(tail_probs)
                if tail_sum > 0:
                    cvar_95 = float(
                        np.dot(tail_outcomes, tail_probs) / tail_sum,
                    )
                else:
                    cvar_95 = var_95
            else:
                cvar_95 = var_95
            # Kayip olasiligi
            loss_prob = float(np.sum(probs[arr < 0]))
        else:
            expected_loss = float(np.mean(arr))
            var_95 = float(np.percentile(arr, 5))
            # CVaR: VaR altindaki ortalama
            tail = arr[arr <= var_95]
            cvar_95 = float(np.mean(tail)) if len(tail) > 0 else var_95
            loss_prob = float(np.mean(arr < 0))

        return RiskQuantification(
            expected_loss=expected_loss,
            var_95=var_95,
            cvar_95=cvar_95,
            probability_of_loss=min(max(loss_prob, 0.0), 1.0),
            worst_case=float(np.min(arr)),
            best_case=float(np.max(arr)),
        )

    def scenario_analysis(
        self,
        scenarios: dict[str, float],
        probabilities: dict[str, float] | None = None,
    ) -> ScenarioAnalysis:
        """Senaryo bazli analiz yapar.

        Args:
            scenarios: Senaryo adi -> deger eslesmesi.
            probabilities: Senaryo olasiliklari (None ise esit).

        Returns:
            Senaryo analiz sonucu.
        """
        if not scenarios:
            return ScenarioAnalysis(
                worst_case=0.0, best_case=0.0, expected_case=0.0,
            )

        values = list(scenarios.values())
        names = list(scenarios.keys())

        if probabilities is not None:
            probs = {k: probabilities.get(k, 0.0) for k in names}
        else:
            equal_prob = 1.0 / len(names)
            probs = {k: equal_prob for k in names}

        # Normalize olasiliklar
        total_prob = sum(probs.values())
        if total_prob > 0:
            probs = {k: v / total_prob for k, v in probs.items()}

        expected = sum(
            scenarios[k] * probs[k] for k in names
        )

        return ScenarioAnalysis(
            worst_case=min(values),
            best_case=max(values),
            expected_case=expected,
            scenarios=dict(scenarios),
            probabilities=probs,
        )

    def aggregate_confidence(
        self,
        confidences: list[float],
        weights: list[float] | None = None,
    ) -> float:
        """Birden fazla guven skorunu birlestirir.

        Agirlikli geometrik ortalama kullanir.

        Args:
            confidences: Guven skorlari (0-1).
            weights: Agirliklar (None ise esit).

        Returns:
            Birlesmis guven skoru (0-1).
        """
        if not confidences:
            return 0.0

        arr = np.asarray(confidences, dtype=float)
        arr = np.clip(arr, 1e-10, 1.0)

        if weights is not None:
            w = np.asarray(weights, dtype=float)
            w = w / np.sum(w)
        else:
            w = np.ones(len(arr)) / len(arr)

        # Agirlikli geometrik ortalama: exp(sum(w_i * log(c_i)))
        log_conf = np.log(arr)
        result = float(np.exp(np.dot(w, log_conf)))
        return min(max(result, 0.0), 1.0)

    def belief_uncertainty(
        self,
        belief_confidences: dict[str, float],
    ) -> dict[str, Any]:
        """Belief kuresinin genel belirsizligini olcer.

        Entropy, ortalama guven, min/max guven hesaplar.

        Args:
            belief_confidences: Belief anahtari -> guven eslesmesi.

        Returns:
            Belirsizlik metrikleri sozlugu.
        """
        if not belief_confidences:
            return {
                "entropy": 0.0,
                "mean_confidence": 0.0,
                "min_confidence": 0.0,
                "max_confidence": 0.0,
                "n_beliefs": 0,
            }

        values = list(belief_confidences.values())
        arr = np.asarray(values, dtype=float)
        arr_clipped = np.clip(arr, 1e-10, 1.0 - 1e-10)

        # Binary entropy: H = -p*log(p) - (1-p)*log(1-p)
        entropy_per_belief = -(
            arr_clipped * np.log2(arr_clipped)
            + (1 - arr_clipped) * np.log2(1 - arr_clipped)
        )
        total_entropy = float(np.mean(entropy_per_belief))

        return {
            "entropy": total_entropy,
            "mean_confidence": float(np.mean(arr)),
            "min_confidence": float(np.min(arr)),
            "max_confidence": float(np.max(arr)),
            "n_beliefs": len(values),
        }

    def should_act(
        self,
        confidence: float,
        risk_level: float,
        threshold: float | None = None,
    ) -> bool:
        """Yeterli kesinlik var mi kontrol eder.

        Risk toleransini ve guven esigini birlikte degerlendirerek
        aksiyona gecilmeli mi karar verir.

        Args:
            confidence: Mevcut guven.
            risk_level: Risk seviyesi (0-1).
            threshold: Minimum guven esigi (None ise dinamik).

        Returns:
            True ise aksiyona gecilmeli.
        """
        if threshold is not None:
            effective_threshold = threshold
        else:
            # Yuksek risk -> yuksek esik, risk_tolerance dusurur
            effective_threshold = 1.0 - self.risk_tolerance * (
                1.0 - risk_level
            )

        return confidence >= effective_threshold
