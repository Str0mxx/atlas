"""ATLAS Akıllı Spam Filtresi modülü.

ML tabanlı filtreleme, phishing tespiti,
gönderici itibarı, içerik analizi,
beyaz/kara liste.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class IntelligentSpamFilter:
    """Akıllı spam filtresi.

    Emailleri spam analizi yapar.

    Attributes:
        _whitelist: Beyaz liste.
        _blacklist: Kara liste.
        _history: Analiz geçmişi.
    """

    def __init__(
        self,
        threshold: float = 0.5,
    ) -> None:
        """Filtreyi başlatır.

        Args:
            threshold: Spam eşiği.
        """
        self._whitelist: set[str] = set()
        self._blacklist: set[str] = set()
        self._sender_reputation: dict[
            str, float
        ] = {}
        self._history: list[
            dict[str, Any]
        ] = []
        self._threshold = threshold
        self._counter = 0
        self._stats = {
            "emails_analyzed": 0,
            "spam_blocked": 0,
            "phishing_detected": 0,
        }

        logger.info(
            "IntelligentSpamFilter "
            "baslatildi",
        )

    def ml_filter(
        self,
        subject: str = "",
        body: str = "",
        sender: str = "",
    ) -> dict[str, Any]:
        """ML tabanlı filtreleme yapar.

        Args:
            subject: Konu.
            body: Gövde.
            sender: Gönderici.

        Returns:
            Filtreleme bilgisi.
        """
        self._counter += 1
        fid = f"spf_{self._counter}"

        # Beyaz/kara liste kontrolü
        if sender in self._blacklist:
            self._stats[
                "spam_blocked"
            ] += 1
            self._stats[
                "emails_analyzed"
            ] += 1
            return {
                "filter_id": fid,
                "verdict": "spam",
                "score": 1.0,
                "reason": "blacklisted",
                "filtered": True,
            }

        if sender in self._whitelist:
            self._stats[
                "emails_analyzed"
            ] += 1
            return {
                "filter_id": fid,
                "verdict": "clean",
                "score": 0.0,
                "reason": "whitelisted",
                "filtered": True,
            }

        spam_score = self._calculate_score(
            subject, body, sender,
        )

        if spam_score >= 0.8:
            verdict = "spam"
            self._stats[
                "spam_blocked"
            ] += 1
        elif spam_score >= self._threshold:
            verdict = "suspicious"
        else:
            verdict = "clean"

        self._stats[
            "emails_analyzed"
        ] += 1

        result = {
            "filter_id": fid,
            "verdict": verdict,
            "score": spam_score,
            "filtered": True,
        }
        self._history.append(result)

        return result

    def detect_phishing(
        self,
        subject: str = "",
        body: str = "",
        sender: str = "",
        links: list[str] | None = None,
    ) -> dict[str, Any]:
        """Phishing tespit eder.

        Args:
            subject: Konu.
            body: Gövde.
            sender: Gönderici.
            links: Bağlantılar.

        Returns:
            Tespit bilgisi.
        """
        links = links or []
        text = (
            f"{subject} {body}".lower()
        )

        phishing_indicators = [
            "verify your account",
            "confirm your identity",
            "suspended",
            "click immediately",
            "update your password",
            "unusual activity",
            "security alert",
        ]

        indicators = sum(
            1 for p in phishing_indicators
            if p in text
        )

        suspicious_links = sum(
            1 for link in links
            if any(
                s in link.lower()
                for s in [
                    "bit.ly", "tinyurl",
                    "signin", "login",
                ]
            )
        )

        risk_score = round(
            min(
                (indicators * 0.25)
                + (suspicious_links * 0.2),
                1.0,
            ),
            2,
        )

        is_phishing = risk_score >= 0.5

        if is_phishing:
            self._stats[
                "phishing_detected"
            ] += 1

        return {
            "is_phishing": is_phishing,
            "risk_score": risk_score,
            "indicators": indicators,
            "suspicious_links": (
                suspicious_links
            ),
            "detected": True,
        }

    def check_reputation(
        self,
        sender: str,
    ) -> dict[str, Any]:
        """Gönderici itibarı kontrol eder.

        Args:
            sender: Gönderici.

        Returns:
            Kontrol bilgisi.
        """
        if sender in self._blacklist:
            reputation = 0.0
            status = "blocked"
        elif sender in self._whitelist:
            reputation = 1.0
            status = "trusted"
        else:
            reputation = (
                self._sender_reputation.get(
                    sender, 0.5,
                )
            )
            status = (
                "good"
                if reputation >= 0.7
                else "neutral"
                if reputation >= 0.3
                else "poor"
            )

        return {
            "sender": sender,
            "reputation": reputation,
            "status": status,
            "checked": True,
        }

    def analyze_content(
        self,
        body: str = "",
    ) -> dict[str, Any]:
        """İçerik analizi yapar.

        Args:
            body: Gövde.

        Returns:
            Analiz bilgisi.
        """
        text = body.lower()

        spam_words = [
            "winner", "lottery", "free",
            "click here", "act now",
            "limited time", "viagra",
            "casino", "prize",
        ]

        matches = [
            w for w in spam_words
            if w in text
        ]

        risk_level = (
            "high"
            if len(matches) >= 3
            else "medium"
            if len(matches) >= 1
            else "low"
        )

        return {
            "spam_words_found": matches,
            "count": len(matches),
            "risk_level": risk_level,
            "analyzed": True,
        }

    def add_to_whitelist(
        self,
        sender: str,
    ) -> dict[str, Any]:
        """Beyaz listeye ekler.

        Args:
            sender: Gönderici.

        Returns:
            Ekleme bilgisi.
        """
        self._whitelist.add(sender)
        self._blacklist.discard(sender)

        return {
            "sender": sender,
            "list": "whitelist",
            "added": True,
        }

    def add_to_blacklist(
        self,
        sender: str,
    ) -> dict[str, Any]:
        """Kara listeye ekler.

        Args:
            sender: Gönderici.

        Returns:
            Ekleme bilgisi.
        """
        self._blacklist.add(sender)
        self._whitelist.discard(sender)

        return {
            "sender": sender,
            "list": "blacklist",
            "added": True,
        }

    def _calculate_score(
        self,
        subject: str,
        body: str,
        sender: str,
    ) -> float:
        """Spam puanı hesaplar."""
        text = (
            f"{subject} {body}".lower()
        )

        spam_words = [
            "winner", "lottery", "free",
            "click here", "act now",
            "limited time", "viagra",
            "casino", "prize",
            "congratulations",
        ]

        match_count = sum(
            1 for w in spam_words
            if w in text
        )

        rep = self._sender_reputation.get(
            sender, 0.5,
        )
        rep_factor = max(
            0, (1 - rep) * 0.3,
        )

        score = round(
            min(
                match_count * 0.15
                + rep_factor,
                1.0,
            ),
            2,
        )

        return score

    @property
    def analyzed_count(self) -> int:
        """Analiz sayısı."""
        return self._stats[
            "emails_analyzed"
        ]

    @property
    def blocked_count(self) -> int:
        """Engellenen sayısı."""
        return self._stats[
            "spam_blocked"
        ]
