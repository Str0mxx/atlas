"""ATLAS Kullanici Hizalayici modulu.

Kullanici tercihlerini ogrenme, hedef onerisi,
onay alma, sinirlara saygi gosterme ve
geri bildirim entegrasyonu.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from app.models.goal_pursuit import AlignmentLevel

logger = logging.getLogger(__name__)


class UserAligner:
    """Kullanici hizalayici.

    Hedeflerin kullanici tercihleri ve
    degerleriyle uyumunu saglar.

    Attributes:
        _preferences: Kullanici tercihleri.
        _boundaries: Sinirlar/kisitlamalar.
        _suggestions: Oneri gecmisi.
        _feedback: Geri bildirim kayitlari.
        _approval_queue: Onay kuyrugu.
    """

    def __init__(self) -> None:
        """Kullanici hizalayiciyi baslatir."""
        self._preferences: dict[str, Any] = {}
        self._boundaries: dict[str, dict[str, Any]] = {}
        self._suggestions: list[dict[str, Any]] = []
        self._feedback: list[dict[str, Any]] = []
        self._approval_queue: list[dict[str, Any]] = []
        self._approved: dict[str, bool] = {}
        self._preference_history: list[dict[str, Any]] = []

        logger.info("UserAligner baslatildi")

    def learn_preference(
        self,
        key: str,
        value: Any,
        source: str = "explicit",
    ) -> None:
        """Kullanici tercihi ogrenir.

        Args:
            key: Tercih anahtari.
            value: Tercih degeri.
            source: Kaynak (explicit/inferred/feedback).
        """
        old_value = self._preferences.get(key)
        self._preferences[key] = value

        self._preference_history.append({
            "key": key,
            "old_value": old_value,
            "new_value": value,
            "source": source,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        logger.info("Tercih ogrendi: %s = %s (%s)", key, value, source)

    def get_preference(
        self,
        key: str,
        default: Any = None,
    ) -> Any:
        """Kullanici tercihini getirir.

        Args:
            key: Tercih anahtari.
            default: Varsayilan deger.

        Returns:
            Tercih degeri.
        """
        return self._preferences.get(key, default)

    def get_all_preferences(self) -> dict[str, Any]:
        """Tum tercihleri getirir.

        Returns:
            Tercih sozlugu.
        """
        return dict(self._preferences)

    def set_boundary(
        self,
        name: str,
        description: str = "",
        hard_limit: bool = True,
        conditions: dict[str, Any] | None = None,
    ) -> None:
        """Sinir/kisitlama ayarlar.

        Args:
            name: Sinir adi.
            description: Aciklama.
            hard_limit: Kesin sinir mi.
            conditions: Kosullar.
        """
        self._boundaries[name] = {
            "description": description,
            "hard_limit": hard_limit,
            "conditions": conditions or {},
        }

    def remove_boundary(self, name: str) -> bool:
        """Sinir kaldirir.

        Args:
            name: Sinir adi.

        Returns:
            Basarili ise True.
        """
        if name in self._boundaries:
            del self._boundaries[name]
            return True
        return False

    def check_boundaries(
        self,
        goal_context: dict[str, Any],
    ) -> dict[str, Any]:
        """Sinirlari kontrol eder.

        Args:
            goal_context: Hedef baglami.

        Returns:
            Sinir kontrol sonucu.
        """
        violations: list[str] = []
        warnings: list[str] = []

        for name, boundary in self._boundaries.items():
            conditions = boundary.get("conditions", {})
            for key, limit in conditions.items():
                value = goal_context.get(key)
                if value is not None and isinstance(value, (int, float)):
                    if isinstance(limit, (int, float)) and value > limit:
                        if boundary.get("hard_limit"):
                            violations.append(
                                f"{name}: {key}={value} > {limit}",
                            )
                        else:
                            warnings.append(
                                f"{name}: {key}={value} > {limit}",
                            )

        return {
            "passed": len(violations) == 0,
            "violations": violations,
            "warnings": warnings,
        }

    def suggest_goal(
        self,
        goal_id: str,
        title: str,
        description: str = "",
        rationale: str = "",
        estimated_value: float = 0.0,
    ) -> dict[str, Any]:
        """Kullaniciya hedef onerir.

        Args:
            goal_id: Hedef ID.
            title: Baslik.
            description: Aciklama.
            rationale: Gerekce.
            estimated_value: Tahmini deger.

        Returns:
            Oneri kaydi.
        """
        suggestion = {
            "goal_id": goal_id,
            "title": title,
            "description": description,
            "rationale": rationale,
            "estimated_value": estimated_value,
            "status": "pending",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._suggestions.append(suggestion)

        # Onay kuyruguna ekle
        self._approval_queue.append({
            "goal_id": goal_id,
            "title": title,
            "type": "goal_suggestion",
        })

        logger.info("Hedef onerisi: %s", title)
        return suggestion

    def approve_goal(self, goal_id: str) -> bool:
        """Hedefi onaylar.

        Args:
            goal_id: Hedef ID.

        Returns:
            Basarili ise True.
        """
        self._approved[goal_id] = True

        # Kuyruktan cikar
        self._approval_queue = [
            q for q in self._approval_queue
            if q.get("goal_id") != goal_id
        ]

        # Oneriyi guncelle
        for s in self._suggestions:
            if s.get("goal_id") == goal_id:
                s["status"] = "approved"

        logger.info("Hedef onaylandi: %s", goal_id)
        return True

    def reject_goal(
        self,
        goal_id: str,
        reason: str = "",
    ) -> bool:
        """Hedefi reddeder.

        Args:
            goal_id: Hedef ID.
            reason: Red nedeni.

        Returns:
            Basarili ise True.
        """
        self._approved[goal_id] = False

        self._approval_queue = [
            q for q in self._approval_queue
            if q.get("goal_id") != goal_id
        ]

        for s in self._suggestions:
            if s.get("goal_id") == goal_id:
                s["status"] = "rejected"
                s["reject_reason"] = reason

        # Geri bildirimden ogren
        if reason:
            self._feedback.append({
                "type": "rejection",
                "goal_id": goal_id,
                "reason": reason,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

        return True

    def is_approved(self, goal_id: str) -> bool | None:
        """Hedef onay durumunu kontrol eder.

        Args:
            goal_id: Hedef ID.

        Returns:
            True/False veya None (beklemede).
        """
        return self._approved.get(goal_id)

    def add_feedback(
        self,
        feedback_type: str,
        content: str,
        goal_id: str = "",
        sentiment: str = "neutral",
    ) -> dict[str, Any]:
        """Geri bildirim ekler.

        Args:
            feedback_type: Tur.
            content: Icerik.
            goal_id: Hedef ID.
            sentiment: Duygu (positive/neutral/negative).

        Returns:
            Geri bildirim kaydi.
        """
        feedback = {
            "type": feedback_type,
            "content": content,
            "goal_id": goal_id,
            "sentiment": sentiment,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._feedback.append(feedback)

        return feedback

    def calculate_alignment(
        self,
        goal_context: dict[str, Any],
    ) -> AlignmentLevel:
        """Hizalama seviyesi hesaplar.

        Args:
            goal_context: Hedef baglami.

        Returns:
            AlignmentLevel degeri.
        """
        # Sinir kontrolu
        boundary_check = self.check_boundaries(goal_context)
        if not boundary_check["passed"]:
            return AlignmentLevel.MISALIGNED

        # Tercih uyumu
        match_count = 0
        total_checks = 0

        for key, pref_value in self._preferences.items():
            if key in goal_context:
                total_checks += 1
                goal_value = goal_context[key]
                if goal_value == pref_value:
                    match_count += 1
                elif isinstance(goal_value, (int, float)) and isinstance(
                    pref_value, (int, float),
                ):
                    if abs(goal_value - pref_value) / max(
                        abs(pref_value), 1,
                    ) < 0.2:
                        match_count += 1

        if total_checks == 0:
            return AlignmentLevel.NEUTRAL

        ratio = match_count / total_checks
        if ratio >= 0.8:
            return AlignmentLevel.STRONG
        if ratio >= 0.5:
            return AlignmentLevel.MODERATE
        if ratio >= 0.3:
            return AlignmentLevel.WEAK
        return AlignmentLevel.MISALIGNED

    def get_approval_queue(self) -> list[dict[str, Any]]:
        """Onay kuyrugunu getirir.

        Returns:
            Bekleyen onaylar.
        """
        return list(self._approval_queue)

    def get_suggestions(
        self,
        status: str = "",
    ) -> list[dict[str, Any]]:
        """Onerileri getirir.

        Args:
            status: Durum filtresi.

        Returns:
            Oneri listesi.
        """
        if status:
            return [
                s for s in self._suggestions
                if s.get("status") == status
            ]
        return list(self._suggestions)

    def get_feedback(
        self,
        feedback_type: str = "",
    ) -> list[dict[str, Any]]:
        """Geri bildirimleri getirir.

        Args:
            feedback_type: Tur filtresi.

        Returns:
            Geri bildirim listesi.
        """
        if feedback_type:
            return [
                f for f in self._feedback
                if f.get("type") == feedback_type
            ]
        return list(self._feedback)

    @property
    def preference_count(self) -> int:
        """Tercih sayisi."""
        return len(self._preferences)

    @property
    def boundary_count(self) -> int:
        """Sinir sayisi."""
        return len(self._boundaries)

    @property
    def suggestion_count(self) -> int:
        """Oneri sayisi."""
        return len(self._suggestions)

    @property
    def pending_approvals(self) -> int:
        """Bekleyen onay sayisi."""
        return len(self._approval_queue)

    @property
    def feedback_count(self) -> int:
        """Geri bildirim sayisi."""
        return len(self._feedback)
