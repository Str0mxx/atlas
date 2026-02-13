"""ForgettingCurve testleri.

Ebbinghaus unutma egrisi: kayit, tutma orani hesaplama, gozden gecirme,
tekrar zamanlama, toplu cozunurluk ve budama testleri.
"""

import math
from datetime import datetime, timedelta, timezone

import pytest

from app.core.memory_palace.forgetting_curve import ForgettingCurve
from app.models.memory_palace import MemoryType


# === Yardimci fonksiyonlar ===


def _make_curve(**kwargs) -> ForgettingCurve:
    """ForgettingCurve olusturur."""
    return ForgettingCurve(**kwargs)


# === Init Testleri ===


class TestInit:
    """ForgettingCurve initialization testleri."""

    def test_defaults(self) -> None:
        """Varsayilan degerlerle baslatma testi."""
        fc = _make_curve()
        assert fc._base_rate == 0.1
        assert fc._traces == {}

    def test_custom_base_rate(self) -> None:
        """Ozel temel unutma orani testi."""
        fc = _make_curve(base_forgetting_rate=0.3)
        assert fc._base_rate == 0.3


# === Register Testleri ===


class TestRegister:
    """ForgettingCurve.register_memory testleri."""

    def test_creates_trace(self) -> None:
        """Hafiza izi olusturma testi."""
        fc = _make_curve()
        trace = fc.register_memory("mem1")
        assert trace.memory_id == "mem1"
        assert trace.memory_type == MemoryType.EPISODIC
        assert fc.get_trace("mem1") is not None

    def test_stability_based_on_importance(self) -> None:
        """Stabilite hesabinin onem dereceye gore yapilmasi testi."""
        fc = _make_curve(base_forgetting_rate=0.1)
        trace = fc.register_memory("mem1", importance=0.5)
        # stability = (1.0 + 0.5) / 0.1 = 15.0
        assert trace.stability == pytest.approx(15.0)

    def test_stability_high_importance(self) -> None:
        """Yuksek onem derecesi icin stabilite hesabi testi."""
        fc = _make_curve(base_forgetting_rate=0.2)
        trace = fc.register_memory("mem1", importance=1.0)
        # stability = (1.0 + 1.0) / 0.2 = 10.0
        assert trace.stability == pytest.approx(10.0)

    def test_initial_strength(self) -> None:
        """Baslangic gucunun 1.0 olmasi testi."""
        fc = _make_curve()
        trace = fc.register_memory("mem1", initial_strength=1.0)
        assert trace.strength == 1.0

    def test_review_count_zero(self) -> None:
        """Baslangic gozden gecirme sayisinin 0 olmasi testi."""
        fc = _make_curve()
        trace = fc.register_memory("mem1")
        assert trace.review_count == 0

    def test_next_review_scheduled(self) -> None:
        """Kayit sonrasi sonraki tekrarin planlanmasi testi."""
        fc = _make_curve()
        fc.register_memory("mem1")
        # schedule_review, trace'i _traces icinde gunceller
        stored = fc.get_trace("mem1")
        assert stored is not None
        assert stored.next_review is not None


# === Retention Testleri ===


class TestRetention:
    """ForgettingCurve.calculate_retention testleri."""

    def test_formula_verification(self) -> None:
        """R = e^(-t/S) formul dogrulama testi."""
        fc = _make_curve(base_forgetting_rate=0.1)
        trace = fc.register_memory("mem1", importance=0.0)
        # stability = (1.0 + 0.0) / 0.1 = 10.0
        S = 10.0
        t = 5.0  # 5 saniye sonra
        at_time = trace.last_review + timedelta(seconds=t)
        retention = fc.calculate_retention("mem1", at_time=at_time)
        expected = math.exp(-t / S)
        assert retention == pytest.approx(expected, rel=1e-6)

    def test_returns_zero_for_unknown(self) -> None:
        """Bilinmeyen hafiza icin 0.0 donmesi testi."""
        fc = _make_curve()
        assert fc.calculate_retention("nonexistent") == 0.0

    def test_strength_at_t_zero(self) -> None:
        """t=0 aninda tutma oraninin ~1.0 olmasi testi."""
        fc = _make_curve()
        trace = fc.register_memory("mem1")
        retention = fc.calculate_retention("mem1", at_time=trace.last_review)
        assert retention == pytest.approx(1.0)

    def test_decays_over_time(self) -> None:
        """Zaman icinde tutma oraninin azalmasi testi."""
        fc = _make_curve()
        trace = fc.register_memory("mem1")
        t1 = trace.last_review + timedelta(seconds=100)
        t2 = trace.last_review + timedelta(seconds=1000)
        r1 = fc.calculate_retention("mem1", at_time=t1)
        r2 = fc.calculate_retention("mem1", at_time=t2)
        assert r1 > r2
        assert r2 > 0.0


