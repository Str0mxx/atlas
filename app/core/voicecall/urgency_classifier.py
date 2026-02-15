"""ATLAS Aciliyet Sınıflandırıcı modülü.

Ses tonu analizi, anahtar kelime tespiti,
stres tespiti, öncelik eskalasyonu,
acil durum tetikleyicileri.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class UrgencyClassifier:
    """Aciliyet sınıflandırıcı.

    Ses ve metin analizine göre aciliyet belirler.

    Attributes:
        _classifications: Sınıflandırma kayıtları.
        _emergency_keywords: Acil durum anahtar kelimeleri.
    """

    def __init__(self) -> None:
        """Sınıflandırıcıyı başlatır."""
        self._classifications: list[
            dict[str, Any]
        ] = []
        self._emergency_keywords: list[str] = [
            "emergency", "urgent", "critical",
            "help", "danger", "fire",
            "acil", "tehlike", "yangın",
        ]
        self._stress_indicators: list[str] = [
            "please hurry", "right now",
            "immediately", "asap",
            "hemen", "acele",
        ]
        self._counter = 0
        self._stats = {
            "classifications": 0,
            "emergencies_detected": 0,
            "escalations": 0,
        }

        logger.info(
            "UrgencyClassifier baslatildi",
        )

    def classify(
        self,
        text: str,
        voice_features: dict[str, float]
        | None = None,
    ) -> dict[str, Any]:
        """Aciliyet sınıflandırır.

        Args:
            text: Metin.
            voice_features: Ses özellikleri.

        Returns:
            Sınıflandırma bilgisi.
        """
        self._counter += 1
        cid = f"uc_{self._counter}"

        # Anahtar kelime analizi
        keyword_score = (
            self._analyze_keywords(text)
        )

        # Ses tonu analizi
        tone_score = self._analyze_tone(
            voice_features or {},
        )

        # Stres tespiti
        stress_score = self._detect_stress(
            text, voice_features or {},
        )

        # Toplam puan
        total = (
            keyword_score * 0.4
            + tone_score * 0.3
            + stress_score * 0.3
        )

        urgency = self._score_to_level(total)
        is_emergency = urgency == "critical"

        classification = {
            "classification_id": cid,
            "text": text,
            "urgency": urgency,
            "total_score": round(total, 3),
            "keyword_score": round(
                keyword_score, 3,
            ),
            "tone_score": round(tone_score, 3),
            "stress_score": round(
                stress_score, 3,
            ),
            "is_emergency": is_emergency,
            "timestamp": time.time(),
        }
        self._classifications.append(
            classification,
        )
        self._stats["classifications"] += 1

        if is_emergency:
            self._stats[
                "emergencies_detected"
            ] += 1

        return classification

    def _analyze_keywords(
        self,
        text: str,
    ) -> float:
        """Anahtar kelime analizi yapar.

        Args:
            text: Metin.

        Returns:
            Puan (0-1).
        """
        text_lower = text.lower()
        matches = sum(
            1 for kw in self._emergency_keywords
            if kw in text_lower
        )
        return min(1.0, matches * 0.3)

    def _analyze_tone(
        self,
        features: dict[str, float],
    ) -> float:
        """Ses tonu analizi yapar.

        Args:
            features: Ses özellikleri.

        Returns:
            Puan (0-1).
        """
        pitch = features.get("pitch", 0.5)
        volume = features.get("volume", 0.5)
        speed = features.get("speed", 0.5)

        # Yüksek pitch + yüksek ses + hızlı konuşma
        score = (
            pitch * 0.3
            + volume * 0.4
            + speed * 0.3
        )
        return min(1.0, max(0.0, score))

    def _detect_stress(
        self,
        text: str,
        features: dict[str, float],
    ) -> float:
        """Stres tespit eder.

        Args:
            text: Metin.
            features: Ses özellikleri.

        Returns:
            Stres puanı (0-1).
        """
        text_lower = text.lower()
        indicator_matches = sum(
            1 for ind in self._stress_indicators
            if ind in text_lower
        )
        text_stress = min(
            1.0, indicator_matches * 0.3,
        )

        voice_stress = features.get(
            "stress", 0.0,
        )

        return max(text_stress, voice_stress)

    def _score_to_level(
        self,
        score: float,
    ) -> str:
        """Puanı seviyeye çevirir.

        Args:
            score: Toplam puan.

        Returns:
            Aciliyet seviyesi.
        """
        if score >= 0.8:
            return "critical"
        if score >= 0.6:
            return "high"
        if score >= 0.4:
            return "medium"
        if score >= 0.2:
            return "low"
        return "routine"

    def escalate(
        self,
        classification_id: str,
        new_level: str,
        reason: str = "",
    ) -> dict[str, Any]:
        """Öncelik yükseltir.

        Args:
            classification_id: Sınıflandırma ID.
            new_level: Yeni seviye.
            reason: Neden.

        Returns:
            Eskalasyon bilgisi.
        """
        cls = None
        for c in self._classifications:
            if (
                c["classification_id"]
                == classification_id
            ):
                cls = c
                break

        if not cls:
            return {
                "error": "classification_not_found",
            }

        old_level = cls["urgency"]
        cls["urgency"] = new_level
        cls["escalated"] = True
        cls["escalation_reason"] = reason
        self._stats["escalations"] += 1

        return {
            "classification_id": classification_id,
            "old_level": old_level,
            "new_level": new_level,
            "reason": reason,
        }

    def add_emergency_keyword(
        self,
        keyword: str,
    ) -> dict[str, Any]:
        """Acil durum anahtar kelimesi ekler.

        Args:
            keyword: Anahtar kelime.

        Returns:
            Ekleme bilgisi.
        """
        if keyword not in self._emergency_keywords:
            self._emergency_keywords.append(
                keyword,
            )
        return {
            "keyword": keyword,
            "added": True,
            "total_keywords": len(
                self._emergency_keywords,
            ),
        }

    def check_emergency_triggers(
        self,
        text: str,
    ) -> dict[str, Any]:
        """Acil durum tetikleyicilerini kontrol eder.

        Args:
            text: Metin.

        Returns:
            Kontrol bilgisi.
        """
        text_lower = text.lower()
        triggered = [
            kw for kw in self._emergency_keywords
            if kw in text_lower
        ]

        return {
            "triggered": len(triggered) > 0,
            "triggers": triggered,
            "trigger_count": len(triggered),
        }

    def get_classifications(
        self,
        urgency: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Sınıflandırmaları getirir.

        Args:
            urgency: Aciliyet filtresi.
            limit: Maks kayıt.

        Returns:
            Sınıflandırma listesi.
        """
        results = self._classifications
        if urgency:
            results = [
                c for c in results
                if c.get("urgency") == urgency
            ]
        return list(results[-limit:])

    @property
    def classification_count(self) -> int:
        """Sınıflandırma sayısı."""
        return self._stats["classifications"]

    @property
    def emergency_count(self) -> int:
        """Acil durum sayısı."""
        return self._stats[
            "emergencies_detected"
        ]
