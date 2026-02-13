"""ATLAS Davranis Tahmini modulu.

Kullanici davranisi, kayip tahmini, sonraki aksiyon
tahmini, katilim tahmini ve yasam boyu deger hesaplama.
"""

import logging
import math
from typing import Any

from app.models.predictive import (
    BehaviorPrediction,
    BehaviorType,
)

logger = logging.getLogger(__name__)


class BehaviorPredictor:
    """Davranis tahmin sistemi.

    Kullanici davranislarini tahmin eder: satin alma,
    kayip (churn), sonraki aksiyon, katilim ve
    yasam boyu deger.

    Attributes:
        _predictions: Tahmin gecmisi.
        _behavior_weights: Davranis agirlik katsayilari.
    """

    def __init__(self, behavior_weights: dict[str, float] | None = None) -> None:
        """Davranis tahmin sistemini baslatir.

        Args:
            behavior_weights: Davranis tipi agirlik katsayilari.
        """
        self._predictions: list[BehaviorPrediction] = []
        self._behavior_weights = behavior_weights or {
            "recency": 0.3,
            "frequency": 0.3,
            "monetary": 0.2,
            "engagement": 0.2,
        }

        logger.info("BehaviorPredictor baslatildi")

    def predict_purchase(self, user_history: list[dict[str, Any]]) -> BehaviorPrediction:
        """Satin alma davranisi tahmin eder.

        RFM (Recency, Frequency, Monetary) analizi ile.

        Args:
            user_history: Kullanici gecmisi (amount, days_ago, vb).

        Returns:
            BehaviorPrediction nesnesi.
        """
        if not user_history:
            return BehaviorPrediction(behavior_type=BehaviorType.PURCHASE, probability=0.1)

        # Recency: son islemin yakinligi
        days_ago_values = [h.get("days_ago", 30) for h in user_history]
        min_days_ago = min(days_ago_values)
        recency_score = max(0.0, 1.0 - min_days_ago / 90)  # 90 gun icinde azalir

        # Frequency: islem sikligi
        frequency = len(user_history)
        frequency_score = min(1.0, frequency / 10)  # 10+ islem tam skor

        # Monetary: ortalama tutar
        amounts = [h.get("amount", 0.0) for h in user_history]
        avg_amount = sum(amounts) / len(amounts) if amounts else 0.0
        monetary_score = min(1.0, avg_amount / 500)  # 500+ yuksek deger

        # Agirlikli skor
        w = self._behavior_weights
        probability = (
            recency_score * w.get("recency", 0.3)
            + frequency_score * w.get("frequency", 0.3)
            + monetary_score * w.get("monetary", 0.2)
        )
        probability = max(0.0, min(1.0, probability))

        # Tahmini sure
        avg_interval = sum(days_ago_values) / len(days_ago_values) if days_ago_values else 30.0
        expected_days = max(1.0, avg_interval * (1 - probability))

        prediction = BehaviorPrediction(
            behavior_type=BehaviorType.PURCHASE,
            probability=probability,
            expected_time_days=expected_days,
            lifetime_value=avg_amount * frequency * 2,  # Basit LTV tahmini
        )
        self._predictions.append(prediction)
        logger.info("Satin alma tahmini: olasilik=%.2f, sure=%.1f gun", probability, expected_days)
        return prediction

    def predict_churn(self, activity_data: list[dict[str, Any]]) -> BehaviorPrediction:
        """Kayip (churn) tahmini yapar.

        Args:
            activity_data: Aktivite verileri (last_active_days, sessions, vb).

        Returns:
            BehaviorPrediction nesnesi.
        """
        if not activity_data:
            return BehaviorPrediction(behavior_type=BehaviorType.CHURN, churn_risk=0.5)

        last = activity_data[-1]
        inactive_days = last.get("inactive_days", 0)
        session_count = last.get("sessions", 0)
        avg_duration = last.get("avg_duration_min", 0)

        # Inactivity skoru (uzun suredir aktif degilse yuksek risk)
        inactivity_risk = min(1.0, inactive_days / 30)

        # Session skoru (az session yuksek risk)
        session_risk = max(0.0, 1.0 - session_count / 20)

        # Duration skoru (kisa sureler yuksek risk)
        duration_risk = max(0.0, 1.0 - avg_duration / 30)

        # Trend: son doneme bakilarak
        if len(activity_data) >= 2:
            prev_sessions = activity_data[-2].get("sessions", 0)
            if prev_sessions > 0 and session_count < prev_sessions * 0.5:
                trend_penalty = 0.2
            else:
                trend_penalty = 0.0
        else:
            trend_penalty = 0.0

        churn_risk = (inactivity_risk * 0.4 + session_risk * 0.3 + duration_risk * 0.3) + trend_penalty
        churn_risk = max(0.0, min(1.0, churn_risk))

        engagement = max(0.0, 1.0 - churn_risk)

        prediction = BehaviorPrediction(
            behavior_type=BehaviorType.CHURN,
            probability=churn_risk,
            churn_risk=churn_risk,
            engagement_score=engagement,
            next_actions=self._suggest_retention_actions(churn_risk),
        )
        self._predictions.append(prediction)
        logger.info("Kayip tahmini: risk=%.2f, katilim=%.2f", churn_risk, engagement)
        return prediction

    def predict_next_action(self, action_sequence: list[str]) -> BehaviorPrediction:
        """Sonraki aksiyonu tahmin eder.

        Markov-benzeri gecis olasiliklari ile.

        Args:
            action_sequence: Eylem sirasi listesi.

        Returns:
            BehaviorPrediction nesnesi.
        """
        if not action_sequence:
            return BehaviorPrediction(behavior_type=BehaviorType.ENGAGEMENT, next_actions=["unknown"])

        # Gecis matrisini olustur
        transitions: dict[str, dict[str, int]] = {}
        for i in range(len(action_sequence) - 1):
            current = action_sequence[i]
            next_act = action_sequence[i + 1]
            if current not in transitions:
                transitions[current] = {}
            transitions[current][next_act] = transitions[current].get(next_act, 0) + 1

        # Son eylemden sonraki en olasi eylemler
        last_action = action_sequence[-1]
        next_probs = transitions.get(last_action, {})

        if not next_probs:
            # Genel frekans kullan
            freq: dict[str, int] = {}
            for a in action_sequence:
                freq[a] = freq.get(a, 0) + 1
            sorted_actions = sorted(freq.items(), key=lambda x: x[1], reverse=True)
            predicted_actions = [a for a, _ in sorted_actions[:3]]
            probability = 0.3
        else:
            total = sum(next_probs.values())
            sorted_next = sorted(next_probs.items(), key=lambda x: x[1], reverse=True)
            predicted_actions = [a for a, _ in sorted_next[:3]]
            probability = sorted_next[0][1] / total if total > 0 else 0.0

        prediction = BehaviorPrediction(
            behavior_type=BehaviorType.ENGAGEMENT,
            probability=probability,
            next_actions=predicted_actions,
        )
        self._predictions.append(prediction)
        return prediction

    def forecast_engagement(self, engagement_history: list[float]) -> BehaviorPrediction:
        """Katilim tahmini yapar.

        Args:
            engagement_history: Katilim skorlari listesi (0-1).

        Returns:
            BehaviorPrediction nesnesi.
        """
        if not engagement_history:
            return BehaviorPrediction(behavior_type=BehaviorType.ENGAGEMENT, engagement_score=0.5)

        # Ustel agirlikli ortalama (son degerlere daha cok agirlik)
        alpha = 0.3
        smoothed = engagement_history[0]
        for val in engagement_history[1:]:
            smoothed = alpha * val + (1 - alpha) * smoothed

        # Trend
        if len(engagement_history) >= 3:
            recent = engagement_history[-3:]
            trend = (recent[-1] - recent[0]) / 2
        else:
            trend = 0.0

        predicted_engagement = max(0.0, min(1.0, smoothed + trend))

        prediction = BehaviorPrediction(
            behavior_type=BehaviorType.ENGAGEMENT,
            engagement_score=predicted_engagement,
            probability=predicted_engagement,
            churn_risk=max(0.0, 1.0 - predicted_engagement),
        )
        self._predictions.append(prediction)
        return prediction

    def estimate_lifetime_value(
        self,
        avg_purchase: float,
        purchase_frequency: float,
        avg_lifespan_months: float = 24.0,
    ) -> BehaviorPrediction:
        """Yasam boyu deger tahmini yapar.

        LTV = Ortalama Satin Alma * Siklik * Yasam Suresi

        Args:
            avg_purchase: Ortalama satin alma tutari.
            purchase_frequency: Aylik satin alma sikligi.
            avg_lifespan_months: Ortalama musteri omru (ay).

        Returns:
            BehaviorPrediction nesnesi.
        """
        ltv = avg_purchase * purchase_frequency * avg_lifespan_months

        # Segment
        if ltv > 10000:
            segment_actions = ["VIP programi", "Kisisel hizmet", "Ozel indirimler"]
        elif ltv > 5000:
            segment_actions = ["Sadakat programi", "Crosell firsatlari"]
        elif ltv > 1000:
            segment_actions = ["Retention kampanyasi", "Upsell onerileri"]
        else:
            segment_actions = ["Aktivasyon kampanyasi", "Deger artirma"]

        prediction = BehaviorPrediction(
            behavior_type=BehaviorType.PURCHASE,
            lifetime_value=ltv,
            probability=min(1.0, purchase_frequency / 4),  # Ayda 4+ alisveris = yuksek
            next_actions=segment_actions,
        )
        self._predictions.append(prediction)
        logger.info("LTV tahmini: %.2f (siklik=%.1f/ay, omur=%.0f ay)", ltv, purchase_frequency, avg_lifespan_months)
        return prediction

    def _suggest_retention_actions(self, churn_risk: float) -> list[str]:
        """Kayip riskine gore retention onerileri.

        Args:
            churn_risk: Kayip riski (0-1).

        Returns:
            Oneri listesi.
        """
        if churn_risk >= 0.8:
            return ["Acil kisisel iletisim", "Ozel teklif sun", "Geri bildirim al"]
        elif churn_risk >= 0.6:
            return ["Reaktivasyon emaili gonder", "Indirim kuponu sun"]
        elif churn_risk >= 0.4:
            return ["Hatirlatma bildirimi gonder", "Yeni ozellik duyurusu"]
        else:
            return ["Standart katilim surecine devam"]

    @property
    def predictions(self) -> list[BehaviorPrediction]:
        """Tahmin gecmisi."""
        return list(self._predictions)

    @property
    def prediction_count(self) -> int:
        """Toplam tahmin sayisi."""
        return len(self._predictions)
