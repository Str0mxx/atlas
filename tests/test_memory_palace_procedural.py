"""ProceduralMemory testleri.

Prosedurel hafiza sistemi: beceri kaydi, pratik takibi, yeterlilik
hesaplama, otomatiklik tespiti, seviye yonetimi ve pratik gecmisi testleri.
"""

import math

from app.core.memory_palace.procedural_memory import ProceduralMemory
from app.models.memory_palace import ProcessingMode, SkillLevel


# === Yardimci fonksiyonlar ===


def _make_procedural(**kwargs) -> ProceduralMemory:
    """ProceduralMemory olusturur."""
    return ProceduralMemory(**kwargs)


# === Init Testleri ===


class TestInit:
    """ProceduralMemory initialization testleri."""

    def test_defaults(self) -> None:
        """Varsayilan degerlerle baslatma testi."""
        pm = _make_procedural()
        assert pm._skills == {}
        assert pm._practice_logs == {}
        assert pm._automaticity_threshold == 0.8
        assert pm._learning_rate == 0.15

    def test_custom_threshold_and_learning_rate(self) -> None:
        """Ozel esik ve ogrenme hizi testi."""
        pm = _make_procedural(automaticity_threshold=0.6, learning_rate=0.25)
        assert pm._automaticity_threshold == 0.6
        assert pm._learning_rate == 0.25


# === RegisterSkill Testleri ===


class TestRegisterSkill:
    """ProceduralMemory.register_skill testleri."""

    def test_basic_registration(self) -> None:
        """Temel beceri kaydi testi."""
        pm = _make_procedural()
        skill = pm.register_skill("Python")
        assert skill.name == "Python"
        assert skill.id in pm._skills
        assert skill.proficiency == 0.0
        assert skill.level == SkillLevel.NOVICE

    def test_with_steps(self) -> None:
        """Adimlarla beceri kaydi testi."""
        pm = _make_procedural()
        steps = [
            {"order": 1, "description": "Degiskenleri tanimla", "duration_estimate": 5.0},
            {"order": 2, "description": "Fonksiyon yaz", "duration_estimate": 10.0},
        ]
        skill = pm.register_skill("Kodlama", steps=steps)
        assert len(skill.steps) == 2
        assert skill.steps[0].order == 1
        assert skill.steps[0].description == "Degiskenleri tanimla"
        assert skill.steps[1].duration_estimate == 10.0

    def test_with_domain(self) -> None:
        """Alanla beceri kaydi testi."""
        pm = _make_procedural()
        skill = pm.register_skill("FastAPI", domain="yazilim")
        assert skill.domain == "yazilim"

    def test_practice_logs_initialized(self) -> None:
        """Pratik loglarinin baslatilmasi testi."""
        pm = _make_procedural()
        skill = pm.register_skill("Docker")
        assert pm._practice_logs[skill.id] == []


# === Practice Testleri ===


class TestPractice:
    """ProceduralMemory.practice testleri."""

    def test_proficiency_increases(self) -> None:
        """Yeterlilik artisi testi."""
        pm = _make_procedural()
        skill = pm.register_skill("Git")
        pm.practice(skill.id, duration=60.0, performance_score=0.8)
        assert skill.proficiency > 0.0

    def test_automaticity_increases(self) -> None:
        """Otomatiklik artisi testi."""
        pm = _make_procedural()
        skill = pm.register_skill("Typing")
        pm.practice(skill.id, duration=60.0, performance_score=0.7)
        assert skill.automaticity > 0.0

    def test_level_updates_after_practice(self) -> None:
        """Pratik sonrasi seviye guncellenmesi testi."""
        pm = _make_procedural(learning_rate=0.5)
        skill = pm.register_skill("Test")
        # Birden fazla pratikle seviyeyi yukselt
        for _ in range(5):
            pm.practice(skill.id, duration=60.0, performance_score=0.9)
        assert skill.level != SkillLevel.NOVICE

    def test_returns_none_for_unknown(self) -> None:
        """Bilinmeyen beceri icin None donmesi testi."""
        pm = _make_procedural()
        result = pm.practice("yok-id", duration=30.0, performance_score=0.5)
        assert result is None

    def test_total_practice_time(self) -> None:
        """Toplam pratik suresinin birikmesi testi."""
        pm = _make_procedural()
        skill = pm.register_skill("SQL")
        pm.practice(skill.id, duration=60.0, performance_score=0.7)
        pm.practice(skill.id, duration=90.0, performance_score=0.8)
        assert skill.total_practice_time == 150.0

    def test_practice_count(self) -> None:
        """Pratik sayacinin artmasi testi."""
        pm = _make_procedural()
        skill = pm.register_skill("Redis")
        pm.practice(skill.id, duration=30.0, performance_score=0.6)
        pm.practice(skill.id, duration=45.0, performance_score=0.7)
        pm.practice(skill.id, duration=60.0, performance_score=0.8)
        assert skill.practice_count == 3

    def test_last_practiced_updated(self) -> None:
        """Son pratik zamaninin guncellenmesi testi."""
        pm = _make_procedural()
        skill = pm.register_skill("Celery")
        assert skill.last_practiced is None
        pm.practice(skill.id, duration=30.0, performance_score=0.5)
        assert skill.last_practiced is not None

    def test_proficiency_formula(self) -> None:
        """Yeterlilik formulunun dogrulugu testi."""
        pm = _make_procedural(learning_rate=0.15)
        skill = pm.register_skill("Math")
        pm.practice(skill.id, duration=60.0, performance_score=0.8)
        expected = min(1.0, math.log(1 + 1) * 0.15)
        assert abs(skill.proficiency - expected) < 1e-9

    def test_automaticity_formula(self) -> None:
        """Otomatiklik formulunun dogrulugu testi."""
        pm = _make_procedural()
        skill = pm.register_skill("Vim")
        pm.practice(skill.id, duration=60.0, performance_score=0.8)
        expected = 1.0 - math.exp(-0.3 * 1)
        assert abs(skill.automaticity - expected) < 1e-9


