"""ATLAS Insan Geri Bildirimi modulu.

Karar toplama, duzeltmelerden ogrenme,
guven guncelleme, tercih ogrenme, uyusmazlik yonetimi.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class HumanFeedbackHandler:
    """Insan geri bildirim yoneticisi.

    Insan geri bildirimlerinden ogrenir.

    Attributes:
        _feedback: Geri bildirim kayitlari.
        _preferences: Tercih kayitlari.
    """

    def __init__(self) -> None:
        """Insan geri bildirim yoneticisini baslatir."""
        self._feedback: list[
            dict[str, Any]
        ] = []
        self._action_feedback: dict[
            str, list[dict[str, Any]]
        ] = {}
        self._preferences: dict[
            str, dict[str, Any]
        ] = {}
        self._disagreements: list[
            dict[str, Any]
        ] = []
        self._corrections: list[
            dict[str, Any]
        ] = []
        self._stats = {
            "approvals": 0,
            "rejections": 0,
            "corrections": 0,
            "overrides": 0,
        }

        logger.info(
            "HumanFeedbackHandler baslatildi",
        )

    def collect_decision(
        self,
        action_id: str,
        human_decision: str,
        system_suggestion: str = "",
        reason: str = "",
    ) -> dict[str, Any]:
        """Insan kararini toplar.

        Args:
            action_id: Aksiyon ID.
            human_decision: Insan karari.
            system_suggestion: Sistem onerisi.
            reason: Neden.

        Returns:
            Kayit bilgisi.
        """
        fb = {
            "action_id": action_id,
            "human_decision": human_decision,
            "system_suggestion": system_suggestion,
            "reason": reason,
            "agreed": (
                human_decision == system_suggestion
            ),
            "timestamp": time.time(),
        }

        self._feedback.append(fb)
        if action_id not in self._action_feedback:
            self._action_feedback[action_id] = []
        self._action_feedback[action_id].append(fb)

        if human_decision == "approve":
            self._stats["approvals"] += 1
        elif human_decision == "reject":
            self._stats["rejections"] += 1
        elif human_decision == "override":
            self._stats["overrides"] += 1

        # Uyusmazlik tespiti
        if not fb["agreed"] and system_suggestion:
            self._disagreements.append(fb)

        return {
            "action_id": action_id,
            "agreed": fb["agreed"],
            "recorded": True,
        }

    def learn_from_correction(
        self,
        action_id: str,
        original_action: str,
        corrected_action: str,
        domain: str = "",
    ) -> dict[str, Any]:
        """Duzeltmeden ogrenir.

        Args:
            action_id: Aksiyon ID.
            original_action: Orijinal aksiyon.
            corrected_action: Duzeltilmis aksiyon.
            domain: Alan.

        Returns:
            Ogrenme bilgisi.
        """
        correction = {
            "action_id": action_id,
            "original": original_action,
            "corrected": corrected_action,
            "domain": domain,
            "timestamp": time.time(),
        }

        self._corrections.append(correction)
        self._stats["corrections"] += 1

        # Tercih guncelle
        if domain:
            self._update_preference(
                domain, corrected_action,
            )

        return {
            "action_id": action_id,
            "learned": True,
            "correction_count": len(
                self._corrections,
            ),
        }

    def update_confidence_from_feedback(
        self,
        action_id: str,
    ) -> dict[str, Any]:
        """Geri bildirimden guven gunceller.

        Args:
            action_id: Aksiyon ID.

        Returns:
            Guncelleme bilgisi.
        """
        fbs = self._action_feedback.get(
            action_id, [],
        )
        if not fbs:
            return {
                "action_id": action_id,
                "adjustment": 0.0,
            }

        agreed = sum(
            1 for fb in fbs if fb.get("agreed")
        )
        total = len(fbs)
        agreement_rate = agreed / total

        # Yuksek uyum = guven artisi
        if agreement_rate > 0.8:
            adjustment = 0.1
        elif agreement_rate > 0.5:
            adjustment = 0.0
        else:
            adjustment = -0.1

        return {
            "action_id": action_id,
            "agreement_rate": round(
                agreement_rate, 4,
            ),
            "adjustment": adjustment,
        }

    def learn_preference(
        self,
        domain: str,
        key: str,
        value: Any,
    ) -> dict[str, Any]:
        """Tercih ogrenir.

        Args:
            domain: Alan.
            key: Tercih anahtari.
            value: Tercih degeri.

        Returns:
            Kayit bilgisi.
        """
        if domain not in self._preferences:
            self._preferences[domain] = {}
        self._preferences[domain][key] = {
            "value": value,
            "updated_at": time.time(),
        }

        return {
            "domain": domain,
            "key": key,
            "learned": True,
        }

    def get_preference(
        self,
        domain: str,
        key: str,
    ) -> Any:
        """Tercihi getirir.

        Args:
            domain: Alan.
            key: Tercih anahtari.

        Returns:
            Tercih degeri veya None.
        """
        prefs = self._preferences.get(domain, {})
        pref = prefs.get(key)
        if pref:
            return pref["value"]
        return None

    def get_disagreements(
        self,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Uyusmazliklari getirir.

        Args:
            limit: Limit.

        Returns:
            Uyusmazlik listesi.
        """
        return list(self._disagreements[-limit:])

    def get_agreement_rate(self) -> float:
        """Uyum oranini getirir.

        Returns:
            Uyum orani.
        """
        if not self._feedback:
            return 0.0
        agreed = sum(
            1 for fb in self._feedback
            if fb.get("agreed")
        )
        return round(
            agreed / len(self._feedback), 4,
        )

    def get_corrections(
        self,
        domain: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Duzeltmeleri getirir.

        Args:
            domain: Alan filtresi.
            limit: Limit.

        Returns:
            Duzeltme listesi.
        """
        corrections = self._corrections
        if domain:
            corrections = [
                c for c in corrections
                if c.get("domain") == domain
            ]
        return list(corrections[-limit:])

    def _update_preference(
        self,
        domain: str,
        action: str,
    ) -> None:
        """Tercihi gunceller (dahili).

        Args:
            domain: Alan.
            action: Tercih edilen aksiyon.
        """
        if domain not in self._preferences:
            self._preferences[domain] = {}
        self._preferences[domain][
            "preferred_action"
        ] = {
            "value": action,
            "updated_at": time.time(),
        }

    @property
    def feedback_count(self) -> int:
        """Geri bildirim sayisi."""
        return len(self._feedback)

    @property
    def correction_count(self) -> int:
        """Duzeltme sayisi."""
        return len(self._corrections)

    @property
    def disagreement_count(self) -> int:
        """Uyusmazlik sayisi."""
        return len(self._disagreements)

    @property
    def preference_count(self) -> int:
        """Tercih sayisi."""
        return sum(
            len(p)
            for p in self._preferences.values()
        )
