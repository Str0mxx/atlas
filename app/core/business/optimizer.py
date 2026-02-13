"""ATLAS Is Optimizasyon modulu.

A/B testing, parametre ayarlama, kaynak yeniden dagitimi,
surec iyilestirme ve maliyet azaltma islemleri.
"""

import logging
import math
from datetime import datetime, timezone
from typing import Any

from app.models.business import (
    ActionPriority,
    Experiment,
    ExperimentStatus,
    ExperimentVariant,
    OptimizationSuggestion,
)

logger = logging.getLogger(__name__)


class BusinessOptimizer:
    """Is optimizasyon sistemi.

    A/B testler yapar, parametreleri ayarlar, kaynaklari
    yeniden dagitir, surecleri iyilestirir ve maliyet
    dusurme onerileri olusturur.

    Attributes:
        _experiments: Deneyler (id -> Experiment).
        _suggestions: Optimizasyon onerileri (id -> OptimizationSuggestion).
        _parameters: Ayarlanabilir parametreler (anahtar -> deger).
        _resource_allocations: Kaynak dagitimlari (alan -> yuzde).
    """

    def __init__(self) -> None:
        """Is optimizasyon sistemini baslatir."""
        self._experiments: dict[str, Experiment] = {}
        self._suggestions: dict[str, OptimizationSuggestion] = {}
        self._parameters: dict[str, Any] = {}
        self._resource_allocations: dict[str, float] = {}

        logger.info("BusinessOptimizer baslatildi")

    def create_experiment(
        self,
        name: str,
        metric_name: str,
        variants: list[dict[str, Any]],
        description: str = "",
        confidence_level: float = 0.95,
    ) -> Experiment:
        """A/B test deneyimi olusturur.

        Args:
            name: Deney adi.
            metric_name: Olculecek metrik.
            variants: Varyant tanimlari (name, parameters).
            description: Deney aciklamasi.
            confidence_level: Guven duzeyi (0.0-1.0).

        Returns:
            Olusturulan Experiment nesnesi.
        """
        experiment_variants = []
        for v in variants:
            variant = ExperimentVariant(
                name=v.get("name", ""),
                parameters=v.get("parameters", {}),
            )
            experiment_variants.append(variant)

        experiment = Experiment(
            name=name,
            description=description,
            metric_name=metric_name,
            variants=experiment_variants,
            confidence_level=confidence_level,
        )
        self._experiments[experiment.id] = experiment
        logger.info("Deney olusturuldu: %s (%d varyant)", name, len(experiment_variants))
        return experiment

    def start_experiment(self, experiment_id: str) -> bool:
        """Deneyimi baslatir.

        Args:
            experiment_id: Deney ID.

        Returns:
            Basarili mi.
        """
        exp = self._experiments.get(experiment_id)
        if not exp or exp.status != ExperimentStatus.DRAFT:
            return False

        exp.status = ExperimentStatus.RUNNING
        exp.started_at = datetime.now(timezone.utc)
        logger.info("Deney baslatildi: %s", exp.name)
        return True

    def record_result(self, experiment_id: str, variant_id: str, metric_value: float, sample_size: int = 1) -> bool:
        """Deney sonucu kaydeder.

        Args:
            experiment_id: Deney ID.
            variant_id: Varyant ID.
            metric_value: Olculen metrik degeri.
            sample_size: Ornek sayisi.

        Returns:
            Basarili mi.
        """
        exp = self._experiments.get(experiment_id)
        if not exp or exp.status != ExperimentStatus.RUNNING:
            return False

        variant = next((v for v in exp.variants if v.id == variant_id), None)
        if not variant:
            return False

        variant.metric_value = metric_value
        variant.sample_size += sample_size
        logger.info("Deney sonucu: %s, varyant=%s, deger=%.2f", exp.name, variant.name, metric_value)
        return True

    def conclude_experiment(self, experiment_id: str) -> str | None:
        """Deneyimi sonuclandirir ve kazanani belirler.

        En yuksek metrik degerine sahip varyant kazanan olur.
        Tum varyantlarin olculmus degeri yoksa sonuc cikarilmaz.

        Args:
            experiment_id: Deney ID.

        Returns:
            Kazanan varyant ID veya None.
        """
        exp = self._experiments.get(experiment_id)
        if not exp or exp.status != ExperimentStatus.RUNNING:
            return None

        # Olculmus varyantlari filtrele
        measured = [v for v in exp.variants if v.metric_value is not None]
        if not measured:
            return None

        winner = max(measured, key=lambda v: v.metric_value)  # type: ignore[arg-type]
        exp.winner_variant_id = winner.id
        exp.status = ExperimentStatus.CONCLUDED
        exp.completed_at = datetime.now(timezone.utc)
        logger.info("Deney sonuclandi: %s, kazanan=%s (%.2f)", exp.name, winner.name, winner.metric_value)  # type: ignore[arg-type]
        return winner.id

    def tune_parameter(self, key: str, value: Any) -> Any:
        """Parametre degerini ayarlar.

        Args:
            key: Parametre anahtari.
            value: Yeni deger.

        Returns:
            Onceki deger (yoksa None).
        """
        old_value = self._parameters.get(key)
        self._parameters[key] = value
        logger.info("Parametre ayarlandi: %s = %s (onceki: %s)", key, value, old_value)
        return old_value

    def get_parameter(self, key: str, default: Any = None) -> Any:
        """Parametre degerini getirir.

        Args:
            key: Parametre anahtari.
            default: Varsayilan deger.

        Returns:
            Parametre degeri.
        """
        return self._parameters.get(key, default)

    def allocate_resources(self, allocations: dict[str, float]) -> bool:
        """Kaynak dagitimini gunceller.

        Toplam dagilim %100'u gecemez.

        Args:
            allocations: Alan -> yuzde dagilimi.

        Returns:
            Basarili mi (toplam <= 100 ise).
        """
        total = sum(allocations.values())
        if total > 100.0:
            logger.warning("Kaynak dagitimi 100%%'u asiyor: %.1f%%", total)
            return False

        self._resource_allocations.update(allocations)
        logger.info("Kaynak dagitimi guncellendi: %s", allocations)
        return True

    def get_resource_allocation(self) -> dict[str, float]:
        """Mevcut kaynak dagitimini getirir.

        Returns:
            Alan -> yuzde dagitim haritasi.
        """
        return dict(self._resource_allocations)

    def suggest_improvement(
        self,
        area: str,
        description: str,
        expected_improvement: float = 0.0,
        effort_estimate: float = 0.0,
        priority: ActionPriority = ActionPriority.MEDIUM,
    ) -> OptimizationSuggestion:
        """Surec iyilestirme onerisi olusturur.

        Args:
            area: Optimizasyon alani.
            description: Oneri aciklamasi.
            expected_improvement: Beklenen iyilestirme (yuzde).
            effort_estimate: Efor tahmini (saat).
            priority: Oncelik.

        Returns:
            Olusturulan OptimizationSuggestion nesnesi.
        """
        suggestion = OptimizationSuggestion(
            area=area,
            description=description,
            expected_improvement=expected_improvement,
            effort_estimate=effort_estimate,
            priority=priority,
        )
        self._suggestions[suggestion.id] = suggestion
        logger.info("Iyilestirme onerisi: %s -> %s (%%%.1f)", area, description[:30], expected_improvement)
        return suggestion

    def apply_suggestion(self, suggestion_id: str) -> bool:
        """Iyilestirme onerisini uygular.

        Args:
            suggestion_id: Oneri ID.

        Returns:
            Basarili mi.
        """
        suggestion = self._suggestions.get(suggestion_id)
        if not suggestion or suggestion.applied:
            return False

        suggestion.applied = True
        logger.info("Oneri uygulandi: %s", suggestion.description[:30])
        return True

    def suggest_cost_reductions(self, costs: dict[str, float], target_reduction_pct: float = 10.0) -> list[OptimizationSuggestion]:
        """Maliyet azaltma onerileri olusturur.

        En yuksek maliyetli alanlardan baslayarak hedef
        azaltma yuzdesine ulasacak oneriler uretir.

        Args:
            costs: Alan -> maliyet haritasi.
            target_reduction_pct: Hedef azaltma yuzdesi.

        Returns:
            Maliyet azaltma onerileri.
        """
        if not costs:
            return []

        sorted_costs = sorted(costs.items(), key=lambda x: x[1], reverse=True)
        total_cost = sum(costs.values())
        target_savings = total_cost * (target_reduction_pct / 100)

        suggestions: list[OptimizationSuggestion] = []
        accumulated_savings = 0.0

        for area, cost in sorted_costs:
            if accumulated_savings >= target_savings:
                break

            # En yuksek maliyetli alanda %15 tasarruf varsayimi
            potential_saving = cost * 0.15
            suggestion = self.suggest_improvement(
                area=area,
                description=f"{area} maliyetini dusur (mevcut: {cost:.0f})",
                expected_improvement=15.0,
                effort_estimate=cost * 0.01,
                priority=ActionPriority.HIGH if cost > total_cost * 0.3 else ActionPriority.MEDIUM,
            )
            suggestions.append(suggestion)
            accumulated_savings += potential_saving

        logger.info("Maliyet azaltma: %d oneri, tahmini tasarruf=%.0f", len(suggestions), accumulated_savings)
        return suggestions

    def get_experiment(self, experiment_id: str) -> Experiment | None:
        """Deney bilgisi getirir.

        Args:
            experiment_id: Deney ID.

        Returns:
            Experiment nesnesi veya None.
        """
        return self._experiments.get(experiment_id)

    def get_pending_suggestions(self) -> list[OptimizationSuggestion]:
        """Uygulanmamis onerileri getirir.

        Returns:
            Uygulanmamis oneri listesi.
        """
        return [s for s in self._suggestions.values() if not s.applied]

    @property
    def experiment_count(self) -> int:
        """Toplam deney sayisi."""
        return len(self._experiments)

    @property
    def suggestion_count(self) -> int:
        """Toplam oneri sayisi."""
        return len(self._suggestions)