# === RetrieveSkill Testleri ===


class TestRetrieveSkill:
    """ProceduralMemory.retrieve_skill testleri."""

    def test_exists(self) -> None:
        """Mevcut beceri getirme testi."""
        pm = _make_procedural()
        skill = pm.register_skill("Docker")
        retrieved = pm.retrieve_skill(skill.id)
        assert retrieved is not None
        assert retrieved.name == "Docker"

    def test_not_found(self) -> None:
        """Olmayan beceri icin None donmesi testi."""
        pm = _make_procedural()
        assert pm.retrieve_skill("yok-id") is None


# === GetByDomain Testleri ===


class TestGetByDomain:
    """ProceduralMemory.get_by_domain testleri."""

    def test_filters_correctly(self) -> None:
        """Alan filtresi dogruluk testi."""
        pm = _make_procedural()
        pm.register_skill("Python", domain="yazilim")
        pm.register_skill("FastAPI", domain="yazilim")
        pm.register_skill("Photoshop", domain="tasarim")
        results = pm.get_by_domain("yazilim")
        assert len(results) == 2
        names = {s.name for s in results}
        assert names == {"Python", "FastAPI"}

    def test_empty_domain(self) -> None:
        """Bos alanda sonuc yoksa bos liste testi."""
        pm = _make_procedural()
        pm.register_skill("Python", domain="yazilim")
        results = pm.get_by_domain("finans")
        assert results == []


# === PracticeHistory Testleri ===


class TestPracticeHistory:
    """ProceduralMemory.get_practice_history testleri."""

    def test_logs_stored(self) -> None:
        """Pratik loglarinin kaydedilmesi testi."""
        pm = _make_procedural()
        skill = pm.register_skill("SQL")
        pm.practice(skill.id, duration=60.0, performance_score=0.7, notes="ilk pratik")
        pm.practice(skill.id, duration=45.0, performance_score=0.8, notes="ikinci pratik")
        history = pm.get_practice_history(skill.id)
        assert len(history) == 2
        assert history[0].notes == "ilk pratik"
        assert history[1].performance_score == 0.8

    def test_empty_for_unknown(self) -> None:
        """Bilinmeyen beceri icin bos liste testi."""
        pm = _make_procedural()
        assert pm.get_practice_history("yok-id") == []

    def test_returns_copy(self) -> None:
        """get_practice_history sonucunun kopya oldugunu dogrulama testi."""
        pm = _make_procedural()
        skill = pm.register_skill("Test")
        pm.practice(skill.id, duration=30.0, performance_score=0.5)
        history = pm.get_practice_history(skill.id)
        history.clear()
        assert len(pm.get_practice_history(skill.id)) == 1


# === Proficiency Testleri ===


class TestProficiency:
    """ProceduralMemory.calculate_proficiency testleri."""

    def test_calculation(self) -> None:
        """Yeterlilik hesaplama testi."""
        pm = _make_procedural(learning_rate=0.15)
        skill = pm.register_skill("Algo")
        pm.practice(skill.id, duration=60.0, performance_score=0.8)
        pm.practice(skill.id, duration=60.0, performance_score=0.9)
        expected = min(1.0, math.log(1 + 2) * 0.15)
        result = pm.calculate_proficiency(skill.id)
        assert abs(result - expected) < 1e-9

    def test_unknown_returns_zero(self) -> None:
        """Bilinmeyen beceri icin 0.0 donmesi testi."""
        pm = _make_procedural()
        assert pm.calculate_proficiency("yok-id") == 0.0


