"""ATLAS Marka Duygu Toplayıcı modülü.

Duygu analizi, kaynak ağırlıklandırma,
trend hesaplama, geçmiş karşılaştırma,
kanal bazlı dağılım.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class BrandSentimentAggregator:
    """Marka duygu toplayıcı.

    Bahsedilme duygularını toplar ve analiz eder.

    Attributes:
        _sentiments: Duygu kayıtları.
        _weights: Kaynak ağırlıkları.
    """

    def __init__(self) -> None:
        """Toplayıcıyı başlatır."""
        self._sentiments: dict[
            str, list[dict[str, Any]]
        ] = {}
        self._weights = {
            "news": 2.0,
            "social_media": 1.0,
            "forum": 0.8,
            "review": 1.5,
        }
        self._history: dict[
            str, list[dict[str, Any]]
        ] = {}
        self._stats = {
            "analyses_run": 0,
            "trends_calculated": 0,
        }

        logger.info(
            "BrandSentimentAggregator "
            "baslatildi",
        )

    def analyze_sentiment(
        self,
        brand: str,
        text: str = "",
        source: str = "social_media",
    ) -> dict[str, Any]:
        """Duygu analizi yapar.

        Args:
            brand: Marka.
            text: Metin.
            source: Kaynak.

        Returns:
            Analiz bilgisi.
        """
        # Basit anahtar kelime tabanlı
        positive = [
            "good", "great", "love",
            "excellent", "best", "amazing",
            "iyi", "harika", "müthiş",
        ]
        negative = [
            "bad", "terrible", "hate",
            "worst", "awful", "poor",
            "kötü", "berbat", "rezalet",
        ]

        text_lower = text.lower()
        pos_count = sum(
            1 for w in positive
            if w in text_lower
        )
        neg_count = sum(
            1 for w in negative
            if w in text_lower
        )

        if pos_count > neg_count:
            sentiment = "positive"
            score = min(
                0.5 + pos_count * 0.15, 1.0,
            )
        elif neg_count > pos_count:
            sentiment = "negative"
            score = max(
                0.5 - neg_count * 0.15, 0.0,
            )
        else:
            sentiment = "neutral"
            score = 0.5

        if brand not in self._sentiments:
            self._sentiments[brand] = []

        self._sentiments[brand].append({
            "sentiment": sentiment,
            "score": round(score, 2),
            "source": source,
            "timestamp": time.time(),
        })
        self._stats["analyses_run"] += 1

        return {
            "brand": brand,
            "sentiment": sentiment,
            "score": round(score, 2),
            "source": source,
            "analyzed": True,
        }

    def weight_sources(
        self,
        brand: str,
    ) -> dict[str, Any]:
        """Kaynak ağırlıklandırma yapar.

        Args:
            brand: Marka.

        Returns:
            Ağırlıklı bilgi.
        """
        entries = self._sentiments.get(
            brand, [],
        )
        if not entries:
            return {
                "brand": brand,
                "weighted": False,
            }

        weighted_sum = 0.0
        weight_total = 0.0

        for e in entries:
            w = self._weights.get(
                e["source"], 1.0,
            )
            weighted_sum += e["score"] * w
            weight_total += w

        avg = round(
            weighted_sum / weight_total, 2,
        ) if weight_total > 0 else 0.5

        return {
            "brand": brand,
            "weighted_score": avg,
            "entries": len(entries),
            "weighted": True,
        }

    def calculate_trend(
        self,
        brand: str,
        window: int = 5,
    ) -> dict[str, Any]:
        """Trend hesaplar.

        Args:
            brand: Marka.
            window: Pencere boyutu.

        Returns:
            Trend bilgisi.
        """
        entries = self._sentiments.get(
            brand, [],
        )
        if len(entries) < window:
            return {
                "brand": brand,
                "calculated": False,
            }

        recent = [
            e["score"]
            for e in entries[-window:]
        ]
        older = [
            e["score"]
            for e in entries[-window * 2:-window]
        ] if len(entries) >= window * 2 else (
            [e["score"] for e in entries[:window]]
        )

        recent_avg = sum(recent) / len(recent)
        older_avg = (
            sum(older) / len(older)
            if older else recent_avg
        )

        diff = round(
            recent_avg - older_avg, 3,
        )
        direction = (
            "improving" if diff > 0.05
            else "declining" if diff < -0.05
            else "stable"
        )

        self._stats[
            "trends_calculated"
        ] += 1

        return {
            "brand": brand,
            "recent_avg": round(
                recent_avg, 2,
            ),
            "older_avg": round(
                older_avg, 2,
            ),
            "diff": diff,
            "direction": direction,
            "calculated": True,
        }

    def compare_historical(
        self,
        brand: str,
        baseline_score: float = 0.5,
    ) -> dict[str, Any]:
        """Geçmiş karşılaştırma yapar.

        Args:
            brand: Marka.
            baseline_score: Temel puan.

        Returns:
            Karşılaştırma bilgisi.
        """
        entries = self._sentiments.get(
            brand, [],
        )
        if not entries:
            return {
                "brand": brand,
                "compared": False,
            }

        current = sum(
            e["score"] for e in entries
        ) / len(entries)
        change = round(
            (current - baseline_score)
            / (baseline_score + 0.01) * 100,
            1,
        )

        return {
            "brand": brand,
            "current_avg": round(current, 2),
            "baseline": baseline_score,
            "change_pct": change,
            "compared": True,
        }

    def breakdown_by_channel(
        self,
        brand: str,
    ) -> dict[str, Any]:
        """Kanal bazlı dağılım hesaplar.

        Args:
            brand: Marka.

        Returns:
            Dağılım bilgisi.
        """
        entries = self._sentiments.get(
            brand, [],
        )
        if not entries:
            return {
                "brand": brand,
                "breakdown": {},
                "channels": 0,
            }

        channels: dict[
            str, list[float]
        ] = {}
        for e in entries:
            src = e["source"]
            if src not in channels:
                channels[src] = []
            channels[src].append(e["score"])

        breakdown = {}
        for src, scores in channels.items():
            breakdown[src] = {
                "avg_score": round(
                    sum(scores) / len(scores),
                    2,
                ),
                "count": len(scores),
            }

        return {
            "brand": brand,
            "breakdown": breakdown,
            "channels": len(breakdown),
        }

    @property
    def analysis_count(self) -> int:
        """Analiz sayısı."""
        return self._stats["analyses_run"]

    @property
    def trend_count(self) -> int:
        """Trend sayısı."""
        return self._stats[
            "trends_calculated"
        ]
