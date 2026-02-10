"""AdaptiveAgent kapsamli testleri.

Adaptif strateji yonetimi, konsept drift algilama,
UCB tabanli strateji secimi ve otonom adaptasyon testleri.
"""

import math

import numpy as np
import pytest

from app.core.learning.adaptation import AdaptiveAgent
from app.models.learning import DriftType


# === Yardimci fonksiyonlar ===

RNG = np.random.default_rng(42)


def _make_agent(
    strategies: list[str] | None = None,
    window_size: int = 20,
    drift_threshold: float = 0.05,
) -> AdaptiveAgent:
    """Test icin standart bir AdaptiveAgent olusturur."""
    if strategies is None:
        strategies = ["alpha", "beta", "gamma"]
    return AdaptiveAgent(
        strategies=strategies,
        window_size=window_size,
        drift_threshold=drift_threshold,
    )


def _fill_strategy(
    agent: AdaptiveAgent,
    strategy: str,
    values: list[float] | np.ndarray,
) -> None:
    """Bir strateji icin performans gecmisini doldurur."""
    for v in values:
        agent.record_outcome(strategy, float(v))


# === TestAdaptiveAgentInit ===


class TestAdaptiveAgentInit:
    """AdaptiveAgent.__init__ testleri."""

    def test_defaults(self) -> None:
        """Ilk strateji current_strategy olarak atanmalidir."""
        agent = AdaptiveAgent(strategies=["a", "b", "c"])
        state = agent.get_state()
        assert state.current_strategy == "a"
        assert set(state.strategies.keys()) == {"a", "b", "c"}
        assert state.switch_count == 0

    def test_empty_strategies_raises(self) -> None:
        """Bos strateji listesi ValueError firlatmalidir."""
        with pytest.raises(ValueError, match="En az bir strateji"):
            AdaptiveAgent(strategies=[])

    def test_custom_params(self) -> None:
        """Ozel window_size ve drift_threshold duzgun atanmalidir."""
        agent = AdaptiveAgent(
            strategies=["x"],
            window_size=100,
            drift_threshold=0.01,
        )
        assert agent.window_size == 100
        assert agent.drift_threshold == 0.01

    def test_single_strategy(self) -> None:
        """Tek strateji ile agent olusturulabilmelidir."""
        agent = AdaptiveAgent(strategies=["solo"])
        state = agent.get_state()
        assert state.current_strategy == "solo"
        assert len(state.strategies) == 1

    def test_strategies_are_copied(self) -> None:
        """Strategies listesi kopyalanmalidir, referans paylasmamallidir."""
        original = ["a", "b"]
        agent = AdaptiveAgent(strategies=original)
        original.append("c")
        assert len(agent.strategies) == 2


# === TestRecordOutcome ===


class TestRecordOutcome:
    """record_outcome testleri."""

    def test_single_record(self) -> None:
        """Tek bir kayit performans gecmisine eklenmalidir."""
        agent = _make_agent()
        agent.record_outcome("alpha", 1.5)
        state = agent.get_state()
        assert 1.5 in state.performance_history
        assert state.strategies["alpha"] == 1.5

    def test_multiple_records(self) -> None:
        """Birden fazla kayit dogru ortalama uretmelidir."""
        agent = _make_agent()
        agent.record_outcome("alpha", 1.0)
        agent.record_outcome("alpha", 3.0)
        agent.record_outcome("alpha", 5.0)
        state = agent.get_state()
        assert state.strategies["alpha"] == pytest.approx(3.0)
        assert len(state.performance_history) == 3

    def test_unknown_strategy_creates_entry(self) -> None:
        """Bilinmeyen strateji icin yeni performans girdisi olusturulmalidirr."""
        agent = _make_agent(strategies=["alpha"])
        agent.record_outcome("new_strategy", 2.0)
        # Performans kaydedilmeli ama strategies listesine eklenmemeli
        state = agent.get_state()
        assert 2.0 in state.performance_history

    def test_records_across_strategies(self) -> None:
        """Farkli stratejiler icin ayri kayitlar tutulmalidir."""
        agent = _make_agent()
        agent.record_outcome("alpha", 1.0)
        agent.record_outcome("beta", 5.0)
        state = agent.get_state()
        assert state.strategies["alpha"] == pytest.approx(1.0)
        assert state.strategies["beta"] == pytest.approx(5.0)

    def test_negative_reward(self) -> None:
        """Negatif odul duzgun kaydedilmelidir."""
        agent = _make_agent()
        agent.record_outcome("alpha", -3.0)
        state = agent.get_state()
        assert state.strategies["alpha"] == pytest.approx(-3.0)


