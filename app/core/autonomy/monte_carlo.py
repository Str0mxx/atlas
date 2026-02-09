"""ATLAS Monte Carlo simulasyon modulu.

Sonuc dagilimi, duyarlilik analizi ve what-if senaryolari
icin Monte Carlo simulasyon motoru.
"""

import logging
from typing import Any, Callable

import numpy as np
from scipy import stats

from app.models.probability import (
    ConfidenceInterval,
    SensitivityResult,
    SimulationConfig,
    SimulationResult,
)

logger = logging.getLogger("atlas.autonomy.monte_carlo")


class MonteCarloSimulator:
    """Monte Carlo simulasyon motoru.

    Tanimlanan degiskenler ve model fonksiyonu ile
    tekrarli simulasyon calistirarak sonuc dagilimi uretir.

    Attributes:
        config: Simulasyon yapilandirmasi.
        rng: Numpy rasgele sayi ureteci.
    """

    def __init__(
        self,
        config: SimulationConfig | None = None,
    ) -> None:
        """MonteCarloSimulator'u baslatir.

        Args:
            config: Simulasyon yapilandirmasi (None ise varsayilan).
        """
        self.config = config or SimulationConfig()
        seed = self.config.random_seed
        self.rng = np.random.default_rng(seed)
        logger.info(
            "MonteCarloSimulator olusturuldu (n=%d, seed=%s)",
            self.config.n_simulations, seed,
        )

    def simulate(
        self,
        model_fn: Callable[..., float],
        config: SimulationConfig | None = None,
    ) -> SimulationResult:
        """Monte Carlo simulasyonu calistirir.

        Args:
            model_fn: Degiskenlerden sonuc ureten fonksiyon.
                      keyword args alir (degisken adlarina gore).
            config: Ozel yapilandirma (None ise self.config).

        Returns:
            Simulasyon sonucu.
        """
        cfg = config or self.config
        n = cfg.n_simulations

        if cfg.random_seed is not None and config is not None:
            rng = np.random.default_rng(cfg.random_seed)
        else:
            rng = self.rng

        # Degisken orneklerini uret
        samples: dict[str, np.ndarray] = {}
        for var_name, var_config in cfg.variables.items():
            samples[var_name] = self._generate_samples(
                var_config, n, rng,
            )

        # Model fonksiyonunu her ornek icin calistir
        results = np.zeros(n)
        for i in range(n):
            kwargs = {
                name: float(arr[i]) for name, arr in samples.items()
            }
            results[i] = model_fn(**kwargs)

        # Istatistikler
        mean = float(np.mean(results))
        std = float(np.std(results, ddof=1)) if n > 1 else 0.0

        percentiles = {
            "5": float(np.percentile(results, 5)),
            "25": float(np.percentile(results, 25)),
            "50": float(np.percentile(results, 50)),
            "75": float(np.percentile(results, 75)),
            "95": float(np.percentile(results, 95)),
        }

        # Guven araligi
        se = std / np.sqrt(n) if n > 0 else 0.0
        if n >= 30:
            lower, upper = stats.norm.interval(0.95, loc=mean, scale=se)
        else:
            lower, upper = (mean - 2 * se, mean + 2 * se)

        ci = ConfidenceInterval(
            lower=float(lower), upper=float(upper),
            confidence_level=0.95, mean=mean,
        )

        convergence = self._check_convergence(results)

        return SimulationResult(
            mean=mean,
            std=std,
            percentiles=percentiles,
            confidence_interval=ci,
            n_simulations=n,
            convergence_achieved=convergence,
        )

    def sensitivity_analysis(
        self,
        model_fn: Callable[..., float],
        config: SimulationConfig | None = None,
    ) -> dict[str, SensitivityResult]:
        """Duyarlilik analizi yapar.

        Her degisken icin Spearman rank korelasyonu hesaplar.

        Args:
            model_fn: Model fonksiyonu.
            config: Simulasyon yapilandirmasi.

        Returns:
            Degisken -> SensitivityResult eslesmesi.
        """
        cfg = config or self.config
        n = cfg.n_simulations

        if cfg.random_seed is not None and config is not None:
            rng = np.random.default_rng(cfg.random_seed)
        else:
            rng = self.rng

        # Ornekleme
        samples: dict[str, np.ndarray] = {}
        for var_name, var_config in cfg.variables.items():
            samples[var_name] = self._generate_samples(
                var_config, n, rng,
            )

        # Ciktilari hesapla
        outputs = np.zeros(n)
        for i in range(n):
            kwargs = {
                name: float(arr[i]) for name, arr in samples.items()
            }
            outputs[i] = model_fn(**kwargs)

        base_value = float(np.mean(outputs))

        # Her degisken icin korelasyon
        results: dict[str, SensitivityResult] = {}
        correlations: dict[str, float] = {}

        for var_name, var_samples in samples.items():
            if np.std(var_samples) < 1e-10:
                corr = 0.0
            else:
                corr_result = stats.spearmanr(var_samples, outputs)
                corr = float(corr_result.statistic)

            correlations[var_name] = corr

        # Impact skorlari: mutlak korelasyona gore normalize
        total_abs_corr = sum(abs(c) for c in correlations.values())

        for var_name, corr in correlations.items():
            if total_abs_corr > 0:
                impact = abs(corr) / total_abs_corr
            else:
                impact = 0.0

            results[var_name] = SensitivityResult(
                variable=var_name,
                base_value=base_value,
                impact_scores={var_name: impact},
                correlation_coefficients={var_name: corr},
            )

        return results

    def what_if(
        self,
        model_fn: Callable[..., float],
        base_params: dict[str, float],
        scenarios: dict[str, dict[str, float]],
    ) -> dict[str, SimulationResult]:
        """What-if senaryolari calistirir.

        Her senaryo icin parametreleri degistirerek simulasyon yapar.

        Args:
            model_fn: Model fonksiyonu.
            base_params: Temel parametreler.
            scenarios: {senaryo_adi: {degisken: deger}}.

        Returns:
            Senaryo -> sonuc eslesmesi.
        """
        results: dict[str, SimulationResult] = {}

        # Temel senaryo
        base_cfg = SimulationConfig(
            n_simulations=self.config.n_simulations,
            random_seed=self.config.random_seed,
            variables={
                k: {"distribution": "normal", "params": {"mean": v, "std": abs(v) * 0.1 or 0.1}}
                for k, v in base_params.items()
            },
        )
        results["base"] = self.simulate(model_fn, base_cfg)

        # Senaryo simulasyonlari
        for scenario_name, scenario_params in scenarios.items():
            merged = dict(base_params)
            merged.update(scenario_params)
            scenario_cfg = SimulationConfig(
                n_simulations=self.config.n_simulations,
                random_seed=self.config.random_seed,
                variables={
                    k: {"distribution": "normal", "params": {"mean": v, "std": abs(v) * 0.1 or 0.1}}
                    for k, v in merged.items()
                },
            )
            results[scenario_name] = self.simulate(
                model_fn, scenario_cfg,
            )

        return results

    def _generate_samples(
        self,
        variable_config: dict[str, Any],
        n: int,
        rng: np.random.Generator | None = None,
    ) -> np.ndarray:
        """Degisken yapilandirmasina gore ornekler uretir.

        Args:
            variable_config: Dagilim tipi ve parametreleri.
            n: Ornek sayisi.
            rng: Rasgele sayi ureteci.

        Returns:
            Uretilen ornekler (numpy array).
        """
        gen = rng or self.rng
        dist = variable_config.get("distribution", "normal")
        params = variable_config.get("params", {})

        if dist == "normal":
            mean = params.get("mean", 0.0)
            std = params.get("std", 1.0)
            return gen.normal(mean, std, n)

        if dist == "uniform":
            low = params.get("low", 0.0)
            high = params.get("high", 1.0)
            return gen.uniform(low, high, n)

        if dist == "beta":
            a = params.get("a", 2.0)
            b = params.get("b", 5.0)
            return gen.beta(a, b, n)

        if dist == "triangular":
            left = params.get("left", 0.0)
            mode = params.get("mode", 0.5)
            right = params.get("right", 1.0)
            return gen.triangular(left, mode, right, n)

        # Varsayilan: normal
        logger.warning(
            "Bilinmeyen dagilim '%s', normal kullaniliyor", dist,
        )
        return gen.normal(0.0, 1.0, n)

    def _check_convergence(
        self,
        results: np.ndarray,
        threshold: float = 0.01,
    ) -> bool:
        """Simulasyonun yakinsayip yakinsamadigini kontrol eder.

        Son %10 ile tum orneklerin ortalamasini karsilastirir.

        Args:
            results: Simulasyon sonuclari.
            threshold: Yakinsaklik esigi.

        Returns:
            True ise yakinsamis.
        """
        n = len(results)
        if n < 20:
            return False

        full_mean = np.mean(results)
        tail_start = int(n * 0.9)
        tail_mean = np.mean(results[tail_start:])

        if abs(full_mean) < 1e-10:
            return bool(abs(tail_mean - full_mean) < threshold)

        relative_diff = abs(tail_mean - full_mean) / abs(full_mean)
        return bool(relative_diff < threshold)
