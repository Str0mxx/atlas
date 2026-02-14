"""ATLAS Ogrenme Cikarici modulu.

Basari kaliplari, basarisizlik analizi,
strateji iyilestirme, bilgi kaydi ve
en iyi uygulama guncellemesi.
"""

import logging
from typing import Any

from app.models.goal_pursuit import LearningRecord, LearningType

logger = logging.getLogger(__name__)


class LearningExtractor:
    """Ogrenme cikarici.

    Hedef takip surecinden ogrenimleri
    cikarir ve kaydeder.

    Attributes:
        _records: Ogrenme kayitlari.
        _patterns: Tespit edilen kalipler.
        _best_practices: En iyi uygulamalar.
        _anti_patterns: Kacınilacak kalipler.
    """

    def __init__(self) -> None:
        """Ogrenme cikariciyi baslatir."""
        self._records: dict[str, LearningRecord] = {}
        self._patterns: dict[str, list[dict[str, Any]]] = {}
        self._best_practices: list[dict[str, Any]] = []
        self._anti_patterns: list[dict[str, Any]] = []
        self._goal_learnings: dict[str, list[str]] = {}

        logger.info("LearningExtractor baslatildi")

    def extract_success_pattern(
        self,
        goal_id: str,
        title: str,
        description: str = "",
        insights: list[str] | None = None,
        applicability: list[str] | None = None,
        confidence: float = 0.5,
    ) -> LearningRecord:
        """Basari kalibi cikarir.

        Args:
            goal_id: Hedef ID.
            title: Baslik.
            description: Aciklama.
            insights: Icegorular.
            applicability: Uygulanabilirlik alanlari.
            confidence: Guven puani.

        Returns:
            LearningRecord nesnesi.
        """
        record = LearningRecord(
            goal_id=goal_id,
            learning_type=LearningType.SUCCESS_PATTERN,
            title=title,
            description=description,
            insights=insights or [],
            applicability=applicability or [],
            confidence=confidence,
        )
        self._records[record.record_id] = record
        self._goal_learnings.setdefault(goal_id, []).append(
            record.record_id,
        )

        self._patterns.setdefault("success", []).append({
            "record_id": record.record_id,
            "title": title,
            "confidence": confidence,
        })

        logger.info("Basari kalibi cikarildi: %s", title)
        return record

    def analyze_failure(
        self,
        goal_id: str,
        title: str,
        description: str = "",
        root_causes: list[str] | None = None,
        lessons: list[str] | None = None,
        confidence: float = 0.5,
    ) -> LearningRecord:
        """Basarisizlik analizi yapar.

        Args:
            goal_id: Hedef ID.
            title: Baslik.
            description: Aciklama.
            root_causes: Kok nedenler.
            lessons: Dersler.
            confidence: Guven puani.

        Returns:
            LearningRecord nesnesi.
        """
        record = LearningRecord(
            goal_id=goal_id,
            learning_type=LearningType.FAILURE_ANALYSIS,
            title=title,
            description=description,
            insights=root_causes or [],
            applicability=lessons or [],
            confidence=confidence,
        )
        self._records[record.record_id] = record
        self._goal_learnings.setdefault(goal_id, []).append(
            record.record_id,
        )

        self._anti_patterns.append({
            "record_id": record.record_id,
            "title": title,
            "root_causes": root_causes or [],
        })

        logger.info("Basarisizlik analiz edildi: %s", title)
        return record

    def refine_strategy(
        self,
        goal_id: str,
        title: str,
        current_strategy: str = "",
        refined_strategy: str = "",
        rationale: list[str] | None = None,
    ) -> LearningRecord:
        """Strateji iyilestirmesi kaydeder.

        Args:
            goal_id: Hedef ID.
            title: Baslik.
            current_strategy: Mevcut strateji.
            refined_strategy: Iyilestirilmis strateji.
            rationale: Gerekce.

        Returns:
            LearningRecord nesnesi.
        """
        record = LearningRecord(
            goal_id=goal_id,
            learning_type=LearningType.STRATEGY_INSIGHT,
            title=title,
            description=f"Onceki: {current_strategy} -> Yeni: {refined_strategy}",
            insights=rationale or [],
        )
        self._records[record.record_id] = record
        self._goal_learnings.setdefault(goal_id, []).append(
            record.record_id,
        )

        return record

    def capture_knowledge(
        self,
        goal_id: str,
        title: str,
        knowledge: str,
        tags: list[str] | None = None,
    ) -> LearningRecord:
        """Bilgi kaydeder.

        Args:
            goal_id: Hedef ID.
            title: Baslik.
            knowledge: Bilgi icerigi.
            tags: Etiketler.

        Returns:
            LearningRecord nesnesi.
        """
        record = LearningRecord(
            goal_id=goal_id,
            learning_type=LearningType.BEST_PRACTICE,
            title=title,
            description=knowledge,
            applicability=tags or [],
        )
        self._records[record.record_id] = record
        self._goal_learnings.setdefault(goal_id, []).append(
            record.record_id,
        )

        return record

    def add_best_practice(
        self,
        title: str,
        description: str,
        context: str = "",
        effectiveness: float = 0.5,
    ) -> dict[str, Any]:
        """En iyi uygulama ekler.

        Args:
            title: Baslik.
            description: Aciklama.
            context: Baglam.
            effectiveness: Etkinlik (0-1).

        Returns:
            Uygulama kaydi.
        """
        practice = {
            "title": title,
            "description": description,
            "context": context,
            "effectiveness": max(0.0, min(1.0, effectiveness)),
            "usage_count": 0,
        }
        self._best_practices.append(practice)
        return practice

    def update_best_practice(
        self,
        index: int,
        effectiveness: float | None = None,
        increment_usage: bool = False,
    ) -> bool:
        """En iyi uygulamayi gunceller.

        Args:
            index: Uygulama indeksi.
            effectiveness: Yeni etkinlik.
            increment_usage: Kullanim sayisini artir.

        Returns:
            Basarili ise True.
        """
        if 0 <= index < len(self._best_practices):
            if effectiveness is not None:
                self._best_practices[index]["effectiveness"] = max(
                    0.0, min(1.0, effectiveness),
                )
            if increment_usage:
                self._best_practices[index]["usage_count"] += 1
            return True
        return False

    def get_learnings_for_goal(
        self,
        goal_id: str,
    ) -> list[LearningRecord]:
        """Hedefe ait ogrenimleri getirir.

        Args:
            goal_id: Hedef ID.

        Returns:
            Ogrenme listesi.
        """
        record_ids = self._goal_learnings.get(goal_id, [])
        return [
            self._records[rid]
            for rid in record_ids
            if rid in self._records
        ]

    def get_by_type(
        self,
        learning_type: LearningType,
    ) -> list[LearningRecord]:
        """Ture gore ogrenimleri getirir.

        Args:
            learning_type: Ogrenme turu.

        Returns:
            Ogrenme listesi.
        """
        return [
            r for r in self._records.values()
            if r.learning_type == learning_type
        ]

    def get_record(
        self,
        record_id: str,
    ) -> LearningRecord | None:
        """Ogrenme kaydini getirir.

        Args:
            record_id: Kayit ID.

        Returns:
            LearningRecord veya None.
        """
        return self._records.get(record_id)

    def get_best_practices(self) -> list[dict[str, Any]]:
        """En iyi uygulamalari getirir.

        Returns:
            Uygulama listesi.
        """
        return sorted(
            self._best_practices,
            key=lambda p: p["effectiveness"],
            reverse=True,
        )

    def get_anti_patterns(self) -> list[dict[str, Any]]:
        """Anti-kalipler getirir.

        Returns:
            Anti-kalip listesi.
        """
        return list(self._anti_patterns)

    @property
    def total_records(self) -> int:
        """Toplam kayit sayisi."""
        return len(self._records)

    @property
    def success_pattern_count(self) -> int:
        """Basari kalibi sayisi."""
        return len(self._patterns.get("success", []))

    @property
    def anti_pattern_count(self) -> int:
        """Anti-kalip sayisi."""
        return len(self._anti_patterns)

    @property
    def best_practice_count(self) -> int:
        """En iyi uygulama sayisi."""
        return len(self._best_practices)
