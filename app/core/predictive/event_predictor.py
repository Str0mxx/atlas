"""ATLAS Olay Tahmini modulu.

Olay olasiligi, zamanlama tahmini, zincirleme etkiler,
tetikleyici kosullar ve onleme tavsiyeleri.
"""

import logging
import math
from typing import Any

from app.models.predictive import (
    DataPoint,
    EventCategory,
    EventPrediction,
)

logger = logging.getLogger(__name__)

# Olay tetikleyici kosullar
_TRIGGER_CONDITIONS: dict[EventCategory, list[str]] = {
    EventCategory.SYSTEM_FAILURE: [
        "CPU kullanimi %90 uzerinde",
        "Bellek doluluk orani kritik",
        "Disk alani %95 uzerinde",
        "Servis yanit suresi 5x artti",
    ],
    EventCategory.SECURITY_BREACH: [
        "Basarisiz giris denemesi artisi",
        "Anormal port taramasi",
        "Bilinmeyen IP erisim calismasi",
        "Yetki yukseltme girisimi",
    ],
    EventCategory.MARKET_SHIFT: [
        "Rakip fiyat degisikligi",
        "Tedarik zinciri aksamasi",
        "Regulasyon degisikligi",
        "Tuketici tercihi degisimi",
    ],
    EventCategory.OPPORTUNITY: [
        "Rakip pazar terk etti",
        "Yeni pazar segmenti ortaya cikti",
        "Teknoloji maliyeti dustu",
        "Mevzuat avantaji olustu",
    ],
    EventCategory.THREAT: [
        "Rakip agresif buyume",
        "Pazar daralmasi sinyali",
        "Tedarikci sorunlari",
        "Regulasyon sikila",
    ],
}

# Zincirleme etki sablonlari
_CASCADE_EFFECTS: dict[EventCategory, list[str]] = {
    EventCategory.SYSTEM_FAILURE: [
        "Hizmet kesintisi",
        "Veri kaybi riski",
        "Musteri memnuniyetsizligi",
        "Gelir kaybi",
    ],
    EventCategory.SECURITY_BREACH: [
        "Veri sizintisi",
        "Itibar kaybi",
        "Hukuki sorumluluk",
        "Musteri kaybi",
    ],
    EventCategory.MARKET_SHIFT: [
        "Pazar payi degisimi",
        "Fiyat baskisi",
        "Strateji revizyonu gerekliligi",
    ],
    EventCategory.OPPORTUNITY: [
        "Gelir artisi",
        "Pazar payi genislemesi",
        "Rekabet avantaji",
    ],
    EventCategory.THREAT: [
        "Pazar payi kaybi",
        "Kar marji daralmasi",
        "Kaynak sikintisi",
    ],
}

# Onleme onerileri
_PREVENTION_ACTIONS: dict[EventCategory, list[str]] = {
    EventCategory.SYSTEM_FAILURE: [
        "Otomatik olceklendirme yapilandir",
        "Izleme alarmlarini guncelle",
        "Yedekleme stratejisini dogrula",
    ],
    EventCategory.SECURITY_BREACH: [
        "Guvenlik yamasini uygula",
        "IDS/IPS kurallarini guncelle",
        "Calisanlara guvenlik egitimi",
    ],
    EventCategory.MARKET_SHIFT: [
        "Pazar izleme frekansini artir",
        "Esnek fiyatlama stratejisi",
        "Cesitlendirilmis portfoy",
    ],
    EventCategory.OPPORTUNITY: [
        "Hizli aksiyon plani hazirla",
        "Kaynak tahsisi yap",
        "Pilot proje baslat",
    ],
    EventCategory.THREAT: [
        "Savunma stratejisi olustur",
        "Maliyet optimizasyonu yap",
        "Alternatif gelir kaynaklari gelistir",
    ],
}