# === TestDetectDrift ===


class TestDetectDrift:
    """detect_drift testleri."""

    def test_no_drift_insufficient_data(self) -> None:
        """Yetersiz veri ile drift algilanmamailidir."""
        agent = _make_agent(window_size=20)
        # 2*window_size = 40'tan az veri
        for i in range(30):
            agent.record_outcome("alpha", 1.0)
        result = agent.detect_drift("alpha")
        assert result.detected is False
        assert result.p_value == 1.0

    def test_no_drift_empty_history(self) -> None:
        """Bos gecmis ile drift algilanmamalidir."""
        agent = _make_agent(window_size=20)
        result = agent.detect_drift("alpha")
        assert result.detected is False
        assert result.window_mean == 0.0
        assert result.reference_mean == 0.0
        assert result.p_value == 1.0

    def test_no_drift_stable(self) -> None:
        """Sabit oduller ile drift algilanmamalidir."""
        agent = _make_agent(window_size=20)
        rng = np.random.default_rng(42)
        # Ayni dagilimdan 60 ornek (2*20 + 20 fazla)
        stable_data = rng.normal(loc=5.0, scale=0.1, size=60)
        _fill_strategy(agent, "alpha", stable_data)

        result = agent.detect_drift("alpha")
        assert result.detected is False
        assert result.p_value > agent.drift_threshold

    def test_drift_detected_sudden(self) -> None:
        """Ani degisim ile drift algilanmalidir."""
        agent = _make_agent(window_size=20, drift_threshold=0.05)
        # Ilk 60 ornek: 1.0 civari, son 20 ornek: 5.0 civari
        rng = np.random.default_rng(42)
        reference_data = rng.normal(loc=1.0, scale=0.1, size=60)
        drift_data = rng.normal(loc=5.0, scale=0.1, size=20)

        _fill_strategy(agent, "alpha", reference_data)
        _fill_strategy(agent, "alpha", drift_data)

        result = agent.detect_drift("alpha")
        assert result.detected is True
        assert result.drift_type == DriftType.SUDDEN
        assert result.p_value < 0.05
        assert result.confidence > 0.95

    def test_drift_type_sudden(self) -> None:
        """Buyuk fark orani (>0.5) SUDDEN donmalidir."""
        agent = _make_agent(window_size=20)
        # ref_mean ~= 1.0, win_mean ~= 3.0 => diff_ratio ~= 2.0 > 0.5
        ref_data = np.ones(40) * 1.0
        win_data = np.ones(20) * 3.0
        _fill_strategy(agent, "alpha", np.concatenate([ref_data, win_data]))

        result = agent.detect_drift("alpha")
        assert result.detected is True
        assert result.drift_type == DriftType.SUDDEN

    def test_drift_type_gradual(self) -> None:
        """Orta fark orani (0.2 < ratio <= 0.5) GRADUAL donmalidir."""
        agent = _make_agent(window_size=20, drift_threshold=0.05)
        # ref_mean = 1.0, win_mean = 1.35 => diff_ratio = 0.35
        rng = np.random.default_rng(42)
        ref_data = rng.normal(loc=1.0, scale=0.01, size=40)
        win_data = rng.normal(loc=1.35, scale=0.01, size=20)
        _fill_strategy(agent, "alpha", np.concatenate([ref_data, win_data]))

        result = agent.detect_drift("alpha")
        assert result.detected is True
        assert result.drift_type == DriftType.GRADUAL

    def test_drift_type_incremental(self) -> None:
        """Kucuk fark orani (<=0.2) INCREMENTAL donmalidir."""
        agent = _make_agent(window_size=20, drift_threshold=0.05)
        # ref_mean = 1.0, win_mean = 1.15 => diff_ratio = 0.15
        rng = np.random.default_rng(42)
        ref_data = rng.normal(loc=1.0, scale=0.01, size=40)
        win_data = rng.normal(loc=1.15, scale=0.01, size=20)
        _fill_strategy(agent, "alpha", np.concatenate([ref_data, win_data]))

        result = agent.detect_drift("alpha")
        assert result.detected is True
        assert result.drift_type == DriftType.INCREMENTAL

    def test_drift_uses_current_strategy_by_default(self) -> None:
        """Strateji belirtilmezse mevcut strateji kontrol edilmelidir."""
        agent = _make_agent(window_size=20)
        rng = np.random.default_rng(42)
        # alpha mevcut strateji (ilk eleman)
        stable_data = rng.normal(loc=5.0, scale=0.1, size=60)
        _fill_strategy(agent, "alpha", stable_data)

        result = agent.detect_drift()  # strategy=None
        assert result.detected is False
        assert result.window_mean != 0.0

    def test_drift_detection_appends_history(self) -> None:
        """Drift algilandiginda gecmise eklenmalidir."""
        agent = _make_agent(window_size=20)
        ref_data = np.ones(40) * 1.0
        drift_data = np.ones(20) * 10.0
        _fill_strategy(agent, "alpha", np.concatenate([ref_data, drift_data]))

        agent.detect_drift("alpha")
        state = agent.get_state()
        assert len(state.drift_detections) == 1
        assert state.drift_detections[0].detected is True

    def test_drift_window_and_reference_means(self) -> None:
        """Pencere ve referans ortalamalari dogru hesaplanmalidir."""
        agent = _make_agent(window_size=20)
        ref_data = np.ones(40) * 2.0
        win_data = np.ones(20) * 8.0
        _fill_strategy(agent, "alpha", np.concatenate([ref_data, win_data]))

        result = agent.detect_drift("alpha")
        assert result.reference_mean == pytest.approx(2.0)
        assert result.window_mean == pytest.approx(8.0)


