"""ExperienceBuffer, SumTree ve RewardFunction testleri.

Oncelikli deneyim tamponu ve coklu hedefli odul fonksiyonu icin
kapsamli birim testleri.
"""

import math

import pytest

from app.agents.base_agent import TaskResult
from app.core.learning.experience_buffer import ExperienceBuffer, SumTree
from app.core.learning.reward_system import RewardFunction
from app.models.learning import Experience, RewardConfig


# === Yardimci fonksiyonlar ===


def _make_experience(
    action: str = "test_action",
    reward: float = 1.0,
    done: bool = False,
) -> Experience:
    """Test icin Experience nesnesi olusturur.

    Args:
        action: Aksiyon adi.
        reward: Odul degeri.
        done: Episode bitti mi.

    Returns:
        Yeni Experience nesnesi.
    """
    return Experience(
        state={"x": 1, "y": 2},
        action=action,
        reward=reward,
        next_state={"x": 2, "y": 3},
        done=done,
    )


def _make_task_result(
    success: bool = True,
    message: str = "tamam",
    errors: list[str] | None = None,
) -> TaskResult:
    """Test icin TaskResult nesnesi olusturur.

    Args:
        success: Basarili mi.
        message: Sonuc mesaji.
        errors: Hata listesi.

    Returns:
        Yeni TaskResult nesnesi.
    """
    return TaskResult(
        success=success,
        data={"result": "ok" if success else "fail"},
        message=message,
        errors=errors or [],
    )


# === SumTree Testleri ===


class TestSumTree:
    """Segment agaci tabanli toplam agaci testleri."""

    def test_init_creates_empty_tree(self) -> None:
        """Bos agac sifir toplam ve sifir boyutla baslamalidir."""
        tree = SumTree(capacity=8)
        assert tree.capacity == 8
        assert tree.total() == 0.0
        assert tree.size == 0

    def test_add_single_element(self) -> None:
        """Tek eleman ekleme toplami ve boyutu dogru guncellemeli."""
        tree = SumTree(capacity=4)
        tree.add(priority=5.0, data="a")
        assert tree.total() == pytest.approx(5.0)
        assert tree.size == 1

    def test_add_multiple_elements(self) -> None:
        """Birden fazla eleman ekleme toplami dogru hesaplamali."""
        tree = SumTree(capacity=8)
        tree.add(2.0, "a")
        tree.add(3.0, "b")
        tree.add(5.0, "c")
        assert tree.total() == pytest.approx(10.0)
        assert tree.size == 3

    def test_get_returns_correct_element(self) -> None:
        """get() verilen toplam degerine gore dogru elemani bulmali."""
        tree = SumTree(capacity=4)
        tree.add(1.0, "a")
        tree.add(2.0, "b")
        tree.add(3.0, "c")
        # s=0.5 ilk segmente duser -> "a"
        idx, priority, data = tree.get(0.5)
        assert data == "a"
        assert priority == pytest.approx(1.0)

    def test_get_high_value_returns_later_element(self) -> None:
        """Yuksek toplam degeri sonraki elemanlara ulasmali."""
        tree = SumTree(capacity=4)
        tree.add(1.0, "a")
        tree.add(2.0, "b")
        tree.add(3.0, "c")
        # s=4.0 ucuncu segmente duser -> "c"
        idx, priority, data = tree.get(4.0)
        assert data == "c"
        assert priority == pytest.approx(3.0)

    def test_update_changes_priority(self) -> None:
        """update() onceligi degistirmeli ve toplami guncellemeli."""
        tree = SumTree(capacity=4)
        tree.add(1.0, "a")
        tree.add(2.0, "b")
        assert tree.total() == pytest.approx(3.0)

        # Ilk elemanin agac indeksini bul ve guncelle
        idx, _, _ = tree.get(0.5)
        tree.update(idx, 10.0)
        assert tree.total() == pytest.approx(12.0)

    def test_capacity_overflow_wraps_around(self) -> None:
        """Kapasite asildiginda en eski elemanlar degistirilmeli."""
        tree = SumTree(capacity=3)
        tree.add(1.0, "a")
        tree.add(2.0, "b")
        tree.add(3.0, "c")
        assert tree.size == 3
        assert tree.total() == pytest.approx(6.0)

        # 4. eleman ekleme -> "a" yerine gecer
        tree.add(4.0, "d")
        assert tree.size == 3
        # Toplam: 4 + 2 + 3 = 9 (1 gitti, 4 geldi)
        assert tree.total() == pytest.approx(9.0)

    def test_total_with_no_elements(self) -> None:
        """Bos agacta total() sifir donmeli."""
        tree = SumTree(capacity=4)
        assert tree.total() == pytest.approx(0.0)