class EventPredictor:
    """Olay tahmin sistemi.

    Gelecekteki olaylarin olasiliklarini, zamanlamalarini
    ve etkilerini tahmin eder. Tetikleyici kosullari izler
    ve onleme onerileri sunar.

    Attributes:
        _predictions: Olay tahmin gecmisi.
        _active_triggers: Aktif tetikleyiciler.
    """

    def __init__(self) -> None:
        """Olay tahmin sistemini baslatir."""
        self._predictions: list[EventPrediction] = []
        self._active_triggers: dict[str, list[str]] = {}

        logger.info("EventPredictor baslatildi")

    def predict_likelihood(
        self,
        category: EventCategory,
        indicators: dict[str, float],
    ) -> EventPrediction:
        """Olay olasligini tahmin eder.

        Args:
            category: Olay kategorisi.
            indicators: Gosterge adi -> deger (0-1) eslesmesi.

        Returns:
            EventPrediction nesnesi.
        """
        if not indicators:
            return EventPrediction(event_category=category, likelihood=0.1)

        # Agirlikli ortalama
        values = list(indicators.values())
        likelihood = sum(max(0.0, min(1.0, v)) for v in values) / len(values)

        # Yuksek gosterge sayisi guveni arttirir
        confidence_bonus = min(0.2, len(indicators) * 0.05)
        likelihood = min(1.0, likelihood + confidence_bonus)

        # Etki skoru
        impact = likelihood * 0.8  # Olasilik ile orantili

        # Tetikleyici kosullar
        triggers = _TRIGGER_CONDITIONS.get(category, [])
        active_triggers = [t for i, t in enumerate(triggers) if i < len(values) and values[i] > 0.5]

        # Zincirleme etkiler
        cascades = _CASCADE_EFFECTS.get(category, [])

        # Onleme aksiyonlari
        preventions = _PREVENTION_ACTIONS.get(category, [])

        prediction = EventPrediction(
            event_category=category,
            description=f"{category.value} olay tahmini",
            likelihood=likelihood,
            trigger_conditions=active_triggers,
            cascade_effects=cascades if likelihood > 0.5 else cascades[:1],
            prevention_actions=preventions if likelihood > 0.3 else preventions[:1],
            impact_score=impact,
        )
        self._predictions.append(prediction)

        logger.info("Olay tahmini: %s, olasilik=%.2f, etki=%.2f", category.value, likelihood, impact)
        return prediction

    def predict_timing(
        self,
        data: list[DataPoint],
        threshold: float,
    ) -> float:
        """Olayin ne zaman gerceklesecegini tahmin eder.

        Mevcut trende gore esik asim suresini hesaplar.

        Args:
            data: Metrik veri noktalari.
            threshold: Olay esigi.

        Returns:
            Tahmini saat cinsinden sure. 0 ise tahmin yapilamadi.
        """
        values = [d.value for d in data]
        if len(values) < 2:
            return 0.0

        # Lineer trend
        n = len(values)
        x_mean = (n - 1) / 2
        y_mean = sum(values) / n
        numerator = sum((i - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((i - x_mean) ** 2 for i in range(n))
        slope = numerator / denominator if denominator != 0 else 0.0

        if slope == 0:
            return 0.0

        last_value = values[-1]
        gap = threshold - last_value

        # Esige ne zaman ulasilacak
        if slope > 0 and gap > 0:
            steps = gap / slope
        elif slope < 0 and gap < 0:
            steps = gap / slope
        else:
            return 0.0  # Esige yaklasmiyor

        return max(0.0, steps)

    def analyze_cascade_effects(self, category: EventCategory, severity: float = 0.5) -> list[str]:
        """Zincirleme etkileri analiz eder.

        Args:
            category: Olay kategorisi.
            severity: Olayin siddeti (0-1).

        Returns:
            Zincirleme etki listesi.
        """
        effects = _CASCADE_EFFECTS.get(category, [])

        if severity >= 0.8:
            return effects  # Tum etkiler
        elif severity >= 0.5:
            return effects[:3]
        elif severity >= 0.3:
            return effects[:2]
        else:
            return effects[:1]

    def check_trigger_conditions(
        self,
        category: EventCategory,
        current_values: dict[str, float],
        thresholds: dict[str, float] | None = None,
    ) -> list[str]:
        """Tetikleyici kosullari kontrol eder.

        Args:
            category: Olay kategorisi.
            current_values: Mevcut metrik degerleri.
            thresholds: Esik degerleri.

        Returns:
            Aktif tetikleyici kosullar listesi.
        """
        if thresholds is None:
            thresholds = {k: 0.8 for k in current_values}

        triggered: list[str] = []
        for name, value in current_values.items():
            threshold = thresholds.get(name, 0.8)
            if value >= threshold:
                triggered.append(f"{name}: {value:.2f} >= {threshold:.2f}")

        if triggered:
            self._active_triggers[category.value] = triggered
            logger.info("Tetikleyici aktif: %s, %d kosul", category.value, len(triggered))

        return triggered

    def get_prevention_recommendations(self, category: EventCategory, likelihood: float) -> list[str]:
        """Onleme tavsiyeleri verir.

        Args:
            category: Olay kategorisi.
            likelihood: Olay olasiligi.

        Returns:
            Tavsiye listesi.
        """
        actions = _PREVENTION_ACTIONS.get(category, ["Durumu izleyin"])

        if likelihood >= 0.7:
            return actions + ["Acil durum plani aktifle"]
        elif likelihood >= 0.4:
            return actions
        else:
            return actions[:1]

    @property
    def predictions(self) -> list[EventPrediction]:
        """Olay tahmin gecmisi."""
        return list(self._predictions)

    @property
    def prediction_count(self) -> int:
        """Toplam tahmin sayisi."""
        return len(self._predictions)

    @property
    def active_triggers(self) -> dict[str, list[str]]:
        """Aktif tetikleyiciler."""
        return dict(self._active_triggers)
