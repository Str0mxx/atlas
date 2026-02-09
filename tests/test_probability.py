"""BayesianNetwork testleri."""

import pytest

from app.core.autonomy.probability import BayesianNetwork
from app.models.probability import (
    ConditionalProbability,
    Evidence,
    PriorBelief,
)


def _simple_network() -> BayesianNetwork:
    """Test icin basit bir Bayesci ag olusturur."""
    bn = BayesianNetwork()
    bn.add_node("weather", ["sunny", "rainy"])
    bn.set_prior(PriorBelief(
        variable="weather",
        probabilities={"sunny": 0.7, "rainy": 0.3},
    ))
    return bn


def _network_with_cpt() -> BayesianNetwork:
    """CPT'li test agi olusturur."""
    bn = _simple_network()
    bn.add_node("umbrella", ["yes", "no"])
    bn.set_prior(PriorBelief(
        variable="umbrella",
        probabilities={"yes": 0.4, "no": 0.6},
    ))
    bn.set_cpt(ConditionalProbability(
        child="umbrella",
        parents=["weather"],
        table={
            "rainy": {"yes": 0.9, "no": 0.1},
            "sunny": {"yes": 0.2, "no": 0.8},
        },
    ))
    return bn


class TestBayesianNetworkInit:
    """BayesianNetwork init testleri."""

    def test_empty_network(self) -> None:
        """Bos ag olusturulmalidir."""
        bn = BayesianNetwork()
        assert bn.nodes == {}
        assert bn.priors == {}
        assert bn.cpts == {}

    def test_correct_types(self) -> None:
        """Alanlar dogru tiplerde olmalidir."""
        bn = BayesianNetwork()
        assert isinstance(bn.nodes, dict)
        assert isinstance(bn.evidence_history, list)


class TestBayesianNetworkAddNode:
    """add_node testleri."""

    def test_single_node(self) -> None:
        """Tek dugum eklenmelidir."""
        bn = BayesianNetwork()
        bn.add_node("x", ["a", "b"])
        assert "x" in bn.nodes
        assert bn.nodes["x"] == ["a", "b"]

    def test_multiple_nodes(self) -> None:
        """Birden fazla dugum eklenmelidir."""
        bn = BayesianNetwork()
        bn.add_node("x", ["a", "b"])
        bn.add_node("y", ["c", "d", "e"])
        assert len(bn.nodes) == 2

    def test_overwrite(self) -> None:
        """Ayni isimli dugum uzerine yazilmalidir."""
        bn = BayesianNetwork()
        bn.add_node("x", ["a", "b"])
        bn.add_node("x", ["c", "d", "e"])
        assert bn.nodes["x"] == ["c", "d", "e"]


class TestBayesianNetworkSetPrior:
    """set_prior testleri."""

    def test_valid_prior(self) -> None:
        """Gecerli prior kaydedilmelidir."""
        bn = BayesianNetwork()
        bn.add_node("x", ["a", "b"])
        bn.set_prior(PriorBelief(
            variable="x", probabilities={"a": 0.6, "b": 0.4},
        ))
        assert "x" in bn.priors

    def test_invalid_sum_raises(self) -> None:
        """Toplami 1 olmayan prior hata vermmelidir."""
        bn = BayesianNetwork()
        with pytest.raises(ValueError, match="1'e toplanmali"):
            bn.set_prior(PriorBelief(
                variable="x", probabilities={"a": 0.3, "b": 0.3},
            ))

    def test_overwrite_prior(self) -> None:
        """Prior guncellenebilmelidir."""
        bn = _simple_network()
        bn.set_prior(PriorBelief(
            variable="weather",
            probabilities={"sunny": 0.5, "rainy": 0.5},
        ))
        assert bn.priors["weather"].probabilities["sunny"] == 0.5


class TestBayesianNetworkSetCpt:
    """set_cpt testleri."""

    def test_valid_cpt(self) -> None:
        """Gecerli CPT kaydedilmelidir."""
        bn = _network_with_cpt()
        assert "umbrella" in bn.cpts

    def test_invalid_row_raises(self) -> None:
        """Satir toplami 1 olmayan CPT hata vermelidir."""
        bn = BayesianNetwork()
        with pytest.raises(ValueError, match="1'e toplanmali"):
            bn.set_cpt(ConditionalProbability(
                child="y", parents=["x"],
                table={"a": {"c": 0.5, "d": 0.3}},
            ))


