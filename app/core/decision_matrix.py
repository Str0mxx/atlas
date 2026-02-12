"""ATLAS Karar Matrisi modulu.

Gelen olaylarin risk, aciliyet ve aksiyon tipini belirler.
Master Agent bu matrisi kullanarak karar verir.
Olasiliksal karar destegi, guven esigi ve risk toleransi icerir.
"""

import logging
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from app.models.decision import RuleChangeRecord

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

# Risk seviyesi -> float eslesmesi
_RISK_LEVEL_MAP: dict[str, float] = {
    "low": 0.2,
    "medium": 0.5,
    "high": 0.9,
}


class DecisionMatrix:
    """Karar matrisi sinifi.

    Olaylari risk ve aciliyet seviyesine gore degerlendirip
    uygun aksiyon tipini belirler. Olasiliksal karar destegi,
    guven esigi ve risk toleransi parametreleri icerir.
    """

    def __init__(
        self,
        confidence_threshold: float = 0.6,
        risk_tolerance: float = 0.5,
    ) -> None:
        """Karar matrisini baslatir.

        Args:
            confidence_threshold: Otonom aksiyon icin minimum guven esigi.
            risk_tolerance: Risk toleransi (0=kacinan, 1=arayan).
        """
        self.rules = dict(DECISION_RULES)
        self.confidence_threshold = confidence_threshold
        self.risk_tolerance = risk_tolerance

        # Lazy import — dairesel bagimliligi onler
        from app.core.autonomy.uncertainty import UncertaintyManager

        self._uncertainty_mgr = UncertaintyManager(
            risk_tolerance=risk_tolerance,
        )
        self._bayesian_net: Any = None
        self._rule_history: list[RuleChangeRecord] = []

        logger.info(
            "Karar matrisi yuklendi (%d kural, guven_esigi=%.2f, "
            "risk_toleransi=%.2f)",
            len(self.rules), confidence_threshold, risk_tolerance,
        )

    async def evaluate(
        self,
        risk: RiskLevel,
        urgency: UrgencyLevel,
        context: dict[str, Any] | None = None,
        beliefs: dict[str, float] | None = None,
    ) -> Decision:
        """Olayi degerlendirir ve karar uretir.

        Beliefs verildiginde guven esigi kontrolu yaparak
        dusuk guvenli durumlarda aksiyonu NOTIFY'a dusurur.

        Args:
            risk: Risk seviyesi.
            urgency: Aciliyet seviyesi.
            context: Ek baglamsal bilgi.
            beliefs: Belief key -> confidence eslesmesi (opsiyonel).

        Returns:
            Uretilen karar.
        """
        action, confidence = self.rules.get(
            (risk, urgency),
            (ActionType.NOTIFY, 0.5),  # Bilinmeyen kombinasyon icin varsayilan
        )

        # Olasiliksal guven kontrolu
        if beliefs:
            avg_confidence = self._uncertainty_mgr.aggregate_confidence(
                list(beliefs.values()),
            )
            risk_float = self._risk_level_to_float(risk)
            if not self._uncertainty_mgr.should_act(
                avg_confidence,
                risk_float,
                self.confidence_threshold,
            ):
                # Guven yetersiz, aksiyonu dusur
                if action in (ActionType.AUTO_FIX, ActionType.IMMEDIATE):
                    action = ActionType.NOTIFY
                    confidence *= avg_confidence

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

    async def evaluate_probabilistic(
        self,
        risk: RiskLevel,
        urgency: UrgencyLevel,
        evidence: list[Any] | None = None,
        context: dict[str, Any] | None = None,
    ) -> Decision:
        """Olasiliksal karar verir (Bayesci ag destegi ile).

        Evidence verildiginde Bayesci ag uzerinden posterior
        guncelleme yapar ve guncel posterior'a gore karar verir.

        Args:
            risk: Risk seviyesi.
            urgency: Aciliyet seviyesi.
            evidence: Kanit listesi (Evidence nesneleri).
            context: Ek baglamsal bilgi.

        Returns:
            Olasiliksal olarak guncellenmis karar.
        """
        action, base_confidence = self.rules.get(
            (risk, urgency),
            (ActionType.NOTIFY, 0.5),
        )

        confidence = base_confidence

        # Bayesci ag varsa ve kanit verilmisse
        if self._bayesian_net is not None and evidence:
            posteriors = {}
            for ev in evidence:
                results = self._bayesian_net.propagate_evidence(ev)
                posteriors.update(results)

            # Posterior'lardan ortalama guven cikart
            if posteriors:
                posterior_confidences: list[float] = []
                for result in posteriors.values():
                    max_prob = max(
                        result.posterior.values(),
                    ) if result.posterior else 0.5
                    posterior_confidences.append(max_prob)

                avg_posterior = self._uncertainty_mgr.aggregate_confidence(
                    posterior_confidences,
                )
                confidence = base_confidence * avg_posterior

                risk_float = self._risk_level_to_float(risk)
                if not self._uncertainty_mgr.should_act(
                    avg_posterior,
                    risk_float,
                    self.confidence_threshold,
                ):
                    if action in (
                        ActionType.AUTO_FIX, ActionType.IMMEDIATE,
                    ):
                        action = ActionType.NOTIFY

        decision = Decision(
            risk=risk,
            urgency=urgency,
            action=action,
            confidence=confidence,
            reason=self._build_reason(risk, urgency, action, context),
        )

        logger.info(
            "Olasiliksal karar: risk=%s, aciliyet=%s -> "
            "aksiyon=%s (guven=%.0f%%)",
            risk.value, urgency.value,
            action.value, confidence * 100,
        )
        return decision

    def set_bayesian_network(self, network: Any) -> None:
        """Bayesci agi ayarlar.

        Args:
            network: Kullanilacak Bayesci ag (BayesianNetwork).
        """
        self._bayesian_net = network
        logger.info("Bayesci ag ayarlandi")

    def set_confidence_threshold(self, threshold: float) -> None:
        """Guven esigini gunceller.

        Args:
            threshold: Yeni guven esigi (0-1).
        """
        self.confidence_threshold = max(0.0, min(1.0, threshold))

    def set_risk_tolerance(self, tolerance: float) -> None:
        """Risk toleransini gunceller.

        Args:
            tolerance: Yeni risk toleransi (0-1).
        """
        self.risk_tolerance = max(0.0, min(1.0, tolerance))
        from app.core.autonomy.uncertainty import UncertaintyManager
        self._uncertainty_mgr = UncertaintyManager(
            risk_tolerance=self.risk_tolerance,
        )

    def update_rule(
        self,
        risk: RiskLevel,
        urgency: UrgencyLevel,
        new_action: ActionType,
        new_confidence: float,
        changed_by: str = "system",
    ) -> RuleChangeRecord:
        """Tek bir karar kuralini calisma zamaninda gunceller.

        Args:
            risk: Guncellenecek kuralin risk seviyesi.
            urgency: Guncellenecek kuralin aciliyet seviyesi.
            new_action: Yeni aksiyon tipi.
            new_confidence: Yeni guven skoru (0-1).
            changed_by: Degisikligi yapan (system/user/learning).

        Returns:
            Kural degisikligi kaydi.
        """
        key = (risk, urgency)
        old_action, old_confidence = self.rules.get(
            key, (ActionType.NOTIFY, 0.5),
        )

        clamped_confidence = max(0.0, min(1.0, new_confidence))
        record = RuleChangeRecord(
            risk=risk.value,
            urgency=urgency.value,
            old_action=old_action.value,
            new_action=new_action.value,
            old_confidence=old_confidence,
            new_confidence=clamped_confidence,
            changed_by=changed_by,
        )

        self.rules[key] = (new_action, clamped_confidence)
        self._rule_history.append(record)

        logger.info(
            "Kural guncellendi: (%s, %s) %s->%s (guven: %.2f->%.2f, by=%s)",
            risk.value, urgency.value,
            old_action.value, new_action.value,
            old_confidence, clamped_confidence,
            changed_by,
        )
        return record

    def get_rule_history(self) -> list[RuleChangeRecord]:
        """Kural degisiklik gecmisini dondurur.

        Returns:
            Tum kural degisikligi kayitlari.
        """
        return list(self._rule_history)

    def reset_rules(self) -> None:
        """Kurallari orijinal varsayilan degerlere sifirlar.

        Not: Degisiklik gecmisi silinmez, denetim izi olarak kalir.
        """
        self.rules = dict(DECISION_RULES)
        logger.info("Karar kurallari varsayilanlara sifirlandi")

    def explain_decision(
        self,
        risk: RiskLevel,
        urgency: UrgencyLevel,
        context: dict[str, Any] | None = None,
        beliefs: dict[str, float] | None = None,
    ) -> str:
        """Karar surecini detayli aciklar.

        Verilen risk/aciliyet icin uygulanacak kararin tam aciklamasini
        insan tarafindan okunabilir formatta uretir.

        Args:
            risk: Risk seviyesi.
            urgency: Aciliyet seviyesi.
            context: Ek baglamsal bilgi.
            beliefs: Belief key -> confidence eslesmesi.

        Returns:
            Detayli karar aciklamasi metni.
        """
        action, confidence = self.rules.get(
            (risk, urgency), (ActionType.NOTIFY, 0.5),
        )

        parts = [
            "Karar Aciklamasi:",
            f"  Risk seviyesi: {risk.value}",
            f"  Aciliyet seviyesi: {urgency.value}",
            f"  Kural tablosundan aksiyon: {action.value} (guven: {confidence:.0%})",
            f"  Guven esigi: {self.confidence_threshold:.0%}",
            f"  Risk toleransi: {self.risk_tolerance:.0%}",
        ]

        if beliefs:
            avg = self._uncertainty_mgr.aggregate_confidence(
                list(beliefs.values()),
            )
            risk_float = self._risk_level_to_float(risk)
            should = self._uncertainty_mgr.should_act(
                avg, risk_float, self.confidence_threshold,
            )
            parts.append(f"  Belief ortalama guven: {avg:.0%}")
            parts.append(f"  Aksiyona gecilmeli: {'evet' if should else 'hayir'}")
            if not should and action in (ActionType.AUTO_FIX, ActionType.IMMEDIATE):
                parts.append("  -> Aksiyon NOTIFY'a dusuruldu (yetersiz guven)")

        if context and context.get("detail"):
            parts.append(f"  Baglamsal detay: {context['detail']}")

        return "\n".join(parts)

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

    @staticmethod
    def _risk_level_to_float(risk: RiskLevel) -> float:
        """RiskLevel enum'ini float'a cevirir.

        Args:
            risk: Risk seviyesi.

        Returns:
            Float risk degeri.
        """
        return _RISK_LEVEL_MAP.get(risk.value, 0.5)
