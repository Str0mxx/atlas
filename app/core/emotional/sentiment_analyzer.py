"""ATLAS Duygu Analizi modulu.

Metin duygu tespiti, duygu siniflandirma, yogunluk puanlama,
alaycilik tespiti ve baglam duyarli analiz.
"""

import logging
import re

from app.models.emotional import Emotion, Sentiment, SentimentResult

logger = logging.getLogger(__name__)

# Pozitif anahtar kelimeler
_POSITIVE_WORDS: set[str] = {
    "guzel", "harika", "mukemmel", "super", "tesekkur", "sagol", "basarili",
    "sevindim", "mutlu", "eyi", "iyi", "bravo", "aferin", "memnun", "tatli",
    "perfect", "great", "good", "nice", "thanks", "excellent", "awesome",
    "love", "happy", "wonderful", "amazing", "fantastic", "brilliant",
}

# Negatif anahtar kelimeler
_NEGATIVE_WORDS: set[str] = {
    "kotu", "berbat", "rezalet", "hata", "bozuk", "yanlis", "sorun", "problem",
    "sinir", "kizgin", "uzgun", "mutsuz", "korku", "endise", "basarisiz",
    "bad", "terrible", "awful", "wrong", "error", "broken", "angry", "sad",
    "frustrated", "annoyed", "disappointed", "hate", "worst", "fail", "poor",
}

# Duygu anahtar kelimeleri
_EMOTION_KEYWORDS: dict[Emotion, set[str]] = {
    Emotion.HAPPY: {"mutlu", "sevincli", "guzel", "harika", "happy", "joy", "glad", "pleased"},
    Emotion.SAD: {"uzgun", "mutsuz", "uzucu", "kayip", "sad", "unhappy", "depressed", "gloomy"},
    Emotion.ANGRY: {"kizgin", "sinir", "ofke", "delir", "angry", "furious", "mad", "rage"},
    Emotion.FEAR: {"korku", "endise", "kaygi", "tedirgin", "fear", "scared", "worried", "anxious"},
    Emotion.SURPRISE: {"saskin", "sasirdim", "beklemiyordum", "surprise", "shocked", "unexpected", "wow"},
    Emotion.DISGUST: {"igrenme", "tiksinme", "midem", "disgusting", "gross", "revolting"},
    Emotion.TRUST: {"guven", "emin", "trust", "reliable", "confident", "sure"},
    Emotion.ANTICIPATION: {"heyecan", "merak", "sabir", "excited", "eager", "looking forward"},
}

# Alaycilik kaliplari
_SARCASM_PATTERNS: list[str] = [
    r"cok\s+guzel\s*[\.\!\?]*\s*(?:tabii|tabi|hadi|evet)",
    r"(?:oh|aa)\s+(?:ne\s+)?guzel",
    r"bravo\s+(?:sana|valla)",
    r"(?:yeah|sure|right)\s+[\.\!\?]",
    r"oh\s+great\b",
    r"how\s+wonderful\b",
]

# Yogunluk artiricilar
_INTENSIFIERS: set[str] = {
    "cok", "asiri", "son derece", "inanilmaz", "very", "extremely",
    "really", "so", "incredibly", "absolutely", "totally", "super",
}


