"""
OKR Score Calculator - OKR puan hesaplama ve analiz modülü.

Bu modül, Key Result'ların ilerlemesini skorlama, ağırlıklı hesaplama,
hedef aggregasyonu, tarihsel karşılaştırma ve benchmark analizi sağlar.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class OKRScoreCalculator:
    """
    OKR puan hesaplayıcı sınıfı.

    Key Result skorlarını hesaplar, ağırlıklandırır, aggregate eder,
    tarihsel trendleri analiz eder ve sektör benchmark'larıyla karşılaştırır.
    """

    def __init__(self) -> None:
        """OKRScoreCalculator başlatıcı."""
        self._scores: list[dict[str, Any]] = []
        self._stats: dict[str, int] = {
            "scores_calculated": 0
        }
        logger.info("OKRScoreCalculator başlatıldı")

    @property
    def score_count(self) -> int:
        """
        Hesaplanan skor sayısını döner.

        Returns:
            Hesaplanan toplam skor sayısı
        """
        return len(self._scores)

    def calculate_score(
        self,
        kr_values: list[dict[str, Any]] | None = None
    ) -> dict[str, Any]:
        """
        Key Result'ların ilerlemesini skorlar.

        Her KR için current/target oranını hesaplar, ortalama skor ve
        performans derecesi (grade) belirler.

        Args:
            kr_values: Key Result değerleri listesi (current, target içeren dict'ler)

        Returns:
            Skor analiz sonucu (score, grade, kr_count, scores, calculated)
        """
        if kr_values is None:
            kr_values = []

        scores: list[float] = []

        for kr in kr_values:
            current = kr.get("current", 0)
            target = max(kr.get("target", 100), 0.001)  # Division by zero önleme
            progress = min(current / target * 100, 100)
            scores.append(progress)

        # Ortalama skor hesapla
        avg_score = round(sum(scores) / max(len(scores), 1), 1)

        # Grade belirleme
        if avg_score >= 90:
            grade = "exceptional"
        elif avg_score >= 70:
            grade = "strong"
        elif avg_score >= 50:
            grade = "on_target"
        elif avg_score >= 30:
            grade = "needs_improvement"
        else:
            grade = "failing"

        result = {
            "score": avg_score,
            "grade": grade,
            "kr_count": len(scores),
            "scores": scores,
            "calculated": True
        }

        # Sonucu kaydet ve istatistik güncelle
        self._scores.append(result)
        self._stats["scores_calculated"] += 1

        logger.info(
            f"OKR skoru hesaplandı: {avg_score} ({grade}), "
            f"{len(scores)} KR"
        )

        return result

    def apply_weights(
        self,
        kr_scores: list[float] | None = None,
        weights: list[float] | None = None
    ) -> dict[str, Any]:
        """
        Key Result skorlarına ağırlık uygular.

        Her KR'ın önem derecesine göre ağırlıklı ortalama hesaplar.
        Eğer ağırlıklar yoksa veya uyumsuzsa basit ortalama alır.

        Args:
            kr_scores: Key Result skorları listesi
            weights: Her KR için ağırlık değerleri listesi

        Returns:
            Ağırlıklı skor sonucu (weighted_score, kr_count, weights_applied, weighted)
        """
        if kr_scores is None:
            kr_scores = []
        if weights is None:
            weights = []

        # Ağırlık uygulanabilir mi kontrol et
        if len(kr_scores) == len(weights) and len(weights) > 0:
            weighted_sum = sum(s * w for s, w in zip(kr_scores, weights))
            total_weight = sum(weights)
            weighted_score = round(weighted_sum / max(total_weight, 0.001), 1)
            weights_applied = True
        else:
            # Ağırlık uygulanamıyorsa basit ortalama
            weighted_score = round(
                sum(kr_scores) / max(len(kr_scores), 1), 1
            ) if kr_scores else 0.0
            weights_applied = False

        result = {
            "weighted_score": weighted_score,
            "kr_count": len(kr_scores),
            "weights_applied": weights_applied,
            "weighted": True
        }

        logger.info(
            f"Ağırlıklı skor hesaplandı: {weighted_score}, "
            f"ağırlık uygulandı: {weights_applied}"
        )

        return result

    def aggregate_scores(
        self,
        objective_scores: list[float] | None = None
    ) -> dict[str, Any]:
        """
        Birden fazla Objective skorunu aggregate eder.

        Tüm Objective'lerin genel performansını, en iyi/kötü skorları
        ve performans dağılımını (spread) hesaplar.

        Args:
            objective_scores: Objective skorları listesi

        Returns:
            Aggregate skor sonucu (overall_score, best, worst, spread, objective_count, aggregated)
        """
        if objective_scores is None:
            objective_scores = []

        overall = round(
            sum(objective_scores) / max(len(objective_scores), 1), 1
        ) if objective_scores else 0.0

        best = max(objective_scores) if objective_scores else 0.0
        worst = min(objective_scores) if objective_scores else 0.0
        spread = round(best - worst, 1)

        result = {
            "overall_score": overall,
            "best": best,
            "worst": worst,
            "spread": spread,
            "objective_count": len(objective_scores),
            "aggregated": True
        }

        logger.info(
            f"Skorlar aggregate edildi: genel={overall}, "
            f"en iyi={best}, en kötü={worst}, spread={spread}"
        )

        return result

    def compare_historical(
        self,
        current_score: float = 0.0,
        previous_scores: list[float] | None = None
    ) -> dict[str, Any]:
        """
        Mevcut skoru geçmiş skorlarla karşılaştırır.

        Performans trendini (improving/declining/stable) ve değişim
        miktarını hesaplar.

        Args:
            current_score: Güncel skor
            previous_scores: Geçmiş dönem skorları listesi

        Returns:
            Tarihsel karşılaştırma sonucu (current_score, previous_average, change, trend, periods_compared, compared)
        """
        if previous_scores is None:
            previous_scores = []

        prev_avg = round(
            sum(previous_scores) / max(len(previous_scores), 1), 1
        ) if previous_scores else 0.0

        change = round(current_score - prev_avg, 1)

        # Trend belirleme
        if change > 5:
            trend = "improving"
        elif change < -5:
            trend = "declining"
        else:
            trend = "stable"

        result = {
            "current_score": current_score,
            "previous_average": prev_avg,
            "change": change,
            "trend": trend,
            "periods_compared": len(previous_scores),
            "compared": True
        }

        logger.info(
            f"Tarihsel karşılaştırma: güncel={current_score}, "
            f"geçmiş ort={prev_avg}, değişim={change}, trend={trend}"
        )

        return result

    def benchmark(
        self,
        score: float = 0.0,
        industry_avg: float = 60.0,
        top_performer: float = 80.0
    ) -> dict[str, Any]:
        """
        Skoru sektör benchmark'larıyla karşılaştırır.

        Sektör ortalaması ve en iyi performansa göre konumlandırma yapar,
        percentile hesaplar.

        Args:
            score: Karşılaştırılacak skor
            industry_avg: Sektör ortalama skoru
            top_performer: En iyi performans skoru

        Returns:
            Benchmark sonucu (score, industry_avg, top_performer, vs_industry, vs_top, percentile, benchmarked)
        """
        vs_industry = round(score - industry_avg, 1)
        vs_top = round(score - top_performer, 1)

        # Percentile belirleme
        if score >= top_performer:
            percentile = 90
        elif score >= industry_avg:
            percentile = 60
        elif score >= industry_avg * 0.8:
            percentile = 40
        else:
            percentile = 20

        result = {
            "score": score,
            "industry_avg": industry_avg,
            "top_performer": top_performer,
            "vs_industry": vs_industry,
            "vs_top": vs_top,
            "percentile": percentile,
            "benchmarked": True
        }

        logger.info(
            f"Benchmark analizi: skor={score}, "
            f"sektör farkı={vs_industry}, en iyi farkı={vs_top}, "
            f"percentile={percentile}"
        )

        return result
