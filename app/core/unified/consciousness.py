"""ATLAS Bilinc Katmani modulu.

Oz-farkindalik, mevcut durum anlayisi,
hedef farkindaliigi, cevre farkindaliigi
ve yetenek farkindaliigi.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from app.models.unified import AwarenessState, ConsciousnessLevel

logger = logging.getLogger(__name__)


class Consciousness:
    """Bilinc katmani.

    Sistemin kendi durumunu, hedeflerini,
    cevresini ve yeteneklerini anlamasi.

    Attributes:
        _level: Bilinc seviyesi.
        _awareness: Guncel farkindalik.
        _state_history: Durum gecmisi.
        _introspections: Ic gozlem kayitlari.
    """

    def __init__(
        self,
        initial_level: ConsciousnessLevel = ConsciousnessLevel.MEDIUM,
    ) -> None:
        """Bilinc katmanini baslatir.

        Args:
            initial_level: Baslangic bilinc seviyesi.
        """
        self._level = initial_level
        self._awareness = AwarenessState()
        self._state_history: list[dict[str, Any]] = []
        self._introspections: list[dict[str, Any]] = []
        self._started_at = datetime.now(timezone.utc)

        logger.info(
            "Consciousness baslatildi (level=%s)",
            initial_level.value,
        )

    def update_self_state(self, state: str) -> None:
        """Oz-durum gunceller.

        Args:
            state: Yeni durum.
        """
        old = self._awareness.self_state
        self._awareness.self_state = state
        self._awareness.timestamp = datetime.now(timezone.utc)

        self._state_history.append({
            "old_state": old,
            "new_state": state,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def update_goals(self, goals: list[str]) -> None:
        """Aktif hedefleri gunceller.

        Args:
            goals: Hedef listesi.
        """
        self._awareness.active_goals = list(goals)

    def update_capabilities(self, capabilities: list[str]) -> None:
        """Yetenekleri gunceller.

        Args:
            capabilities: Yetenek listesi.
        """
        self._awareness.capabilities = list(capabilities)

    def update_environment(self, env: dict[str, Any]) -> None:
        """Cevre bilgisini gunceller.

        Args:
            env: Cevre verisi.
        """
        self._awareness.environment.update(env)

    def update_limitations(self, limitations: list[str]) -> None:
        """Sinirliliklari gunceller.

        Args:
            limitations: Sinirlilik listesi.
        """
        self._awareness.limitations = list(limitations)

    def set_level(self, level: ConsciousnessLevel) -> None:
        """Bilinc seviyesini ayarlar.

        Args:
            level: Yeni seviye.
        """
        old = self._level
        self._level = level

        self._state_history.append({
            "type": "level_change",
            "old_level": old.value,
            "new_level": level.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        logger.info("Bilinc seviyesi: %s -> %s", old.value, level.value)

    def introspect(self) -> dict[str, Any]:
        """Ic gozlem yapar.

        Returns:
            Ic gozlem sonucu.
        """
        result = {
            "level": self._level.value,
            "self_state": self._awareness.self_state,
            "goal_count": len(self._awareness.active_goals),
            "capability_count": len(self._awareness.capabilities),
            "environment_keys": list(self._awareness.environment.keys()),
            "limitation_count": len(self._awareness.limitations),
            "confidence": self._awareness.confidence,
            "uptime": (
                datetime.now(timezone.utc) - self._started_at
            ).total_seconds(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._introspections.append(result)
        return result

    def assess_confidence(self) -> float:
        """Guven seviyesini degerlendirir.

        Returns:
            Guven puani (0-1).
        """
        factors = []

        # Hedef farkindaliigi
        if self._awareness.active_goals:
            factors.append(0.8)
        else:
            factors.append(0.3)

        # Yetenek farkindaliigi
        if self._awareness.capabilities:
            factors.append(0.9)
        else:
            factors.append(0.4)

        # Cevre farkindaliigi
        if self._awareness.environment:
            factors.append(0.7)
        else:
            factors.append(0.3)

        # Sinirlilik farkindaliigi (bilmek iyi)
        if self._awareness.limitations:
            factors.append(0.8)
        else:
            factors.append(0.5)

        confidence = sum(factors) / len(factors) if factors else 0.5
        self._awareness.confidence = round(confidence, 3)
        return self._awareness.confidence

    def get_awareness(self) -> AwarenessState:
        """Guncel farkindaligi getirir.

        Returns:
            AwarenessState nesnesi.
        """
        return self._awareness

    def get_state_history(
        self,
        limit: int = 0,
    ) -> list[dict[str, Any]]:
        """Durum gecmisini getirir.

        Args:
            limit: Maks kayit.

        Returns:
            Gecmis listesi.
        """
        if limit > 0:
            return self._state_history[-limit:]
        return list(self._state_history)

    def get_introspections(
        self,
        limit: int = 0,
    ) -> list[dict[str, Any]]:
        """Ic gozlemleri getirir.

        Args:
            limit: Maks kayit.

        Returns:
            Ic gozlem listesi.
        """
        if limit > 0:
            return self._introspections[-limit:]
        return list(self._introspections)

    @property
    def level(self) -> ConsciousnessLevel:
        """Bilinc seviyesi."""
        return self._level

    @property
    def uptime(self) -> float:
        """Calisma suresi (saniye)."""
        return (datetime.now(timezone.utc) - self._started_at).total_seconds()

    @property
    def introspection_count(self) -> int:
        """Ic gozlem sayisi."""
        return len(self._introspections)
