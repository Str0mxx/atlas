"""ATLAS Prosedurel hafiza modulu.

Beceri kaydi, pratik takibi, yeterlilik hesaplama,
otomatiklik tespiti ve seviye yonetimi.
"""

import logging
import math
from datetime import datetime, timezone

from app.models.memory_palace import (
    PracticeLog,
    ProcessingMode,
    Skill,
    SkillLevel,
    SkillStep,
)

logger = logging.getLogger(__name__)


class ProceduralMemory:
    """Prosedurel (islem) hafiza sistemi.

    Becerileri kayit eder, pratik ile yeterlilik ve
    otomatiklik duzeylerini hesaplar, logaritmik ogrenme
    egrisi ve ustel otomatiklik modeli kullanir.

    Attributes:
        _skills: Kayitli beceriler (id -> Skill).
        _practice_logs: Pratik kayitlari (skill_id -> logs).
        _automaticity_threshold: Otomatik isleme esigi.
        _learning_rate: Ogrenme hizi katsayisi.
    """

    def __init__(
        self,
        automaticity_threshold: float = 0.8,
        learning_rate: float = 0.15,
    ) -> None:
        self._skills: dict[str, Skill] = {}
        self._practice_logs: dict[str, list[PracticeLog]] = {}
        self._automaticity_threshold = automaticity_threshold
        self._learning_rate = learning_rate

    def register_skill(
        self,
        name: str,
        steps: list[dict[str, str | int | float]] | None = None,
        domain: str = "",
    ) -> Skill:
        """Yeni beceri kaydeder.

        Args:
            name: Beceri adi.
            steps: Beceri adimlari (order, description, duration_estimate).
            domain: Beceri alani.

        Returns:
            Olusturulan Skill nesnesi.
        """
        skill_steps: list[SkillStep] = []
        if steps:
            for step_data in steps:
                skill_step = SkillStep(
                    order=int(step_data.get("order", 0)),
                    description=str(step_data.get("description", "")),
                    duration_estimate=float(
                        step_data.get("duration_estimate", 0.0)
                    ),
                )
                skill_steps.append(skill_step)

        skill = Skill(
            name=name,
            domain=domain,
            steps=skill_steps,
        )

        self._skills[skill.id] = skill
        self._practice_logs[skill.id] = []

        logger.info(
            "Beceri kaydedildi: %s (alan=%s, adim=%d)",
            name,
            domain or "genel",
            len(skill_steps),
        )
        return skill

    def practice(
        self,
        skill_id: str,
        duration: float,
        performance_score: float,
        notes: str = "",
    ) -> Skill | None:
        """Pratik kaydeder ve beceri metriklerini gunceller.

        Yeterlilik logaritmik ogrenme egrisi ile,
        otomatiklik ustel buyume ile hesaplanir.

        Args:
            skill_id: Beceri ID'si.
            duration: Pratik suresi (saniye).
            performance_score: Performans puani (0.0-1.0).
            notes: Pratik notlari.

        Returns:
            Guncellenmis Skill nesnesi veya bulunamazsa None.
        """
        skill = self._skills.get(skill_id)
        if skill is None:
            logger.warning("Beceri bulunamadi: %s", skill_id)
            return None

        # Pratik logunu kaydet
        practice_log = PracticeLog(
            skill_id=skill_id,
            duration=duration,
            performance_score=performance_score,
            notes=notes,
        )
        self._practice_logs.setdefault(skill_id, []).append(practice_log)

        # Metrikleri guncelle
        skill.practice_count += 1
        skill.total_practice_time += duration

        # Yeterlilik: logaritmik ogrenme egrisi
        skill.proficiency = min(
            1.0,
            math.log(1 + skill.practice_count) * self._learning_rate,
        )

        # Otomatiklik: ustel buyume (1 - e^(-0.3 * n))
        skill.automaticity = 1.0 - math.exp(-0.3 * skill.practice_count)

        # Otomatik isleme modu kontrolu
        if skill.automaticity >= self._automaticity_threshold:
            skill.processing_mode = ProcessingMode.AUTOMATIC

        # Seviye guncelle
        self._update_level(skill)

        # Son pratik zamani
        skill.last_practiced = datetime.now(timezone.utc)

        logger.info(
            "Pratik kaydedildi: %s (sayi=%d, yeterlilik=%.3f, "
            "otomatiklik=%.3f, seviye=%s)",
            skill.name,
            skill.practice_count,
            skill.proficiency,
            skill.automaticity,
            skill.level.value,
        )
        return skill

    def retrieve_skill(self, skill_id: str) -> Skill | None:
        """Beceri bilgisini getirir.

        Args:
            skill_id: Beceri ID'si.

        Returns:
            Skill nesnesi veya bulunamazsa None.
        """
        return self._skills.get(skill_id)

    def get_by_domain(self, domain: str) -> list[Skill]:
        """Belirli bir alana ait becerileri listeler.

        Args:
            domain: Beceri alani.

        Returns:
            Alana ait Skill listesi.
        """
        return [
            skill
            for skill in self._skills.values()
            if skill.domain == domain
        ]

    def get_practice_history(self, skill_id: str) -> list[PracticeLog]:
        """Becerinin pratik gecmisini dondurur.

        Args:
            skill_id: Beceri ID'si.

        Returns:
            PracticeLog listesi (bos liste eger beceri yoksa).
        """
        return list(self._practice_logs.get(skill_id, []))

    def calculate_proficiency(self, skill_id: str) -> float:
        """Mevcut yeterlilik degerini hesaplar.

        Logaritmik ogrenme egrisi: min(1.0, log(1 + n) * rate)

        Args:
            skill_id: Beceri ID'si.

        Returns:
            Yeterlilik degeri (0.0-1.0). Beceri bulunamazsa 0.0.
        """
        skill = self._skills.get(skill_id)
        if skill is None:
            return 0.0

        return min(
            1.0,
            math.log(1 + skill.practice_count) * self._learning_rate,
        )

    def is_automatic(self, skill_id: str) -> bool:
        """Becerinin otomatik isleme esigini asip asmadigini kontrol eder.

        Args:
            skill_id: Beceri ID'si.

        Returns:
            Otomatik isleme modundaysa True, degilse veya bulunamazsa False.
        """
        skill = self._skills.get(skill_id)
        if skill is None:
            return False

        return skill.automaticity >= self._automaticity_threshold

    def _update_level(self, skill: Skill) -> None:
        """Yeterlilik degerine gore beceri seviyesini gunceller.

        Seviye esikleri:
            0.0 - 0.2: NOVICE
            0.2 - 0.4: BEGINNER
            0.4 - 0.6: INTERMEDIATE
            0.6 - 0.8: ADVANCED
            0.8 - 1.0: EXPERT

        Args:
            skill: Guncellenecek Skill nesnesi.
        """
        proficiency = skill.proficiency

        if proficiency >= 0.8:
            skill.level = SkillLevel.EXPERT
        elif proficiency >= 0.6:
            skill.level = SkillLevel.ADVANCED
        elif proficiency >= 0.4:
            skill.level = SkillLevel.INTERMEDIATE
        elif proficiency >= 0.2:
            skill.level = SkillLevel.BEGINNER
        else:
            skill.level = SkillLevel.NOVICE

    def count(self) -> int:
        """Toplam beceri sayisini dondurur.

        Returns:
            Kayitli Skill sayisi.
        """
        return len(self._skills)
