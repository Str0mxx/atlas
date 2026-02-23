"""Token sayici.

Dogru sayim, modele ozel,
onbellekleme ve tahmin.
"""

import hashlib
import logging
import time
from typing import Any

from app.models.contextwindow_models import (
    TokenUsage,
)

logger = logging.getLogger(__name__)

# Varsayilan ayarlar
_DEFAULT_CHARS_PER_TOKEN = 4
_MAX_CACHE_SIZE = 10000
_CACHE_TTL = 3600.0

# Model token limitleri
_MODEL_LIMITS: dict[str, int] = {
    "gpt-3.5-turbo": 4096,
    "gpt-4": 8192,
    "gpt-4-32k": 32768,
    "gpt-4-turbo": 128000,
    "gpt-4o": 128000,
    "claude-3-haiku": 200000,
    "claude-3-sonnet": 200000,
    "claude-3-opus": 200000,
    "claude-3.5-sonnet": 200000,
    "claude-4-sonnet": 200000,
    "claude-4-opus": 200000,
    "default": 128000,
}

# Modele ozel karakter/token oranlari
_MODEL_RATIOS: dict[str, float] = {
    "gpt-3.5-turbo": 4.0,
    "gpt-4": 4.0,
    "gpt-4-turbo": 4.0,
    "gpt-4o": 3.8,
    "claude-3-haiku": 3.5,
    "claude-3-sonnet": 3.5,
    "claude-3-opus": 3.5,
    "claude-3.5-sonnet": 3.5,
    "claude-4-sonnet": 3.5,
    "claude-4-opus": 3.5,
    "default": 4.0,
}


