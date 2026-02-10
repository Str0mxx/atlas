"""Ogrenme modelleri unit testleri.

Reinforcement Learning deneyim, odul, politika, Q-tablosu,
ogrenme yapilandirmasi, metrik, drift algilama ve adaptasyon
modellerinin varsayilan degerler, ozel degerler ve sinir
kosullarini test eder.
"""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.models.learning import (
    AdaptationState,
    DriftDetection,
    DriftType,
    Experience,
    LearningConfig,
    LearningMetrics,
    PolicyConfig,
    PolicyType,
    PrioritizedExperience,
    QTableEntry,
    RewardConfig,
    RewardSignal,
)


# === Enum Testleri ===


class TestPolicyType:
    """PolicyType enum testleri."""

    def test_values(self) -> None:
        """Tum PolicyType degerlerini dogrular."""
        assert PolicyType.EPSILON_GREEDY == "epsilon_greedy"
        assert PolicyType.UCB == "ucb"
        assert PolicyType.SOFTMAX == "softmax"
        assert PolicyType.GRADIENT == "gradient"

    def test_count(self) -> None:
        """PolicyType uye sayisini dogrular."""
        assert len(PolicyType) == 4

    def test_string_membership(self) -> None:
        """String degerlerle enum uyeligi dogrulanir."""
        assert PolicyType("epsilon_greedy") is PolicyType.EPSILON_GREEDY
        assert PolicyType("ucb") is PolicyType.UCB
        assert PolicyType("softmax") is PolicyType.SOFTMAX
        assert PolicyType("gradient") is PolicyType.GRADIENT


class TestDriftType:
    """DriftType enum testleri."""

    def test_values(self) -> None:
        """Tum DriftType degerlerini dogrular."""
        assert DriftType.SUDDEN == "sudden"
        assert DriftType.GRADUAL == "gradual"
        assert DriftType.INCREMENTAL == "incremental"
        assert DriftType.RECURRING == "recurring"

    def test_count(self) -> None:
        """DriftType uye sayisini dogrular."""
        assert len(DriftType) == 4

    def test_string_membership(self) -> None:
        """String degerlerle enum uyeligi dogrulanir."""
        assert DriftType("sudden") is DriftType.SUDDEN
        assert DriftType("gradual") is DriftType.GRADUAL
        assert DriftType("incremental") is DriftType.INCREMENTAL
        assert DriftType("recurring") is DriftType.RECURRING


# === Model Testleri ===


