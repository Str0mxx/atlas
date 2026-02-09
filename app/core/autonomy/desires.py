"""ATLAS Desire/Goal sistemi modulu.

Sistemin hedeflerini yonetir. Hedef hiyerarsisi, onceliklendirme,
cakisma cozme, hedef benimseme ve birakma islemlerini saglar.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from app.core.decision_matrix import DecisionMatrix
from app.models.autonomy import (
    Desire,
    GoalPriority,
    GoalStatus,
)

logger = logging.getLogger("atlas.autonomy.desires")

# Oncelik -> baz skor eslesmesi
_PRIORITY_BASE_SCORE: dict[GoalPriority, float] = {
    GoalPriority.CRITICAL: 0.9,
    GoalPriority.HIGH: 0.7,
    GoalPriority.MEDIUM: 0.5,
    GoalPriority.LOW: 0.3,
}


class DesireBase:
    """Sistemin hedeflerini yoneten sinif.

    Hedefleri hiyerarsik olarak yonetir, dinamik onceliklendirme yapar
    ve cakisan hedefler arasinda secim yapar.

    Attributes:
        desires: Aktif hedefler (id -> Desire).
        decision_matrix: Karar matrisi (oncelik esleme icin).
    """

    def __init__(
        self,
        decision_matrix: DecisionMatrix | None = None,
    ) -> None:
        """DesireBase'i baslatir.

        Args:
            decision_matrix: Karar matrisi (None ise yeni olusturulur).
        """
        self.desires: dict[str, Desire] = {}
        self.decision_matrix = decision_matrix or DecisionMatrix()
        logger.info("DesireBase olusturuldu")

    async def adopt(self, desire: Desire) -> Desire:
        """Yeni hedef benimser.

        Args:
            desire: Benimsenen hedef.

        Returns:
            Kaydedilen hedef.
        """
        desire.priority_score = _PRIORITY_BASE_SCORE.get(
            desire.priority, 0.5,
        )
        self.desires[desire.id] = desire
        logger.info(
            "Hedef benimsendi: %s (oncelik=%.2f)",
            desire.name, desire.priority_score,
        )
        return desire

    async def drop(
        self,
        desire_id: str,
        reason: str = "",
    ) -> Desire | None:
        """Hedefi birakir (DROPPED durumuna getirir).

        Args:
            desire_id: Birakilacak hedef ID.
            reason: Birakma nedeni.

        Returns:
            Guncellenmis hedef veya None.
        """
        desire = self.desires.get(desire_id)
        if desire is None:
            return None

        desire.status = GoalStatus.DROPPED
        desire.metadata["drop_reason"] = reason
        logger.info("Hedef birakildi: %s (neden: %s)", desire.name, reason)
        return desire

    async def achieve(self, desire_id: str) -> Desire | None:
        """Hedefi tamamlanmis olarak isaretler.

        Args:
            desire_id: Tamamlanan hedef ID.

        Returns:
            Guncellenmis hedef veya None.
        """
        desire = self.desires.get(desire_id)
        if desire is None:
            return None

        desire.status = GoalStatus.ACHIEVED
        logger.info("Hedef tamamlandi: %s", desire.name)
        return desire

    async def add_sub_goal(
        self,
        parent_id: str,
        child: Desire,
    ) -> Desire | None:
        """Ust hedefe alt hedef ekler.

        Args:
            parent_id: Ust hedef ID.
            child: Alt hedef.

        Returns:
            Guncellenmis ust hedef veya None.
        """
        parent = self.desires.get(parent_id)
        if parent is None:
            return None

        child.parent_id = parent_id
        child.priority_score = _PRIORITY_BASE_SCORE.get(
            child.priority, 0.5,
        )
        self.desires[child.id] = child
        parent.sub_goal_ids.append(child.id)
        logger.info(
            "Alt hedef eklendi: %s -> %s", parent.name, child.name,
        )
        return parent

    async def update_priorities(
        self,
        beliefs: dict[str, Any],
    ) -> list[Desire]:
        """Tum hedeflerin oncelik puanlarini yeniden hesaplar.

        Belief durumuna, zaman baskisina ve baz oncelik'e gore
        dinamik puanlama yapar.

        Args:
            beliefs: Mevcut belief snapshot'i (key -> value).

        Returns:
            Guncellenen hedefler listesi.
        """
        updated: list[Desire] = []
        now = datetime.now(timezone.utc)

        for desire in self.desires.values():
            if desire.status != GoalStatus.ACTIVE:
                continue

            # Baz skor
            base_score = _PRIORITY_BASE_SCORE.get(desire.priority, 0.5)

            # Zaman baskisi (deadline varsa)
            time_bonus = 0.0
            if desire.deadline is not None:
                remaining = (desire.deadline - now).total_seconds()
                if remaining <= 0:
                    time_bonus = 0.3
                elif remaining < 3600:  # 1 saatten az
                    time_bonus = 0.2
                elif remaining < 86400:  # 1 gunden az
                    time_bonus = 0.1

            # Belief uyumu (preconditions ne kadar saglaniyor)
            belief_bonus = 0.0
            if desire.preconditions:
                matched = sum(
                    1 for k, v in desire.preconditions.items()
                    if beliefs.get(k) == v
                )
                belief_bonus = 0.1 * (matched / len(desire.preconditions))

            # Toplam skor
            new_score = min(1.0, base_score + time_bonus + belief_bonus)
            desire.priority_score = new_score
            updated.append(desire)

        return updated

    async def resolve_conflicts(
        self,
        desire_ids: list[str],
    ) -> str | None:
        """Cakisan hedefler arasinda en yuksek oncelikliyi secer.

        Args:
            desire_ids: Cakisan hedef ID'leri.

        Returns:
            Secilen hedef ID veya None.
        """
        if not desire_ids:
            return None

        candidates = [
            self.desires[did] for did in desire_ids
            if did in self.desires
        ]
        if not candidates:
            return None

        winner = max(candidates, key=lambda d: d.priority_score)
        logger.info(
            "Cakisma cozuldu: %s (skor=%.2f)",
            winner.name, winner.priority_score,
        )
        return winner.id

    def get_active(self) -> list[Desire]:
        """Aktif hedefleri oncelik sirasina gore dondurur.

        Returns:
            Oncelik puanina gore sirali aktif hedefler.
        """
        active = [
            d for d in self.desires.values()
            if d.status == GoalStatus.ACTIVE
        ]
        active.sort(key=lambda d: d.priority_score, reverse=True)
        return active

    def get_achievable(self, beliefs: dict[str, Any]) -> list[Desire]:
        """On kosullari saglanan hedefleri dondurur.

        Args:
            beliefs: Mevcut belief key-value eslemesi.

        Returns:
            On kosullari saglanan aktif hedefler.
        """
        result: list[Desire] = []
        for desire in self.get_active():
            if not desire.preconditions:
                result.append(desire)
                continue

            all_met = all(
                beliefs.get(k) == v
                for k, v in desire.preconditions.items()
            )
            if all_met:
                result.append(desire)
        return result

    def get(self, desire_id: str) -> Desire | None:
        """Tek bir hedefi getirir."""
        return self.desires.get(desire_id)

    def get_sub_goals(self, parent_id: str) -> list[Desire]:
        """Ust hedefin alt hedeflerini dondurur."""
        return [
            d for d in self.desires.values()
            if d.parent_id == parent_id
        ]

    def snapshot(self) -> dict[str, Any]:
        """Mevcut hedef durumunun goruntusunu dondurur."""
        return {
            "total": len(self.desires),
            "active": len(self.get_active()),
            "desires": {
                did: {
                    "name": d.name,
                    "priority": d.priority.value,
                    "priority_score": d.priority_score,
                    "status": d.status.value,
                }
                for did, d in self.desires.items()
            },
        }
