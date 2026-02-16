"""ATLAS Yanıt İşleyici modülü.

Yanıt tespiti, duygu analizi,
niyet çıkarma, otomatik kategorileme,
özet üretimi.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class ResponseHandler:
    """Yanıt işleyici.

    Gelen yanıtları analiz eder ve işler.

    Attributes:
        _responses: Yanıt kayıtları.
    """

    SENTIMENT_KEYWORDS = {
        "positive": [
            "great", "excellent", "thank",
            "interested", "love", "perfect",
            "wonderful", "amazing", "yes",
            "agree", "happy", "pleased",
        ],
        "negative": [
            "no", "not interested",
            "unsubscribe", "stop", "remove",
            "complaint", "terrible", "worst",
            "disappointed", "angry", "never",
        ],
        "neutral": [
            "ok", "maybe", "consider",
            "think", "later", "possibly",
            "perhaps", "depends",
        ],
    }

    INTENT_PATTERNS = {
        "interested": [
            "tell me more", "interested",
            "schedule", "meeting", "demo",
            "pricing", "learn more",
        ],
        "not_interested": [
            "not interested", "no thanks",
            "pass", "decline", "remove",
        ],
        "question": [
            "how", "what", "when", "where",
            "why", "can you", "could you",
            "is it", "do you",
        ],
        "complaint": [
            "issue", "problem", "bug",
            "broken", "error", "complaint",
        ],
        "referral": [
            "colleague", "forward",
            "refer", "contact instead",
            "speak with", "talk to",
        ],
    }

    def __init__(self) -> None:
        """İşleyiciyi başlatır."""
        self._responses: list[
            dict[str, Any]
        ] = []
        self._counter = 0
        self._stats = {
            "responses_processed": 0,
            "positive": 0,
            "negative": 0,
            "neutral": 0,
        }

        logger.info(
            "ResponseHandler baslatildi",
        )

    def process_response(
        self,
        email_id: str,
        from_addr: str,
        subject: str,
        body: str,
    ) -> dict[str, Any]:
        """Yanıtı işler.

        Args:
            email_id: İlgili email ID.
            from_addr: Gönderen.
            subject: Konu.
            body: Gövde.

        Returns:
            İşlem bilgisi.
        """
        self._counter += 1
        rid = f"resp_{self._counter}"

        sentiment = self.analyze_sentiment(
            body,
        )
        intent = self.extract_intent(body)
        category = self._categorize(
            sentiment["sentiment"],
            intent["intent"],
        )
        summary = self._summarize(body)

        response = {
            "response_id": rid,
            "email_id": email_id,
            "from": from_addr,
            "subject": subject,
            "body": body,
            "sentiment": sentiment[
                "sentiment"
            ],
            "intent": intent["intent"],
            "category": category,
            "summary": summary,
            "processed_at": time.time(),
        }
        self._responses.append(response)
        self._stats[
            "responses_processed"
        ] += 1
        self._stats[
            sentiment["sentiment"]
        ] += 1

        return {
            "response_id": rid,
            "email_id": email_id,
            "sentiment": sentiment[
                "sentiment"
            ],
            "confidence": sentiment[
                "confidence"
            ],
            "intent": intent["intent"],
            "category": category,
            "summary": summary,
            "processed": True,
        }

    def analyze_sentiment(
        self,
        text: str,
    ) -> dict[str, Any]:
        """Duygu analizi yapar.

        Args:
            text: Metin.

        Returns:
            Analiz bilgisi.
        """
        text_lower = text.lower()
        scores = {
            "positive": 0,
            "negative": 0,
            "neutral": 0,
        }

        for sentiment, keywords in (
            self.SENTIMENT_KEYWORDS.items()
        ):
            for kw in keywords:
                if kw in text_lower:
                    scores[sentiment] += 1

        total = sum(scores.values())
        if total == 0:
            return {
                "sentiment": "neutral",
                "confidence": 0.5,
                "scores": scores,
            }

        best = max(
            scores, key=scores.get,
        )
        confidence = (
            scores[best] / max(total, 1)
        )

        return {
            "sentiment": best,
            "confidence": round(
                confidence, 2,
            ),
            "scores": scores,
        }

    def extract_intent(
        self,
        text: str,
    ) -> dict[str, Any]:
        """Niyet çıkarır.

        Args:
            text: Metin.

        Returns:
            Niyet bilgisi.
        """
        text_lower = text.lower()
        scores: dict[str, int] = {}

        for intent, patterns in (
            self.INTENT_PATTERNS.items()
        ):
            count = 0
            for p in patterns:
                if p in text_lower:
                    count += 1
            if count > 0:
                scores[intent] = count

        if not scores:
            return {
                "intent": "unknown",
                "confidence": 0.0,
            }

        best = max(
            scores, key=scores.get,
        )
        total = sum(scores.values())
        confidence = (
            scores[best] / max(total, 1)
        )

        return {
            "intent": best,
            "confidence": round(
                confidence, 2,
            ),
            "all_intents": scores,
        }

    def _categorize(
        self,
        sentiment: str,
        intent: str,
    ) -> str:
        """Kategorilendirir."""
        if intent == "interested":
            return "hot_lead"
        if intent == "not_interested":
            return "closed"
        if intent == "complaint":
            return "support"
        if intent == "referral":
            return "referral"
        if intent == "question":
            return "inquiry"
        if sentiment == "positive":
            return "warm_lead"
        if sentiment == "negative":
            return "at_risk"
        return "neutral"

    def _summarize(
        self,
        text: str,
        max_words: int = 30,
    ) -> str:
        """Özet üretir."""
        words = text.split()
        if len(words) <= max_words:
            return text.strip()
        return (
            " ".join(words[:max_words])
            + "..."
        )

    def get_responses(
        self,
        email_id: str | None = None,
        sentiment: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Yanıtları getirir.

        Args:
            email_id: Email filtresi.
            sentiment: Duygu filtresi.
            limit: Maks kayıt.

        Returns:
            Yanıt listesi.
        """
        results = self._responses
        if email_id:
            results = [
                r for r in results
                if r["email_id"] == email_id
            ]
        if sentiment:
            results = [
                r for r in results
                if r["sentiment"] == sentiment
            ]
        return list(results[-limit:])

    @property
    def response_count(self) -> int:
        """İşlenen yanıt sayısı."""
        return self._stats[
            "responses_processed"
        ]