# === Review Testleri ===


class TestReview:
    """ForgettingCurve.review testleri."""

    def test_strength_reset_to_one(self) -> None:
        """Gozden gecirme sonrasi gucun 1.0 olmasi testi."""
        fc = _make_curve()
        fc.register_memory("mem1")
        updated = fc.review("mem1")
        assert updated is not None
        assert updated.strength == 1.0

    def test_stability_increases(self) -> None:
        """Stabilitenin 1.5 kati artmasi testi."""
        fc = _make_curve(base_forgetting_rate=0.1)
        trace = fc.register_memory("mem1", importance=0.0)
        original_stability = trace.stability  # (1+0)/0.1 = 10.0
        updated = fc.review("mem1")
        assert updated is not None
        assert updated.stability == pytest.approx(original_stability * 1.5)

    def test_review_count_increments(self) -> None:
        """Gozden gecirme sayacinin artmasi testi."""
        fc = _make_curve()
        fc.register_memory("mem1")
        updated = fc.review("mem1")
        assert updated is not None
        assert updated.review_count == 1
        updated2 = fc.review("mem1")
        assert updated2 is not None
        assert updated2.review_count == 2

    def test_schedules_next_review(self) -> None:
        """Gozden gecirme sonrasi sonraki tekrarin planlanmasi testi."""
        fc = _make_curve()
        fc.register_memory("mem1")
        updated = fc.review("mem1")
        assert updated is not None
        assert updated.next_review is not None

    def test_review_unknown_returns_none(self) -> None:
        """Bilinmeyen hafiza icin None donmesi testi."""
        fc = _make_curve()
        assert fc.review("nonexistent") is None


# === DueReviews Testleri ===


class TestDueReviews:
    """ForgettingCurve.get_due_reviews testleri."""

    def test_returns_due_traces(self) -> None:
        """Tekrar zamani gelen izlerin donmesi testi."""
        fc = _make_curve()
        fc.register_memory("mem1")
        # Gelecekte yeterince ileri bir zaman ver
        far_future = datetime.now(timezone.utc) + timedelta(days=365)
        due = fc.get_due_reviews(before=far_future)
        assert len(due) >= 1
        ids = [t.memory_id for t in due]
        assert "mem1" in ids

    def test_empty_if_none_due(self) -> None:
        """Tekrari gereken iz yoksa bos liste testi."""
        fc = _make_curve()
        fc.register_memory("mem1")
        # Gecmiste bir zaman ver (hicbir sey due olmamali)
        past = datetime(2000, 1, 1, tzinfo=timezone.utc)
        due = fc.get_due_reviews(before=past)
        assert due == []

    def test_empty_when_no_traces(self) -> None:
        """Hicbir iz yoksa bos liste testi."""
        fc = _make_curve()
        due = fc.get_due_reviews()
        assert due == []


# === Schedule Testleri ===