class TestExperience:
    """Experience modeli testleri."""

    def test_defaults(self) -> None:
        """Varsayilan degerlerin dogru atandigini dogrular."""
        exp = Experience(action="move_left")
        assert exp.state == {}
        assert exp.action == "move_left"
        assert exp.reward == 0.0
        assert exp.next_state == {}
        assert exp.done is False
        assert exp.metadata == {}

    def test_timestamp_auto_generation(self) -> None:
        """Timestamp otomatik olarak UTC olarak uretilmelidir."""
        before = datetime.now(timezone.utc)
        exp = Experience(action="test")
        after = datetime.now(timezone.utc)
        assert isinstance(exp.timestamp, datetime)
        assert before <= exp.timestamp <= after

    def test_custom_values(self) -> None:
        """Ozel degerlerin dogru atandigini dogrular."""
        state = {"position": [1, 2], "velocity": 0.5}
        next_state = {"position": [1, 3], "velocity": 0.6}
        custom_ts = datetime(2026, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        exp = Experience(
            state=state,
            action="accelerate",
            reward=1.5,
            next_state=next_state,
            done=True,
            timestamp=custom_ts,
            metadata={"episode": 42, "step": 10},
        )
        assert exp.state == state
        assert exp.action == "accelerate"
        assert exp.reward == 1.5
        assert exp.next_state == next_state
        assert exp.done is True
        assert exp.timestamp == custom_ts
        assert exp.metadata["episode"] == 42
        assert exp.metadata["step"] == 10

    def test_negative_reward(self) -> None:
        """Negatif odul degerinin kabul edildigini dogrular."""
        exp = Experience(action="bad_action", reward=-10.0)
        assert exp.reward == -10.0


class TestPrioritizedExperience:
    """PrioritizedExperience modeli testleri."""

    def test_defaults(self) -> None:
        """Varsayilan oncelik ve agirlik degerlerini dogrular."""
        exp = Experience(action="test")
        pexp = PrioritizedExperience(experience=exp)
        assert pexp.priority == 1.0
        assert pexp.weight == 1.0
        assert pexp.experience.action == "test"

    def test_custom_priority_weight(self) -> None:
        """Ozel oncelik ve agirlik degerlerini dogrular."""
        exp = Experience(
            state={"x": 1},
            action="jump",
            reward=5.0,
            next_state={"x": 2},
            done=False,
        )
        pexp = PrioritizedExperience(
            experience=exp,
            priority=0.85,
            weight=0.3,
        )
        assert pexp.priority == 0.85
        assert pexp.weight == 0.3
        assert pexp.experience.reward == 5.0

    def test_wraps_experience_correctly(self) -> None:
        """Deneyim nesnesinin dogru sarmalandigini dogrular."""
        exp = Experience(
            state={"level": 3},
            action="attack",
            reward=10.0,
            next_state={"level": 3},
            done=True,
            metadata={"enemy": "boss"},
        )
        pexp = PrioritizedExperience(experience=exp, priority=99.0)
        assert pexp.experience.state["level"] == 3
        assert pexp.experience.done is True
        assert pexp.experience.metadata["enemy"] == "boss"


class TestRewardSignal:
    """RewardSignal modeli testleri."""

    def test_defaults(self) -> None:
        """Varsayilan degerlerin dogru atandigini dogrular."""
        signal = RewardSignal()
        assert signal.value == 0.0
        assert signal.components == {}
        assert signal.shaped_value == 0.0
        assert signal.intrinsic_bonus == 0.0

    def test_custom_components(self) -> None:
        """Ozel odul bilesenlerini dogrular."""
        signal = RewardSignal(
            value=3.5,
            components={"task_completion": 2.0, "efficiency": 1.0, "safety": 0.5},
            shaped_value=3.2,
            intrinsic_bonus=0.3,
        )
        assert signal.value == 3.5
        assert signal.components["task_completion"] == 2.0
        assert signal.components["efficiency"] == 1.0
        assert signal.components["safety"] == 0.5
        assert signal.shaped_value == 3.2
        assert signal.intrinsic_bonus == 0.3


class TestRewardConfig:
    """RewardConfig modeli testleri."""

    def test_default_objectives(self) -> None:
        """Varsayilan hedef agirliklarinin dogru atandigini dogrular."""
        config = RewardConfig()
        assert config.objectives == {
            "success_rate": 0.6,
            "efficiency": 0.3,
            "exploration": 0.1,
        }
        assert config.shaping_gamma == 0.99
        assert config.curiosity_weight == 0.1
        assert config.success_reward == 1.0
        assert config.failure_penalty == -0.5

    def test_custom_objectives(self) -> None:
        """Ozel hedef agirliklarinin atanabildigini dogrular."""
        config = RewardConfig(
            objectives={"speed": 0.5, "quality": 0.5},
            shaping_gamma=0.95,
            curiosity_weight=0.2,
            success_reward=5.0,
            failure_penalty=-2.0,
        )
        assert config.objectives["speed"] == 0.5
        assert config.objectives["quality"] == 0.5
        assert config.shaping_gamma == 0.95
        assert config.curiosity_weight == 0.2
        assert config.success_reward == 5.0
        assert config.failure_penalty == -2.0

    def test_shaping_gamma_bounds(self) -> None:
        """shaping_gamma 0-1 arasi olmalidir."""
        config_low = RewardConfig(shaping_gamma=0.0)
        assert config_low.shaping_gamma == 0.0
        config_high = RewardConfig(shaping_gamma=1.0)
        assert config_high.shaping_gamma == 1.0
        with pytest.raises(ValidationError):
            RewardConfig(shaping_gamma=-0.01)
        with pytest.raises(ValidationError):
            RewardConfig(shaping_gamma=1.01)

    def test_curiosity_weight_non_negative(self) -> None:
        """curiosity_weight sifir veya pozitif olmalidir."""
        config = RewardConfig(curiosity_weight=0.0)
        assert config.curiosity_weight == 0.0
        with pytest.raises(ValidationError):
            RewardConfig(curiosity_weight=-0.1)


class TestPolicyConfig:
    """PolicyConfig modeli testleri."""

    def test_defaults(self) -> None:
        """Varsayilan degerlerin dogru atandigini dogrular."""
        config = PolicyConfig()
        assert config.policy_type == PolicyType.EPSILON_GREEDY
        assert config.epsilon == 0.1
        assert config.epsilon_decay == 0.995
        assert config.epsilon_min == 0.01
        assert config.ucb_c == 2.0
        assert config.temperature == 1.0
        assert config.learning_rate == 0.01

    def test_epsilon_bounds(self) -> None:
        """Epsilon 0-1 arasi olmalidir."""
        config_low = PolicyConfig(epsilon=0.0)
        assert config_low.epsilon == 0.0
        config_high = PolicyConfig(epsilon=1.0)
        assert config_high.epsilon == 1.0
        with pytest.raises(ValidationError):
            PolicyConfig(epsilon=-0.1)
        with pytest.raises(ValidationError):
            PolicyConfig(epsilon=1.1)

    def test_temperature_positive(self) -> None:
        """Sicaklik degeri sifirdan buyuk olmalidir."""
        config = PolicyConfig(temperature=0.5)
        assert config.temperature == 0.5
        with pytest.raises(ValidationError):
            PolicyConfig(temperature=0.0)
        with pytest.raises(ValidationError):
            PolicyConfig(temperature=-1.0)

    def test_custom_policy_type(self) -> None:
        """Farkli politika tipleri atanabilmelidir."""
        config = PolicyConfig(
            policy_type=PolicyType.UCB,
            ucb_c=3.0,
        )
        assert config.policy_type == PolicyType.UCB
        assert config.ucb_c == 3.0


class TestQTableEntry:
    """QTableEntry modeli testleri."""

    def test_defaults(self) -> None:
        """Varsayilan degerlerin dogru atandigini dogrular."""
        entry = QTableEntry(state="s1", action="a1")
        assert entry.state == "s1"
        assert entry.action == "a1"
        assert entry.value == 0.0
        assert entry.visits == 0

    def test_custom_values(self) -> None:
        """Ozel degerlerin dogru atandigini dogrular."""
        entry = QTableEntry(
            state="room_A",
            action="go_east",
            value=7.5,
            visits=100,
        )
        assert entry.state == "room_A"
        assert entry.action == "go_east"
        assert entry.value == 7.5
        assert entry.visits == 100

    def test_negative_value(self) -> None:
        """Negatif Q-degerinin kabul edildigini dogrular."""
        entry = QTableEntry(state="s_bad", action="a_bad", value=-3.2)
        assert entry.value == -3.2


class TestLearningConfig:
    """LearningConfig modeli testleri."""

    def test_defaults(self) -> None:
        """Varsayilan degerlerin dogru atandigini dogrular."""
        config = LearningConfig()
        assert config.gamma == 0.99
        assert config.alpha == 0.1
        assert config.alpha_decay == 0.999
        assert config.batch_size == 32
        assert config.buffer_size == 10000
        assert config.double_q is False
        assert config.use_torch is False

    def test_gamma_bounds(self) -> None:
        """Gamma iskonto faktoru 0-1 arasi olmalidir."""
        config_low = LearningConfig(gamma=0.0)
        assert config_low.gamma == 0.0
        config_high = LearningConfig(gamma=1.0)
        assert config_high.gamma == 1.0
        with pytest.raises(ValidationError):
            LearningConfig(gamma=-0.01)
        with pytest.raises(ValidationError):
            LearningConfig(gamma=1.01)

    def test_alpha_validation(self) -> None:
        """Alpha ogrenme orani 0'dan buyuk ve 1'e esit/kucuk olmalidir."""
        config = LearningConfig(alpha=1.0)
        assert config.alpha == 1.0
        config_small = LearningConfig(alpha=0.001)
        assert config_small.alpha == 0.001
        with pytest.raises(ValidationError):
            LearningConfig(alpha=0.0)
        with pytest.raises(ValidationError):
            LearningConfig(alpha=1.1)

    def test_batch_size_minimum(self) -> None:
        """batch_size en az 1 olmalidir."""
        config = LearningConfig(batch_size=1)
        assert config.batch_size == 1
        with pytest.raises(ValidationError):
            LearningConfig(batch_size=0)

    def test_buffer_size_minimum(self) -> None:
        """buffer_size en az 100 olmalidir."""
        config = LearningConfig(buffer_size=100)
        assert config.buffer_size == 100
        with pytest.raises(ValidationError):
            LearningConfig(buffer_size=99)

    def test_double_q_enabled(self) -> None:
        """Double Q-Learning bayragi aktif edilebilmelidir."""
        config = LearningConfig(double_q=True, use_torch=True)
        assert config.double_q is True
        assert config.use_torch is True


class TestLearningMetrics:
    """LearningMetrics modeli testleri."""

    def test_defaults(self) -> None:
        """Varsayilan degerlerin dogru atandigini dogrular."""
        metrics = LearningMetrics()
        assert metrics.total_episodes == 0
        assert metrics.avg_reward == 0.0
        assert metrics.epsilon_current == 0.1
        assert metrics.q_table_size == 0
        assert metrics.convergence_rate == 0.0
        assert metrics.metadata == {}

    def test_custom_values(self) -> None:
        """Ozel degerlerin dogru atandigini dogrular."""
        metrics = LearningMetrics(
            total_episodes=500,
            avg_reward=7.8,
            epsilon_current=0.05,
            q_table_size=1200,
            convergence_rate=0.92,
            metadata={"best_episode": 423, "training_time_s": 120.5},
        )
        assert metrics.total_episodes == 500
        assert metrics.avg_reward == 7.8
        assert metrics.epsilon_current == 0.05
        assert metrics.q_table_size == 1200
        assert metrics.convergence_rate == 0.92
        assert metrics.metadata["best_episode"] == 423
        assert metrics.metadata["training_time_s"] == 120.5


class TestDriftDetection:
    """DriftDetection modeli testleri."""

    def test_defaults(self) -> None:
        """Varsayilan degerlerin dogru atandigini dogrular."""
        dd = DriftDetection()
        assert dd.detected is False
        assert dd.drift_type is None
        assert dd.confidence == 0.0
        assert dd.window_mean == 0.0
        assert dd.reference_mean == 0.0
        assert dd.p_value == 1.0

    def test_detected_with_drift_type(self) -> None:
        """Drift algilandiginda tip ve guven degerini dogrular."""
        dd = DriftDetection(
            detected=True,
            drift_type=DriftType.SUDDEN,
            confidence=0.95,
            window_mean=0.3,
            reference_mean=0.7,
            p_value=0.001,
        )
        assert dd.detected is True
        assert dd.drift_type == DriftType.SUDDEN
        assert dd.confidence == 0.95
        assert dd.window_mean == 0.3
        assert dd.reference_mean == 0.7
        assert dd.p_value == 0.001

    def test_gradual_drift(self) -> None:
        """Yavas drift algilamasini dogrular."""
        dd = DriftDetection(
            detected=True,
            drift_type=DriftType.GRADUAL,
            confidence=0.75,
            p_value=0.04,
        )
        assert dd.drift_type == DriftType.GRADUAL
        assert dd.confidence == 0.75


class TestAdaptationState:
    """AdaptationState modeli testleri."""

    def test_defaults(self) -> None:
        """Varsayilan degerlerin dogru atandigini dogrular."""
        state = AdaptationState()
        assert state.current_strategy == ""
        assert state.strategies == {}
        assert state.switch_count == 0
        assert state.performance_history == []
        assert state.drift_detections == []

    def test_with_strategies(self) -> None:
        """Strateji performans skorlarini dogrular."""
        state = AdaptationState(
            current_strategy="aggressive",
            strategies={
                "aggressive": 0.85,
                "conservative": 0.72,
                "balanced": 0.78,
            },
            switch_count=3,
        )
        assert state.current_strategy == "aggressive"
        assert state.strategies["aggressive"] == 0.85
        assert state.strategies["conservative"] == 0.72
        assert state.strategies["balanced"] == 0.78
        assert state.switch_count == 3

    def test_with_drift_detections(self) -> None:
        """Drift algilama gecmisini dogrular."""
        d1 = DriftDetection(
            detected=True,
            drift_type=DriftType.SUDDEN,
            confidence=0.9,
        )
        d2 = DriftDetection(
            detected=True,
            drift_type=DriftType.RECURRING,
            confidence=0.8,
        )
        state = AdaptationState(
            current_strategy="adaptive",
            drift_detections=[d1, d2],
            performance_history=[0.5, 0.6, 0.55, 0.7, 0.8],
        )
        assert len(state.drift_detections) == 2
        assert state.drift_detections[0].drift_type == DriftType.SUDDEN
        assert state.drift_detections[1].drift_type == DriftType.RECURRING
        assert len(state.performance_history) == 5
        assert state.performance_history[-1] == 0.8

    def test_serialization_roundtrip(self) -> None:
        """Serializasyon ve deserializasyonun dogru calistigini dogrular."""
        dd = DriftDetection(
            detected=True,
            drift_type=DriftType.INCREMENTAL,
            confidence=0.88,
        )
        state = AdaptationState(
            current_strategy="explore",
            strategies={"explore": 0.6, "exploit": 0.9},
            switch_count=2,
            performance_history=[0.4, 0.6, 0.8],
            drift_detections=[dd],
        )
        data = state.model_dump()
        restored = AdaptationState(**data)
        assert restored.current_strategy == "explore"
        assert restored.strategies["exploit"] == 0.9
        assert restored.switch_count == 2
        assert len(restored.drift_detections) == 1
        assert restored.drift_detections[0].drift_type == DriftType.INCREMENTAL
        assert restored.drift_detections[0].confidence == 0.88