class TokenCounter:
    """Token sayici.

    Dogru sayim, modele ozel,
    onbellekleme ve tahmin.

    Attributes:
        _model: Hedef model.
        _cache: Token onbellegi.
        _total_counted: Toplam sayim.
    """

    def __init__(
        self,
        model: str = "default",
    ) -> None:
        """TokenCounter baslatir.

        Args:
            model: Hedef model adi.
        """
        self._model: str = model
        self._cache: dict[
            str, tuple[int, float]
        ] = {}
        self._total_counted: int = 0
        self._total_cached_hits: int = 0
        self._chars_per_token: float = (
            _MODEL_RATIOS.get(
                model,
                _MODEL_RATIOS["default"],
            )
        )

        logger.info(
            "TokenCounter baslatildi: %s",
            model,
        )

    # ---- Sayim ----

    def count(self, text: str) -> int:
        """Token sayisi hesaplar.

        Args:
            text: Metin.

        Returns:
            Token sayisi.
        """
        if not text:
            return 0

        # Onbellek kontrol
        key = self._hash(text)
        cached = self._get_cached(key)
        if cached is not None:
            self._total_cached_hits += 1
            return cached

        # Hesapla
        tokens = self._estimate(text)
        self._set_cached(key, tokens)
        self._total_counted += 1

        return tokens

    def count_messages(
        self,
        messages: list[dict[str, str]],
    ) -> int:
        """Mesaj listesi token sayisi.

        Args:
            messages: Mesaj listesi
                (role, content).

        Returns:
            Toplam token sayisi.
        """
        total = 0
        for msg in messages:
            content = msg.get("content", "")
            role = msg.get("role", "")
            # Role + separator overhead
            total += self.count(content)
            total += self.count(role) + 4
        return total

    def count_with_detail(
        self,
        messages: list[dict[str, str]],
    ) -> list[TokenUsage]:
        """Detayli mesaj token sayimi.

        Args:
            messages: Mesaj listesi.

        Returns:
            TokenUsage listesi.
        """
        result: list[TokenUsage] = []
        now = time.time()

        for msg in messages:
            content = msg.get("content", "")
            role = msg.get("role", "")
            tokens = (
                self.count(content)
                + self.count(role)
                + 4
            )

            usage = TokenUsage(
                role=role,
                content_hash=self._hash(
                    content,
                ),
                token_count=tokens,
                timestamp=now,
                is_system=role == "system",
            )
            result.append(usage)

        return result

    def count_remaining(
        self,
        used: int,
        max_tokens: int | None = None,
    ) -> int:
        """Kalan token sayisi.

        Args:
            used: Kullanilan token.
            max_tokens: Maks token.

        Returns:
            Kalan token.
        """
        limit = (
            max_tokens
            if max_tokens is not None
            else self.get_model_limit()
        )
        return max(0, limit - used)

    # ---- Model Bilgisi ----

    def get_model_limit(self) -> int:
        """Model token limitini dondurur.

        Returns:
            Token limiti.
        """
        return _MODEL_LIMITS.get(
            self._model,
            _MODEL_LIMITS["default"],
        )

    def set_model(
        self, model: str,
    ) -> None:
        """Modeli degistirir.

        Args:
            model: Yeni model adi.
        """
        self._model = model
        self._chars_per_token = (
            _MODEL_RATIOS.get(
                model,
                _MODEL_RATIOS["default"],
            )
        )

    def get_model(self) -> str:
        """Mevcut modeli dondurur.

        Returns:
            Model adi.
        """
        return self._model

    def list_models(self) -> dict[str, int]:
        """Taninan modelleri dondurur.

        Returns:
            Model-limit eslemesi.
        """
        return dict(_MODEL_LIMITS)

    # ---- Tahmin ----

    def estimate_tokens(
        self, text: str,
    ) -> int:
        """Hizli tahmin (onbellek yok).

        Args:
            text: Metin.

        Returns:
            Tahmini token sayisi.
        """
        return self._estimate(text)

    def estimate_ratio(
        self,
        used: int,
        max_tokens: int | None = None,
    ) -> float:
        """Kullanim oranini dondurur.

        Args:
            used: Kullanilan token.
            max_tokens: Maks token.

        Returns:
            Oran (0.0-1.0).
        """
        limit = (
            max_tokens
            if max_tokens is not None
            else self.get_model_limit()
        )
        if limit <= 0:
            return 1.0
        return min(1.0, used / limit)

    def will_fit(
        self,
        text: str,
        used: int,
        max_tokens: int | None = None,
    ) -> bool:
        """Metni sigar mi kontrol eder.

        Args:
            text: Metin.
            used: Kullanilan token.
            max_tokens: Maks token.

        Returns:
            Sigar ise True.
        """
        needed = self.count(text)
        remaining = self.count_remaining(
            used, max_tokens,
        )
        return needed <= remaining

    # ---- Onbellek ----

    def clear_cache(self) -> int:
        """Onbellegi temizler.

        Returns:
            Temizlenen kayit sayisi.
        """
        count = len(self._cache)
        self._cache = {}
        return count

    def get_cache_size(self) -> int:
        """Onbellek boyutunu dondurur.

        Returns:
            Kayit sayisi.
        """
        return len(self._cache)

    def _get_cached(
        self, key: str,
    ) -> int | None:
        """Onbellekten deger alir.

        Args:
            key: Anahtar.

        Returns:
            Token sayisi veya None.
        """
        entry = self._cache.get(key)
        if entry is None:
            return None

        tokens, ts = entry
        if time.time() - ts > _CACHE_TTL:
            del self._cache[key]
            return None

        return tokens

    def _set_cached(
        self, key: str, tokens: int,
    ) -> None:
        """Onbellege yazar.

        Args:
            key: Anahtar.
            tokens: Token sayisi.
        """
        if len(self._cache) >= _MAX_CACHE_SIZE:
            # En eski %20 temizle
            items = sorted(
                self._cache.items(),
                key=lambda x: x[1][1],
            )
            remove = len(items) // 5
            for k, _ in items[:remove]:
                del self._cache[k]

        self._cache[key] = (
            tokens,
            time.time(),
        )

    # ---- Yardimci ----

    def _estimate(self, text: str) -> int:
        """Token sayisi tahmin eder.

        Args:
            text: Metin.

        Returns:
            Tahmini token sayisi.
        """
        if not text:
            return 0

        # Karakter bazli tahmin
        base = len(text) / self._chars_per_token

        # Ozel karakter cezasi
        specials = sum(
            1
            for c in text
            if not c.isalnum()
            and c != " "
        )
        penalty = specials * 0.3

        return max(1, int(base + penalty))

    @staticmethod
    def _hash(text: str) -> str:
        """Metin hash'i olusturur.

        Args:
            text: Metin.

        Returns:
            Hash degeri.
        """
        return hashlib.md5(
            text.encode("utf-8"),
        ).hexdigest()[:12]

    # ---- Istatistikler ----

    def get_stats(
        self,
    ) -> dict[str, Any]:
        """Istatistikleri dondurur.

        Returns:
            Istatistik sozlugu.
        """
        return {
            "model": self._model,
            "model_limit": (
                self.get_model_limit()
            ),
            "chars_per_token": (
                self._chars_per_token
            ),
            "cache_size": len(self._cache),
            "total_counted": (
                self._total_counted
            ),
            "total_cached_hits": (
                self._total_cached_hits
            ),
        }