# === TestSelectStrategy ===


class TestSelectStrategy:
    """select_strategy testleri."""

    def test_untried_first(self) -> None:
        """Denenmemis strateji oncelikli secilmelidir."""
        agent = _make_agent(strategies=["alpha", "beta", "gamma"])
        agent.record_outcome("alpha", 100.0)
        # beta denenmemis, onu donmeli
        selected = agent.select_strategy()
        assert selected == "beta"

    def test_untried_returns_first_untried(self) -> None:
        """Birden fazla denenmemis strateji varsa ilki donmalidir."""
        agent = _make_agent(strategies=["alpha", "beta", "gamma"])
        agent.record_outcome("alpha", 5.0)
        selected = agent.select_strategy()
        # Dongude ilk denenmemis strateji donmeli
        assert selected == "beta"

    def test_no_data_returns_first(self) -> None:
        """Hic veri yoksa ilk strateji donmalidir."""
        agent = _make_agent()
        selected = agent.select_strategy()
        assert selected == "alpha"

    def test_best_average(self) -> None:
        """Yeterli veri ile en yuksek UCB skorlu strateji secilmelidir."""
        agent = _make_agent(strategies=["alpha", "beta"])
        # Her ikisi de denensin
        for _ in range(50):
            agent.record_outcome("alpha", 1.0)
        for _ in range(50):
            agent.record_outcome("beta", 5.0)
        selected = agent.select_strategy()
        # beta'nin ortalamasi cok daha yuksek, UCB skoru da yuksek olmali
        assert selected == "beta"

    def test_ucb_exploration(self) -> None:
        """Az denenmis stratejiye UCB kesfif bonusu uygulanmalidir."""
        agent = _make_agent(strategies=["alpha", "beta"])
        # alpha cok denenmis, beta az denenmis
        for _ in range(100):
            agent.record_outcome("alpha", 2.0)
        agent.record_outcome("beta", 1.5)

        # UCB bonusu: sqrt(2 * ln(total) / count)
        # alpha: avg=2.0, bonus=sqrt(2*ln(101)/100) ~ 0.30
        # beta: avg=1.5, bonus=sqrt(2*ln(101)/1) ~ 3.04
        # beta score ~= 4.54, alpha score ~= 2.30
        selected = agent.select_strategy()
        assert selected == "beta"

    def test_ucb_convergence(self) -> None:
        """Yeterli kesfiften sonra UCB en iyi stratejiyi secmelidir."""
        agent = _make_agent(strategies=["alpha", "beta"])
        rng = np.random.default_rng(42)
        # Her iki strateji de yeterince denenmis
        for _ in range(200):
            agent.record_outcome("alpha", float(rng.normal(1.0, 0.1)))
        for _ in range(200):
            agent.record_outcome("beta", float(rng.normal(5.0, 0.1)))
        selected = agent.select_strategy()
        assert selected == "beta"


# === TestSwitchStrategy ===


class TestSwitchStrategy:
    """switch_strategy testleri."""

    def test_switch_increments_count(self) -> None:
        """Farkli stratejiye gecis switch_count artirmalidir."""
        agent = _make_agent(strategies=["alpha", "beta"])
        assert agent.get_state().switch_count == 0
        agent.switch_strategy("beta")
        assert agent.get_state().switch_count == 1
        assert agent.get_state().current_strategy == "beta"

    def test_switch_to_same_no_op(self) -> None:
        """Ayni stratejiye gecis switch_count artirmamalidir."""
        agent = _make_agent(strategies=["alpha", "beta"])
        agent.switch_strategy("alpha")  # Zaten alpha
        assert agent.get_state().switch_count == 0
        assert agent.get_state().current_strategy == "alpha"

    def test_switch_unknown_ignores(self) -> None:
        """Bilinmeyen stratejiye gecis yoksayilmalidir."""
        agent = _make_agent(strategies=["alpha", "beta"])
        agent.switch_strategy("nonexistent")
        assert agent.get_state().switch_count == 0
        assert agent.get_state().current_strategy == "alpha"

    def test_multiple_switches(self) -> None:
        """Birden fazla gecis dogru sayilmalidir."""
        agent = _make_agent(strategies=["alpha", "beta", "gamma"])
        agent.switch_strategy("beta")
        agent.switch_strategy("gamma")
        agent.switch_strategy("alpha")
        assert agent.get_state().switch_count == 3

    def test_switch_back_and_forth(self) -> None:
        """Ileri geri gecisler her seferinde sayilmalidir."""
        agent = _make_agent(strategies=["alpha", "beta"])
        agent.switch_strategy("beta")
        agent.switch_strategy("alpha")
        agent.switch_strategy("beta")
        assert agent.get_state().switch_count == 3
        assert agent.get_state().current_strategy == "beta"


# === TestAdapt ===