# === ExperienceBuffer Testleri ===


class TestExperienceBuffer:
    """Oncelikli deneyim tekrari tamponu testleri."""

    def test_init_defaults(self) -> None:
        """Varsayilan parametreler dogru atanmalidir."""
        buf = ExperienceBuffer()
        assert buf.max_size == 10000
        assert buf.alpha == pytest.approx(0.6)
        assert buf.beta == pytest.approx(0.4)
        assert buf.beta_increment == pytest.approx(0.001)
        assert len(buf) == 0

    def test_init_custom_params(self) -> None:
        """Ozel parametreler dogru atanmalidir."""
        buf = ExperienceBuffer(max_size=100, alpha=0.5, beta=0.3, beta_increment=0.01)
        assert buf.max_size == 100
        assert buf.alpha == pytest.approx(0.5)
        assert buf.beta == pytest.approx(0.3)
        assert buf.beta_increment == pytest.approx(0.01)

    def test_add_single_experience(self) -> None:
        """Tek deneyim ekleme tampon boyutunu 1 yapmali."""
        buf = ExperienceBuffer(max_size=10)
        exp = _make_experience()
        buf.add(exp)
        assert len(buf) == 1

    def test_add_with_explicit_priority(self) -> None:
        """Acik oncelik degeri ile ekleme basarili olmali."""
        buf = ExperienceBuffer(max_size=10)
        exp = _make_experience()
        buf.add(exp, priority=5.0)
        assert len(buf) == 1

    def test_add_multiple_experiences(self) -> None:
        """Birden fazla deneyim ekleme boyutu dogru artirmali."""
        buf = ExperienceBuffer(max_size=100)
        for i in range(10):
            buf.add(_make_experience(action=f"action_{i}"))
        assert len(buf) == 10

    def test_sample_empty_buffer_returns_empty(self) -> None:
        """Bos tampondan ornekleme bos liste donmeli."""
        buf = ExperienceBuffer(max_size=10)
        samples = buf.sample(batch_size=5)
        assert samples == []

    def test_sample_returns_correct_count(self) -> None:
        """Ornekleme istenen sayida deneyim donmeli."""
        buf = ExperienceBuffer(max_size=100)
        for i in range(20):
            buf.add(_make_experience(action=f"a_{i}"), priority=float(i + 1))
        samples = buf.sample(batch_size=10)
        assert len(samples) == 10

    def test_sample_with_batch_larger_than_buffer(self) -> None:
        """Tampondan buyuk batch_size istenmesi tampon boyutuna sinirlanmali."""
        buf = ExperienceBuffer(max_size=100)
        for i in range(5):
            buf.add(_make_experience(action=f"a_{i}"), priority=float(i + 1))
        samples = buf.sample(batch_size=50)
        assert len(samples) <= 5

    def test_sample_returns_prioritized_experiences(self) -> None:
        """Ornekleme PrioritizedExperience nesneleri donmeli."""
        buf = ExperienceBuffer(max_size=100)
        for i in range(10):
            buf.add(_make_experience(action=f"a_{i}"), priority=float(i + 1))
        samples = buf.sample(batch_size=5)
        for s in samples:
            assert hasattr(s, "experience")
            assert hasattr(s, "priority")
            assert hasattr(s, "weight")
            assert s.priority > 0
            assert s.weight > 0

    def test_sample_increments_beta(self) -> None:
        """Her ornekleme beta degerini artirmali."""
        buf = ExperienceBuffer(max_size=100, beta=0.4, beta_increment=0.1)
        for i in range(10):
            buf.add(_make_experience(action=f"a_{i}"), priority=float(i + 1))
        initial_beta = buf.beta
        buf.sample(batch_size=3)
        assert buf.beta == pytest.approx(initial_beta + 0.1)

    def test_sample_beta_capped_at_one(self) -> None:
        """Beta degeri 1.0'i asmamali."""
        buf = ExperienceBuffer(max_size=100, beta=0.95, beta_increment=0.1)
        for i in range(10):
            buf.add(_make_experience(action=f"a_{i}"), priority=float(i + 1))
        buf.sample(batch_size=3)
        assert buf.beta <= 1.0

    def test_len_reflects_current_size(self) -> None:
        """len() tampondaki mevcut eleman sayisini donmeli."""
        buf = ExperienceBuffer(max_size=50)
        assert len(buf) == 0
        buf.add(_make_experience())
        assert len(buf) == 1
        buf.add(_make_experience(action="second"))
        assert len(buf) == 2

    def test_clear_resets_buffer(self) -> None:
        """clear() tamponu tamamen sifirlamali."""
        buf = ExperienceBuffer(max_size=50)
        for i in range(10):
            buf.add(_make_experience(action=f"a_{i}"))
        assert len(buf) == 10

        buf.clear()
        assert len(buf) == 0
        stats = buf.get_stats()
        assert stats["total_added"] == 0

    def test_get_stats_initial(self) -> None:
        """Bos tampon istatistikleri dogru varsayilan degerler icermeli."""
        buf = ExperienceBuffer(max_size=100)
        stats = buf.get_stats()
        assert stats["size"] == 0
        assert stats["max_size"] == 100
        assert stats["total_added"] == 0
        assert stats["beta"] == pytest.approx(0.4)

    def test_get_stats_after_adds(self) -> None:
        """Ekleme sonrasi istatistikler dogru guncellenmeli."""
        buf = ExperienceBuffer(max_size=100)
        for i in range(5):
            buf.add(_make_experience(action=f"a_{i}"))
        stats = buf.get_stats()
        assert stats["size"] == 5
        assert stats["total_added"] == 5
        assert stats["total_priority"] > 0
        assert stats["max_priority"] >= 1.0

    def test_overflow_replaces_oldest(self) -> None:
        """Kapasite asildiginda boyut max_size'da kalmali."""
        buf = ExperienceBuffer(max_size=5)
        for i in range(10):
            buf.add(_make_experience(action=f"a_{i}"))
        assert len(buf) == 5

    def test_update_priorities(self) -> None:
        """Oncelik guncelleme toplam onceligi degistirmeli."""
        buf = ExperienceBuffer(max_size=100)
        for i in range(5):
            buf.add(_make_experience(action=f"a_{i}"), priority=1.0)

        stats_before = buf.get_stats()
        total_before = stats_before["total_priority"]

        # Ornekleme yapip indeksleri elde et (SumTree indeksleri icin)
        samples = buf.sample(batch_size=2)
        if samples:
            # Dogrudan agac indekslerini kullan
            tree_indices = []
            for i in range(min(2, buf._tree.size)):
                idx = i + buf._tree.capacity - 1
                tree_indices.append(idx)
            new_priorities = [10.0] * len(tree_indices)
            buf.update_priorities(tree_indices, new_priorities)

            stats_after = buf.get_stats()
            assert stats_after["total_priority"] != pytest.approx(total_before)