class SentimentAnalyzer:
    """Duygu analiz sistemi.

    Metin uzerinden duygu polaritesi, duygu sinifi,
    yogunluk ve alaycilik tespiti yapar.

    Attributes:
        _history: Analiz gecmisi.
    """

    def __init__(self) -> None:
        """Duygu analizcisini baslatir."""
        self._history: list[SentimentResult] = []
        logger.info("SentimentAnalyzer baslatildi")

    def analyze(self, text: str, context: str = "") -> SentimentResult:
        """Metni analiz eder.

        Args:
            text: Analiz edilecek metin.
            context: Baglamsal bilgi.

        Returns:
            SentimentResult nesnesi.
        """
        lower = text.lower()
        words = set(re.findall(r'\w+', lower))

        sentiment = self._detect_sentiment(words)
        emotion = self._classify_emotion(words)
        intensity = self._calculate_intensity(words, lower)
        is_sarcastic = self._detect_sarcasm(lower)
        keywords = self._extract_keywords(words)

        # Alaycilik durumunda sentiment'i ters cevir
        if is_sarcastic and sentiment == Sentiment.POSITIVE:
            sentiment = Sentiment.NEGATIVE

        # Baglamsal ayarlama
        if context:
            sentiment, emotion = self._context_adjust(sentiment, emotion, context)

        confidence = self._calculate_confidence(words, keywords)

        result = SentimentResult(
            text=text,
            sentiment=sentiment,
            emotion=emotion,
            intensity=intensity,
            confidence=confidence,
            is_sarcastic=is_sarcastic,
            keywords=keywords,
        )

        self._history.append(result)
        return result

    def batch_analyze(self, texts: list[str]) -> list[SentimentResult]:
        """Toplu analiz yapar.

        Args:
            texts: Metin listesi.

        Returns:
            SentimentResult listesi.
        """
        return [self.analyze(t) for t in texts]

    def get_dominant_sentiment(self, results: list[SentimentResult] | None = None) -> Sentiment:
        """Baskin duyguyu getirir.

        Args:
            results: Analiz sonuclari (None ise gecmis).

        Returns:
            Baskin Sentiment.
        """
        target = results or self._history
        if not target:
            return Sentiment.NEUTRAL

        counts: dict[Sentiment, int] = {}
        for r in target:
            counts[r.sentiment] = counts.get(r.sentiment, 0) + 1

        return max(counts, key=counts.get)  # type: ignore[arg-type]

    def _detect_sentiment(self, words: set[str]) -> Sentiment:
        """Duygu polaritesini tespit eder."""
        pos = len(words & _POSITIVE_WORDS)
        neg = len(words & _NEGATIVE_WORDS)

        if pos > 0 and neg > 0:
            return Sentiment.MIXED
        if pos > neg:
            return Sentiment.POSITIVE
        if neg > pos:
            return Sentiment.NEGATIVE
        return Sentiment.NEUTRAL

    def _classify_emotion(self, words: set[str]) -> Emotion:
        """Duygu sinifini belirler."""
        best_emotion = Emotion.TRUST
        best_count = 0

        for emotion, keywords in _EMOTION_KEYWORDS.items():
            count = len(words & keywords)
            if count > best_count:
                best_count = count
                best_emotion = emotion

        return best_emotion

    def _calculate_intensity(self, words: set[str], text: str) -> float:
        """Yogunluk puani hesaplar."""
        base = 0.5

        # Yogunlastiricilar
        intensifier_count = len(words & _INTENSIFIERS)
        base += intensifier_count * 0.1

        # Unlem isaretleri
        exclamation_count = text.count("!")
        base += min(exclamation_count * 0.05, 0.2)

        # Buyuk harf orani
        upper_ratio = sum(1 for c in text if c.isupper()) / max(len(text), 1)
        if upper_ratio > 0.5:
            base += 0.15

        return min(max(base, 0.0), 1.0)

    def _detect_sarcasm(self, text: str) -> bool:
        """Alaycilik tespit eder."""
        for pattern in _SARCASM_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False

    def _extract_keywords(self, words: set[str]) -> list[str]:
        """Duygusal anahtar kelimeleri cikarir."""
        keywords: list[str] = []
        for w in words:
            if w in _POSITIVE_WORDS or w in _NEGATIVE_WORDS:
                keywords.append(w)
        return sorted(keywords)

    def _calculate_confidence(self, words: set[str], keywords: list[str]) -> float:
        """Guven puani hesaplar."""
        if not words:
            return 0.3
        keyword_ratio = len(keywords) / max(len(words), 1)
        return min(0.4 + keyword_ratio * 3.0, 1.0)

    def _context_adjust(
        self, sentiment: Sentiment, emotion: Emotion, context: str
    ) -> tuple[Sentiment, Emotion]:
        """Baglama gore ayarlama yapar."""
        ctx_lower = context.lower()
        if "complaint" in ctx_lower or "sikayet" in ctx_lower:
            if sentiment == Sentiment.NEUTRAL:
                sentiment = Sentiment.NEGATIVE
        if "success" in ctx_lower or "basari" in ctx_lower:
            if sentiment == Sentiment.NEUTRAL:
                sentiment = Sentiment.POSITIVE
                emotion = Emotion.HAPPY
        return sentiment, emotion

    @property
    def history(self) -> list[SentimentResult]:
        """Analiz gecmisi."""
        return list(self._history)

    @property
    def analysis_count(self) -> int:
        """Analiz sayisi."""
        return len(self._history)
