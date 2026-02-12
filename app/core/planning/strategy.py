"""ATLAS Strategy Engine modulu.

Strateji motoru: uzun/kisa vadeli planlama, senaryo analizi
ve adaptif strateji yonetimi.
"""

import logging
import math
from datetime import datetime, timezone
from typing import Any

from app.models.planning import (
    Scenario,
    ScenarioLikelihood,
    Strategy,
    StrategyEvaluation,
    StrategyType,
)

logger = logging.getLogger(__name__)

# Senaryo olasilik agirlik haritasi
_LIKELIHOOD_WEIGHTS: dict[ScenarioLikelihood, float] = {
    ScenarioLikelihood.VERY_LIKELY: 0.9,
    ScenarioLikelihood.LIKELY: 0.7,
    ScenarioLikelihood.POSSIBLE: 0.5,
    ScenarioLikelihood.UNLIKELY: 0.3,
    ScenarioLikelihood.RARE: 0.1,
}


class StrategyEngine:
    """Strateji motoru.

    Uzun ve kisa vadeli strateji planlama, senaryo analizi,
    performans degerlendirme ve adaptif strateji degistirme.

    Attributes:
        strategies: Kayitli stratejiler (id -> Strategy).
        active_strategy_id: Aktif strateji ID.
        kpi_history: KPI gecmis verileri (kpi_adi -> [deger]).
        environment: Cevresel kosullar (anahtar -> deger).
    """

    def __init__(self) -> None:
        self.strategies: dict[str, Strategy] = {}
        self.active_strategy_id: str | None = None
        self.kpi_history: dict[str, list[float]] = {}
        self.environment: dict[str, Any] = {}

    def register_strategy(self, strategy: Strategy) -> None:
        """Strateji kayit eder.

        Args:
            strategy: Kaydedilecek strateji.
        """
        self.strategies[strategy.id] = strategy
        logger.info(
            "Strateji kaydedildi: %s (tip=%s, ufuk=%d gun)",
            strategy.name,
            strategy.strategy_type.value,
            strategy.time_horizon,
        )

    def activate_strategy(self, strategy_id: str) -> bool:
        """Stratejiyi aktive eder.

        Args:
            strategy_id: Aktive edilecek strateji ID.

        Returns:
            Basarili mi.
        """
        if strategy_id not in self.strategies:
            return False

        # Onceki aktif stratejiyi deaktive et
        if self.active_strategy_id and self.active_strategy_id in self.strategies:
            self.strategies[self.active_strategy_id].active = False

        self.strategies[strategy_id].active = True
        self.active_strategy_id = strategy_id

        logger.info("Strateji aktive edildi: %s", self.strategies[strategy_id].name)
        return True

    def update_environment(self, updates: dict[str, Any]) -> None:
        """Cevresel kosullari gunceller.

        Args:
            updates: Guncellenecek kosullar.
        """
        self.environment.update(updates)

    def record_kpi(self, kpi_name: str, value: float) -> None:
        """KPI degeri kaydeder.

        Args:
            kpi_name: KPI adi.
            value: KPI degeri.
        """
        if kpi_name not in self.kpi_history:
            self.kpi_history[kpi_name] = []
        self.kpi_history[kpi_name].append(value)

    async def evaluate_strategy(
        self, strategy_id: str
    ) -> StrategyEvaluation:
        """Stratejiyi degerlendirir.

        KPI performansini, senaryo uyumunu ve cevresel kosullari
        analiz ederek genel puan hesaplar.

        Args:
            strategy_id: Degerlendirilecek strateji ID.

        Returns:
            StrategyEvaluation.

        Raises:
            ValueError: Strateji bulunamazsa.
        """
        strategy = self.strategies.get(strategy_id)
        if strategy is None:
            raise ValueError(f"Strateji bulunamadi: {strategy_id}")

        kpi_scores: dict[str, float] = {}
        strengths: list[str] = []
        weaknesses: list[str] = []

        # KPI performans degerlendirmesi
        for kpi_name, target in strategy.kpis.items():
            history = self.kpi_history.get(kpi_name, [])
            if not history:
                kpi_scores[kpi_name] = 0.0
                weaknesses.append(f"KPI verisi yok: {kpi_name}")
                continue

            current = history[-1]
            if target == 0:
                score = 1.0 if current == 0 else 0.0
            else:
                ratio = current / target
                score = min(1.0, ratio)
            kpi_scores[kpi_name] = score

            if score >= 0.8:
                strengths.append(f"{kpi_name}: hedefe yakin (%.0f%%)" % (score * 100))
            elif score < 0.5:
                weaknesses.append(f"{kpi_name}: hedefin altinda (%.0f%%)" % (score * 100))

        # Senaryo analizi
        scenario_score = await self._evaluate_scenarios(strategy.scenarios)

        # Genel puan hesapla
        kpi_avg = (
            sum(kpi_scores.values()) / len(kpi_scores)
            if kpi_scores
            else 0.5
        )
        overall_score = 0.6 * kpi_avg + 0.3 * scenario_score + 0.1 * strategy.confidence

        # Oneri
        recommendation = self._generate_recommendation(
            overall_score, strengths, weaknesses, strategy
        )

        evaluation = StrategyEvaluation(
            strategy_id=strategy_id,
            score=min(1.0, max(0.0, overall_score)),
            kpi_scores=kpi_scores,
            strengths=strengths,
            weaknesses=weaknesses,
            recommendation=recommendation,
        )

        logger.info(
            "Strateji degerlendirmesi: %s -> puan=%.2f",
            strategy.name,
            evaluation.score,
        )
        return evaluation

    async def _evaluate_scenarios(
        self, scenarios: list[Scenario]
    ) -> float:
        """Senaryolari degerlendirir.

        Her senaryonun cevresel kosullarla uyumunu kontrol eder.

        Args:
            scenarios: Degerlendirilecek senaryolar.

        Returns:
            Senaryo uyum puani (0.0-1.0).
        """
        if not scenarios:
            return 0.5

        total_weight = 0.0
        weighted_match = 0.0

        for scenario in scenarios:
            weight = _LIKELIHOOD_WEIGHTS.get(scenario.likelihood, 0.5)
            total_weight += weight

            # Senaryo kosullarinin kac tanesi mevcut cevreyle uyumlu
            if scenario.conditions:
                matched = sum(
                    1
                    for key, val in scenario.conditions.items()
                    if self.environment.get(key) == val
                )
                match_ratio = matched / len(scenario.conditions)
            else:
                match_ratio = 0.5

            weighted_match += weight * match_ratio

        if total_weight == 0:
            return 0.5

        return weighted_match / total_weight

    def _generate_recommendation(
        self,
        score: float,
        strengths: list[str],
        weaknesses: list[str],
        strategy: Strategy,
    ) -> str:
        """Degerlendirmeye gore oneri uretir.

        Args:
            score: Genel puan.
            strengths: Guclu yonler.
            weaknesses: Zayif yonler.
            strategy: Degerlendirilen strateji.

        Returns:
            Oneri metni.
        """
        if score >= 0.8:
            return "Strateji basarili ilerliyor. Mevcut rotada devam edilmeli."
        elif score >= 0.6:
            if weaknesses:
                areas = ", ".join(w.split(":")[0] for w in weaknesses[:2])
                return f"Strateji orta seviyede. {areas} alanlarinda iyilestirme gerekli."
            return "Strateji kabul edilebilir seviyede. Kucuk iyilestirmeler yapilabilir."
        elif score >= 0.4:
            return "Strateji beklentilerin altinda. Revizyon veya alternatif strateji dusunulmeli."
        else:
            return "Strateji basarisiz. Acil strateji degisikligi oneriliyor."

    async def select_best_strategy(self) -> Strategy | None:
        """Mevcut kosullara en uygun stratejiyi secer.

        Tum stratejileri degerlendirir ve en yuksek puanliyi dondurur.

        Returns:
            En iyi strateji veya None.
        """
        if not self.strategies:
            return None

        best_score = -1.0
        best_strategy: Strategy | None = None

        for strategy_id, strategy in self.strategies.items():
            evaluation = await self.evaluate_strategy(strategy_id)
            if evaluation.score > best_score:
                best_score = evaluation.score
                best_strategy = strategy

        if best_strategy:
            logger.info(
                "En iyi strateji secildi: %s (puan=%.2f)",
                best_strategy.name,
                best_score,
            )

        return best_strategy

    async def adapt_strategy(self, strategy_id: str) -> Strategy | None:
        """Stratejiyi mevcut performansa gore adapte eder.

        Dusuk performansli KPI'lari analiz eder ve
        strateji parametrelerini gunceller.

        Args:
            strategy_id: Adapte edilecek strateji ID.

        Returns:
            Adapte edilmis strateji veya None.
        """
        strategy = self.strategies.get(strategy_id)
        if strategy is None:
            return None

        evaluation = await self.evaluate_strategy(strategy_id)

        # Dusuk puanli KPI'lari tespit et
        low_kpis = {
            kpi: score
            for kpi, score in evaluation.kpi_scores.items()
            if score < 0.5
        }

        if not low_kpis:
            return strategy

        # KPI hedeflerini gercekci seviyeye guncelle
        for kpi_name in low_kpis:
            history = self.kpi_history.get(kpi_name, [])
            if history and kpi_name in strategy.kpis:
                recent_avg = sum(history[-5:]) / len(history[-5:])
                current_target = strategy.kpis[kpi_name]
                # Hedefi mevcut performans ile hedef arasinin ortasina cek
                new_target = (recent_avg + current_target) / 2
                strategy.kpis[kpi_name] = new_target

        # Guven skorunu guncelle
        strategy.confidence = min(1.0, max(0.0, evaluation.score))

        logger.info(
            "Strateji adapte edildi: %s (yeni guven=%.2f)",
            strategy.name,
            strategy.confidence,
        )
        return strategy

    async def scenario_planning(
        self, scenarios: list[Scenario]
    ) -> dict[str, float]:
        """Senaryo planlama analizi yapar.

        Her senaryo icin beklenen etki hesaplar.

        Args:
            scenarios: Analiz edilecek senaryolar.

        Returns:
            Senaryo-etki eslesmesi (senaryo_id -> beklenen_etki).
        """
        results: dict[str, float] = {}

        for scenario in scenarios:
            weight = _LIKELIHOOD_WEIGHTS.get(scenario.likelihood, 0.5)
            probability = scenario.probability

            # Beklenen etki = olasilik * agirlik * toplam etki
            total_impact = sum(scenario.impact.values()) if scenario.impact else 0.0
            expected_impact = probability * weight * total_impact

            results[scenario.id] = expected_impact

        return results

    def get_kpi_trend(self, kpi_name: str, window: int = 5) -> float | None:
        """KPI trendini hesaplar.

        Son window kayit icin basit trend (son - ilk) / ilk.

        Args:
            kpi_name: KPI adi.
            window: Pencere buyuklugu.

        Returns:
            Trend degeri veya None.
        """
        history = self.kpi_history.get(kpi_name, [])
        if len(history) < 2:
            return None

        recent = history[-window:]
        if len(recent) < 2:
            return None

        first = recent[0]
        last = recent[-1]

        if first == 0:
            return None

        return (last - first) / abs(first)

    def get_active_strategy(self) -> Strategy | None:
        """Aktif stratejiyi dondurur.

        Returns:
            Aktif strateji veya None.
        """
        if self.active_strategy_id is None:
            return None
        return self.strategies.get(self.active_strategy_id)
