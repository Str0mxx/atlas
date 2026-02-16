"""ATLAS Email Sınıflandırıcı modülü.

Kategori tespiti, öncelik atama,
spam filtreleme, niyet tespiti,
gönderici profilleme.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class EmailClassifier:
    """Email sınıflandırıcı.

    Emailleri otomatik sınıflandırır.

    Attributes:
        _classifications: Sınıflandırma kayıtları.
        _sender_profiles: Gönderici profilleri.
    """

    def __init__(self) -> None:
        """Sınıflandırıcıyı başlatır."""
        self._classifications: list[
            dict[str, Any]
        ] = []
        self._sender_profiles: dict[
            str, dict[str, Any]
        ] = {}
        self._counter = 0
        self._stats = {
            "emails_classified": 0,
            "spam_detected": 0,
        }
        self._category_keywords = {
            "business": [
                "meeting", "project",
                "deadline", "report",
                "proposal", "contract",
            ],
            "personal": [
                "birthday", "vacation",
                "family", "dinner",
                "weekend", "holiday",
            ],
            "marketing": [
                "offer", "discount",
                "sale", "subscribe",
                "unsubscribe", "promo",
            ],
            "transactional": [
                "receipt", "confirmation",
                "order", "shipping",
                "invoice", "payment",
            ],
        }

        logger.info(
            "EmailClassifier baslatildi",
        )

    def detect_category(
        self,
        subject: str = "",
        body: str = "",
        sender: str = "",
    ) -> dict[str, Any]:
        """Kategori tespit eder.

        Args:
            subject: Konu.
            body: Gövde.
            sender: Gönderici.

        Returns:
            Tespit bilgisi.
        """
        self._counter += 1
        cid = f"ecl_{self._counter}"

        text = (
            f"{subject} {body}".lower()
        )
        category = "business"
        max_score = 0

        for cat, keywords in (
            self._category_keywords.items()
        ):
            score = sum(
                1 for kw in keywords
                if kw in text
            )
            if score > max_score:
                max_score = score
                category = cat

        confidence = round(
            min(max_score * 0.2 + 0.3, 1.0),
            2,
        )

        result = {
            "classification_id": cid,
            "category": category,
            "confidence": confidence,
            "detected": True,
        }
        self._classifications.append(result)
        self._stats[
            "emails_classified"
        ] += 1

        return result

    def assign_priority(
        self,
        subject: str = "",
        body: str = "",
        sender: str = "",
        is_vip: bool = False,
    ) -> dict[str, Any]:
        """Öncelik atar.

        Args:
            subject: Konu.
            body: Gövde.
            sender: Gönderici.
            is_vip: VIP gönderici.

        Returns:
            Atama bilgisi.
        """
        text = (
            f"{subject} {body}".lower()
        )

        urgent_words = [
            "urgent", "asap", "critical",
            "immediately", "acil",
        ]
        high_words = [
            "important", "deadline",
            "priority", "review",
        ]

        urgent_count = sum(
            1 for w in urgent_words
            if w in text
        )
        high_count = sum(
            1 for w in high_words
            if w in text
        )

        if is_vip or urgent_count >= 2:
            priority = "critical"
        elif urgent_count >= 1:
            priority = "high"
        elif high_count >= 1:
            priority = "high"
        else:
            priority = "medium"

        return {
            "priority": priority,
            "is_vip": is_vip,
            "assigned": True,
        }

    def filter_spam(
        self,
        subject: str = "",
        body: str = "",
        sender: str = "",
    ) -> dict[str, Any]:
        """Spam filtreler.

        Args:
            subject: Konu.
            body: Gövde.
            sender: Gönderici.

        Returns:
            Filtreleme bilgisi.
        """
        text = (
            f"{subject} {body}".lower()
        )

        spam_words = [
            "winner", "lottery", "free",
            "click here", "act now",
            "limited time", "congratulations",
            "viagra", "casino",
        ]

        spam_score = sum(
            1 for w in spam_words
            if w in text
        )

        if spam_score >= 3:
            verdict = "spam"
        elif spam_score >= 1:
            verdict = "suspicious"
        else:
            verdict = "clean"

        if verdict == "spam":
            self._stats[
                "spam_detected"
            ] += 1

        return {
            "verdict": verdict,
            "spam_score": round(
                min(spam_score * 0.2, 1.0),
                2,
            ),
            "filtered": True,
        }

    def detect_intent(
        self,
        subject: str = "",
        body: str = "",
    ) -> dict[str, Any]:
        """Niyet tespit eder.

        Args:
            subject: Konu.
            body: Gövde.

        Returns:
            Tespit bilgisi.
        """
        text = (
            f"{subject} {body}".lower()
        )

        intent_patterns = {
            "request": [
                "please", "could you",
                "can you", "would you",
                "need", "request",
            ],
            "information": [
                "fyi", "update",
                "attached", "sharing",
                "report", "summary",
            ],
            "question": [
                "?", "how", "what",
                "when", "where", "why",
            ],
            "action_required": [
                "action required",
                "please review",
                "approval needed",
                "sign", "confirm",
            ],
        }

        intents = []
        for intent, patterns in (
            intent_patterns.items()
        ):
            matches = sum(
                1 for p in patterns
                if p in text
            )
            if matches > 0:
                intents.append({
                    "intent": intent,
                    "confidence": round(
                        min(
                            matches * 0.25,
                            1.0,
                        ),
                        2,
                    ),
                })

        intents.sort(
            key=lambda x: x["confidence"],
            reverse=True,
        )

        primary = (
            intents[0]["intent"]
            if intents
            else "information"
        )

        return {
            "primary_intent": primary,
            "intents": intents,
            "detected": True,
        }

    def profile_sender(
        self,
        sender: str = "",
        domain: str = "",
        history_count: int = 0,
        avg_response_time: float = 0.0,
    ) -> dict[str, Any]:
        """Gönderici profili oluşturur.

        Args:
            sender: Gönderici.
            domain: Alan adı.
            history_count: Geçmiş sayısı.
            avg_response_time: Ort yanıt süresi.

        Returns:
            Profil bilgisi.
        """
        if not domain and "@" in sender:
            domain = sender.split("@")[-1]

        reputation = (
            "trusted"
            if history_count >= 10
            else "known"
            if history_count >= 3
            else "new"
        )

        self._sender_profiles[sender] = {
            "sender": sender,
            "domain": domain,
            "history_count": history_count,
            "reputation": reputation,
            "avg_response_time": (
                avg_response_time
            ),
            "timestamp": time.time(),
        }

        return {
            "sender": sender,
            "domain": domain,
            "reputation": reputation,
            "profiled": True,
        }

    @property
    def classification_count(self) -> int:
        """Sınıflandırma sayısı."""
        return self._stats[
            "emails_classified"
        ]

    @property
    def spam_count(self) -> int:
        """Spam sayısı."""
        return self._stats[
            "spam_detected"
        ]