class TestSchedule:
    """ForgettingCurve.schedule_review testleri."""

    def test_interval_calculation(self) -> None:
        """Aralik hesabinin dogru yapilmasi testi."""
        fc = _make_curve(base_forgetting_rate=0.1)
        fc.register_memory("mem1", importance=0.0)
        # stability = 10.0, interval = 10.0 * ln(1/0.1) = 10.0 * ln(10)
        schedule = fc.schedule_review("mem1")
        assert schedule is not None
        expected_interval = 10.0 * math.log(1.0 / 0.1)
        assert schedule.interval_seconds == pytest.approx(expected_interval, rel=1e-3)

    def test_returns_none_for_unknown(self) -> None:
        """Bilinmeyen hafiza icin None donmesi testi."""
        fc = _make_curve()
        assert fc.schedule_review("nonexistent") is None


# === DecayAll Testleri ===


class TestDecayAll:
    """ForgettingCurve.decay_all testleri."""

    def test_all_traces_get_current_retention(self) -> None:
        """Tum izlerin guncel tutma oranini almasi testi."""
        fc = _make_curve()
        fc.register_memory("mem1")
        fc.register_memory("mem2")
        retentions = fc.decay_all()
        assert "mem1" in retentions
        assert "mem2" in retentions
        assert 0.0 <= retentions["mem1"] <= 1.0
        assert 0.0 <= retentions["mem2"] <= 1.0

    def test_empty_when_no_traces(self) -> None:
        """Hicbir iz yoksa bos sozluk testi."""
        fc = _make_curve()
        retentions = fc.decay_all()
        assert retentions == {}


# === Prune Testleri ===


class TestPrune:
    """ForgettingCurve.prune_forgotten testleri."""

    def test_removes_below_threshold(self) -> None:
        """Esik degerinin altindaki izlerin silinmesi testi."""
        fc = _make_curve(base_forgetting_rate=0.1)
        trace = fc.register_memory("mem1", importance=0.0)
        # stability = 10.0, cok uzun sure sonra retention ~0
        # Trace'in last_review'ini cok eski yap
        old_time = datetime.now(timezone.utc) - timedelta(days=3650)
        fc._traces["mem1"] = trace.model_copy(update={"last_review": old_time})
        removed = fc.prune_forgotten(threshold=0.01)
        assert removed >= 1
        assert fc.get_trace("mem1") is None

    def test_keeps_above_threshold(self) -> None:
        """Esik degerinin ustundeki izlerin korunmasi testi."""
        fc = _make_curve()
        fc.register_memory("mem1")
        # Yeni kaydedilmis iz, retention ~1.0, silinmemeli
        removed = fc.prune_forgotten(threshold=0.01)
        assert removed == 0
        assert fc.get_trace("mem1") is not None

    def test_returns_count(self) -> None:
        """Silinen iz sayisinin dogru donmesi testi."""
        fc = _make_curve(base_forgetting_rate=0.1)
        old_time = datetime.now(timezone.utc) - timedelta(days=3650)
        for i in range(3):
            trace = fc.register_memory(f"mem{i}", importance=0.0)
            fc._traces[f"mem{i}"] = trace.model_copy(update={"last_review": old_time})
        removed = fc.prune_forgotten(threshold=0.01)
        assert removed == 3


# === Trace Testleri ===


class TestTrace:
    """ForgettingCurve.get_trace testleri."""

    def test_get_existing(self) -> None:
        """Mevcut hafiza izini alma testi."""
        fc = _make_curve()
        fc.register_memory("mem1")
        trace = fc.get_trace("mem1")
        assert trace is not None
        assert trace.memory_id == "mem1"

    def test_none_for_unknown(self) -> None:
        """Bilinmeyen hafiza icin None donmesi testi."""
        fc = _make_curve()
        assert fc.get_trace("nonexistent") is None


# === Count Testleri ===


class TestCount:
    """ForgettingCurve.count testleri."""

    def test_empty(self) -> None:
        """Bos koleksiyon icin sifir donmesi testi."""
        fc = _make_curve()
        assert fc.count() == 0

    def test_after_registrations(self) -> None:
        """Kayitlardan sonra dogru sayimin donmesi testi."""
        fc = _make_curve()
        fc.register_memory("mem1")
        fc.register_memory("mem2")
        fc.register_memory("mem3")
        assert fc.count() == 3
