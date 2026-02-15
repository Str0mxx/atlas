"""ATLAS Karar Kaydedici modulu.

Karar baglami yakalama, girdi verileri,
degerlendirilen alternatifler, faktorler, zaman damgasi.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class DecisionRecorder:
    """Karar kaydedici.

    Karar sureclerini kaydeder.

    Attributes:
        _decisions: Karar kayitlari.
        _contexts: Baglam kayitlari.
    """

    def __init__(self) -> None:
        """Karar kaydediciyi baslatir."""
        self._decisions: dict[
            str, dict[str, Any]
        ] = {}
        self._contexts: dict[
            str, dict[str, Any]
        ] = {}
        self._stats = {
            "recorded": 0,
        }

        logger.info(
            "DecisionRecorder baslatildi",
        )

    def record_decision(
        self,
        decision_id: str,
        decision_type: str = "",
        description: str = "",
        system: str = "",
    ) -> dict[str, Any]:
        """Karar kaydeder.

        Args:
            decision_id: Karar ID.
            decision_type: Karar tipi.
            description: Aciklama.
            system: Sistem adi.

        Returns:
            Kayit bilgisi.
        """
        record = {
            "decision_id": decision_id,
            "decision_type": decision_type,
            "description": description,
            "system": system,
            "inputs": {},
            "alternatives": [],
            "factors": [],
            "outcome": None,
            "recorded_at": time.time(),
            "completed_at": None,
        }

        self._decisions[decision_id] = record
        self._stats["recorded"] += 1

        return {
            "decision_id": decision_id,
            "recorded": True,
        }

    def capture_context(
        self,
        decision_id: str,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Karar baglamini yakalar.

        Args:
            decision_id: Karar ID.
            context: Baglam verisi.

        Returns:
            Yakalama bilgisi.
        """
        decision = self._decisions.get(
            decision_id,
        )
        if not decision:
            return {"error": "decision_not_found"}

        self._contexts[decision_id] = {
            "decision_id": decision_id,
            "context": dict(context),
            "captured_at": time.time(),
        }

        return {
            "decision_id": decision_id,
            "context_captured": True,
            "fields": len(context),
        }

    def log_inputs(
        self,
        decision_id: str,
        inputs: dict[str, Any],
    ) -> dict[str, Any]:
        """Girdi verilerini kaydeder.

        Args:
            decision_id: Karar ID.
            inputs: Girdi verileri.

        Returns:
            Kayit bilgisi.
        """
        decision = self._decisions.get(
            decision_id,
        )
        if not decision:
            return {"error": "decision_not_found"}

        decision["inputs"].update(inputs)

        return {
            "decision_id": decision_id,
            "inputs_logged": True,
            "input_count": len(decision["inputs"]),
        }

    def log_alternatives(
        self,
        decision_id: str,
        alternatives: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Degerlendirilen alternatifleri kaydeder.

        Args:
            decision_id: Karar ID.
            alternatives: Alternatifler.

        Returns:
            Kayit bilgisi.
        """
        decision = self._decisions.get(
            decision_id,
        )
        if not decision:
            return {"error": "decision_not_found"}

        for alt in alternatives:
            alt["logged_at"] = time.time()
            decision["alternatives"].append(alt)

        return {
            "decision_id": decision_id,
            "alternatives_logged": True,
            "count": len(
                decision["alternatives"],
            ),
        }

    def log_factors(
        self,
        decision_id: str,
        factors: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Degerlendirilen faktorleri kaydeder.

        Args:
            decision_id: Karar ID.
            factors: Faktorler.

        Returns:
            Kayit bilgisi.
        """
        decision = self._decisions.get(
            decision_id,
        )
        if not decision:
            return {"error": "decision_not_found"}

        for f in factors:
            f["logged_at"] = time.time()
            decision["factors"].append(f)

        return {
            "decision_id": decision_id,
            "factors_logged": True,
            "count": len(decision["factors"]),
        }

    def record_outcome(
        self,
        decision_id: str,
        outcome: str,
        confidence: float = 0.0,
        rationale: str = "",
    ) -> dict[str, Any]:
        """Karar sonucunu kaydeder.

        Args:
            decision_id: Karar ID.
            outcome: Sonuc.
            confidence: Guven skoru.
            rationale: Gerekce.

        Returns:
            Kayit bilgisi.
        """
        decision = self._decisions.get(
            decision_id,
        )
        if not decision:
            return {"error": "decision_not_found"}

        decision["outcome"] = {
            "result": outcome,
            "confidence": confidence,
            "rationale": rationale,
            "decided_at": time.time(),
        }
        decision["completed_at"] = time.time()

        return {
            "decision_id": decision_id,
            "outcome_recorded": True,
            "confidence": confidence,
        }

    def get_decision(
        self,
        decision_id: str,
    ) -> dict[str, Any]:
        """Karar kaydini getirir.

        Args:
            decision_id: Karar ID.

        Returns:
            Karar kaydi.
        """
        decision = self._decisions.get(
            decision_id,
        )
        if not decision:
            return {"error": "decision_not_found"}

        result = dict(decision)
        ctx = self._contexts.get(decision_id)
        if ctx:
            result["context"] = ctx["context"]

        return result

    def get_decisions(
        self,
        system: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Karar listesi getirir.

        Args:
            system: Sistem filtresi.
            limit: Limit.

        Returns:
            Karar listesi.
        """
        decisions = list(
            self._decisions.values(),
        )
        if system:
            decisions = [
                d for d in decisions
                if d.get("system") == system
            ]
        return decisions[-limit:]

    @property
    def decision_count(self) -> int:
        """Karar sayisi."""
        return len(self._decisions)

    @property
    def recorded_count(self) -> int:
        """Kaydedilen sayisi."""
        return self._stats["recorded"]
