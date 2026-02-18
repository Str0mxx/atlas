"""
Karar gezgini modulu.

Karar gozetleme, baglam goruntusu,
muhakeme gosterimi, sonuc takibi,
karsilastirma.
"""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class DecisionExplorer:
    """Karar gezgini.

    Attributes:
        _decisions: Karar kayitlari.
        _stats: Istatistikler.
    """

    def __init__(self) -> None:
        """Gezgini baslatir."""
        self._decisions: list[dict] = []
        self._stats: dict[str, int] = {
            "decisions_recorded": 0,
            "outcomes_tracked": 0,
        }
        logger.info(
            "DecisionExplorer baslatildi"
        )

    @property
    def decision_count(self) -> int:
        """Karar sayisi."""
        return len(self._decisions)

    def record_decision(
        self,
        title: str = "",
        actor: str = "",
        context: str = "",
        reasoning: str = "",
        alternatives: list[str]
        | None = None,
        outcome: str = "pending",
        category: str = "operational",
        confidence: float = 0.8,
    ) -> dict[str, Any]:
        """Karar kaydeder.

        Args:
            title: Baslik.
            actor: Karar veren.
            context: Baglam.
            reasoning: Muhakeme.
            alternatives: Alternatifler.
            outcome: Sonuc.
            category: Kategori.
            confidence: Guven skoru.

        Returns:
            Kayit bilgisi.
        """
        try:
            did = f"dc_{uuid4()!s:.8}"
            decision = {
                "decision_id": did,
                "title": title,
                "actor": actor,
                "context": context,
                "reasoning": reasoning,
                "alternatives": (
                    alternatives or []
                ),
                "outcome": outcome,
                "category": category,
                "confidence": confidence,
                "timestamp": datetime.now(
                    timezone.utc
                ).isoformat(),
                "outcome_history": [],
            }
            self._decisions.append(decision)
            self._stats[
                "decisions_recorded"
            ] += 1

            return {
                "decision_id": did,
                "title": title,
                "actor": actor,
                "category": category,
                "recorded": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "recorded": False,
                "error": str(e),
            }

    def explore_decision(
        self,
        decision_id: str = "",
    ) -> dict[str, Any]:
        """Karar detayini getirir.

        Args:
            decision_id: Karar ID.

        Returns:
            Karar detayi.
        """
        try:
            for d in self._decisions:
                if (
                    d["decision_id"]
                    == decision_id
                ):
                    return {
                        "decision": d,
                        "found": True,
                    }

            return {
                "decision_id": decision_id,
                "found": False,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "found": False,
                "error": str(e),
            }

    def track_outcome(
        self,
        decision_id: str = "",
        outcome: str = "",
        success: bool = True,
        notes: str = "",
    ) -> dict[str, Any]:
        """Sonuc takibi yapar.

        Args:
            decision_id: Karar ID.
            outcome: Sonuc.
            success: Basarili mi.
            notes: Notlar.

        Returns:
            Takip bilgisi.
        """
        try:
            for d in self._decisions:
                if (
                    d["decision_id"]
                    == decision_id
                ):
                    d["outcome"] = outcome
                    d["outcome_history"].append(
                        {
                            "outcome": outcome,
                            "success": success,
                            "notes": notes,
                            "timestamp": (
                                datetime.now(
                                    timezone.utc
                                ).isoformat()
                            ),
                        }
                    )
                    self._stats[
                        "outcomes_tracked"
                    ] += 1

                    return {
                        "decision_id": (
                            decision_id
                        ),
                        "outcome": outcome,
                        "success": success,
                        "tracked": True,
                    }

            return {
                "decision_id": decision_id,
                "tracked": False,
                "reason": "not_found",
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "tracked": False,
                "error": str(e),
            }

    def compare_decisions(
        self,
        decision_ids: list[str]
        | None = None,
    ) -> dict[str, Any]:
        """Kararlari karsilastirir.

        Args:
            decision_ids: Karar ID listesi.

        Returns:
            Karsilastirma bilgisi.
        """
        try:
            ids = decision_ids or []
            found = []

            for d in self._decisions:
                if d["decision_id"] in ids:
                    found.append({
                        "decision_id": d[
                            "decision_id"
                        ],
                        "title": d["title"],
                        "outcome": d[
                            "outcome"
                        ],
                        "confidence": d[
                            "confidence"
                        ],
                        "category": d[
                            "category"
                        ],
                        "alternatives_count": (
                            len(
                                d[
                                    "alternatives"
                                ]
                            )
                        ),
                    })

            return {
                "decisions": found,
                "compared_count": len(found),
                "requested_count": len(ids),
                "compared": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "compared": False,
                "error": str(e),
            }

    def get_by_actor(
        self,
        actor: str = "",
    ) -> dict[str, Any]:
        """Aktore gore kararlari getirir.

        Args:
            actor: Aktor adi.

        Returns:
            Karar listesi.
        """
        try:
            decisions = [
                d
                for d in self._decisions
                if d["actor"] == actor
            ]

            return {
                "actor": actor,
                "decisions": decisions,
                "decision_count": len(
                    decisions
                ),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }

    def get_by_category(
        self,
        category: str = "operational",
    ) -> dict[str, Any]:
        """Kategoriye gore kararlari getirir.

        Args:
            category: Kategori.

        Returns:
            Karar listesi.
        """
        try:
            decisions = [
                d
                for d in self._decisions
                if d["category"] == category
            ]

            return {
                "category": category,
                "decisions": decisions,
                "decision_count": len(
                    decisions
                ),
                "retrieved": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "retrieved": False,
                "error": str(e),
            }

    def get_success_rate(
        self,
    ) -> dict[str, Any]:
        """Basari oranini hesaplar.

        Returns:
            Basari orani bilgisi.
        """
        try:
            total = 0
            successful = 0

            for d in self._decisions:
                for oh in d.get(
                    "outcome_history", []
                ):
                    total += 1
                    if oh.get("success"):
                        successful += 1

            rate = (
                (successful / total * 100)
                if total > 0
                else 0.0
            )

            return {
                "total_outcomes": total,
                "successful": successful,
                "success_rate": round(
                    rate, 1
                ),
                "calculated": True,
            }

        except Exception as e:
            logger.error(f"Hata: {e}")
            return {
                "calculated": False,
                "error": str(e),
            }
