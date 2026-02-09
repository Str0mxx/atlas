"""UncertaintyManager testleri."""

import numpy as np
import pytest

from app.core.autonomy.uncertainty import UncertaintyManager


class TestUncertaintyManagerInit:
    """Init testleri."""

    def test_defaults(self) -> None:
        """Varsayilan degerler dogru olmalidir."""
        um = UncertaintyManager()
        assert um.default_confidence_level == 0.95
        assert um.risk_tolerance == 0.5

    def test_custom_params(self) -> None:
        """Ozel parametreler atanabilmelidir."""
        um = UncertaintyManager(
            default_confidence_level=0.99, risk_tolerance=0.8,
        )
        assert um.default_confidence_level == 0.99
        assert um.risk_tolerance == 0.8


class TestConfidenceIntervalCalc:
    """confidence_interval testleri."""

    def test_small_sample_t_dist(self) -> None:
        """n<30 icin t-dagilimi kullanilmalidir (daha genis CI)."""
        um = UncertaintyManager()
        data = list(np.random.default_rng(42).normal(10, 2, 10))
        ci = um.confidence_interval(data)
        assert ci.lower < ci.mean < ci.upper
        assert ci.confidence_level == 0.95

    def test_large_sample_normal(self) -> None:
        """n>=30 icin normal dagilim kullanilmalidir."""
        um = UncertaintyManager()
        data = list(np.random.default_rng(42).normal(50, 5, 100))
        ci = um.confidence_interval(data)
        assert ci.lower < ci.mean < ci.upper

    def test_single_value(self) -> None:
        """Tek deger icin lower==upper olmalidir."""
        um = UncertaintyManager()
        ci = um.confidence_interval([5.0])
        assert ci.lower == ci.upper == ci.mean == 5.0

    def test_custom_confidence_level(self) -> None:
        """Ozel guven duzeyi kullanilabilmelidir."""
        um = UncertaintyManager()
        data = list(np.random.default_rng(42).normal(0, 1, 50))
        ci_95 = um.confidence_interval(data, 0.95)
        ci_99 = um.confidence_interval(data, 0.99)
        # %99 CI %95'ten daha genis olmali
        width_95 = ci_95.upper - ci_95.lower
        width_99 = ci_99.upper - ci_99.lower
        assert width_99 > width_95


class TestQuantifyRisk:
    """quantify_risk testleri."""

    def test_uniform_outcomes(self) -> None:
        """Esit dagilmis sonuclar icin metrikler dogru olmalidir."""
        um = UncertaintyManager()
        outcomes = list(range(-10, 11))
        rq = um.quantify_risk(outcomes)
        assert rq.worst_case == -10
        assert rq.best_case == 10

    def test_with_probabilities(self) -> None:
        """Olasilikli sonuclar icin beklenen kayip dogru olmalidir."""
        um = UncertaintyManager()
        rq = um.quantify_risk(
            [100, -50], probabilities=[0.8, 0.2],
        )
        assert rq.expected_loss == pytest.approx(70.0)

    def test_all_positive(self) -> None:
        """Tumu pozitif sonuclarda kayip olasiligi sifir olmalidir."""
        um = UncertaintyManager()
        rq = um.quantify_risk([1.0, 2.0, 3.0, 4.0, 5.0])
        assert rq.probability_of_loss == 0.0

    def test_all_negative(self) -> None:
        """Tumu negatif sonuclarda kayip olasiligi 1.0 olmalidir."""
        um = UncertaintyManager()
        rq = um.quantify_risk([-5.0, -3.0, -1.0])
        assert rq.probability_of_loss == 1.0

    def test_empty(self) -> None:
        """Bos sonuclar varsayilan dondermelidir."""
        um = UncertaintyManager()
        rq = um.quantify_risk([])
        assert rq.expected_loss == 0.0


class TestScenarioAnalysisCalc:
    """scenario_analysis testleri."""

    def test_equal_probability(self) -> None:
        """Esit olasilikta expected_case ortalama olmalidir."""
        um = UncertaintyManager()
        sa = um.scenario_analysis({"good": 100, "bad": -50})
        assert sa.worst_case == -50
        assert sa.best_case == 100
        assert sa.expected_case == pytest.approx(25.0)

    def test_weighted(self) -> None:
        """Agirlikli senaryolar dogru beklenen deger uretmelidir."""
        um = UncertaintyManager()
        sa = um.scenario_analysis(
            {"good": 100, "bad": -50},
            probabilities={"good": 0.8, "bad": 0.2},
        )
        assert sa.expected_case == pytest.approx(70.0)

    def test_single_scenario(self) -> None:
        """Tek senaryoda tum degerler esit olmalidir."""
        um = UncertaintyManager()
        sa = um.scenario_analysis({"only": 42})
        assert sa.worst_case == sa.best_case == sa.expected_case == 42


