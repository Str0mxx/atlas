"""ATLAS Sinyal Toplayıcı modülü.

Çoklu kaynak sinyalleri, sinyal ağırlıklandırma,
gürültü filtreleme, korelasyon,
aksiyon sinyalleri.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class SignalAggregator:
    """Sinyal toplayıcı.

    Çoklu kaynaklardan sinyalleri toplar ve işler.

    Attributes:
        _signals: Sinyal kayıtları.
        _sources: Kaynak ağırlıkları.
    """

    DEFAULT_WEIGHTS = {
        "market": 1.0,
        "competitor": 0.9,
        "patent": 0.7,
        "academic": 0.6,
        "regulation": 0.8,
        "investment": 0.85,
        "news": 0.5,
        "social": 0.3,
    }

    def __init__(self) -> None:
        """Toplayıcıyı başlatır."""
        self._signals: list[
            dict[str, Any]
        ] = []
        self._sources: dict[
            str, float
        ] = dict(self.DEFAULT_WEIGHTS)
        self._correlations: list[
            dict[str, Any]
        ] = []
        self._counter = 0
        self._stats = {
            "signals_collected": 0,
            "signals_filtered": 0,
            "correlations_found": 0,
        }

        logger.info(
            "SignalAggregator baslatildi",
        )

    def collect_signal(
        self,
        source_type: str,
        title: str,
        strength: float = 0.5,
        description: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Sinyal toplar.

        Args:
            source_type: Kaynak tipi.
            title: Başlık.
            strength: Güç (0-1).
            description: Açıklama.
            metadata: Ek veri.

        Returns:
            Toplama bilgisi.
        """
        self._counter += 1
        sid = f"sig_{self._counter}"

        weight = self._sources.get(
            source_type, 0.5,
        )
        weighted_strength = round(
            strength * weight, 3,
        )

        signal = {
            "signal_id": sid,
            "source_type": source_type,
            "title": title,
            "raw_strength": strength,
            "weight": weight,
            "weighted_strength": (
                weighted_strength
            ),
            "description": description,
            "metadata": metadata or {},
            "actionable": (
                weighted_strength >= 0.6
            ),
            "collected_at": time.time(),
        }
        self._signals.append(signal)
        self._stats[
            "signals_collected"
        ] += 1

        return {
            "signal_id": sid,
            "source_type": source_type,
            "title": title,
            "weighted_strength": (
                weighted_strength
            ),
            "actionable": signal[
                "actionable"
            ],
            "collected": True,
        }

    def set_source_weight(
        self,
        source_type: str,
        weight: float,
    ) -> dict[str, Any]:
        """Kaynak ağırlığı ayarlar.

        Args:
            source_type: Kaynak tipi.
            weight: Ağırlık (0-1).

        Returns:
            Ayar bilgisi.
        """
        self._sources[source_type] = max(
            0.0, min(1.0, weight),
        )
        return {
            "source_type": source_type,
            "weight": self._sources[
                source_type
            ],
            "set": True,
        }

    def filter_noise(
        self,
        threshold: float = 0.3,
    ) -> dict[str, Any]:
        """Gürültü filtreler.

        Args:
            threshold: Eşik değeri.

        Returns:
            Filtreleme bilgisi.
        """
        before = len(self._signals)
        self._signals = [
            s for s in self._signals
            if s["weighted_strength"]
            >= threshold
        ]
        filtered = before - len(
            self._signals,
        )
        self._stats[
            "signals_filtered"
        ] += filtered

        return {
            "before": before,
            "after": len(self._signals),
            "filtered": filtered,
            "threshold": threshold,
        }

    def find_correlations(
        self,
    ) -> dict[str, Any]:
        """Korelasyonları bulur.

        Returns:
            Korelasyon bilgisi.
        """
        correlations = []

        # Basit kaynak tipi korelasyonu
        by_source: dict[
            str, list[dict[str, Any]]
        ] = {}
        for s in self._signals:
            st = s["source_type"]
            if st not in by_source:
                by_source[st] = []
            by_source[st].append(s)

        sources = list(by_source.keys())
        for i in range(len(sources)):
            for j in range(
                i + 1, len(sources),
            ):
                s1 = sources[i]
                s2 = sources[j]
                # Ortak anahtar kelime var mı
                titles1 = set(
                    w.lower()
                    for s in by_source[s1]
                    for w in s["title"].split()
                )
                titles2 = set(
                    w.lower()
                    for s in by_source[s2]
                    for w in s["title"].split()
                )
                overlap = titles1 & titles2
                if len(overlap) > 1:
                    correlations.append({
                        "sources": [s1, s2],
                        "common_terms": list(
                            overlap,
                        )[:5],
                        "strength": round(
                            len(overlap)
                            / max(
                                len(
                                    titles1
                                    | titles2
                                ),
                                1,
                            ),
                            2,
                        ),
                    })

        self._correlations = correlations
        self._stats[
            "correlations_found"
        ] = len(correlations)

        return {
            "correlations": correlations,
            "count": len(correlations),
        }

    def get_actionable_signals(
        self,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Aksiyon sinyallerini getirir.

        Args:
            limit: Maks kayıt.

        Returns:
            Sinyal listesi.
        """
        actionable = [
            s for s in self._signals
            if s["actionable"]
        ]
        actionable.sort(
            key=lambda x: x[
                "weighted_strength"
            ],
            reverse=True,
        )
        return actionable[:limit]

    def get_signals(
        self,
        source_type: str | None = None,
        min_strength: float = 0.0,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Sinyalleri getirir.

        Args:
            source_type: Kaynak filtresi.
            min_strength: Min güç filtresi.
            limit: Maks kayıt.

        Returns:
            Sinyal listesi.
        """
        results = self._signals
        if source_type:
            results = [
                s for s in results
                if s["source_type"]
                == source_type
            ]
        if min_strength > 0:
            results = [
                s for s in results
                if s["weighted_strength"]
                >= min_strength
            ]
        return list(results[-limit:])

    def get_summary(self) -> dict[str, Any]:
        """Özet bilgi döndürür."""
        by_source: dict[str, int] = {}
        for s in self._signals:
            st = s["source_type"]
            by_source[st] = (
                by_source.get(st, 0) + 1
            )

        actionable = sum(
            1 for s in self._signals
            if s["actionable"]
        )

        return {
            "total_signals": len(
                self._signals,
            ),
            "actionable": actionable,
            "by_source": by_source,
            "sources": len(by_source),
        }

    @property
    def signal_count(self) -> int:
        """Sinyal sayısı."""
        return len(self._signals)

    @property
    def actionable_count(self) -> int:
        """Aksiyon sinyal sayısı."""
        return sum(
            1 for s in self._signals
            if s["actionable"]
        )
