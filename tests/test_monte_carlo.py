"""Monte Carlo simulasyon testleri."""

import numpy as np
import pytest

from app.core.autonomy.monte_carlo import MonteCarloSimulator
from app.models.probability import SimulationConfig


def _linear_model(x: float = 0.0, y: float = 0.0) -> float:
    """Basit lineer test modeli."""
    return 2 * x + 3 * y


def _single_var_model(price: float = 0.0) -> float:
    """Tek degiskenli test modeli."""
    return price * 1.1


class TestMonteCarloSimulatorInit:
    """Init testleri."""

    def test_defaults(self) -> None:
        """Varsayilan yapilandirma dogru olmalidir."""
        mc = MonteCarloSimulator()
        assert mc.config.n_simulations == 10000
        assert mc.config.random_seed is None

    def test_custom_config(self) -> None:
        """Ozel yapilandirma atanabilmelidir."""
        cfg = SimulationConfig(n_simulations=500, random_seed=42)
        mc = MonteCarloSimulator(config=cfg)
        assert mc.config.n_simulations == 500
        assert mc.config.random_seed == 42


class TestSimulate:
    """simulate testleri."""

    def test_normal_distribution(self) -> None:
        """Normal dagilimla simulasyon dogru istatistik vermelidir."""
        cfg = SimulationConfig(
            n_simulations=5000,
            random_seed=42,
            variables={
                "x": {"distribution": "normal", "params": {"mean": 10, "std": 2}},
            },
        )
        mc = MonteCarloSimulator(config=cfg)
        result = mc.simulate(lambda x: x)
        assert result.mean == pytest.approx(10, abs=0.5)
        assert result.std == pytest.approx(2, abs=0.5)
        assert result.n_simulations == 5000

    def test_uniform_distribution(self) -> None:
        """Uniform dagilim dogru aralikta orneklemmelidir."""
        cfg = SimulationConfig(
            n_simulations=5000,
            random_seed=42,
            variables={
                "x": {"distribution": "uniform", "params": {"low": 0, "high": 10}},
            },
        )
        mc = MonteCarloSimulator(config=cfg)
        result = mc.simulate(lambda x: x)
        assert result.mean == pytest.approx(5, abs=0.5)

    def test_beta_distribution(self) -> None:
        """Beta dagilim 0-1 araliginda orneklemmelidir."""
        cfg = SimulationConfig(
            n_simulations=5000,
            random_seed=42,
            variables={
                "x": {"distribution": "beta", "params": {"a": 2, "b": 5}},
            },
        )
        mc = MonteCarloSimulator(config=cfg)
        result = mc.simulate(lambda x: x)
        # Beta(2,5) mean = 2/7 ≈ 0.286
        assert 0.1 < result.mean < 0.5

    def test_triangular_distribution(self) -> None:
        """Ucgen dagilim dogru mod civarinda orneklemmelidir."""
        cfg = SimulationConfig(
            n_simulations=5000,
            random_seed=42,
            variables={
                "x": {"distribution": "triangular", "params": {"left": 0, "mode": 0.8, "right": 1}},
            },
        )
        mc = MonteCarloSimulator(config=cfg)
        result = mc.simulate(lambda x: x)
        assert 0.4 < result.mean < 0.8

    def test_multi_variable(self) -> None:
        """Cok degiskenli model dogru calismmalidir."""
        cfg = SimulationConfig(
            n_simulations=5000,
            random_seed=42,
            variables={
                "x": {"distribution": "normal", "params": {"mean": 1, "std": 0.1}},
                "y": {"distribution": "normal", "params": {"mean": 2, "std": 0.1}},
            },
        )
        mc = MonteCarloSimulator(config=cfg)
        result = mc.simulate(_linear_model)
        # E[2x + 3y] = 2*1 + 3*2 = 8
        assert result.mean == pytest.approx(8, abs=0.5)

    def test_percentiles(self) -> None:
        """Yuzdelik degerleri hesaplanmalidir."""
        cfg = SimulationConfig(
            n_simulations=1000,
            random_seed=42,
            variables={
                "x": {"distribution": "normal", "params": {"mean": 0, "std": 1}},
            },
        )
        mc = MonteCarloSimulator(config=cfg)
        result = mc.simulate(lambda x: x)
        assert "5" in result.percentiles
        assert "50" in result.percentiles
        assert "95" in result.percentiles
        assert result.percentiles["5"] < result.percentiles["95"]

    def test_confidence_interval(self) -> None:
        """Guven araligi hesaplanmalidir."""
        cfg = SimulationConfig(
            n_simulations=1000,
            random_seed=42,
            variables={
                "x": {"distribution": "normal", "params": {"mean": 50, "std": 5}},
            },
        )
        mc = MonteCarloSimulator(config=cfg)
        result = mc.simulate(lambda x: x)
        ci = result.confidence_interval
        assert ci is not None
        assert ci.lower < ci.mean < ci.upper

    def test_convergence(self) -> None:
        """Yeterli ornekte yakinsaklik saglanmalidir."""
        cfg = SimulationConfig(
            n_simulations=10000,
            random_seed=42,
            variables={
                "x": {"distribution": "normal", "params": {"mean": 100, "std": 1}},
            },
        )
        mc = MonteCarloSimulator(config=cfg)
        result = mc.simulate(lambda x: x)
        assert result.convergence_achieved is True


