"""ATLAS Karar Matrisi modulu.

Gelen olaylarin risk, aciliyet ve aksiyon tipini belirler.
Master Agent bu matrisi kullanarak karar verir.
"""

import logging
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class RiskLevel(str, Enum):
    """Risk seviyesi tanimlari."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class UrgencyLevel(str, Enum):
    """Aciliyet seviyesi tanimlari."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ActionType(str, Enum):
    """Aksiyon tipi tanimlari."""

    LOG = "log"                  # Sadece kaydet
    NOTIFY = "notify"            # Bildir (Telegram vb.)
    AUTO_FIX = "auto_fix"        # Otomatik duzelt
    IMMEDIATE = "immediate"      # Hemen mudahale et


class Decision(BaseModel):
    """Karar matrisi sonucu."""

    risk: RiskLevel
    urgency: UrgencyLevel
    action: ActionType
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str = ""


# === Karar kurallari tablosu ===
# (risk, urgency) -> (action, confidence)
DECISION_RULES: dict[tuple[RiskLevel, UrgencyLevel], tuple[ActionType, float]] = {
    # Dusuk risk
    (RiskLevel.LOW, UrgencyLevel.LOW): (ActionType.LOG, 0.95),
    (RiskLevel.LOW, UrgencyLevel.MEDIUM): (ActionType.LOG, 0.90),
    (RiskLevel.LOW, UrgencyLevel.HIGH): (ActionType.NOTIFY, 0.85),
    # Orta risk
    (RiskLevel.MEDIUM, UrgencyLevel.LOW): (ActionType.NOTIFY, 0.85),
    (RiskLevel.MEDIUM, UrgencyLevel.MEDIUM): (ActionType.NOTIFY, 0.80),
    (RiskLevel.MEDIUM, UrgencyLevel.HIGH): (ActionType.AUTO_FIX, 0.75),
    # Yuksek risk
    (RiskLevel.HIGH, UrgencyLevel.LOW): (ActionType.NOTIFY, 0.80),
    (RiskLevel.HIGH, UrgencyLevel.MEDIUM): (ActionType.AUTO_FIX, 0.70),
    (RiskLevel.HIGH, UrgencyLevel.HIGH): (ActionType.IMMEDIATE, 0.90),
}


class DecisionMatrix:
    """Karar matrisi sinifi.

    Olaylari risk ve aciliyet seviyesine gore degerlendirip
    uygun aksiyon tipini belirler.
    """

    def __init__(self) -> None:
        """Karar matrisini baslatir."""
        self.rules = DECISION_RULES
        logger.info("Karar matrisi yuklendi (%d kural)", len(self.rules))

    async def evaluate(
        self,
        risk: RiskLevel,
        urgency: UrgencyLevel,
        context: dict[str, Any] | None = None,
    ) -> Decision:
        """Olayi degerlendirir ve karar uretir.

        Args:
            risk: Risk seviyesi.
            urgency: Aciliyet seviyesi.
            context: Ek baglamsal bilgi.

        Returns:
            Uretilen karar.
        """
        action, confidence = self.rules.get(
            (risk, urgency),
            (ActionType.NOTIFY, 0.5),  # Bilinmeyen kombinasyon icin varsayilan
        )

        decision = Decision(
            risk=risk,
            urgency=urgency,
            action=action,
            confidence=confidence,
            reason=self._build_reason(risk, urgency, action, context),
        )

        logger.info(
            "Karar: risk=%s, aciliyet=%s -> aksiyon=%s (guven=%.0f%%)",
            risk.value,
            urgency.value,
            action.value,
            confidence * 100,
        )
        return decision

    def _build_reason(
        self,
        risk: RiskLevel,
        urgency: UrgencyLevel,
        action: ActionType,
        context: dict[str, Any] | None,
    ) -> str:
        """Karar icin aciklama metni olusturur."""
        reason_parts = [
            f"Risk: {risk.value}",
            f"Aciliyet: {urgency.value}",
            f"Secilen aksiyon: {action.value}",
        ]
        if context and context.get("detail"):
            reason_parts.append(f"Detay: {context['detail']}")
        return " | ".join(reason_parts)

    def get_action_for(self, risk: str, urgency: str) -> ActionType:
        """Basit arayuz: string degerlerle aksiyon tipi dondurur.

        Args:
            risk: Risk seviyesi (low/medium/high).
            urgency: Aciliyet seviyesi (low/medium/high).

        Returns:
            Uygun aksiyon tipi.
        """
        risk_level = RiskLevel(risk)
        urgency_level = UrgencyLevel(urgency)
        action, _ = self.rules.get(
            (risk_level, urgency_level),
            (ActionType.NOTIFY, 0.5),
        )
        return action