class TestBayesianNetworkUpdatePosterior:
    """update_posterior testleri."""

    def test_direct_evidence_shifts(self) -> None:
        """Dogrudan kanit posterior'i kaydirmalidir."""
        bn = _simple_network()
        ev = Evidence(variable="weather", observed_value="rainy", confidence=0.9)
        result = bn.update_posterior("weather", [ev])
        assert result.posterior["rainy"] > 0.3
        assert result.posterior["sunny"] < 0.7

    def test_multiple_evidence(self) -> None:
        """Birden fazla kanit islenmmelidir."""
        bn = _simple_network()
        evs = [
            Evidence(variable="weather", observed_value="rainy", confidence=0.8),
            Evidence(variable="weather", observed_value="rainy", confidence=0.7),
        ]
        result = bn.update_posterior("weather", evs)
        assert result.posterior["rainy"] > 0.5
        assert len(result.evidence_used) == 2

    def test_no_evidence_keeps_prior(self) -> None:
        """Kanit yoksa prior korunmalidir."""
        bn = _simple_network()
        result = bn.update_posterior("weather", [])
        assert abs(result.posterior["sunny"] - 0.7) < 0.01

    def test_extreme_confidence(self) -> None:
        """Asiri degerler crash etmemelidir."""
        bn = _simple_network()
        ev = Evidence(variable="weather", observed_value="sunny", confidence=1.0)
        result = bn.update_posterior("weather", [ev])
        assert result.posterior["sunny"] > 0.5
        assert sum(result.posterior.values()) == pytest.approx(1.0, abs=0.01)

    def test_unknown_variable(self) -> None:
        """Bilinmeyen degisken bos sonuc donmelidir."""
        bn = BayesianNetwork()
        result = bn.update_posterior("unknown", [])
        assert result.posterior == {}


class TestBayesianNetworkPropagateEvidence:
    """propagate_evidence testleri."""

    def test_propagates_to_self(self) -> None:
        """Kanit kendi degiskenini guncellemmelidir."""
        bn = _simple_network()
        ev = Evidence(variable="weather", observed_value="rainy", confidence=0.8)
        results = bn.propagate_evidence(ev)
        assert "weather" in results

    def test_propagates_to_children(self) -> None:
        """Kanit cocuk degiskenlere yayilmalidir."""
        bn = _network_with_cpt()
        ev = Evidence(variable="weather", observed_value="rainy", confidence=0.9)
        results = bn.propagate_evidence(ev)
        assert "umbrella" in results

    def test_returns_posterior_results(self) -> None:
        """Sonuclar PosteriorResult icermelidir."""
        bn = _simple_network()
        ev = Evidence(variable="weather", observed_value="sunny", confidence=0.8)
        results = bn.propagate_evidence(ev)
        for result in results.values():
            assert hasattr(result, "posterior")


class TestBayesianNetworkGetProbability:
    """get_probability testleri."""

    def test_from_prior(self) -> None:
        """Prior'dan olasilik donmelidir."""
        bn = _simple_network()
        assert bn.get_probability("weather", "sunny") == 0.7

    def test_uniform_if_no_prior(self) -> None:
        """Prior yoksa uniform dagitim donmelidir."""
        bn = BayesianNetwork()
        bn.add_node("x", ["a", "b"])
        assert bn.get_probability("x", "a") == 0.5

    def test_unknown_state(self) -> None:
        """Bilinmeyen durum icin 0 donmelidir."""
        bn = _simple_network()
        assert bn.get_probability("weather", "snowy") == 0.0


class TestBayesianNetworkJointProbability:
    """get_joint_probability testleri."""

    def test_independent_product(self) -> None:
        """Bagimsiz degiskenlerin birlesiik olasiligi carpimdir."""
        bn = BayesianNetwork()
        bn.add_node("a", ["x", "y"])
        bn.add_node("b", ["x", "y"])
        bn.set_prior(PriorBelief(variable="a", probabilities={"x": 0.6, "y": 0.4}))
        bn.set_prior(PriorBelief(variable="b", probabilities={"x": 0.3, "y": 0.7}))
        joint = bn.get_joint_probability({"a": "x", "b": "x"})
        assert joint == pytest.approx(0.18, abs=0.01)

    def test_empty_returns_zero(self) -> None:
        """Bos sorgu sifir donmelidir."""
        bn = BayesianNetwork()
        assert bn.get_joint_probability({}) == 0.0


class TestBayesianNetworkNormalize:
    """_normalize testleri."""

    def test_standard(self) -> None:
        """Standart normalizasyon calismmalidir."""
        bn = BayesianNetwork()
        result = bn._normalize({"a": 2.0, "b": 3.0})
        assert result["a"] == pytest.approx(0.4)
        assert result["b"] == pytest.approx(0.6)

    def test_zero_sum_uniform(self) -> None:
        """Sifir toplamda uniform donmelidir."""
        bn = BayesianNetwork()
        result = bn._normalize({"a": 0.0, "b": 0.0})
        assert result["a"] == pytest.approx(0.5)


class TestBayesianNetworkSnapshot:
    """snapshot testleri."""

    def test_structure(self) -> None:
        """Snapshot beklenen anahtarlari icermelidir."""
        bn = _simple_network()
        snap = bn.snapshot()
        assert "nodes" in snap
        assert "priors" in snap
        assert "evidence_count" in snap

    def test_reflects_state(self) -> None:
        """Snapshot mevcut durumu yansitmalidir."""
        bn = _simple_network()
        snap = bn.snapshot()
        assert "weather" in snap["nodes"]
        assert snap["evidence_count"] == 0
