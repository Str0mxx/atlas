"""ATLAS Aksiyon Karar Verici modülü.

Kendi başına çöz vs eskalasyon, güven eşiği,
etki değerlendirmesi, risk değerlendirmesi,
onay yönlendirmesi.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class ActionDecider:
    """Aksiyon karar verici.

    Aksiyonları değerlendirir ve karar verir.

    Attributes:
        _decisions: Karar kayıtları.
        _thresholds: Güven eşikleri.
    """

    def __init__(
        self,
        auto_threshold: float = 0.8,
        escalation_threshold: float = 0.5,
    ) -> None:
        """Karar vericiyi başlatır.

        Args:
            auto_threshold: Otomatik işlem eşiği.
            escalation_threshold: Eskalasyon eşiği.
        """
        self._decisions: list[
            dict[str, Any]
        ] = []
        self._thresholds = {
            "auto": auto_threshold,
            "escalation": escalation_threshold,
        }
        self._approval_rules: list[
            dict[str, Any]
        ] = []
        self._counter = 0
        self._stats = {
            "decisions_made": 0,
            "auto_handled": 0,
            "escalated": 0,
            "deferred": 0,
        }

        logger.info(
            "ActionDecider baslatildi",
        )

    def decide(
        self,
        action: str,
        confidence: float = 0.5,
        impact: str = "low",
        risk: float = 0.3,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Aksiyon kararı verir.

        Args:
            action: Aksiyon açıklaması.
            confidence: Güven seviyesi (0-1).
            impact: Etki seviyesi.
            risk: Risk seviyesi (0-1).
            context: Bağlam.

        Returns:
            Karar bilgisi.
        """
        self._counter += 1
        did = f"dec_{self._counter}"
        confidence = max(0.0, min(1.0, confidence))
        risk = max(0.0, min(1.0, risk))

        # Karar mantığı
        decision_type = self._evaluate(
            confidence, impact, risk,
        )

        # Onay gereksinimi kontrolü
        needs_approval = (
            self._check_approval_needed(
                action, impact, risk,
            )
        )
        if needs_approval:
            decision_type = "escalate"

        decision = {
            "decision_id": did,
            "action": action,
            "decision_type": decision_type,
            "confidence": confidence,
            "impact": impact,
            "risk": risk,
            "needs_approval": needs_approval,
            "context": context or {},
            "decided_at": time.time(),
        }
        self._decisions.append(decision)
        self._stats["decisions_made"] += 1

        if decision_type == "auto_handle":
            self._stats["auto_handled"] += 1
        elif decision_type == "escalate":
            self._stats["escalated"] += 1
        elif decision_type == "defer":
            self._stats["deferred"] += 1

        return decision

    def _evaluate(
        self,
        confidence: float,
        impact: str,
        risk: float,
    ) -> str:
        """Karar değerlendirir.

        Args:
            confidence: Güven seviyesi.
            impact: Etki seviyesi.
            risk: Risk seviyesi.

        Returns:
            Karar tipi.
        """
        auto_threshold = self._thresholds["auto"]
        esc_threshold = self._thresholds[
            "escalation"
        ]

        # Yüksek güven + düşük risk = otomatik
        if (
            confidence >= auto_threshold
            and risk < 0.3
            and impact in ("low", "medium")
        ):
            return "auto_handle"

        # Düşük güven = eskalasyon
        if confidence < esc_threshold:
            return "escalate"

        # Yüksek risk = eskalasyon
        if risk > 0.7:
            return "escalate"

        # Yüksek etki = bildirim
        if impact in ("high", "critical"):
            return "notify"

        # Orta seviye = bildirim
        if confidence >= esc_threshold:
            return "notify"

        return "defer"

    def assess_impact(
        self,
        action: str,
        affected_systems: list[str]
        | None = None,
        reversible: bool = True,
        scope: str = "local",
    ) -> dict[str, Any]:
        """Etki değerlendirmesi yapar.

        Args:
            action: Aksiyon.
            affected_systems: Etkilenen sistemler.
            reversible: Geri alınabilir mi.
            scope: Kapsam.

        Returns:
            Değerlendirme bilgisi.
        """
        affected = affected_systems or []
        system_count = len(affected)

        # Etki hesaplama
        if system_count > 5:
            level = "critical"
        elif system_count > 2:
            level = "high"
        elif system_count > 0:
            level = "medium"
        else:
            level = "low"

        # Geri alınamazsa bir seviye artır
        if not reversible:
            levels = [
                "low", "medium",
                "high", "critical",
            ]
            idx = levels.index(level)
            if idx < len(levels) - 1:
                level = levels[idx + 1]

        # Kapsam etkisi
        if scope in ("global", "production"):
            levels = [
                "low", "medium",
                "high", "critical",
            ]
            idx = levels.index(level)
            if idx < len(levels) - 1:
                level = levels[idx + 1]

        return {
            "action": action,
            "impact_level": level,
            "affected_systems": affected,
            "reversible": reversible,
            "scope": scope,
        }

    def evaluate_risk(
        self,
        action: str,
        failure_probability: float = 0.1,
        failure_impact: str = "low",
        has_fallback: bool = True,
    ) -> dict[str, Any]:
        """Risk değerlendirmesi yapar.

        Args:
            action: Aksiyon.
            failure_probability: Başarısızlık olasılığı.
            failure_impact: Başarısızlık etkisi.
            has_fallback: Fallback var mı.

        Returns:
            Risk bilgisi.
        """
        impact_scores = {
            "low": 0.2,
            "medium": 0.5,
            "high": 0.8,
            "critical": 1.0,
        }
        impact_score = impact_scores.get(
            failure_impact, 0.5,
        )

        risk_score = (
            failure_probability * impact_score
        )
        if not has_fallback:
            risk_score = min(1.0, risk_score * 1.5)

        if risk_score > 0.7:
            risk_level = "high"
        elif risk_score > 0.4:
            risk_level = "medium"
        else:
            risk_level = "low"

        return {
            "action": action,
            "risk_score": round(risk_score, 3),
            "risk_level": risk_level,
            "failure_probability": (
                failure_probability
            ),
            "failure_impact": failure_impact,
            "has_fallback": has_fallback,
        }

    def add_approval_rule(
        self,
        pattern: str,
        requires_approval: bool = True,
        min_priority: int = 1,
    ) -> dict[str, Any]:
        """Onay kuralı ekler.

        Args:
            pattern: Aksiyon kalıbı.
            requires_approval: Onay gerekli mi.
            min_priority: Min öncelik.

        Returns:
            Kural bilgisi.
        """
        rule = {
            "pattern": pattern,
            "requires_approval": requires_approval,
            "min_priority": min_priority,
            "created_at": time.time(),
        }
        self._approval_rules.append(rule)

        return {
            "pattern": pattern,
            "added": True,
        }

    def _check_approval_needed(
        self,
        action: str,
        impact: str,
        risk: float,
    ) -> bool:
        """Onay gereksinimi kontrol eder.

        Args:
            action: Aksiyon.
            impact: Etki seviyesi.
            risk: Risk seviyesi.

        Returns:
            Onay gerekli mi.
        """
        # Yüksek etki veya risk
        if impact in ("high", "critical"):
            return True
        if risk > 0.7:
            return True

        # Kural bazlı kontrol
        for rule in self._approval_rules:
            if (
                rule["requires_approval"]
                and rule["pattern"] in action
            ):
                return True

        return False

    def route_approval(
        self,
        decision_id: str,
        approver: str = "user",
    ) -> dict[str, Any]:
        """Onay yönlendirir.

        Args:
            decision_id: Karar ID.
            approver: Onaylayıcı.

        Returns:
            Yönlendirme bilgisi.
        """
        decision = None
        for d in self._decisions:
            if d["decision_id"] == decision_id:
                decision = d
                break

        if not decision:
            return {
                "error": "decision_not_found",
            }

        decision["approval_routed_to"] = approver
        decision["approval_status"] = "pending"

        return {
            "decision_id": decision_id,
            "routed_to": approver,
            "status": "pending",
        }

    def get_decisions(
        self,
        decision_type: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Kararları getirir.

        Args:
            decision_type: Tip filtresi.
            limit: Maks kayıt.

        Returns:
            Karar listesi.
        """
        results = self._decisions
        if decision_type:
            results = [
                d for d in results
                if d.get("decision_type")
                == decision_type
            ]
        return list(results[-limit:])

    @property
    def decision_count(self) -> int:
        """Karar sayısı."""
        return self._stats["decisions_made"]

    @property
    def auto_handle_rate(self) -> float:
        """Otomatik işlem oranı."""
        total = self._stats["decisions_made"]
        if total == 0:
            return 0.0
        return round(
            self._stats["auto_handled"] / total,
            3,
        )