# === Automatic Testleri ===


class TestAutomatic:
    """ProceduralMemory.is_automatic testleri."""

    def test_below_threshold(self) -> None:
        """Esik altinda otomatik olmamasi testi."""
        pm = _make_procedural(automaticity_threshold=0.8)
        skill = pm.register_skill("Yeni beceri")
        pm.practice(skill.id, duration=30.0, performance_score=0.5)
        assert pm.is_automatic(skill.id) is False

    def test_above_threshold(self) -> None:
        """Esik uzerinde otomatik olmasi testi."""
        pm = _make_procedural(automaticity_threshold=0.5)
        skill = pm.register_skill("Kolay beceri")
        # automaticity = 1 - e^(-0.3*n), n=3 => ~0.593
        for _ in range(3):
            pm.practice(skill.id, duration=60.0, performance_score=0.9)
        assert pm.is_automatic(skill.id) is True

    def test_transitions_to_automatic_processing_mode(self) -> None:
        """Otomatik isleme moduna gecis testi."""
        pm = _make_procedural(automaticity_threshold=0.5)
        skill = pm.register_skill("Otomasyon")
        assert skill.processing_mode == ProcessingMode.CONTROLLED
        # Yeterince pratik yaparak otomatik esigini as
        for _ in range(5):
            pm.practice(skill.id, duration=60.0, performance_score=0.9)
        assert skill.processing_mode == ProcessingMode.AUTOMATIC

    def test_unknown_skill_returns_false(self) -> None:
        """Bilinmeyen beceri icin False donmesi testi."""
        pm = _make_procedural()
        assert pm.is_automatic("yok-id") is False


# === Level Testleri ===


class TestLevel:
    """Beceri seviyesi gecis testleri."""

    def test_starts_as_novice(self) -> None:
        """Baslangic seviyesi NOVICE testi."""
        pm = _make_procedural()
        skill = pm.register_skill("Yeni")
        assert skill.level == SkillLevel.NOVICE

    def test_novice_to_beginner(self) -> None:
        """NOVICE'den BEGINNER'a gecis testi."""
        pm = _make_procedural(learning_rate=0.3)
        skill = pm.register_skill("Ogrenme-1")
        # proficiency = log(1+1) * 0.3 = 0.693 * 0.3 = ~0.208 -> BEGINNER
        pm.practice(skill.id, duration=60.0, performance_score=0.8)
        assert skill.level == SkillLevel.BEGINNER

    def test_beginner_to_intermediate(self) -> None:
        """BEGINNER'dan INTERMEDIATE'e gecis testi."""
        pm = _make_procedural(learning_rate=0.3)
        skill = pm.register_skill("Ogrenme-2")
        # n=3: proficiency = log(4) * 0.3 = 1.386 * 0.3 = ~0.416 -> INTERMEDIATE
        for _ in range(3):
            pm.practice(skill.id, duration=60.0, performance_score=0.8)
        assert skill.level == SkillLevel.INTERMEDIATE

    def test_intermediate_to_advanced(self) -> None:
        """INTERMEDIATE'den ADVANCED'a gecis testi."""
        pm = _make_procedural(learning_rate=0.3)
        skill = pm.register_skill("Ogrenme-3")
        # n=6: proficiency = log(7) * 0.3 = 1.946 * 0.3 = ~0.584 -> yeterli degil
        # n=7: proficiency = log(8) * 0.3 = 2.079 * 0.3 = ~0.624 -> ADVANCED
        for _ in range(7):
            pm.practice(skill.id, duration=60.0, performance_score=0.8)
        assert skill.level == SkillLevel.ADVANCED

    def test_advanced_to_expert(self) -> None:
        """ADVANCED'dan EXPERT'e gecis testi."""
        pm = _make_procedural(learning_rate=0.3)
        skill = pm.register_skill("Ogrenme-4")
        # n=13: proficiency = log(14) * 0.3 = 2.639 * 0.3 = ~0.792 -> yeterli degil
        # n=14: proficiency = log(15) * 0.3 = 2.708 * 0.3 = ~0.812 -> EXPERT
        for _ in range(14):
            pm.practice(skill.id, duration=60.0, performance_score=0.8)
        assert skill.level == SkillLevel.EXPERT


# === Count Testleri ===


class TestCount:
    """ProceduralMemory.count testleri."""

    def test_empty(self) -> None:
        """Bos hafizada sifir sayisi testi."""
        pm = _make_procedural()
        assert pm.count() == 0

    def test_after_registrations(self) -> None:
        """Kayitlardan sonra dogru sayim testi."""
        pm = _make_procedural()
        pm.register_skill("Python")
        pm.register_skill("Docker")
        pm.register_skill("Redis")
        assert pm.count() == 3
