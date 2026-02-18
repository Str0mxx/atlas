"""
Adalet analizcisi modulu.

Adalet metrikleri, esit firsat,
esitlenmis oranlar, kalibrasyon,
grup adaleti.
"""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class FairnessAnalyzer:
    """Adalet analizcisi.

    Attributes:
        _analyses: Analizler.
        _metrics: Metrikler.
        _stats: Istatistikler.
    """

    FAIRNESS_METRICS: list[str] = [
        "demographic_parity",
        "equal_opportunity",
        "equalized_odds",
        "calibration",
        "predictive_parity",
        "treatment_equality",
    ]

    def __init__(
        self,
        fairness_threshold: float = 0.8,
    ) -> None:
        """Analizcisi baslatir.

        Args:
            fairness_threshold: Adalet esigi.
        """
        self._fairness_threshold = (
            fairness_threshold
        )
        self._analyses: dict[
            str, dict
        ] = {}
        self._metrics: dict[
            str, dict
        ] = {}
        self._stats: dict[str, int] = {
            "analyses_done": 0,
            "unfair_found": 0,
            "metrics_calculated": 0,
        }
        logger.info(
            "FairnessAnalyzer baslatildi"
        )

    @property
    def analysis_count(self) -> int:
        """Analiz sayisi."""
        return len(self._analyses)

    def analyze_fairness(
        self,
        predictions: list[dict]
        | None = None,
        protected_attr: str = "",
        outcome_attr: str = "outcome",
        predicted_attr: str = "predicted",
    ) -> dict[str, Any]:
        """Adalet analizi yapar.

        Args:
            predictions: Tahminler.
            protected_attr: Korunan ozellik.
            outcome_attr: Gercek sonuc.
            predicted_attr: Tahmin.

        Returns:
            Analiz bilgisi.
        """
        try:
            aid = f"fair_{uuid4()!s:.8}"
            preds = predictions or []

            if not preds or not protected_attr:
                self._analyses[aid] = {
                    "analysis_id": aid,
                    "metrics": {},
                    "is_fair": True,
                    "score": 1.0,
                }
                return {
                    "analysis_id": aid,
                    "metrics": {},
                    "is_fair": True,
                    "fairness_score": 1.0,
                    "analyzed": True,
                }

            metrics: dict[str, Any] = {}

            # Gruplara ayir
            groups = (
                self._split_groups(
                    preds,
                    protected_attr,
                )
            )

            # 1. Demografik parite
            dp = (
                self._demographic_parity(
                    groups,
                    predicted_attr,
                )
            )
            metrics["demographic_parity"] = (
                dp
            )

            # 2. Esit firsat
            eo = (
                self._equal_opportunity(
                    groups,
                    outcome_attr,
                    predicted_attr,
                )
            )
            metrics["equal_opportunity"] = (
                eo
            )

            # 3. Esitlenmis oranlar
            eod = self._equalized_odds(
                groups,
                outcome_attr,
                predicted_attr,
            )
            metrics["equalized_odds"] = eod

            # 4. Kalibrasyon
            cal = self._calibration(
                groups,
                outcome_attr,
                predicted_attr,
            )
            metrics["calibration"] = cal

            # 5. Grup adaleti
            gf = self._group_fairness(
                groups,
                outcome_attr,
                predicted_attr,
            )
            metrics["group_fairness"] = gf

            # Genel puan
            scores = [
                m.get("score", 1.0)
                for m in metrics.values()
                if isinstance(m, dict)
            ]
            avg_score = (
                sum(scores) / len(scores)
                if scores
                else 1.0
            )
            is_fair = (
                avg_score
                >= self._fairness_threshold
            )

            self._analyses[aid] = {
                "analysis_id": aid,
                "protected_attr": (
                    protected_attr
                ),
                "metrics": metrics,
                "is_fair": is_fair,
                "score": round(
                    avg_score, 4
                ),
                "analyzed_at": (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                ),
            }

            self._stats[
                "analyses_done"
            ] += 1
            self._stats[
                "metrics_calculated"
            ] += len(metrics)
            if not is_fair:
                self._stats[
                    "unfair_found"
                ] += 1

            return {
                "analysis_id": aid,
                "metrics": metrics,
                "is_fair": is_fair,
                "fairness_score": round(
                    avg_score, 4
                ),
                "analyzed": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "analyzed": False,
                "error": str(e),
            }

    def _split_groups(
        self,
        records: list[dict],
        attr: str,
    ) -> dict[str, list[dict]]:
        """Gruplara ayirir."""
        groups: dict[str, list] = {}
        for r in records:
            g = str(
                r.get(attr, "unknown")
            )
            groups.setdefault(g, [])
            groups[g].append(r)
        return groups

    def _demographic_parity(
        self,
        groups: dict[str, list],
        predicted_attr: str,
    ) -> dict[str, Any]:
        """Demografik parite hesaplar."""
        rates: dict[str, float] = {}
        for g, recs in groups.items():
            if not recs:
                continue
            pos = sum(
                1
                for r in recs
                if r.get(predicted_attr)
            )
            rates[g] = pos / len(recs)

        if len(rates) < 2:
            return {
                "score": 1.0,
                "rates": rates,
                "fair": True,
            }

        max_r = max(rates.values())
        min_r = min(rates.values())
        score = (
            min_r / max_r
            if max_r > 0
            else 1.0
        )

        return {
            "score": round(score, 4),
            "rates": {
                k: round(v, 4)
                for k, v in rates.items()
            },
            "gap": round(max_r - min_r, 4),
            "fair": (
                score
                >= self._fairness_threshold
            ),
        }

    def _equal_opportunity(
        self,
        groups: dict[str, list],
        outcome_attr: str,
        predicted_attr: str,
    ) -> dict[str, Any]:
        """Esit firsat hesaplar (TPR)."""
        tpr: dict[str, float] = {}
        for g, recs in groups.items():
            positives = [
                r
                for r in recs
                if r.get(outcome_attr)
            ]
            if not positives:
                continue
            tp = sum(
                1
                for r in positives
                if r.get(predicted_attr)
            )
            tpr[g] = tp / len(positives)

        if len(tpr) < 2:
            return {
                "score": 1.0,
                "tpr": tpr,
                "fair": True,
            }

        max_t = max(tpr.values())
        min_t = min(tpr.values())
        score = (
            min_t / max_t
            if max_t > 0
            else 1.0
        )

        return {
            "score": round(score, 4),
            "tpr": {
                k: round(v, 4)
                for k, v in tpr.items()
            },
            "fair": (
                score
                >= self._fairness_threshold
            ),
        }

    def _equalized_odds(
        self,
        groups: dict[str, list],
        outcome_attr: str,
        predicted_attr: str,
    ) -> dict[str, Any]:
        """Esitlenmis oranlar (TPR+FPR)."""
        tpr: dict[str, float] = {}
        fpr: dict[str, float] = {}

        for g, recs in groups.items():
            pos = [
                r
                for r in recs
                if r.get(outcome_attr)
            ]
            neg = [
                r
                for r in recs
                if not r.get(outcome_attr)
            ]

            if pos:
                tp = sum(
                    1
                    for r in pos
                    if r.get(predicted_attr)
                )
                tpr[g] = tp / len(pos)
            if neg:
                fp = sum(
                    1
                    for r in neg
                    if r.get(predicted_attr)
                )
                fpr[g] = fp / len(neg)

        tpr_score = 1.0
        fpr_score = 1.0

        if len(tpr) >= 2:
            mx = max(tpr.values())
            mn = min(tpr.values())
            tpr_score = (
                mn / mx if mx > 0 else 1.0
            )

        if len(fpr) >= 2:
            mx = max(fpr.values())
            mn = min(fpr.values())
            fpr_score = (
                1.0 - (mx - mn)
            )

        score = (
            tpr_score + fpr_score
        ) / 2

        return {
            "score": round(score, 4),
            "tpr": {
                k: round(v, 4)
                for k, v in tpr.items()
            },
            "fpr": {
                k: round(v, 4)
                for k, v in fpr.items()
            },
            "fair": (
                score
                >= self._fairness_threshold
            ),
        }

    def _calibration(
        self,
        groups: dict[str, list],
        outcome_attr: str,
        predicted_attr: str,
    ) -> dict[str, Any]:
        """Kalibrasyon kontrolu."""
        ppv: dict[str, float] = {}
        for g, recs in groups.items():
            predicted_pos = [
                r
                for r in recs
                if r.get(predicted_attr)
            ]
            if not predicted_pos:
                continue
            tp = sum(
                1
                for r in predicted_pos
                if r.get(outcome_attr)
            )
            ppv[g] = tp / len(
                predicted_pos
            )

        if len(ppv) < 2:
            return {
                "score": 1.0,
                "ppv": ppv,
                "fair": True,
            }

        mx = max(ppv.values())
        mn = min(ppv.values())
        score = (
            mn / mx if mx > 0 else 1.0
        )

        return {
            "score": round(score, 4),
            "ppv": {
                k: round(v, 4)
                for k, v in ppv.items()
            },
            "fair": (
                score
                >= self._fairness_threshold
            ),
        }

    def _group_fairness(
        self,
        groups: dict[str, list],
        outcome_attr: str,
        predicted_attr: str,
    ) -> dict[str, Any]:
        """Grup adaleti kontrolu."""
        accuracy: dict[str, float] = {}
        for g, recs in groups.items():
            if not recs:
                continue
            correct = sum(
                1
                for r in recs
                if (
                    bool(
                        r.get(
                            predicted_attr
                        )
                    )
                    == bool(
                        r.get(outcome_attr)
                    )
                )
            )
            accuracy[g] = correct / len(
                recs
            )

        if len(accuracy) < 2:
            return {
                "score": 1.0,
                "accuracy": accuracy,
                "fair": True,
            }

        mx = max(accuracy.values())
        mn = min(accuracy.values())
        score = (
            mn / mx if mx > 0 else 1.0
        )

        return {
            "score": round(score, 4),
            "accuracy": {
                k: round(v, 4)
                for k, v in accuracy.items()
            },
            "fair": (
                score
                >= self._fairness_threshold
            ),
        }

    def compare_analyses(
        self,
        analysis_ids: list[str]
        | None = None,
    ) -> dict[str, Any]:
        """Analizleri karsilastirir.

        Args:
            analysis_ids: Analiz ID'leri.

        Returns:
            Karsilastirma bilgisi.
        """
        try:
            ids = analysis_ids or []
            results: list[dict] = []

            for aid in ids:
                a = self._analyses.get(aid)
                if a:
                    results.append({
                        "analysis_id": aid,
                        "score": a["score"],
                        "is_fair": a[
                            "is_fair"
                        ],
                    })

            return {
                "comparisons": results,
                "count": len(results),
                "compared": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "compared": False,
                "error": str(e),
            }

    def get_summary(
        self,
    ) -> dict[str, Any]:
        """Ozet getirir."""
        try:
            return {
                "total_analyses": len(
                    self._analyses
                ),
                "stats": dict(self._stats),
                "retrieved": True,
            }
        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }
