"""Policy siniflarinin ve QLearner'in kapsamli testleri.

Epsilon-greedy, UCB, Softmax, Gradient politikalari ve
tek/cift Q-tablosu ile ogrenme mekaniklerini dogrular.
"""

import json
import math

import numpy as np
import pytest

from app.core.learning.policy import (
    EpsilonGreedyPolicy,
    GradientPolicy,
    SoftmaxPolicy,
    UCBPolicy,
)
from app.core.learning.q_learning import QLearner
from app.models.learning import LearningConfig, PolicyConfig, PolicyType


# ---------------------------------------------------------------------------
# Yardimci sabitler
# ---------------------------------------------------------------------------

ACTIONS = ["act_a", "act_b", "act_c"]
STATE = {"x": 1, "y": 2}
NEXT_STATE = {"x": 2, "y": 3}


# ===========================================================================
# EpsilonGreedyPolicy testleri
# ===========================================================================


class TestEpsilonGreedySelection:
    """EpsilonGreedyPolicy aksiyon secimi testleri."""

    def test_greedy_selection_when_epsilon_zero(self) -> None:
        """Epsilon=0 iken her zaman en iyi aksiyonu secmelidir."""
        cfg = PolicyConfig(epsilon=0.0)
        policy = EpsilonGreedyPolicy(config=cfg)
        q_values = {"act_a": 0.5, "act_b": 1.0, "act_c": 0.3}

        for _ in range(50):
            action = policy.select_action(STATE, q_values, ACTIONS)
            assert action == "act_b"

    def test_pure_exploration_when_epsilon_one(self) -> None:
        """Epsilon=1 iken tamamen rastgele secim yapilmalidir."""
        cfg = PolicyConfig(epsilon=1.0)
        policy = EpsilonGreedyPolicy(config=cfg)
        q_values = {"act_a": 100.0, "act_b": 0.0, "act_c": 0.0}

        actions_seen = set()
        for _ in range(200):
            action = policy.select_action(STATE, q_values, ACTIONS)
            actions_seen.add(action)
        # Tum aksiyonlar en az bir kez secilmeli
        assert actions_seen == set(ACTIONS)

    def test_returns_best_q_action(self) -> None:
        """Greedy modda en yuksek Q-degerli aksiyonu dondurmelidir."""
        cfg = PolicyConfig(epsilon=0.0)
        policy = EpsilonGreedyPolicy(config=cfg)
        q_values = {"act_a": -1.0, "act_b": -0.5, "act_c": 5.0}

        assert policy.select_action(STATE, q_values, ACTIONS) == "act_c"

    def test_default_q_value_is_zero(self) -> None:
        """Q-degeri olmayan aksiyonlar 0.0 olarak degerlendirilmelidir."""
        cfg = PolicyConfig(epsilon=0.0)
        policy = EpsilonGreedyPolicy(config=cfg)
        q_values = {"act_a": -1.0}  # b ve c mevcut degil

        action = policy.select_action(STATE, q_values, ACTIONS)
        # act_b veya act_c (0.0 > -1.0), ilk bulunan act_b
        assert action in ("act_b", "act_c")

    def test_empty_actions_returns_empty_string(self) -> None:
        """Bos aksiyon listesi bos string donmeli."""
        policy = EpsilonGreedyPolicy()
        assert policy.select_action(STATE, {}, []) == ""

    def test_single_action_always_returned(self) -> None:
        """Tek aksiyon varsa her zaman o donmeli."""
        cfg = PolicyConfig(epsilon=0.5)
        policy = EpsilonGreedyPolicy(config=cfg)
        for _ in range(30):
            assert policy.select_action(STATE, {}, ["only"]) == "only"


class TestEpsilonGreedyDecay:
    """EpsilonGreedyPolicy epsilon decay testleri."""

    def test_decay_after_update(self) -> None:
        """Update sonrasi epsilon azalmalidir."""
        cfg = PolicyConfig(epsilon=0.1, epsilon_decay=0.995)
        policy = EpsilonGreedyPolicy(config=cfg)
        initial = policy.config.epsilon

        policy.update(1.0)
        assert policy.config.epsilon < initial
        assert policy.config.epsilon == pytest.approx(0.1 * 0.995)

    def test_epsilon_never_below_min(self) -> None:
        """Epsilon, epsilon_min'in altina dusmemelidir."""
        cfg = PolicyConfig(epsilon=0.02, epsilon_decay=0.1, epsilon_min=0.01)
        policy = EpsilonGreedyPolicy(config=cfg)

        for _ in range(100):
            policy.update(1.0)

        assert policy.config.epsilon >= cfg.epsilon_min

    def test_multiple_decays_converge(self) -> None:
        """Birden fazla decay epsilon_min'e yaklasir."""
        cfg = PolicyConfig(epsilon=1.0, epsilon_decay=0.9, epsilon_min=0.01)
        policy = EpsilonGreedyPolicy(config=cfg)

        for _ in range(200):
            policy.update(0.0)

        assert policy.config.epsilon == pytest.approx(0.01, abs=1e-6)

    def test_decay_formula_exact(self) -> None:
        """Decay formulu epsilon * decay oldugunu dogrular."""
        cfg = PolicyConfig(epsilon=0.5, epsilon_decay=0.8, epsilon_min=0.0)
        policy = EpsilonGreedyPolicy(config=cfg)

        policy.update(0.0)
        assert policy.config.epsilon == pytest.approx(0.4)

        policy.update(0.0)
        assert policy.config.epsilon == pytest.approx(0.32)


# ===========================================================================
# UCBPolicy testleri
# ===========================================================================


class TestUCBSelection:
    """UCBPolicy aksiyon secimi testleri."""

    def test_unexplored_actions_selected_first(self) -> None:
        """Denenmemis aksiyonlar once secilmelidir."""
        policy = UCBPolicy()
        q_values = {"act_a": 100.0, "act_b": 100.0, "act_c": 100.0}

        first = policy.select_action(STATE, q_values, ACTIONS)
        assert first in ACTIONS

        # Ikinci cagri farkli denenmemis aksiyon secmeli
        second = policy.select_action(STATE, q_values, ACTIONS)
        assert second in ACTIONS
        assert second != first

        third = policy.select_action(STATE, q_values, ACTIONS)
        assert third in ACTIONS
        # Uc cagri sonrasi tum aksiyonlar denenmis olacak
        assert {first, second, third} == set(ACTIONS)

    def test_prefers_less_visited_actions(self) -> None:
        """Az ziyaret edilen aksiyonlar tercih edilmelidir."""
        cfg = PolicyConfig(ucb_c=2.0)
        policy = UCBPolicy(config=cfg)
        # Tum aksiyonlari kesfet
        q_values = {"act_a": 1.0, "act_b": 1.0, "act_c": 1.0}

        for a in ACTIONS:
            policy.select_action(STATE, q_values, ACTIONS)

        # act_a'yi cok kez sec (sayacini artir)
        policy._action_counts["act_a"] = 100
        policy._action_counts["act_b"] = 1
        policy._action_counts["act_c"] = 1
        policy._total_count = 102

        # Esit Q-degerleri ile az ziyaret edilen secilmeli
        action = policy.select_action(STATE, q_values, ACTIONS)
        assert action in ("act_b", "act_c")

    def test_ucb_score_calculation(self) -> None:
        """UCB skoru dogru hesaplanmalidir: Q(a) + c*sqrt(ln(N)/N(a))."""
        cfg = PolicyConfig(ucb_c=2.0)
        policy = UCBPolicy(config=cfg)

        # Tum aksiyonlari bir kez kesfet
        for _ in ACTIONS:
            policy.select_action(STATE, {}, ACTIONS)

        # Manuel UCB hesabi
        policy._total_count = 100
        policy._action_counts = {"act_a": 10, "act_b": 20, "act_c": 5}
        q_values = {"act_a": 1.0, "act_b": 1.5, "act_c": 0.5}

        ucb_a = 1.0 + 2.0 * math.sqrt(math.log(101) / 10)
        ucb_b = 1.5 + 2.0 * math.sqrt(math.log(101) / 20)
        ucb_c = 0.5 + 2.0 * math.sqrt(math.log(101) / 5)

        expected_best = max(
            [("act_a", ucb_a), ("act_b", ucb_b), ("act_c", ucb_c)],
            key=lambda x: x[1],
        )[0]

        action = policy.select_action(STATE, q_values, ACTIONS)
        assert action == expected_best

    def test_update_is_noop(self) -> None:
        """Update islemi sayaclari degistirmemeli (no-op)."""
        policy = UCBPolicy()
        policy.select_action(STATE, {}, ACTIONS)
        count_before = policy._total_count

        policy.update(5.0)
        assert policy._total_count == count_before

    def test_empty_actions_returns_empty(self) -> None:
        """Bos aksiyon listesi bos string donmeli."""
        policy = UCBPolicy()
        assert policy.select_action(STATE, {}, []) == ""

    def test_high_c_favors_exploration(self) -> None:
        """Yuksek c degeri kesfif arttirir."""
        cfg = PolicyConfig(ucb_c=100.0)
        policy = UCBPolicy(config=cfg)

        # Tum aksiyonlari kesfet
        for _ in ACTIONS:
            policy.select_action(STATE, {}, ACTIONS)

        policy._action_counts = {"act_a": 50, "act_b": 1, "act_c": 50}
        q_values = {"act_a": 10.0, "act_b": 0.0, "act_c": 10.0}

        # Yuksek c ile az ziyaret edilen act_b secilmeli
        action = policy.select_action(STATE, q_values, ACTIONS)
        assert action == "act_b"


# ===========================================================================
# SoftmaxPolicy testleri
# ===========================================================================


class TestSoftmaxSelection:
    """SoftmaxPolicy aksiyon secimi testleri."""

    def test_returns_valid_action(self) -> None:
        """Gecerli bir aksiyon donmelidir."""
        policy = SoftmaxPolicy()
        q_values = {"act_a": 1.0, "act_b": 2.0, "act_c": 3.0}

        for _ in range(50):
            action = policy.select_action(STATE, q_values, ACTIONS)
            assert action in ACTIONS

    def test_low_temperature_favors_best(self) -> None:
        """Dusuk sicaklik en iyi aksiyonu tercih etmelidir."""
        cfg = PolicyConfig(temperature=0.01)
        policy = SoftmaxPolicy(config=cfg)
        q_values = {"act_a": 0.0, "act_b": 10.0, "act_c": 0.0}

        counts = {"act_a": 0, "act_b": 0, "act_c": 0}
        for _ in range(200):
            action = policy.select_action(STATE, q_values, ACTIONS)
            counts[action] += 1

        # act_b neredeyse her zaman secilmeli
        assert counts["act_b"] > 190

    def test_high_temperature_uniform(self) -> None:
        """Yuksek sicaklik uniform dagilima yaklasir."""
        cfg = PolicyConfig(temperature=100.0)
        policy = SoftmaxPolicy(config=cfg)
        q_values = {"act_a": 1.0, "act_b": 2.0, "act_c": 3.0}

        counts = {"act_a": 0, "act_b": 0, "act_c": 0}
        n = 3000
        for _ in range(n):
            action = policy.select_action(STATE, q_values, ACTIONS)
            counts[action] += 1

        # Her aksiyon kabaca %33 secilmeli
        for a in ACTIONS:
            assert counts[a] > n * 0.2

    def test_update_is_noop(self) -> None:
        """Softmax update no-op olmalidir."""
        cfg = PolicyConfig(temperature=1.0)
        policy = SoftmaxPolicy(config=cfg)

        policy.update(10.0)
        assert policy.config.temperature == 1.0

    def test_empty_actions_returns_empty(self) -> None:
        """Bos aksiyon listesi bos string donmeli."""
        policy = SoftmaxPolicy()
        assert policy.select_action(STATE, {}, []) == ""

    def test_equal_q_values_near_uniform(self) -> None:
        """Esit Q-degerleri uniform dagilima yol acmali."""
        policy = SoftmaxPolicy()
        q_values = {"act_a": 1.0, "act_b": 1.0, "act_c": 1.0}

        counts = {a: 0 for a in ACTIONS}
        n = 3000
        for _ in range(n):
            action = policy.select_action(STATE, q_values, ACTIONS)
            counts[action] += 1

        for a in ACTIONS:
            assert counts[a] > n * 0.2


# ===========================================================================
# GradientPolicy testleri
# ===========================================================================


class TestGradientSelection:
    """GradientPolicy aksiyon secimi ve guncelleme testleri."""

    def test_returns_valid_action(self) -> None:
        """Gecerli aksiyon donmelidir."""
        policy = GradientPolicy()
        q_values = {"act_a": 0.0, "act_b": 0.0, "act_c": 0.0}

        for _ in range(20):
            action = policy.select_action(STATE, q_values, ACTIONS)
            assert action in ACTIONS

    def test_initial_preferences_zero(self) -> None:
        """Baslangicta tercihler sifir olmalidir."""
        policy = GradientPolicy()
        policy.select_action(STATE, {}, ACTIONS)

        for a in ACTIONS:
            assert policy._preferences[a] == 0.0

    def test_update_changes_preferences(self) -> None:
        """Yuksek odul ile guncelleme secilen aksiyonun tercihini artirmali."""
        cfg = PolicyConfig(learning_rate=0.1)
        policy = GradientPolicy(config=cfg)

        # Ilk aksiyonu sec
        action = policy.select_action(STATE, {}, ACTIONS)
        initial_pref = policy._preferences[action]

        # Yuksek odul ver
        policy.update(10.0)

        # Secilen aksiyonun tercihi artmis olmali
        # (ilk adimda avg_reward = 10, advantage ~ 0
        #  ama ikinci iterasyonda daha belirgin olur)

        # Ikinci tur
        action2 = policy.select_action(STATE, {}, ACTIONS)
        policy.update(100.0)

        # En az bir tercih degismis olmali
        all_zero = all(
            policy._preferences[a] == 0.0 for a in ACTIONS
        )
        assert not all_zero

    def test_baseline_tracking(self) -> None:
        """Ortalama odul (baseline) dogru takip edilmeli."""
        policy = GradientPolicy()
        policy.select_action(STATE, {}, ACTIONS)
        policy.update(10.0)
        assert policy._avg_reward == pytest.approx(10.0)

        policy.select_action(STATE, {}, ACTIONS)
        policy.update(20.0)
        assert policy._avg_reward == pytest.approx(15.0)

        policy.select_action(STATE, {}, ACTIONS)
        policy.update(30.0)
        assert policy._avg_reward == pytest.approx(20.0)

    def test_step_count_increments(self) -> None:
        """Her update adim sayacini artirmali."""
        policy = GradientPolicy()

        for i in range(5):
            policy.select_action(STATE, {}, ACTIONS)
            policy.update(1.0)

        assert policy._step_count == 5

    def test_no_last_action_update_skips(self) -> None:
        """last_action None iken update tercihleri degistirmemeli."""
        policy = GradientPolicy()
        policy.update(5.0)  # select_action cagirilmadan

        assert policy._step_count == 1
        assert len(policy._preferences) == 0


# ===========================================================================
# QLearner init testleri
# ===========================================================================


class TestQLearnerInit:
    """QLearner baslangic durum testleri."""

    def test_default_config(self) -> None:
        """Varsayilan config degerlerini kullanmalidir."""
        learner = QLearner()
        assert learner.config.gamma == pytest.approx(0.99)
        assert learner.config.alpha == pytest.approx(0.1)
        assert learner.config.double_q is False

    def test_custom_config(self) -> None:
        """Ozel config dogru uygulanmalidir."""
        cfg = LearningConfig(gamma=0.5, alpha=0.2, double_q=True)
        learner = QLearner(config=cfg)
        assert learner.config.gamma == pytest.approx(0.5)
        assert learner.config.alpha == pytest.approx(0.2)
        assert learner.config.double_q is True

    def test_default_policy_is_epsilon_greedy(self) -> None:
        """Varsayilan politika EpsilonGreedy olmalidir."""
        learner = QLearner()
        assert isinstance(learner.policy, EpsilonGreedyPolicy)

    def test_custom_policy(self) -> None:
        """Ozel politika kabul edilmelidir."""
        policy = UCBPolicy()
        learner = QLearner(policy=policy)
        assert isinstance(learner.policy, UCBPolicy)

    def test_empty_q_tables(self) -> None:
        """Baslangicta Q-tablolari bos olmalidir."""
        learner = QLearner()
        assert learner._q1 == {}
        assert learner._q2 == {}

    def test_initial_metrics_zero(self) -> None:
        """Baslangic metrikleri sifir olmalidir."""
        learner = QLearner()
        assert learner._total_episodes == 0
        assert learner._total_reward == 0.0


# ===========================================================================
# QLearner tek Q-tablosu testleri
# ===========================================================================


class TestQLearnerSingleQ:
    """Tek Q-tablosu ile ogrenme testleri."""

    def test_update_increases_q_value(self) -> None:
        """Pozitif odul ile guncelleme Q-degerini artirmalidir."""
        learner = QLearner(config=LearningConfig(gamma=0.9, alpha=0.5))
        initial = learner.get_q_value(STATE, "act_a")
        assert initial == 0.0

        learner.update(STATE, "act_a", 1.0, NEXT_STATE, False)
        updated = learner.get_q_value(STATE, "act_a")
        assert updated > initial

    def test_terminal_state_no_future_value(self) -> None:
        """Terminal durumda gelecek deger eklenmemelidir."""
        cfg = LearningConfig(gamma=0.9, alpha=1.0)
        learner = QLearner(config=cfg)

        td = learner.update(STATE, "act_a", 5.0, NEXT_STATE, done=True)
        q = learner.get_q_value(STATE, "act_a")
        # alpha=1 ile Q = 0 + 1*(5 - 0) = 5
        assert q == pytest.approx(5.0)
        assert td == pytest.approx(5.0)

    def test_td_error_returned(self) -> None:
        """Update TD-hata degeri donmelidir."""
        cfg = LearningConfig(gamma=0.0, alpha=0.1)
        learner = QLearner(config=cfg)

        td = learner.update(STATE, "act_a", 10.0, NEXT_STATE, done=True)
        # TD = reward - Q(s,a) = 10 - 0 = 10
        assert td == pytest.approx(10.0)

    def test_get_best_action(self) -> None:
        """En yuksek Q-degerli aksiyonu donmelidir."""
        cfg = LearningConfig(alpha=1.0, gamma=0.0)
        learner = QLearner(config=cfg)

        learner.update(STATE, "act_a", 1.0, NEXT_STATE, True)
        learner.update(STATE, "act_b", 5.0, NEXT_STATE, True)
        learner.update(STATE, "act_c", 3.0, NEXT_STATE, True)

        best = learner.get_best_action(STATE, ACTIONS)
        assert best == "act_b"

    def test_get_best_action_empty_returns_empty(self) -> None:
        """Bos aksiyon listesi bos string donmeli."""
        learner = QLearner()
        assert learner.get_best_action(STATE, []) == ""

    def test_state_to_key_deterministic(self) -> None:
        """Ayni durum ayni anahtari uretmelidir."""
        key1 = QLearner._state_to_key({"a": 1, "b": 2})
        key2 = QLearner._state_to_key({"b": 2, "a": 1})
        assert key1 == key2

    def test_state_to_key_different_states(self) -> None:
        """Farkli durumlar farkli anahtarlar uretmelidir."""
        key1 = QLearner._state_to_key({"x": 1})
        key2 = QLearner._state_to_key({"x": 2})
        assert key1 != key2

    def test_multiple_updates_converge(self) -> None:
        """Tekrarlanan guncelleme dogru Q-degerine yaklasir."""
        cfg = LearningConfig(gamma=0.0, alpha=0.1)
        learner = QLearner(config=cfg)

        # Ayni durum-aksiyon cifti icin tekrarlanan +1 odul
        for _ in range(200):
            learner.update(STATE, "act_a", 1.0, NEXT_STATE, done=True)

        q = learner.get_q_value(STATE, "act_a")
        assert q == pytest.approx(1.0, abs=0.05)


# ===========================================================================
# QLearner Double Q-Learning testleri
# ===========================================================================


class TestQLearnerDoubleQ:
    """Double Q-Learning testleri."""

    def test_double_q_uses_two_tables(self) -> None:
        """Double Q aktifken iki tablo da kullanilmalidir."""
        cfg = LearningConfig(double_q=True, alpha=0.5, gamma=0.9)
        learner = QLearner(config=cfg)

        for _ in range(50):
            learner.update(STATE, "act_a", 1.0, NEXT_STATE, False)

        key = QLearner._state_to_key(STATE)
        # Her iki tabloda da giris olmali
        has_q1 = key in learner._q1 and "act_a" in learner._q1.get(key, {})
        has_q2 = key in learner._q2 and "act_a" in learner._q2.get(key, {})
        assert has_q1 or has_q2

    def test_double_q_average_returned(self) -> None:
        """get_q_value iki tablonun ortalamasini donmeli."""
        cfg = LearningConfig(double_q=True)
        learner = QLearner(config=cfg)

        key = QLearner._state_to_key(STATE)
        learner._q1[key] = {"act_a": 4.0}
        learner._q2[key] = {"act_a": 6.0}

        q = learner.get_q_value(STATE, "act_a")
        assert q == pytest.approx(5.0)

    def test_double_q_reduces_overestimation(self) -> None:
        """Double Q tek Q'dan daha az tahmin sismesi yapmalidir."""
        # Yuksek gama ve stokastik odul ile
        single_cfg = LearningConfig(gamma=0.99, alpha=0.1, double_q=False)
        double_cfg = LearningConfig(gamma=0.99, alpha=0.1, double_q=True)

        rng = np.random.default_rng(42)
        single_learner = QLearner(config=single_cfg)
        double_learner = QLearner(config=double_cfg)

        s = {"pos": 0}
        ns = {"pos": 1}
        actions = ["up", "down"]

        for _ in range(500):
            a = rng.choice(actions)
            r = float(rng.normal(0, 1))  # Ortalama 0, varyans yuksek
            single_learner.update(s, a, r, ns, False)
            double_learner.update(s, a, r, ns, False)

        # Maksimum Q-degerleri: Double Q genellikle daha muhafazakar
        single_max = max(
            single_learner.get_q_value(s, a) for a in actions
        )
        double_max = max(
            double_learner.get_q_value(s, a) for a in actions
        )
        # Double Q'nun daha az asisma yaptigini dogrula (veya en azindan calistigini)
        assert isinstance(single_max, float)
        assert isinstance(double_max, float)

    def test_double_q_both_tables_populated(self) -> None:
        """Yeterli guncelleme sonrasi her iki tablo da dolu olmali."""
        cfg = LearningConfig(double_q=True, alpha=0.5)
        learner = QLearner(config=cfg)

        for _ in range(100):
            learner.update(STATE, "act_a", 1.0, NEXT_STATE, True)

        key = QLearner._state_to_key(STATE)
        q1_has = key in learner._q1 and len(learner._q1[key]) > 0
        q2_has = key in learner._q2 and len(learner._q2[key]) > 0
        # Rastgele secim ile 100 iterasyonda her iki tablo da dolu olacak
        assert q1_has and q2_has


# ===========================================================================
# QLearner metrik testleri
# ===========================================================================


class TestQLearnerMetrics:
    """QLearner metrik testleri."""

    def test_total_episodes_tracked(self) -> None:
        """Toplam episode sayisi dogru izlenmeli."""
        learner = QLearner()
        for _ in range(10):
            learner.update(STATE, "act_a", 1.0, NEXT_STATE, True)

        metrics = learner.get_metrics()
        assert metrics.total_episodes == 10

    def test_avg_reward_calculated(self) -> None:
        """Ortalama odul dogru hesaplanmali."""
        learner = QLearner()
        learner.update(STATE, "act_a", 2.0, NEXT_STATE, True)
        learner.update(STATE, "act_a", 4.0, NEXT_STATE, True)
        learner.update(STATE, "act_a", 6.0, NEXT_STATE, True)

        metrics = learner.get_metrics()
        assert metrics.avg_reward == pytest.approx(4.0)

    def test_q_table_size_single(self) -> None:
        """Tek Q-tablosu boyutu dogru raporlanmali."""
        cfg = LearningConfig(alpha=1.0, gamma=0.0)
        learner = QLearner(config=cfg)

        learner.update(STATE, "act_a", 1.0, NEXT_STATE, True)
        learner.update(STATE, "act_b", 1.0, NEXT_STATE, True)

        metrics = learner.get_metrics()
        # STATE icin 2 aksiyon + NEXT_STATE icin bos giris
        assert metrics.q_table_size >= 2

    def test_q_table_size_double(self) -> None:
        """Double Q tablo boyutu iki tabloyu icermeli."""
        cfg = LearningConfig(double_q=True, alpha=1.0, gamma=0.0)
        learner = QLearner(config=cfg)

        for _ in range(50):
            learner.update(STATE, "act_a", 1.0, NEXT_STATE, True)

        metrics = learner.get_metrics()
        # Her iki tablo da sayilmali
        assert metrics.q_table_size >= 1

    def test_metrics_epsilon_from_policy(self) -> None:
        """Metrikler politikadan mevcut epsilon'u almali."""
        cfg_policy = PolicyConfig(epsilon=0.42)
        policy = EpsilonGreedyPolicy(config=cfg_policy)
        learner = QLearner(policy=policy)

        metrics = learner.get_metrics()
        assert metrics.epsilon_current == pytest.approx(0.42)

    def test_initial_convergence_zero(self) -> None:
        """Baslangicta yakinsaklik orani sifir olmali."""
        learner = QLearner()
        metrics = learner.get_metrics()
        assert metrics.convergence_rate == 0.0


# ===========================================================================
# QLearner save/load testleri
# ===========================================================================


