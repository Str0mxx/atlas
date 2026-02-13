"""ATLAS Ebbinghaus Unutma Egrisi Sistemi.

Hafiza izlerinin zaman icindeki guc kaybini modelleyen,
tekrar zamanlama ve otomatik budama islemleri saglayan sistem.
Ebbinghaus unutma egrisi formulune dayanir: R = e^(-t/S).
"""

import logging
import math
from datetime import datetime, timedelta, timezone

from app.models.memory_palace import (
    MemoryTrace,
    MemoryType,
    ReviewSchedule,
)

logger = logging.getLogger(__name__)


class ForgettingCurve:
    """Ebbinghaus unutma egrisi sistemi.

    Hafiza izlerinin zaman icinde guc kaybini modelleyerek
    optimal tekrar zamanlamasi saglar. Unutma formulune gore
    R = e^(-t/S) hesabi yapilir.

    Attributes:
        _traces: Hafiza ID bazli hafiza izleri.
        _base_rate: Temel unutma orani (threshold).
    """

    def __init__(self, base_forgetting_rate: float = 0.1) -> None:
        """Unutma egrisi sistemini baslatir.

        Args:
            base_forgetting_rate: Temel unutma orani (tekrar esigi olarak kullanilir).
        """
        self._traces: dict[str, MemoryTrace] = {}
        self._base_rate = base_forgetting_rate
        logger.info(
            "Unutma egrisi baslatildi, temel oran=%.3f", base_forgetting_rate
        )

    def register_memory(
        self,
        memory_id: str,
        memory_type: MemoryType = MemoryType.EPISODIC,
        initial_strength: float = 1.0,
        importance: float = 0.5,
    ) -> MemoryTrace:
        """Yeni hafiza izi olusturur ve kaydeder.

        Stabilite hesabi: stability = (1 + importance) / base_rate.

        Args:
            memory_id: Hafiza ID.
            memory_type: Hafiza tipi.
            initial_strength: Baslangic gucu (0.0-1.0).
            importance: Onem derecesi (0.0-1.0).

        Returns:
            Olusturulan hafiza izi.
        """
        initial_strength = max(0.0, min(1.0, initial_strength))
        importance = max(0.0, min(1.0, importance))

        stability = (1.0 + importance) / self._base_rate
        now = datetime.now(timezone.utc)

        trace = MemoryTrace(
            memory_id=memory_id,
            memory_type=memory_type,
            strength=initial_strength,
            stability=stability,
            last_review=now,
            next_review=None,
            review_count=0,
        )
        self._traces[memory_id] = trace

        # Ilk tekrar zamanlamasini planla
        self.schedule_review(memory_id)

        logger.info(
            "Hafiza izi olusturuldu: %s (tip=%s, guc=%.2f, stabilite=%.2f)",
            memory_id,
            memory_type.value,
            initial_strength,
            stability,
        )
        return trace

    def calculate_retention(
        self, memory_id: str, at_time: datetime | None = None,
    ) -> float:
        """Ebbinghaus unutma egrisi ile tutma oranini hesaplar.

        Formul: R = e^(-t/S), burada t = son tekrardan gecen sure (saniye),
        S = stabilite parametresi.

        Args:
            memory_id: Hafiza ID.
            at_time: Hesaplama zamani (None ise simdiki zaman).

        Returns:
            Tutma orani (0.0-1.0). Bulunamazsa 0.0.
        """
        trace = self._traces.get(memory_id)
        if trace is None:
            return 0.0

        if at_time is None:
            at_time = datetime.now(timezone.utc)

        elapsed = (at_time - trace.last_review).total_seconds()
        if elapsed < 0:
            elapsed = 0.0

        if trace.stability <= 0:
            return 0.0

        retention = math.exp(-elapsed / trace.stability)
        return max(0.0, min(1.0, retention))

    def review(self, memory_id: str) -> MemoryTrace | None:
        """Hafiza izini gozden gecirir ve guclendirir.

        Gozden gecirme islemi: strength=1.0, stability *= 1.5,
        review_count += 1, last_review = simdiki zaman,
        ve sonraki tekrari planlar.

        Args:
            memory_id: Gozden gecirilecek hafiza ID.

        Returns:
            Guncellenmis hafiza izi veya None (bulunamazsa).
        """
        trace = self._traces.get(memory_id)
        if trace is None:
            logger.warning("Gozden gecirme basarisiz: %s bulunamadi", memory_id)
            return None

        now = datetime.now(timezone.utc)
        new_stability = trace.stability * 1.5
        new_review_count = trace.review_count + 1

        # Pydantic model'i yeniden olustur
        updated_trace = MemoryTrace(
            id=trace.id,
            memory_id=trace.memory_id,
            memory_type=trace.memory_type,
            strength=1.0,
            stability=new_stability,
            last_review=now,
            next_review=trace.next_review,
            review_count=new_review_count,
            created_at=trace.created_at,
        )
        self._traces[memory_id] = updated_trace

        # Sonraki tekrari planla
        self.schedule_review(memory_id)

        logger.debug(
            "Hafiza gozden gecirildi: %s (tekrar=%d, stabilite=%.2f)",
            memory_id,
            new_review_count,
            new_stability,
        )
        return self._traces[memory_id]

    def get_due_reviews(
        self, before: datetime | None = None,
    ) -> list[MemoryTrace]:
        """Tekrar zamani gelmis hafiza izlerini dondurur.

        Args:
            before: Bu zamandan once planlanan izler (None ise simdiki zaman).

        Returns:
            Tekrari gereken hafiza izleri listesi.
        """
        if before is None:
            before = datetime.now(timezone.utc)

        due: list[MemoryTrace] = []
        for trace in self._traces.values():
            if trace.next_review is not None and trace.next_review <= before:
                due.append(trace)

        logger.debug(
            "Tekrari gereken iz sayisi: %d (esik=%s)", len(due), before.isoformat()
        )
        return due

    def schedule_review(self, memory_id: str) -> ReviewSchedule | None:
        """Sonraki tekrar zamanini planlar.

        Aralik hesabi: interval = stability * ln(1 / threshold),
        burada threshold = base_rate.
        Sonraki tekrar = simdiki zaman + interval saniye.

        Args:
            memory_id: Planlanacak hafiza ID.

        Returns:
            Tekrar zamanlama bilgisi veya None (bulunamazsa).
        """
        trace = self._traces.get(memory_id)
        if trace is None:
            logger.warning("Zamanlama basarisiz: %s bulunamadi", memory_id)
            return None

        if self._base_rate <= 0.0 or self._base_rate >= 1.0:
            interval_seconds = trace.stability
        else:
            interval_seconds = trace.stability * math.log(1.0 / self._base_rate)

        now = datetime.now(timezone.utc)
        next_review = now + timedelta(seconds=interval_seconds)

        # Trace'i guncelle
        updated_trace = MemoryTrace(
            id=trace.id,
            memory_id=trace.memory_id,
            memory_type=trace.memory_type,
            strength=trace.strength,
            stability=trace.stability,
            last_review=trace.last_review,
            next_review=next_review,
            review_count=trace.review_count,
            created_at=trace.created_at,
        )
        self._traces[memory_id] = updated_trace

        schedule = ReviewSchedule(
            memory_id=memory_id,
            scheduled_at=next_review,
            interval_seconds=interval_seconds,
            review_number=trace.review_count + 1,
        )

        logger.debug(
            "Tekrar planlandi: %s -> %s (aralik=%.0f sn)",
            memory_id,
            next_review.isoformat(),
            interval_seconds,
        )
        return schedule

    def decay_all(
        self, at_time: datetime | None = None,
    ) -> dict[str, float]:
        """Tum hafiza izlerinin guncel tutma oranini hesaplar.

        Args:
            at_time: Hesaplama zamani (None ise simdiki zaman).

        Returns:
            Her hafiza ID icin tutma orani sozlugu.
        """
        if at_time is None:
            at_time = datetime.now(timezone.utc)

        retentions: dict[str, float] = {}
        for memory_id in self._traces:
            retentions[memory_id] = self.calculate_retention(memory_id, at_time)

        logger.debug("Tum izler hesaplandi: %d iz", len(retentions))
        return retentions

    def prune_forgotten(self, threshold: float = 0.01) -> int:
        """Tutma orani esik degerinin altinda olan izleri siler.

        Args:
            threshold: Silme esigi (bu degerden dusuk tutma oranina
                      sahip izler silinir).

        Returns:
            Silinen iz sayisi.
        """
        now = datetime.now(timezone.utc)
        to_remove: list[str] = []

        for memory_id in self._traces:
            retention = self.calculate_retention(memory_id, now)
            if retention < threshold:
                to_remove.append(memory_id)

        for memory_id in to_remove:
            del self._traces[memory_id]

        if to_remove:
            logger.info(
                "Unutulan izler budandi: %d iz silindi (esik=%.3f)",
                len(to_remove),
                threshold,
            )
        return len(to_remove)

    def get_trace(self, memory_id: str) -> MemoryTrace | None:
        """Hafiza izini dondurur.

        Args:
            memory_id: Hafiza ID.

        Returns:
            Hafiza izi veya None (bulunamazsa).
        """
        return self._traces.get(memory_id)

    def _calculate_stability(
        self,
        base_stability: float,
        review_count: int,
        importance: float,
    ) -> float:
        """Stabilite parametresini hesaplar.

        Formul: S = base * (1 + review_count * 0.5) * (1 + importance).

        Args:
            base_stability: Temel stabilite degeri.
            review_count: Gozden gecirme sayisi.
            importance: Onem derecesi (0.0-1.0).

        Returns:
            Hesaplanan stabilite degeri.
        """
        stability = base_stability * (1.0 + review_count * 0.5) * (1.0 + importance)
        return stability

    def count(self) -> int:
        """Toplam hafiza izi sayisini dondurur.

        Returns:
            Kayitli iz sayisi.
        """
        return len(self._traces)