class TestAdapt:
    """adapt testleri."""

    def test_adapt_no_change(self) -> None:
        """Drift yoksa ve mevcut strateji en iyiyse degismemeli."""
        agent = _make_agent(strategies=["alpha", "beta"], window_size=20)
        # alpha en iyi, yeterli veri yok drift icin
        for _ in range(10):
            agent.record_outcome("alpha", 5.0)
            agent.record_outcome("beta", 1.0)

        result = agent.adapt()
        # Yeterli veri yok drift icin, alpha zaten iyi
        assert agent.get_state().current_strategy == result

    def test_adapt_with_drift(self) -> None:
        """Drift algilandiginda strateji degisimi tetiklenmelidir."""
        agent = _make_agent(strategies=["alpha", "beta"], window_size=20)

        # alpha icin drift olustur: once iyi, sonra kotu
        good_data = np.ones(40) * 5.0
        bad_data = np.ones(20) * 0.1
        _fill_strategy(agent, "alpha", np.concatenate([good_data, bad_data]))

        # beta iyi performans gostersin
        _fill_strategy(agent, "beta", np.ones(60) * 4.0)

        result = agent.adapt()
        # Drift algilanmali ve beta'ya gecmeli
        assert result == "beta"
        assert agent.get_state().current_strategy == "beta"

    def test_adapt_switches_to_better(self) -> None:
        """Daha iyi bir strateji varsa gecis yapilmalidir."""
        agent = _make_agent(strategies=["alpha", "beta"], window_size=20)

        # alpha kotu, drift ile daha da kotulesiyor
        ref_data = np.ones(40) * 1.0
        drift_data = np.ones(20) * 0.01
        _fill_strategy(agent, "alpha", np.concatenate([ref_data, drift_data]))

        # beta cok iyi
        _fill_strategy(agent, "beta", np.ones(60) * 10.0)

        result = agent.adapt()
        assert result == "beta"

    def test_adapt_returns_current_when_no_data(self) -> None:
        """Veri yoksa mevcut stratejiyi donmalidir."""
        agent = _make_agent(strategies=["alpha", "beta"])
        result = agent.adapt()
        assert result == "alpha"

    def test_adapt_with_untried_strategy(self) -> None:
        """Denenmemis strateji varsa drift durumunda ona gecmeli."""
        agent = _make_agent(strategies=["alpha", "beta", "gamma"], window_size=20)

        # alpha icin drift olustur
        ref_data = np.ones(40) * 5.0
        drift_data = np.ones(20) * 0.1
        _fill_strategy(agent, "alpha", np.concatenate([ref_data, drift_data]))

        # beta denenmemis (select_strategy bunu tercih eder)
        result = agent.adapt()
        # Drift algliandiktan sonra denenmemis strateji secilmeli
        assert result == "beta"

    def test_adapt_idempotent_without_drift(self) -> None:
        """Drift yoksa tekrar adapt cagrisi strateji degistirmemeli."""
        agent = _make_agent(strategies=["alpha", "beta"], window_size=20)
        rng = np.random.default_rng(42)
        stable_data = rng.normal(loc=3.0, scale=0.1, size=15)
        _fill_strategy(agent, "alpha", stable_data)
        _fill_strategy(agent, "beta", stable_data)

        result1 = agent.adapt()
        result2 = agent.adapt()
        assert result1 == result2


# === TestGetState ===


class TestGetState:
    """get_state testleri."""

    def test_state_fields(self) -> None:
        """AdaptationState tum gerekli alanlari icermelidir."""
        agent = _make_agent(strategies=["alpha", "beta"])
        state = agent.get_state()
        assert hasattr(state, "current_strategy")
        assert hasattr(state, "strategies")
        assert hasattr(state, "switch_count")
        assert hasattr(state, "performance_history")
        assert hasattr(state, "drift_detections")

    def test_state_initial_values(self) -> None:
        """Baslangic durumu dogru olmalidir."""
        agent = _make_agent(strategies=["alpha", "beta"])
        state = agent.get_state()
        assert state.current_strategy == "alpha"
        assert state.strategies == {"alpha": 0.0, "beta": 0.0, "gamma": 0.0} or \
            state.strategies == {"alpha": 0.0, "beta": 0.0}
        assert state.switch_count == 0
        assert state.performance_history == []
        assert state.drift_detections == []

    def test_state_after_operations(self) -> None:
        """Islemlerden sonra durum dogru guncellenmeli."""
        agent = _make_agent(strategies=["alpha", "beta"], window_size=20)

        # Kayitlar ekle
        agent.record_outcome("alpha", 1.0)
        agent.record_outcome("alpha", 3.0)
        agent.record_outcome("beta", 5.0)

        # Strateji degistir
        agent.switch_strategy("beta")

        state = agent.get_state()
        assert state.current_strategy == "beta"
        assert state.strategies["alpha"] == pytest.approx(2.0)
        assert state.strategies["beta"] == pytest.approx(5.0)
        assert state.switch_count == 1
        assert len(state.performance_history) == 3

    def test_state_performance_history_limit(self) -> None:
        """Performans gecmisi en fazla 100 kayit donmalidir."""
        agent = _make_agent(strategies=["alpha"], window_size=20)
        for i in range(150):
            agent.record_outcome("alpha", float(i))
        state = agent.get_state()
        assert len(state.performance_history) == 100
        # Son 100 kayit gelmeli
        assert state.performance_history[0] == pytest.approx(50.0)
        assert state.performance_history[-1] == pytest.approx(149.0)

    def test_state_drift_detections_limit(self) -> None:
        """Drift gecmisi en fazla 10 kayit donmalidir."""
        agent = _make_agent(strategies=["alpha"], window_size=20)
        # 12 adet drift algilama olustur
        for i in range(12):
            ref_data = np.ones(40) * 1.0
            drift_data = np.ones(20) * (10.0 + i)
            _fill_strategy(agent, "alpha", np.concatenate([ref_data, drift_data]))
            agent.detect_drift("alpha")
            # Gecmisi sifirla, tekrar doldurmak icin
            agent._performance["alpha"] = []

        state = agent.get_state()
        assert len(state.drift_detections) <= 10

    def test_state_strategies_scores(self) -> None:
        """Strateji skorlari ortalama odul olmalidir."""
        agent = _make_agent(strategies=["alpha", "beta", "gamma"])
        agent.record_outcome("alpha", 2.0)
        agent.record_outcome("alpha", 4.0)
        agent.record_outcome("beta", 10.0)
        # gamma'ya kayit eklenmemis

        state = agent.get_state()
        assert state.strategies["alpha"] == pytest.approx(3.0)
        assert state.strategies["beta"] == pytest.approx(10.0)
        assert state.strategies["gamma"] == pytest.approx(0.0)