class TestAggregateConfidence:
    """aggregate_confidence testleri."""

    def test_equal_weights(self) -> None:
        """Esit agirlikla geometrik ortalama dogru olmalidir."""
        um = UncertaintyManager()
        result = um.aggregate_confidence([0.9, 0.9, 0.9])
        assert result == pytest.approx(0.9, abs=0.01)

    def test_custom_weights(self) -> None:
        """Ozel agirliklar sonucu etkilemelidir."""
        um = UncertaintyManager()
        # Yuksek agirlikli yuksek guven, sonucu yukari ceker
        result = um.aggregate_confidence(
            [0.9, 0.1], weights=[0.9, 0.1],
        )
        assert result > 0.5

    def test_single_value(self) -> None:
        """Tek deger kendisini donmelidir."""
        um = UncertaintyManager()
        result = um.aggregate_confidence([0.8])
        assert result == pytest.approx(0.8, abs=0.01)

    def test_empty(self) -> None:
        """Bos liste sifir donmelidir."""
        um = UncertaintyManager()
        assert um.aggregate_confidence([]) == 0.0


class TestBeliefUncertainty:
    """belief_uncertainty testleri."""

    def test_all_confident(self) -> None:
        """Tumu yuksek guvenli belief'lerde entropi dusuk olmalidir."""
        um = UncertaintyManager()
        result = um.belief_uncertainty({"a": 0.99, "b": 0.99})
        assert result["entropy"] < 0.1

    def test_all_uncertain(self) -> None:
        """Tumu 0.5 guvenli belief'lerde entropi yuksek olmalidir."""
        um = UncertaintyManager()
        result = um.belief_uncertainty({"a": 0.5, "b": 0.5})
        assert result["entropy"] > 0.9

    def test_mixed(self) -> None:
        """Karisik guvenlerde min/max dogru olmalidir."""
        um = UncertaintyManager()
        result = um.belief_uncertainty({"a": 0.2, "b": 0.8})
        assert result["min_confidence"] == pytest.approx(0.2)
        assert result["max_confidence"] == pytest.approx(0.8)
        assert result["n_beliefs"] == 2

    def test_empty(self) -> None:
        """Bos belief sozlugu sifir donmelidir."""
        um = UncertaintyManager()
        result = um.belief_uncertainty({})
        assert result["entropy"] == 0.0
        assert result["n_beliefs"] == 0


class TestShouldAct:
    """should_act testleri."""

    def test_high_confidence_passes(self) -> None:
        """Yuksek guven aksiyona izin vermelidir."""
        um = UncertaintyManager(risk_tolerance=0.5)
        assert um.should_act(0.9, 0.5) is True

    def test_low_confidence_fails(self) -> None:
        """Dusuk guven aksiyonu engellemmelidir."""
        um = UncertaintyManager(risk_tolerance=0.5)
        assert um.should_act(0.2, 0.8) is False

    def test_explicit_threshold(self) -> None:
        """Acik esik dinamik esigi gecersiz kilmalidir."""
        um = UncertaintyManager(risk_tolerance=0.5)
        assert um.should_act(0.7, 0.9, threshold=0.6) is True
        assert um.should_act(0.5, 0.9, threshold=0.6) is False

    def test_high_tolerance_permissive(self) -> None:
        """Yuksek risk toleransi daha izin verici olmalidir."""
        um = UncertaintyManager(risk_tolerance=1.0)
        # risk_tolerance=1.0: threshold = 1 - 1*(1-risk) = risk
        # risk=0.3 -> threshold=0.3
        assert um.should_act(0.4, 0.3) is True

    def test_low_tolerance_conservative(self) -> None:
        """Dusuk risk toleransi daha muhafazakar olmalidir."""
        um = UncertaintyManager(risk_tolerance=0.0)
        # risk_tolerance=0.0: threshold = 1 - 0*(1-risk) = 1.0
        assert um.should_act(0.99, 0.5) is False

    def test_exact_threshold(self) -> None:
        """Esik degerinde True donmelidir."""
        um = UncertaintyManager()
        assert um.should_act(0.7, 0.5, threshold=0.7) is True
