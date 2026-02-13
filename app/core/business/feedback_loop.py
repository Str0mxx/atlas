"""ATLAS Geri Bildirim Dongusu modulu.

Sonuc toplama, ogrenme cikarma, strateji duzeltme,
surekli iyilestirme ve bilgi tabani guncelleme islemleri.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from app.models.business import (
    FeedbackEntry,
    Insight,
    InsightType,
    StrategyAdjustment,
)

logger = logging.getLogger(__name__)

# Sonuc-ic goru tipi eslestirmesi
_OUTCOME_TO_INSIGHT_TYPE: dict[str, InsightType] = {
    "success": InsightType.SUCCESS_PATTERN,
    "failure": InsightType.FAILURE_LESSON,
    "partial": InsightType.PROCESS_IMPROVEMENT,
}


class FeedbackLoop:
    """Geri bildirim dongusu sistemi.

    Strateji sonuclarini toplar, ogrenme cikarir,
    stratejileri duzeltir, surekli iyilestirme saglar
    ve bilgi tabanini gunceller.

    Attributes:
        _feedback: Geri bildirim kayitlari (id -> FeedbackEntry).
        _insights: Cikarilmis ic goruler (id -> Insight).
        _adjustments: Strateji duzeltmeleri (id -> StrategyAdjustment).
        _knowledge_base: Bilgi tabani (konu -> icerik).
    """

    def __init__(self) -> None:
        """Geri bildirim dongusu sistemini baslatir."""
        self._feedback: dict[str, FeedbackEntry] = {}
        self._insights: dict[str, Insight] = {}
        self._adjustments: dict[str, StrategyAdjustment] = {}
        self._knowledge_base: dict[str, list[str]] = {}

        logger.info("FeedbackLoop baslatildi")

    def collect_result(
        self,
        strategy_id: str,
        outcome: str,
        source: str = "",
        lessons: list[str] | None = None,
        metrics: dict[str, float] | None = None,
    ) -> FeedbackEntry:
        """Strateji sonucunu toplar.

        Args:
            strategy_id: Iliskili strateji ID.
            outcome: Sonuc ('success', 'failure', 'partial').
            source: Geri bildirim kaynagi.
            lessons: Cikarilan dersler.
            metrics: Metrik sonuclari.

        Returns:
            Olusturulan FeedbackEntry nesnesi.
        """
        entry = FeedbackEntry(
            strategy_id=strategy_id,
            source=source,
            outcome=outcome,
            lessons=lessons or [],
            metrics=metrics or {},
        )
        self._feedback[entry.id] = entry
        logger.info("Geri bildirim toplandi: strateji=%s, sonuc=%s", strategy_id[:8], outcome)
        return entry

    def extract_learning(self, feedback_id: str) -> Insight | None:
        """Geri bildirimden ogrenme cikarir.

        Sonuc tipine gore uygun ic goru tipi secilir
        ve derslerden ic goru olusturulur.

        Args:
            feedback_id: Geri bildirim ID.

        Returns:
            Cikarilmis Insight nesnesi veya None.
        """
        entry = self._feedback.get(feedback_id)
        if not entry:
            return None

        if not entry.lessons:
            return None

        insight_type = _OUTCOME_TO_INSIGHT_TYPE.get(entry.outcome, InsightType.PROCESS_IMPROVEMENT)

        # Guven derecesini sonuca gore hesapla
        if entry.outcome == "success":
            confidence = 0.8
        elif entry.outcome == "failure":
            confidence = 0.7
        else:
            confidence = 0.5

        insight = Insight(
            insight_type=insight_type,
            title=f"{entry.outcome.capitalize()} ogrenmesi: {entry.lessons[0][:50]}",
            description="; ".join(entry.lessons),
            confidence=confidence,
            source_feedback_ids=[feedback_id],
        )
        self._insights[insight.id] = insight
        logger.info("Ogrenme cikarildi: %s (tip=%s, guven=%.2f)", insight.title[:30], insight_type.value, confidence)
        return insight

    def adjust_strategy(
        self,
        strategy_id: str,
        insight_id: str = "",
        adjustment_type: str = "",
        description: str = "",
    ) -> StrategyAdjustment:
        """Strateji duzeltmesi kaydeder.

        Args:
            strategy_id: Duzeltilecek strateji ID.
            insight_id: Tetikleyen ic goru ID.
            adjustment_type: Duzeltme tipi.
            description: Duzeltme aciklamasi.

        Returns:
            Olusturulan StrategyAdjustment nesnesi.
        """
        adjustment = StrategyAdjustment(
            strategy_id=strategy_id,
            insight_id=insight_id,
            adjustment_type=adjustment_type,
            description=description,
        )
        self._adjustments[adjustment.id] = adjustment
        logger.info("Strateji duzeltildi: strateji=%s, tip=%s", strategy_id[:8], adjustment_type)
        return adjustment

    def continuous_improvement(self, min_confidence: float = 0.6) -> list[Insight]:
        """Surekli iyilestirme onerileri cikarir.

        Yuksek guvenli ve eyleme gecirilebilir ic goruleri
        dondurur.

        Args:
            min_confidence: Minimum guven esigi.

        Returns:
            Eyleme gecirilebilir ic goruler.
        """
        actionable = [
            insight for insight in self._insights.values()
            if insight.actionable and insight.confidence >= min_confidence
        ]
        actionable.sort(key=lambda i: i.confidence, reverse=True)
        logger.info("Surekli iyilestirme: %d eyleme gecirilebilir ic goru", len(actionable))
        return actionable

    def update_knowledge_base(self, topic: str, content: str) -> None:
        """Bilgi tabanini gunceller.

        Args:
            topic: Konu.
            content: Icerik.
        """
        if topic not in self._knowledge_base:
            self._knowledge_base[topic] = []
        self._knowledge_base[topic].append(content)
        logger.info("Bilgi tabani guncellendi: %s (%d kayit)", topic, len(self._knowledge_base[topic]))

    def query_knowledge(self, topic: str) -> list[str]:
        """Bilgi tabanindan sorgular.

        Args:
            topic: Konu.

        Returns:
            Iliskili bilgi listesi.
        """
        return self._knowledge_base.get(topic, [])

    def get_strategy_feedback(self, strategy_id: str) -> list[FeedbackEntry]:
        """Strateji geri bildirimlerini getirir.

        Args:
            strategy_id: Strateji ID.

        Returns:
            Iliskili geri bildirimler.
        """
        return [f for f in self._feedback.values() if f.strategy_id == strategy_id]

    def get_insights_by_type(self, insight_type: InsightType) -> list[Insight]:
        """Tipe gore ic goruleri getirir.

        Args:
            insight_type: Ic goru tipi.

        Returns:
            Eslesen ic goruler.
        """
        return [i for i in self._insights.values() if i.insight_type == insight_type]

    def mark_insight_applied(self, insight_id: str) -> bool:
        """Ic goruyu uygulanmis olarak isaretler.

        Args:
            insight_id: Ic goru ID.

        Returns:
            Basarili mi.
        """
        insight = self._insights.get(insight_id)
        if not insight:
            return False

        insight.applied_count += 1
        logger.info("Ic goru uygulandi: %s (toplam=%d)", insight.title[:30], insight.applied_count)
        return True

    @property
    def feedback_count(self) -> int:
        """Toplam geri bildirim sayisi."""
        return len(self._feedback)

    @property
    def insight_count(self) -> int:
        """Toplam ic goru sayisi."""
        return len(self._insights)

    @property
    def knowledge_topics(self) -> list[str]:
        """Bilgi tabani konulari."""
        return list(self._knowledge_base.keys())
