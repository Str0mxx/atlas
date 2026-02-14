"""ATLAS Strateji Evrimcisi modulu.

Strateji mutasyonu, caprazlama,
uygunluk degerlendirme, secim baskisi
ve nesil takibi.
"""

import logging
import random
from typing import Any

from app.models.adaptive import (
    StrategyRecord,
    StrategyStatus,
)

logger = logging.getLogger(__name__)


class StrategyEvolver:
    """Strateji evrimcisi.

    Evrimsel algoritmalarla stratejileri
    gelistirir ve optimize eder.

    Attributes:
        _strategies: Strateji havuzu.
        _generation: Mevcut nesil.
        _mutation_rate: Mutasyon orani.
        _crossover_rate: Caprazlama orani.
    """

    def __init__(
        self,
        mutation_rate: float = 0.1,
        crossover_rate: float = 0.7,
    ) -> None:
        """Strateji evrimcisini baslatir.

        Args:
            mutation_rate: Mutasyon orani.
            crossover_rate: Caprazlama orani.
        """
        self._strategies: dict[str, StrategyRecord] = {}
        self._generation = 0
        self._mutation_rate = max(0.0, min(1.0, mutation_rate))
        self._crossover_rate = max(0.0, min(1.0, crossover_rate))
        self._history: list[dict[str, Any]] = []

        logger.info(
            "StrategyEvolver baslatildi "
            "(mutation=%.2f, crossover=%.2f)",
            self._mutation_rate, self._crossover_rate,
        )

    def create_strategy(
        self,
        name: str,
        parameters: dict[str, Any],
    ) -> StrategyRecord:
        """Strateji olusturur.

        Args:
            name: Strateji adi.
            parameters: Parametreler.

        Returns:
            Strateji kaydi.
        """
        strategy = StrategyRecord(
            name=name,
            status=StrategyStatus.CANDIDATE,
            generation=self._generation,
            parameters=parameters,
        )
        self._strategies[strategy.strategy_id] = strategy
        return strategy

    def mutate(
        self,
        strategy_id: str,
        param_key: str = "",
    ) -> StrategyRecord | None:
        """Stratejiyi mutasyona ugratir.

        Args:
            strategy_id: Strateji ID.
            param_key: Mutasyon parametresi.

        Returns:
            Yeni strateji veya None.
        """
        parent = self._strategies.get(strategy_id)
        if not parent:
            return None

        new_params = dict(parent.parameters)

        if param_key and param_key in new_params:
            val = new_params[param_key]
            if isinstance(val, (int, float)):
                factor = 1.0 + (random.random() - 0.5) * 0.4
                new_val = type(val)(val * factor)
                new_params[param_key] = new_val
        else:
            # Rastgele bir parametreyi mutasyona ugrat
            numeric_keys = [
                k for k, v in new_params.items()
                if isinstance(v, (int, float))
            ]
            if numeric_keys:
                key = random.choice(numeric_keys)
                val = new_params[key]
                factor = 1.0 + (random.random() - 0.5) * 0.4
                new_params[key] = type(val)(val * factor)

        child = StrategyRecord(
            name=f"{parent.name}_mut",
            status=StrategyStatus.CANDIDATE,
            generation=self._generation,
            parameters=new_params,
        )
        self._strategies[child.strategy_id] = child
        self._history.append({
            "op": "mutate",
            "parent": strategy_id,
            "child": child.strategy_id,
            "generation": self._generation,
        })
        return child

    def crossover(
        self,
        id_a: str,
        id_b: str,
    ) -> StrategyRecord | None:
        """Iki stratejiyi caprazlar.

        Args:
            id_a: Birinci strateji.
            id_b: Ikinci strateji.

        Returns:
            Yeni strateji veya None.
        """
        parent_a = self._strategies.get(id_a)
        parent_b = self._strategies.get(id_b)
        if not parent_a or not parent_b:
            return None

        new_params: dict[str, Any] = {}
        all_keys = set(parent_a.parameters) | set(
            parent_b.parameters,
        )
        for key in all_keys:
            if random.random() < 0.5:
                new_params[key] = parent_a.parameters.get(
                    key, parent_b.parameters.get(key),
                )
            else:
                new_params[key] = parent_b.parameters.get(
                    key, parent_a.parameters.get(key),
                )

        child = StrategyRecord(
            name=f"{parent_a.name}x{parent_b.name}",
            status=StrategyStatus.CANDIDATE,
            generation=self._generation,
            parameters=new_params,
        )
        self._strategies[child.strategy_id] = child
        self._history.append({
            "op": "crossover",
            "parents": [id_a, id_b],
            "child": child.strategy_id,
            "generation": self._generation,
        })
        return child

    def evaluate_fitness(
        self,
        strategy_id: str,
        fitness: float,
    ) -> bool:
        """Uygunluk degerini atar.

        Args:
            strategy_id: Strateji ID.
            fitness: Uygunluk degeri.

        Returns:
            Basarili ise True.
        """
        strategy = self._strategies.get(strategy_id)
        if not strategy:
            return False
        strategy.fitness = fitness
        strategy.status = StrategyStatus.TESTING
        return True

    def select_best(
        self,
        top_n: int = 3,
    ) -> list[StrategyRecord]:
        """En iyi stratejileri secer.

        Args:
            top_n: Kac tane secinelecek.

        Returns:
            En iyi stratejiler.
        """
        candidates = sorted(
            self._strategies.values(),
            key=lambda s: s.fitness,
            reverse=True,
        )
        return candidates[:top_n]

    def promote(
        self,
        strategy_id: str,
    ) -> bool:
        """Stratejiyi aktif yapar.

        Args:
            strategy_id: Strateji ID.

        Returns:
            Basarili ise True.
        """
        strategy = self._strategies.get(strategy_id)
        if not strategy:
            return False
        strategy.status = StrategyStatus.ACTIVE
        return True

    def retire(
        self,
        strategy_id: str,
    ) -> bool:
        """Stratejiyi emekli eder.

        Args:
            strategy_id: Strateji ID.

        Returns:
            Basarili ise True.
        """
        strategy = self._strategies.get(strategy_id)
        if not strategy:
            return False
        strategy.status = StrategyStatus.RETIRED
        return True

    def advance_generation(self) -> int:
        """Nesli ilerletir.

        Returns:
            Yeni nesil numarasi.
        """
        self._generation += 1
        return self._generation

    def get_strategy(
        self,
        strategy_id: str,
    ) -> dict[str, Any] | None:
        """Strateji bilgisi getirir.

        Args:
            strategy_id: Strateji ID.

        Returns:
            Strateji bilgisi veya None.
        """
        s = self._strategies.get(strategy_id)
        if not s:
            return None
        return {
            "strategy_id": s.strategy_id,
            "name": s.name,
            "status": s.status.value,
            "fitness": s.fitness,
            "generation": s.generation,
            "parameters": s.parameters,
        }

    @property
    def strategy_count(self) -> int:
        """Strateji sayisi."""
        return len(self._strategies)

    @property
    def generation(self) -> int:
        """Mevcut nesil."""
        return self._generation

    @property
    def active_count(self) -> int:
        """Aktif strateji sayisi."""
        return sum(
            1 for s in self._strategies.values()
            if s.status == StrategyStatus.ACTIVE
        )
