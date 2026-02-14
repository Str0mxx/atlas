"""ATLAS Ilerleme Degerlendirici modulu.

Hedef ilerleme takibi, kilometre tasi
degerlendirmesi, rota duzeltme, hedef
terk karari ve basari bildirimi.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from app.models.goal_pursuit import GoalState

logger = logging.getLogger(__name__)


class ProgressEvaluator:
    """Ilerleme degerlendirici.

    Hedeflerin ilerlemesini izler,
    degerlendirir ve yonlendirir.

    Attributes:
        _progress: Hedef ilerleme kayitlari.
        _milestones: Kilometre tasi durumlari.
        _corrections: Rota duzeltmeleri.
        _evaluations: Degerlendirme gecmisi.
    """

    def __init__(self) -> None:
        """Ilerleme degerlendiriciyi baslatir."""
        self._progress: dict[str, dict[str, Any]] = {}
        self._milestones: dict[str, list[dict[str, Any]]] = {}
        self._corrections: dict[str, list[dict[str, Any]]] = {}
        self._evaluations: list[dict[str, Any]] = []

        logger.info("ProgressEvaluator baslatildi")

    def track_progress(
        self,
        goal_id: str,
        progress: float,
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Ilerleme kaydeder.

        Args:
            goal_id: Hedef ID.
            progress: Ilerleme orani (0-1).
            details: Detaylar.

        Returns:
            Ilerleme kaydi.
        """
        clamped = max(0.0, min(1.0, progress))
        now = datetime.now(timezone.utc).isoformat()

        if goal_id not in self._progress:
            self._progress[goal_id] = {
                "current": 0.0,
                "history": [],
                "state": GoalState.ACTIVE.value,
                "started_at": now,
            }

        record = self._progress[goal_id]
        previous = record["current"]
        record["current"] = clamped
        record["history"].append({
            "progress": clamped,
            "previous": previous,
            "timestamp": now,
            "details": details or {},
        })

        return {
            "goal_id": goal_id,
            "progress": clamped,
            "delta": round(clamped - previous, 4),
        }

    def add_milestone(
        self,
        goal_id: str,
        name: str,
        target_progress: float = 0.5,
    ) -> dict[str, Any]:
        """Kilometre tasi ekler.

        Args:
            goal_id: Hedef ID.
            name: Tas adi.
            target_progress: Hedef ilerleme.

        Returns:
            Kilometre tasi kaydi.
        """
        milestone = {
            "name": name,
            "target_progress": max(0.0, min(1.0, target_progress)),
            "reached": False,
            "reached_at": None,
        }
        self._milestones.setdefault(goal_id, []).append(milestone)
        return milestone

    def evaluate_milestones(
        self,
        goal_id: str,
    ) -> dict[str, Any]:
        """Kilometre taslarini degerlendirir.

        Args:
            goal_id: Hedef ID.

        Returns:
            Degerlendirme sonucu.
        """
        milestones = self._milestones.get(goal_id, [])
        progress_record = self._progress.get(goal_id, {})
        current = progress_record.get("current", 0.0)

        reached = 0
        total = len(milestones)
        now = datetime.now(timezone.utc).isoformat()

        for ms in milestones:
            if not ms["reached"] and current >= ms["target_progress"]:
                ms["reached"] = True
                ms["reached_at"] = now
                reached += 1

        already_reached = sum(1 for m in milestones if m["reached"])

        return {
            "goal_id": goal_id,
            "total_milestones": total,
            "reached": already_reached,
            "newly_reached": reached,
            "remaining": total - already_reached,
        }

    def suggest_correction(
        self,
        goal_id: str,
        issue: str,
        suggestion: str,
        severity: str = "medium",
    ) -> dict[str, Any]:
        """Rota duzeltme onerisi kaydeder.

        Args:
            goal_id: Hedef ID.
            issue: Tespit edilen sorun.
            suggestion: Oneri.
            severity: Ciddiyet (low/medium/high).

        Returns:
            Duzeltme kaydi.
        """
        correction = {
            "issue": issue,
            "suggestion": suggestion,
            "severity": severity,
            "applied": False,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._corrections.setdefault(goal_id, []).append(correction)
        return correction

    def apply_correction(
        self,
        goal_id: str,
        index: int,
    ) -> bool:
        """Rota duzeltmesini uygular.

        Args:
            goal_id: Hedef ID.
            index: Duzeltme indeksi.

        Returns:
            Basarili ise True.
        """
        corrections = self._corrections.get(goal_id, [])
        if 0 <= index < len(corrections):
            corrections[index]["applied"] = True
            return True
        return False

    def should_abandon(
        self,
        goal_id: str,
        min_progress_rate: float = 0.01,
        max_stale_entries: int = 5,
    ) -> dict[str, Any]:
        """Hedef terk kararini degerlendirir.

        Args:
            goal_id: Hedef ID.
            min_progress_rate: Minimum ilerleme orani.
            max_stale_entries: Maksimum durgun girdi sayisi.

        Returns:
            Terk degerlendirmesi.
        """
        record = self._progress.get(goal_id)
        if not record:
            return {
                "goal_id": goal_id,
                "should_abandon": False,
                "reason": "Ilerleme kaydi yok",
            }

        history = record.get("history", [])
        if len(history) < 2:
            return {
                "goal_id": goal_id,
                "should_abandon": False,
                "reason": "Yeterli veri yok",
            }

        # Son girdilerdeki ilerleme
        recent = history[-max_stale_entries:]
        deltas = [
            abs(recent[i]["progress"] - recent[i - 1]["progress"])
            for i in range(1, len(recent))
        ]

        avg_delta = sum(deltas) / len(deltas) if deltas else 0.0
        stale = avg_delta < min_progress_rate

        return {
            "goal_id": goal_id,
            "should_abandon": stale,
            "avg_delta": round(avg_delta, 6),
            "reason": "Ilerleme durgun" if stale else "Ilerleme devam ediyor",
        }

    def declare_success(
        self,
        goal_id: str,
    ) -> dict[str, Any]:
        """Basari bildirir.

        Args:
            goal_id: Hedef ID.

        Returns:
            Basari bildirimi.
        """
        record = self._progress.get(goal_id)
        if not record:
            return {"success": False, "reason": "Ilerleme kaydi yok"}

        record["state"] = GoalState.COMPLETED.value
        record["completed_at"] = datetime.now(timezone.utc).isoformat()

        milestones = self._milestones.get(goal_id, [])
        reached = sum(1 for m in milestones if m["reached"])

        evaluation = {
            "goal_id": goal_id,
            "final_progress": record["current"],
            "milestones_reached": reached,
            "total_milestones": len(milestones),
            "corrections_applied": sum(
                1 for c in self._corrections.get(goal_id, [])
                if c["applied"]
            ),
            "declared_at": record["completed_at"],
        }
        self._evaluations.append(evaluation)

        logger.info("Hedef basarili: %s", goal_id)
        return {"success": True, **evaluation}

    def declare_failure(
        self,
        goal_id: str,
        reason: str = "",
    ) -> dict[str, Any]:
        """Basarisizlik bildirir.

        Args:
            goal_id: Hedef ID.
            reason: Basarisizlik nedeni.

        Returns:
            Basarisizlik bildirimi.
        """
        record = self._progress.get(goal_id)
        if not record:
            return {"success": False, "reason": "Ilerleme kaydi yok"}

        record["state"] = GoalState.FAILED.value

        evaluation = {
            "goal_id": goal_id,
            "final_progress": record["current"],
            "reason": reason,
            "declared_at": datetime.now(timezone.utc).isoformat(),
        }
        self._evaluations.append(evaluation)

        return {"success": True, **evaluation}

    def get_progress(
        self,
        goal_id: str,
    ) -> dict[str, Any] | None:
        """Ilerleme getirir.

        Args:
            goal_id: Hedef ID.

        Returns:
            Ilerleme kaydi veya None.
        """
        return self._progress.get(goal_id)

    def get_corrections(
        self,
        goal_id: str,
    ) -> list[dict[str, Any]]:
        """Rota duzeltmelerini getirir.

        Args:
            goal_id: Hedef ID.

        Returns:
            Duzeltme listesi.
        """
        return list(self._corrections.get(goal_id, []))

    @property
    def total_tracked(self) -> int:
        """Takip edilen hedef sayisi."""
        return len(self._progress)

    @property
    def total_evaluations(self) -> int:
        """Toplam degerlendirme sayisi."""
        return len(self._evaluations)

    @property
    def success_count(self) -> int:
        """Basarili hedef sayisi."""
        return sum(
            1 for r in self._progress.values()
            if r.get("state") == GoalState.COMPLETED.value
        )