# === RewardFunction Testleri ===


class TestRewardFunction:
    """Coklu hedefli odul fonksiyonu testleri."""

    def test_init_default_config(self) -> None:
        """Varsayilan yapilandirma ile olusturma basarili olmali."""
        rf = RewardFunction()
        assert rf.config is not None
        assert rf.config.success_reward == 1.0
        assert rf.config.failure_penalty == -0.5
        assert "success_rate" in rf.config.objectives

    def test_init_custom_config(self) -> None:
        """Ozel yapilandirma dogru atanmalidir."""
        config = RewardConfig(
            success_reward=2.0,
            failure_penalty=-1.0,
            curiosity_weight=0.5,
        )
        rf = RewardFunction(config=config)
        assert rf.config.success_reward == 2.0
        assert rf.config.failure_penalty == -1.0
        assert rf.config.curiosity_weight == pytest.approx(0.5)

    def test_calculate_success_positive_reward(self) -> None:
        """Basarili gorev pozitif odul donmeli."""
        rf = RewardFunction()
        result = _make_task_result(success=True)
        signal = rf.calculate(result)
        assert signal.value > 0

    def test_calculate_failure_negative_reward(self) -> None:
        """Basarisiz gorev negatif odul donmeli."""
        rf = RewardFunction()
        result = _make_task_result(success=False, errors=["hata olustu"])
        signal = rf.calculate(result)
        assert signal.value < 0

    def test_calculate_returns_reward_signal(self) -> None:
        """calculate() RewardSignal nesnesi donmeli."""
        rf = RewardFunction()
        result = _make_task_result(success=True)
        signal = rf.calculate(result)
        assert hasattr(signal, "value")
        assert hasattr(signal, "components")
        assert hasattr(signal, "shaped_value")
        assert hasattr(signal, "intrinsic_bonus")

    def test_calculate_with_context(self) -> None:
        """Baglamsal bilgi ile hesaplama bilesenleri etkilemeli."""
        rf = RewardFunction()
        result = _make_task_result(success=True)
        context = {"efficiency": 0.9, "exploration": 0.5}
        signal = rf.calculate(result, context=context)
        assert "efficiency" in signal.components
        assert "exploration" in signal.components
        assert signal.components["efficiency"] == pytest.approx(0.9)
        assert signal.components["exploration"] == pytest.approx(0.5)

    def test_calculate_increments_episode_count(self) -> None:
        """Her calculate() cagrisi episode sayacini artirmali."""
        rf = RewardFunction()
        result = _make_task_result(success=True)
        rf.calculate(result)
        rf.calculate(result)
        rf.calculate(result)
        stats = rf.get_stats()
        assert stats["episode_count"] == 3

    def test_shape_reward_basic(self) -> None:
        """Odul sekillendirme dogru formulu uygulamali: r + gamma*phi(s') - phi(s)."""
        rf = RewardFunction()
        current_state = {"a": 1.0, "b": 2.0}  # phi = 3.0
        next_state = {"a": 3.0, "b": 4.0}  # phi = 7.0
        gamma = 0.9

        shaped = rf.shape_reward(
            current_reward=1.0,
            current_state=current_state,
            next_state=next_state,
            gamma=gamma,
        )
        # F = 0.9 * 7.0 - 3.0 = 6.3 - 3.0 = 3.3
        # shaped = 1.0 + 3.3 = 4.3
        assert shaped == pytest.approx(4.3)

    def test_shape_reward_uses_config_gamma(self) -> None:
        """gamma None ise config'deki shaping_gamma kullanilmali."""
        config = RewardConfig(shaping_gamma=0.5)
        rf = RewardFunction(config=config)
        current_state = {"val": 2.0}  # phi = 2.0
        next_state = {"val": 4.0}  # phi = 4.0

        shaped = rf.shape_reward(
            current_reward=0.0,
            current_state=current_state,
            next_state=next_state,
            gamma=None,
        )
        # F = 0.5 * 4.0 - 2.0 = 2.0 - 2.0 = 0.0
        # shaped = 0.0 + 0.0 = 0.0
        assert shaped == pytest.approx(0.0)

    def test_shape_reward_negative_shaping(self) -> None:
        """Sonraki durum daha kotu ise negatif sekillendirme olmali."""
        rf = RewardFunction()
        current_state = {"val": 10.0}  # phi = 10.0
        next_state = {"val": 1.0}  # phi = 1.0
        gamma = 0.99

        shaped = rf.shape_reward(
            current_reward=0.0,
            current_state=current_state,
            next_state=next_state,
            gamma=gamma,
        )
        # F = 0.99 * 1.0 - 10.0 = 0.99 - 10.0 = -9.01
        assert shaped < 0

    def test_intrinsic_motivation_low_count_high_bonus(self) -> None:
        """Dusuk ziyaret sayisi yuksek merak bonusu vermeli."""
        config = RewardConfig(curiosity_weight=1.0)
        rf = RewardFunction(config=config)
        state = {"task": "new"}
        state_key = str(sorted(state.items()))
        visit_counts = {state_key: 0}

        bonus = rf.intrinsic_motivation(state, visit_counts)
        # beta / sqrt(0 + 1) = 1.0 / 1.0 = 1.0
        assert bonus == pytest.approx(1.0)

    def test_intrinsic_motivation_high_count_low_bonus(self) -> None:
        """Yuksek ziyaret sayisi dusuk merak bonusu vermeli."""
        config = RewardConfig(curiosity_weight=1.0)
        rf = RewardFunction(config=config)
        state = {"task": "old"}
        state_key = str(sorted(state.items()))
        visit_counts = {state_key: 99}

        bonus = rf.intrinsic_motivation(state, visit_counts)
        # beta / sqrt(99 + 1) = 1.0 / 10.0 = 0.1
        assert bonus == pytest.approx(0.1)

    def test_intrinsic_motivation_unseen_state(self) -> None:
        """Hic gorulmemis durum icin maksimum bonus verilmeli."""
        config = RewardConfig(curiosity_weight=0.5)
        rf = RewardFunction(config=config)
        state = {"brand_new": True}
        visit_counts = {}  # Bos — durum hic gorulmemis

        bonus = rf.intrinsic_motivation(state, visit_counts)
        # beta / sqrt(0 + 1) = 0.5 / 1.0 = 0.5
        assert bonus == pytest.approx(0.5)

    def test_intrinsic_motivation_decreases_with_visits(self) -> None:
        """Ziyaret sayisi arttikca bonus azalmali."""
        config = RewardConfig(curiosity_weight=1.0)
        rf = RewardFunction(config=config)
        state = {"x": 1}
        state_key = str(sorted(state.items()))

        bonus_low = rf.intrinsic_motivation(state, {state_key: 1})
        bonus_high = rf.intrinsic_motivation(state, {state_key: 100})
        assert bonus_low > bonus_high

    def test_update_objectives(self) -> None:
        """Hedef agirliklari guncelleme dogru uygulanmali."""
        rf = RewardFunction()
        rf.update_objectives({"new_obj": 0.5})
        assert "new_obj" in rf.config.objectives
        assert rf.config.objectives["new_obj"] == pytest.approx(0.5)

    def test_update_objectives_overrides_existing(self) -> None:
        """Mevcut hedef agirligi degistirilmeli."""
        rf = RewardFunction()
        old_val = rf.config.objectives.get("success_rate")
        rf.update_objectives({"success_rate": 0.99})
        assert rf.config.objectives["success_rate"] == pytest.approx(0.99)
        assert rf.config.objectives["success_rate"] != old_val

    def test_get_stats_initial(self) -> None:
        """Baslangicta istatistikler sifir olmali."""
        rf = RewardFunction()
        stats = rf.get_stats()
        assert stats["episode_count"] == 0
        assert stats["total_reward"] == 0.0
        assert stats["avg_reward"] == 0.0

    def test_get_stats_after_calculations(self) -> None:
        """Hesaplamalar sonrasi istatistikler dogru guncellenmeli."""
        rf = RewardFunction()
        rf.calculate(_make_task_result(success=True))
        rf.calculate(_make_task_result(success=False))
        stats = rf.get_stats()
        assert stats["episode_count"] == 2
        assert stats["total_reward"] != 0.0
        assert stats["avg_reward"] == pytest.approx(
            stats["total_reward"] / stats["episode_count"],
        )

    def test_state_potential_sums_numeric_values(self) -> None:
        """_state_potential() sayisal degerlerin toplamini donmeli."""
        rf = RewardFunction()
        state = {"a": 3.0, "b": 7, "c": "text", "d": True}
        # float(3.0) + float(7) = 10.0, "text" atlanir
        # bool int'in alt sinifi oldugu icin True = 1 eklenir
        potential = rf._state_potential(state)
        assert potential == pytest.approx(11.0)

    def test_state_potential_empty_state(self) -> None:
        """Bos durum icin potansiyel sifir olmali."""
        rf = RewardFunction()
        assert rf._state_potential({}) == pytest.approx(0.0)
