"""ATLAS Catisma Cozucu modulu.

Kullanici hayal kirikligi tespiti, yakinlastirma stratejileri,
uygun ozur, alternatif sunma ve insan eskalasyonu.
"""

import logging

from app.models.emotional import (
    ConflictEvent,
    ConflictLevel,
    EscalationAction,
    UserEmotionalState,
)

logger = logging.getLogger(__name__)

# De-eskalasyon mesajlari
_DEESCALATION_MESSAGES: dict[ConflictLevel, list[str]] = {
    ConflictLevel.MILD: [
        "Anliyorum, daha iyi yapabilirim.",
        "Haklisiniz, hemen duzelteyim.",
    ],
    ConflictLevel.MODERATE: [
        "Ozur dilerim, bu durumun sinir bozucu oldugunu biliyorum.",
        "Bu benim hatam, hemen cozum uretiyorum.",
    ],
    ConflictLevel.HIGH: [
        "Gercekten ozur dilerim. Bu kabul edilemez ve duzeltilecek.",
        "Sizi hayal kirikligina ugrattigim icin cok uzgunum.",
    ],
    ConflictLevel.CRITICAL: [
        "Bu ciddi bir sorun ve en kisa surede Fatih'e bildiriyorum.",
        "Durumu anladim, hemen insan destegi devreye giriyor.",
    ],
}


class ConflictResolver:
    """Catisma cozucu sistemi.

    Kullanici frustrasyonunu tespit eder, uygun
    de-eskalasyon stratejileri uygular.

    Attributes:
        _events: Catisma olaylari.
        _consecutive_negatives: Ardisik negatif etkilesimler.
    """

    def __init__(self, escalation_threshold: float = 0.8) -> None:
        """Catisma cozucuyu baslatir.

        Args:
            escalation_threshold: Eskalasyon esigi.
        """
        self._events: list[ConflictEvent] = []
        self._consecutive_negatives: dict[str, int] = {}
        self._escalation_threshold = escalation_threshold

        logger.info("ConflictResolver baslatildi (threshold=%.2f)", escalation_threshold)

    def assess_conflict(self, user_id: str, state: UserEmotionalState) -> ConflictLevel:
        """Catisma seviyesini degerlendirir.

        Args:
            user_id: Kullanici ID.
            state: Kullanici duygusal durumu.

        Returns:
            ConflictLevel degeri.
        """
        frustration = state.frustration_level
        consecutive = self._consecutive_negatives.get(user_id, 0)

        if frustration > 0.9 or consecutive >= 5:
            return ConflictLevel.CRITICAL
        if frustration > 0.7 or consecutive >= 4:
            return ConflictLevel.HIGH
        if frustration > 0.4 or consecutive >= 3:
            return ConflictLevel.MODERATE
        if frustration > 0.2 or consecutive >= 2:
            return ConflictLevel.MILD
        return ConflictLevel.NONE

    def track_negative(self, user_id: str) -> int:
        """Negatif etkilesim sayar.

        Args:
            user_id: Kullanici ID.

        Returns:
            Ardisik negatif sayisi.
        """
        count = self._consecutive_negatives.get(user_id, 0) + 1
        self._consecutive_negatives[user_id] = count
        return count

    def reset_negative(self, user_id: str) -> None:
        """Negatif sayacini sifirlar.

        Args:
            user_id: Kullanici ID.
        """
        self._consecutive_negatives[user_id] = 0

    def determine_action(self, level: ConflictLevel) -> EscalationAction:
        """Eskalasyon aksiyonunu belirler.

        Args:
            level: Catisma seviyesi.

        Returns:
            EscalationAction degeri.
        """
        action_map: dict[ConflictLevel, EscalationAction] = {
            ConflictLevel.NONE: EscalationAction.NONE,
            ConflictLevel.MILD: EscalationAction.ACKNOWLEDGE,
            ConflictLevel.MODERATE: EscalationAction.APOLOGIZE,
            ConflictLevel.HIGH: EscalationAction.OFFER_ALTERNATIVE,
            ConflictLevel.CRITICAL: EscalationAction.ESCALATE_HUMAN,
        }
        return action_map.get(level, EscalationAction.NONE)

    def get_deescalation_message(self, level: ConflictLevel) -> str:
        """De-eskalasyon mesaji getirir.

        Args:
            level: Catisma seviyesi.

        Returns:
            De-eskalasyon mesaji.
        """
        messages = _DEESCALATION_MESSAGES.get(level, [])
        if not messages:
            return ""
        return messages[0]

    def resolve(self, user_id: str, state: UserEmotionalState, trigger: str = "") -> ConflictEvent:
        """Catismayi cozer.

        Args:
            user_id: Kullanici ID.
            state: Kullanici duygusal durumu.
            trigger: Tetikleyici.

        Returns:
            ConflictEvent nesnesi.
        """
        level = self.assess_conflict(user_id, state)
        action = self.determine_action(level)
        message = self.get_deescalation_message(level)

        resolved = level in (ConflictLevel.NONE, ConflictLevel.MILD)

        event = ConflictEvent(
            user_id=user_id,
            level=level,
            trigger=trigger,
            action_taken=action,
            resolved=resolved,
            resolution_note=message,
        )

        self._events.append(event)

        if level == ConflictLevel.CRITICAL:
            logger.warning("KRITIK catisma: %s - insan eskalasyonu", user_id)
        elif level != ConflictLevel.NONE:
            logger.info("Catisma cozumlendi: %s level=%s", user_id, level.value)

        return event

    def should_escalate_to_human(self, user_id: str, state: UserEmotionalState) -> bool:
        """Insana eskalasyon gerekli mi.

        Args:
            user_id: Kullanici ID.
            state: Kullanici duygusal durumu.

        Returns:
            Eskalasyon gerekli mi.
        """
        return (
            state.frustration_level >= self._escalation_threshold
            or self._consecutive_negatives.get(user_id, 0) >= 5
        )

    def get_user_conflicts(self, user_id: str) -> list[ConflictEvent]:
        """Kullanici catismalarini getirir.

        Args:
            user_id: Kullanici ID.

        Returns:
            ConflictEvent listesi.
        """
        return [e for e in self._events if e.user_id == user_id]

    @property
    def event_count(self) -> int:
        """Olay sayisi."""
        return len(self._events)

    @property
    def unresolved_count(self) -> int:
        """Cozulmemis catisma sayisi."""
        return sum(1 for e in self._events if not e.resolved)