class TestSensitivityAnalysis:
    """sensitivity_analysis testleri."""

    def test_identifies_impactful_variable(self) -> None:
        """En etkili degisken dogru tanimlanmalidir."""
        cfg = SimulationConfig(
            n_simulations=2000,
            random_seed=42,
            variables={
                "x": {"distribution": "normal", "params": {"mean": 5, "std": 2}},
                "y": {"distribution": "normal", "params": {"mean": 5, "std": 0.01}},
            },
        )
        mc = MonteCarloSimulator(config=cfg)
        results = mc.sensitivity_analysis(_linear_model, cfg)
        assert "x" in results
        assert "y" in results
        # x daha etkili olmali (daha yuksek varyans)
        x_impact = results["x"].impact_scores.get("x", 0)
        y_impact = results["y"].impact_scores.get("y", 0)
        assert x_impact > y_impact

    def test_correlation_signs(self) -> None:
        """Korelasyon isareti dogru olmalidir."""
        cfg = SimulationConfig(
            n_simulations=2000,
            random_seed=42,
            variables={
                "x": {"distribution": "normal", "params": {"mean": 5, "std": 2}},
                "y": {"distribution": "normal", "params": {"mean": 5, "std": 2}},
            },
        )
        mc = MonteCarloSimulator(config=cfg)
        results = mc.sensitivity_analysis(_linear_model, cfg)
        # 2x + 3y: her ikisi de pozitif korelasyon
        assert results["x"].correlation_coefficients["x"] > 0
        assert results["y"].correlation_coefficients["y"] > 0

    def test_single_variable(self) -> None:
        """Tek degiskenli analiz calismmalidir."""
        cfg = SimulationConfig(
            n_simulations=1000,
            random_seed=42,
            variables={
                "price": {"distribution": "normal", "params": {"mean": 100, "std": 10}},
            },
        )
        mc = MonteCarloSimulator(config=cfg)
        results = mc.sensitivity_analysis(_single_var_model, cfg)
        assert "price" in results


class TestWhatIf:
    """what_if testleri."""

    def test_base_scenario(self) -> None:
        """Temel senaryo sonuc icermelidir."""
        mc = MonteCarloSimulator(
            config=SimulationConfig(n_simulations=500, random_seed=42),
        )
        results = mc.what_if(
            _single_var_model,
            base_params={"price": 100},
            scenarios={"high_price": {"price": 200}},
        )
        assert "base" in results
        assert "high_price" in results

    def test_scenario_comparison(self) -> None:
        """Yuksek parametreli senaryo daha yuksek sonuc vermelidir."""
        mc = MonteCarloSimulator(
            config=SimulationConfig(n_simulations=1000, random_seed=42),
        )
        results = mc.what_if(
            _single_var_model,
            base_params={"price": 100},
            scenarios={"double": {"price": 200}},
        )
        assert results["double"].mean > results["base"].mean

    def test_empty_scenarios(self) -> None:
        """Bos senaryo sadece base donmelidir."""
        mc = MonteCarloSimulator(
            config=SimulationConfig(n_simulations=500, random_seed=42),
        )
        results = mc.what_if(
            _single_var_model,
            base_params={"price": 50},
            scenarios={},
        )
        assert len(results) == 1
        assert "base" in results


class TestGenerateSamples:
    """_generate_samples testleri."""

    def test_normal(self) -> None:
        """Normal dagilim ornekleri dogru olmalidir."""
        mc = MonteCarloSimulator(
            config=SimulationConfig(random_seed=42),
        )
        samples = mc._generate_samples(
            {"distribution": "normal", "params": {"mean": 0, "std": 1}},
            1000,
        )
        assert len(samples) == 1000
        assert abs(np.mean(samples)) < 0.2

    def test_unknown_distribution(self) -> None:
        """Bilinmeyen dagilim normal varsayilan kullanmalidir."""
        mc = MonteCarloSimulator(
            config=SimulationConfig(random_seed=42),
        )
        samples = mc._generate_samples(
            {"distribution": "unknown_dist"}, 100,
        )
        assert len(samples) == 100


class TestCheckConvergence:
    """_check_convergence testleri."""

    def test_converged(self) -> None:
        """Yakinsamis seri True donmelidir."""
        mc = MonteCarloSimulator()
        rng = np.random.default_rng(42)
        results = rng.normal(10, 0.1, 10000)
        assert mc._check_convergence(results) is True

    def test_short_series(self) -> None:
        """Kisa seri False donmelidir."""
        mc = MonteCarloSimulator()
        results = np.array([1.0, 2.0, 3.0])
        assert mc._check_convergence(results) is False


class TestReproducibility:
    """Tekrarlanabilirlik testleri."""

    def test_same_seed_same_result(self) -> None:
        """Ayni seed ayni sonuc vermelidir."""
        cfg = SimulationConfig(
            n_simulations=1000, random_seed=42,
            variables={
                "x": {"distribution": "normal", "params": {"mean": 0, "std": 1}},
            },
        )
        mc1 = MonteCarloSimulator(config=cfg)
        mc2 = MonteCarloSimulator(config=cfg)
        r1 = mc1.simulate(lambda x: x, cfg)
        r2 = mc2.simulate(lambda x: x, cfg)
        assert r1.mean == pytest.approx(r2.mean, abs=0.001)