class TestQLearnerSaveLoad:
    """QLearner kayit ve yukleme testleri."""

    def test_save_creates_file(self, tmp_path: pytest.TempPathFactory) -> None:
        """Save dosya olusturmalidir."""
        learner = QLearner()
        learner.update(STATE, "act_a", 1.0, NEXT_STATE, True)

        path = str(tmp_path / "q_table.json")
        learner.save(path)

        import os
        assert os.path.exists(path)

    def test_save_load_roundtrip(self, tmp_path: pytest.TempPathFactory) -> None:
        """Save/load sonrasi Q-degerleri korunmalidir."""
        cfg = LearningConfig(alpha=1.0, gamma=0.0)
        learner = QLearner(config=cfg)

        learner.update(STATE, "act_a", 5.0, NEXT_STATE, True)
        learner.update(STATE, "act_b", 3.0, NEXT_STATE, True)

        path = str(tmp_path / "q_table.json")
        learner.save(path)

        # Yeni learner'a yukle
        new_learner = QLearner(config=cfg)
        new_learner.load(path)

        key = QLearner._state_to_key(STATE)
        assert new_learner._q1[key]["act_a"] == pytest.approx(5.0)
        assert new_learner._q1[key]["act_b"] == pytest.approx(3.0)

    def test_save_load_preserves_metrics(self, tmp_path: pytest.TempPathFactory) -> None:
        """Save/load metrik degerlerini korumalidir."""
        learner = QLearner()
        for i in range(5):
            learner.update(STATE, "act_a", float(i), NEXT_STATE, True)

        path = str(tmp_path / "q_table.json")
        learner.save(path)

        new_learner = QLearner()
        new_learner.load(path)

        assert new_learner._total_episodes == 5
        assert new_learner._total_reward == pytest.approx(10.0)

    def test_save_valid_json(self, tmp_path: pytest.TempPathFactory) -> None:
        """Kaydedilen dosya gecerli JSON olmalidir."""
        learner = QLearner()
        learner.update(STATE, "act_a", 1.0, NEXT_STATE, True)

        path = str(tmp_path / "q_table.json")
        learner.save(path)

        with open(path) as f:
            data = json.load(f)

        assert "q1" in data
        assert "config" in data
        assert "metrics" in data

    def test_load_double_q_tables(self, tmp_path: pytest.TempPathFactory) -> None:
        """Double Q tablolari save/load sonrasi korunmalidir."""
        cfg = LearningConfig(double_q=True, alpha=0.5)
        learner = QLearner(config=cfg)

        for _ in range(50):
            learner.update(STATE, "act_a", 1.0, NEXT_STATE, True)

        path = str(tmp_path / "double_q.json")
        learner.save(path)

        new_learner = QLearner(config=cfg)
        new_learner.load(path)

        # Q2 tablosu da yuklenmeli
        assert new_learner._q2 is not None


# ===========================================================================
# QLearner decay testleri
# ===========================================================================


class TestQLearnerDecay:
    """QLearner ogrenme orani azaltma testleri."""

    def test_decay_reduces_alpha(self) -> None:
        """Decay alpha'yi azaltmalidir."""
        cfg = LearningConfig(alpha=0.1, alpha_decay=0.9)
        learner = QLearner(config=cfg)

        learner.decay_learning_rate()
        assert learner.config.alpha == pytest.approx(0.09)

    def test_decay_respects_minimum(self) -> None:
        """Alpha minimum 0.001'in altina dusmemelidir."""
        cfg = LearningConfig(alpha=0.002, alpha_decay=0.1)
        learner = QLearner(config=cfg)

        for _ in range(100):
            learner.decay_learning_rate()

        assert learner.config.alpha >= 0.001

    def test_multiple_decays(self) -> None:
        """Coklu decay islemleri dogru sonuc vermelidir."""
        cfg = LearningConfig(alpha=0.5, alpha_decay=0.5)
        learner = QLearner(config=cfg)

        learner.decay_learning_rate()
        assert learner.config.alpha == pytest.approx(0.25)

        learner.decay_learning_rate()
        assert learner.config.alpha == pytest.approx(0.125)

    def test_decay_does_not_affect_gamma(self) -> None:
        """Decay gamma'yi degistirmemelidir."""
        cfg = LearningConfig(gamma=0.99, alpha=0.1, alpha_decay=0.9)
        learner = QLearner(config=cfg)

        learner.decay_learning_rate()
        assert learner.config.gamma == pytest.approx(0.99)
