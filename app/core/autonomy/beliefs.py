"""ATLAS Belief sistemi modulu.

Sistemin dunya hakkindaki inanclarini yonetir.
Sensor verilerinden belief guncelleme, celiskili bilgi revizyonu
ve zaman bazli guven azalmasi saglar.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from app.models.autonomy import (
    Belief,
    BeliefCategory,
    BeliefSource,
    BeliefUpdate,
)

logger = logging.getLogger("atlas.autonomy.beliefs")

# Monitor adi -> BeliefCategory eslesmesi
_MONITOR_CATEGORY_MAP: dict[str, BeliefCategory] = {
    "server": BeliefCategory.SERVER,
    "security": BeliefCategory.SECURITY,
    "ads": BeliefCategory.MARKETING,
    "opportunity": BeliefCategory.OPPORTUNITY,
}

# Risk seviyesi -> guven skoru eslesmesi
_RISK_CONFIDENCE_MAP: dict[str, float] = {
    "high": 0.95,
    "medium": 0.75,
    "low": 0.5,
}

# Minimum guven esigi (altinda belief silinir)
_DECAY_THRESHOLD = 0.1


class BeliefBase:
    """Sistemin dunya hakkindaki inanclarini yoneten sinif.

    Belief'ler anahtar-deger cifti olarak saklanir.
    Her belief bir guven skoru tasir ve zaman icinde azalir.

    Attributes:
        beliefs: Aktif belief'ler (key -> Belief).
        revision_history: Revizyon gecmisi.
    """

    def __init__(self) -> None:
        """BeliefBase'i baslatir."""
        self.beliefs: dict[str, Belief] = {}
        self.revision_history: list[dict[str, Any]] = []
        logger.info("BeliefBase olusturuldu")

    async def update(self, belief_update: BeliefUpdate) -> Belief:
        """Belief'i gunceller veya yeni belief ekler.

        Mevcut belief varsa revizyon mantigi uygulanir.
        Yoksa yeni belief olusturulur.

        Args:
            belief_update: Guncelleme verisi.

        Returns:
            Guncel belief.
        """
        existing = self.beliefs.get(belief_update.key)
        if existing is not None:
            revised = await self.revise(
                belief_update.key,
                belief_update.value,
                belief_update.confidence,
            )
            if revised is not None:
                revised.source = belief_update.source
                return revised
            # Revizyon gerekmedi, mevcut belief'i dondur
            return existing

        # Yeni belief olustur
        belief = Belief(
            key=belief_update.key,
            value=belief_update.value,
            confidence=belief_update.confidence,
            source=belief_update.source,
        )
        self.beliefs[belief.key] = belief
        logger.info("Yeni belief eklendi: %s", belief.key)
        return belief

    async def update_from_monitor(
        self,
        monitor_name: str,
        risk: str,
        urgency: str,
        details: list[dict[str, Any]],
    ) -> list[Belief]:
        """Monitor sonucundan belief'leri gunceller.

        MonitorResult verilerini belief'lere cevirir.

        Args:
            monitor_name: Monitor adi.
            risk: Risk seviyesi.
            urgency: Aciliyet seviyesi.
            details: Detayli bulgular.

        Returns:
            Guncellenen belief listesi.
        """
        category = _MONITOR_CATEGORY_MAP.get(
            monitor_name, BeliefCategory.SYSTEM,
        )
        confidence = _RISK_CONFIDENCE_MAP.get(risk, 0.5)
        updated_beliefs: list[Belief] = []

        # Risk/urgency belief'lerini guncelle
        risk_update = BeliefUpdate(
            key=f"{category.value}:risk",
            value=risk,
            confidence=confidence,
            source=BeliefSource.MONITOR,
        )
        updated_beliefs.append(await self.update(risk_update))

        urgency_update = BeliefUpdate(
            key=f"{category.value}:urgency",
            value=urgency,
            confidence=confidence,
            source=BeliefSource.MONITOR,
        )
        updated_beliefs.append(await self.update(urgency_update))

        # Detaylardan belief olustur
        for detail in details:
            for field, value in detail.items():
                detail_update = BeliefUpdate(
                    key=f"{category.value}:{field}",
                    value=value,
                    confidence=confidence,
                    source=BeliefSource.MONITOR,
                )
                updated_beliefs.append(await self.update(detail_update))

        logger.info(
            "Monitor'dan %d belief guncellendi: %s",
            len(updated_beliefs), monitor_name,
        )
        return updated_beliefs

    async def revise(
        self,
        key: str,
        new_value: Any,
        new_confidence: float,
    ) -> Belief | None:
        """Celiskili bilgi geldigi zaman belief'i revize eder.

        Eger mevcut belief ile celisiyorsa, guven skorlarina gore
        hangisinin kabul edilecegi belirlenir.

        Args:
            key: Belief anahtari.
            new_value: Yeni deger.
            new_confidence: Yeni guven skoru.

        Returns:
            Revize edilmis belief veya None (degisiklik yoksa).
        """
        existing = self.beliefs.get(key)
        if existing is None:
            return None

        # Ayni deger ise sadece confidence guncelle
        if existing.value == new_value:
            if new_confidence != existing.confidence:
                existing.confidence = new_confidence
                existing.timestamp = datetime.now(timezone.utc)
                return existing
            return None

        # Celiskili deger — revizyon gerekli
        self.revision_history.append({
            "key": key,
            "old_value": existing.value,
            "old_confidence": existing.confidence,
            "new_value": new_value,
            "new_confidence": new_confidence,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        if new_confidence >= existing.confidence:
            # Yeni bilgi daha guvenilir
            existing.value = new_value
            existing.confidence = new_confidence
            existing.timestamp = datetime.now(timezone.utc)
            logger.info(
                "Belief revize edildi: %s (conf: %.2f -> %.2f)",
                key, existing.confidence, new_confidence,
            )
            return existing

        # Mevcut bilgi daha guvenilir, degisiklik yok
        logger.debug(
            "Belief revizyonu reddedildi: %s (mevcut=%.2f > yeni=%.2f)",
            key, existing.confidence, new_confidence,
        )
        return None

    async def decay(self) -> list[str]:
        """Tum belief'lerin guven skorunu zamanla azaltir.

        Her belief'in decay_rate ve gecen sureye gore
        guven skoru dusurulur. Esik altina dusenler silinir.

        Returns:
            Silinen belief anahtarlari listesi.
        """
        now = datetime.now(timezone.utc)
        removed: list[str] = []

        for key in list(self.beliefs.keys()):
            belief = self.beliefs[key]
            if belief.decay_rate <= 0:
                continue

            hours_elapsed = (now - belief.timestamp).total_seconds() / 3600
            if hours_elapsed <= 0:
                continue

            new_confidence = belief.confidence - (
                belief.decay_rate * hours_elapsed
            )
            new_confidence = max(0.0, new_confidence)

            if new_confidence < _DECAY_THRESHOLD:
                del self.beliefs[key]
                removed.append(key)
                logger.debug("Belief decay ile silindi: %s", key)
            else:
                belief.confidence = new_confidence

        if removed:
            logger.info("%d belief decay ile silindi", len(removed))
        return removed

    def get(self, key: str) -> Belief | None:
        """Tek bir belief'i getirir.

        Args:
            key: Belief anahtari.

        Returns:
            Belief veya None.
        """
        return self.beliefs.get(key)

    def get_by_category(self, category: BeliefCategory) -> list[Belief]:
        """Kategoriye gore belief'leri getirir.

        Args:
            category: Belief kategorisi.

        Returns:
            Eslesen belief listesi.
        """
        return [
            b for b in self.beliefs.values()
            if b.category == category
        ]

    def get_confident(self, min_confidence: float = 0.5) -> list[Belief]:
        """Belirli guven seviyesinin ustundeki belief'leri getirir.

        Args:
            min_confidence: Minimum guven skoru.

        Returns:
            Eslesen belief listesi.
        """
        return [
            b for b in self.beliefs.values()
            if b.confidence >= min_confidence
        ]

    def get_all(self) -> list[Belief]:
        """Tum belief'leri liste olarak dondurur.

        Returns:
            Tum aktif belief'ler.
        """
        return list(self.beliefs.values())

    def remove(self, key: str) -> bool:
        """Belief'i siler.

        Args:
            key: Silinecek belief anahtari.

        Returns:
            Silme basarili mi.
        """
        if key in self.beliefs:
            del self.beliefs[key]
            return True
        return False

    def clear(self) -> None:
        """Tum belief'leri temizler."""
        self.beliefs.clear()

    def snapshot(self) -> dict[str, Any]:
        """Mevcut belief durumunun anlik goruntusunu dondurur.

        Returns:
            Belief durumu sozlugu.
        """
        return {
            "count": len(self.beliefs),
            "beliefs": {
                key: {
                    "value": b.value,
                    "confidence": b.confidence,
                    "category": b.category.value,
                    "source": b.source.value,
                }
                for key, b in self.beliefs.items()
            },
            "revision_count": len(self.revision_history),
        }