# === Ek entegrasyon testleri ===


class TestAdaptiveAgentIntegration:
    """Uçtan uca entegrasyon testleri."""

    def test_full_lifecycle(self) -> None:
        """Tam yasam dongusu: kayit, drift, adaptasyon."""
        agent = _make_agent(strategies=["alpha", "beta", "gamma"], window_size=20)
        rng = np.random.default_rng(42)

        # Faz 1: alpha baslangicdaki en iyi, beta de iyi
        _fill_strategy(agent, "alpha", rng.normal(3.0, 0.1, size=40))
        _fill_strategy(agent, "beta", rng.normal(5.0, 0.1, size=40))
        _fill_strategy(agent, "gamma", rng.normal(1.0, 0.1, size=40))

        # Drift oncesi: alpha mevcut strateji
        state1 = agent.get_state()
        assert state1.current_strategy == "alpha"

        # Faz 2: alpha performansi dusuyor (drift)
        _fill_strategy(agent, "alpha", rng.normal(0.1, 0.01, size=20))

        # adapt() cagrisi drift algilayip strateji degistirmeli
        # beta UCB skoru en yuksek olmali (avg ~5.0)
        new_strategy = agent.adapt()
        assert new_strategy == "beta"
        assert agent.get_state().switch_count >= 1

    def test_drift_then_recovery(self) -> None:
        """Drift sonrasi yeni stratejiye gecis ve calisma."""
        agent = _make_agent(strategies=["alpha", "beta"], window_size=20)

        # alpha stabil baslasin
        _fill_strategy(agent, "alpha", np.ones(40) * 5.0)
        _fill_strategy(agent, "beta", np.ones(40) * 4.0)

        # alpha'da drift
        _fill_strategy(agent, "alpha", np.ones(20) * 0.5)

        agent.adapt()
        assert agent.get_state().current_strategy == "beta"

        # beta ile devam et
        _fill_strategy(agent, "beta", np.ones(20) * 4.0)
        result = agent.adapt()
        assert result == "beta"

    def test_confidence_range(self) -> None:
        """Drift confidence 0 ile 1 arasinda olmalidir."""
        agent = _make_agent(window_size=20)
        ref_data = np.ones(40) * 1.0
        drift_data = np.ones(20) * 10.0
        _fill_strategy(agent, "alpha", np.concatenate([ref_data, drift_data]))

        result = agent.detect_drift("alpha")
        assert 0.0 <= result.confidence <= 1.0

    def test_p_value_range(self) -> None:
        """p_value 0 ile 1 arasinda olmalidir."""
        agent = _make_agent(window_size=20)
        rng = np.random.default_rng(42)
        data = rng.normal(loc=3.0, scale=1.0, size=60)
        _fill_strategy(agent, "alpha", data)

        result = agent.detect_drift("alpha")
        assert 0.0 <= result.p_value <= 1.0
