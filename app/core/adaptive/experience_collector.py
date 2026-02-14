"""ATLAS Deneyim Toplayici modulu.

Etkilesim loglama, sonuc takibi,
baglam yakalama, geri bildirim toplama
ve basari/basarisizlik etiketleme.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from app.models.adaptive import (
    ExperienceRecord,
    ExperienceType,
    OutcomeType,
)

logger = logging.getLogger(__name__)


class ExperienceCollector:
    """Deneyim toplayici.

    Tum etkilesimleri ve sonuclari
    kaydeder, baglamla zenginlestirir.

    Attributes:
        _experiences: Deneyim deposu.
        _context_stack: Baglam yigini.
        _outcome_counts: Sonuc sayaclari.
    """

    def __init__(self) -> None:
        """Deneyim toplayiciyi baslatir."""
        self._experiences: list[ExperienceRecord] = []
        self._context_stack: list[dict[str, Any]] = []
        self._outcome_counts: dict[str, int] = {
            o.value: 0 for o in OutcomeType
        }
        self._tag_index: dict[str, list[int]] = {}

        logger.info("ExperienceCollector baslatildi")

    def record(
        self,
        action: str,
        experience_type: ExperienceType = ExperienceType.INTERACTION,
        outcome: OutcomeType = OutcomeType.UNKNOWN,
        context: dict[str, Any] | None = None,
        reward: float = 0.0,
        tags: list[str] | None = None,
    ) -> ExperienceRecord:
        """Deneyim kaydeder.

        Args:
            action: Yapilan aksiyon.
            experience_type: Deneyim turu.
            outcome: Sonuc.
            context: Baglam bilgisi.
            reward: Odul degeri.
            tags: Etiketler.

        Returns:
            Deneyim kaydi.
        """
        merged_context = self._get_current_context()
        if context:
            merged_context.update(context)

        exp = ExperienceRecord(
            experience_type=experience_type,
            outcome=outcome,
            action=action,
            context=merged_context,
            reward=reward,
            tags=tags or [],
        )
        idx = len(self._experiences)
        self._experiences.append(exp)
        self._outcome_counts[outcome.value] += 1

        for tag in exp.tags:
            if tag not in self._tag_index:
                self._tag_index[tag] = []
            self._tag_index[tag].append(idx)

        logger.info(
            "Deneyim kaydedildi: %s (%s -> %s)",
            action, experience_type.value, outcome.value,
        )
        return exp

    def record_success(
        self,
        action: str,
        reward: float = 1.0,
        context: dict[str, Any] | None = None,
        tags: list[str] | None = None,
    ) -> ExperienceRecord:
        """Basarili deneyim kaydeder.

        Args:
            action: Aksiyon.
            reward: Odul.
            context: Baglam.
            tags: Etiketler.

        Returns:
            Deneyim kaydi.
        """
        return self.record(
            action=action,
            outcome=OutcomeType.SUCCESS,
            reward=reward,
            context=context,
            tags=tags,
        )

    def record_failure(
        self,
        action: str,
        reward: float = -1.0,
        context: dict[str, Any] | None = None,
        tags: list[str] | None = None,
    ) -> ExperienceRecord:
        """Basarisiz deneyim kaydeder.

        Args:
            action: Aksiyon.
            reward: Odul (negatif).
            context: Baglam.
            tags: Etiketler.

        Returns:
            Deneyim kaydi.
        """
        return self.record(
            action=action,
            outcome=OutcomeType.FAILURE,
            reward=reward,
            context=context,
            tags=tags,
        )

    def push_context(
        self,
        context: dict[str, Any],
    ) -> None:
        """Baglam ekler.

        Args:
            context: Baglam bilgisi.
        """
        self._context_stack.append(context)

    def pop_context(self) -> dict[str, Any] | None:
        """Baglam cikarir.

        Returns:
            Cikarilan baglam veya None.
        """
        if self._context_stack:
            return self._context_stack.pop()
        return None

    def get_by_outcome(
        self,
        outcome: OutcomeType,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Sonuca gore deneyim getirir.

        Args:
            outcome: Sonuc filtresi.
            limit: Maks kayit.

        Returns:
            Deneyim listesi.
        """
        filtered = [
            e for e in self._experiences
            if e.outcome == outcome
        ]
        return [
            {
                "experience_id": e.experience_id,
                "action": e.action,
                "outcome": e.outcome.value,
                "reward": e.reward,
                "tags": e.tags,
            }
            for e in filtered[-limit:]
        ]

    def get_by_tag(
        self,
        tag: str,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Etikete gore deneyim getirir.

        Args:
            tag: Etiket.
            limit: Maks kayit.

        Returns:
            Deneyim listesi.
        """
        indices = self._tag_index.get(tag, [])
        results = []
        for idx in indices[-limit:]:
            e = self._experiences[idx]
            results.append({
                "experience_id": e.experience_id,
                "action": e.action,
                "outcome": e.outcome.value,
                "reward": e.reward,
            })
        return results

    def get_success_rate(
        self,
        tag: str = "",
    ) -> float:
        """Basari oranini hesaplar.

        Args:
            tag: Etiket filtresi (bos=tum).

        Returns:
            Basari orani (0.0-1.0).
        """
        if tag:
            indices = self._tag_index.get(tag, [])
            if not indices:
                return 0.0
            exps = [self._experiences[i] for i in indices]
        else:
            exps = self._experiences

        if not exps:
            return 0.0

        successes = sum(
            1 for e in exps
            if e.outcome == OutcomeType.SUCCESS
        )
        return successes / len(exps)

    def get_recent(
        self,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Son deneyimleri getirir.

        Args:
            limit: Maks kayit.

        Returns:
            Deneyim listesi.
        """
        return [
            {
                "experience_id": e.experience_id,
                "action": e.action,
                "type": e.experience_type.value,
                "outcome": e.outcome.value,
                "reward": e.reward,
                "tags": e.tags,
            }
            for e in self._experiences[-limit:]
        ]

    def _get_current_context(self) -> dict[str, Any]:
        """Mevcut baglami birlestirir.

        Returns:
            Birlesmis baglam.
        """
        merged: dict[str, Any] = {}
        for ctx in self._context_stack:
            merged.update(ctx)
        return merged

    @property
    def total_count(self) -> int:
        """Toplam deneyim sayisi."""
        return len(self._experiences)

    @property
    def success_count(self) -> int:
        """Basarili deneyim sayisi."""
        return self._outcome_counts.get("success", 0)

    @property
    def failure_count(self) -> int:
        """Basarisiz deneyim sayisi."""
        return self._outcome_counts.get("failure", 0)

    @property
    def tag_count(self) -> int:
        """Benzersiz etiket sayisi."""
        return len(self._tag_index)
