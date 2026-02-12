"""ATLAS yerel AI cikarim modulu.

Bulut API'si erisimez oldugundan yerel LLM,
kural tabanli kararlar ve cache'li yanitlar saglar.
"""

import hashlib
import logging
from enum import Enum
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)


class LocalLLMProvider(str, Enum):
    """Yerel LLM saglayici tanimlari."""

    OLLAMA = "ollama"
    RULE_BASED = "rule_based"
    CACHED = "cached"


# Fallback karar kurallari (risk, urgency) -> action
FALLBACK_RULES: dict[tuple[str, str], str] = {
    ("low", "low"): "log",
    ("low", "medium"): "log",
    ("low", "high"): "notify",
    ("medium", "low"): "notify",
    ("medium", "medium"): "notify",
    ("medium", "high"): "notify",
    ("high", "low"): "notify",
    ("high", "medium"): "notify",
    ("high", "high"): "notify",  # Cevrimdisi: auto_fix/immediate yerine notify
}

# Onceden tanimli kural tabanli yanitlar
_RULE_RESPONSES: dict[str, str] = {
    "server_check": "Sunucu kontrolu yapildi. Cevrimdisi modda detayli analiz yapilamaz.",
    "security_scan": "Guvenlik taramasi yapildi. Cevrimdisi modda sinirli kontrol yapildi.",
    "risk_assessment": "Risk degerlendirmesi: Cevrimdisi modda muhafazakar yaklasim uygulanir.",
    "general": "Islem kaydedildi. Baglanti geldiginde detayli analiz yapilacak.",
}


class LocalLLM:
    """Yerel AI cikarim sinifi.

    Bulut API'si erisimez oldugundan yerel model,
    kural tabanli veya cache'li yanitlar uretir.

    Attributes:
        provider: Aktif saglayici (ollama/rule_based/cached).
        ollama_url: Ollama API adresi.
        model_name: Ollama model adi.
    """

    def __init__(
        self,
        provider: LocalLLMProvider | None = None,
        ollama_url: str | None = None,
        model_name: str | None = None,
    ) -> None:
        """LocalLLM'i baslatir.

        Args:
            provider: LLM saglayici (varsayilan: settings'ten).
            ollama_url: Ollama API adresi.
            model_name: Ollama model adi.
        """
        self.provider = provider or LocalLLMProvider(settings.local_llm_provider)
        self.ollama_url = ollama_url or settings.local_llm_ollama_url
        self.model_name = model_name or settings.local_llm_model
        self._response_cache: dict[str, str] = {}

        logger.info(
            "LocalLLM olusturuldu (provider=%s, model=%s)",
            self.provider.value, self.model_name,
        )

    async def generate(
        self,
        prompt: str,
        context: dict[str, Any] | None = None,
    ) -> str:
        """Yanik uretir (provider sirasina gore dener).

        Args:
            prompt: Giris metni.
            context: Ek baglam bilgisi.

        Returns:
            Uretilen yanit metni.
        """
        # Oncelik: cache -> ollama -> rule_based
        cached = await self._cached_generate(prompt, context)
        if cached is not None:
            return cached

        if self.provider == LocalLLMProvider.OLLAMA:
            try:
                result = await self._ollama_generate(prompt, context)
                # Basarili yaniti cache'le
                prompt_hash = self._hash_prompt(prompt)
                await self.cache_response(prompt_hash, result)
                return result
            except Exception as exc:
                logger.warning("Ollama basarisiz, rule_based'e dusuldu: %s", exc)

        return self._rule_based_generate(prompt, context)

    async def _ollama_generate(
        self,
        prompt: str,
        context: dict[str, Any] | None = None,
    ) -> str:
        """Ollama API ile yanit uretir.

        Args:
            prompt: Giris metni.
            context: Ek baglam bilgisi.

        Returns:
            Ollama'dan uretilen yanit.

        Raises:
            Exception: Ollama baglantisi basarisiz.
        """
        import httpx

        payload: dict[str, Any] = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
        }
        if context:
            payload["system"] = str(context)

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{self.ollama_url}/api/generate",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            return str(data.get("response", ""))

    def _rule_based_generate(
        self,
        prompt: str,
        context: dict[str, Any] | None = None,
    ) -> str:
        """Kural tabanli yanit uretir.

        Args:
            prompt: Giris metni.
            context: Ek baglam bilgisi.

        Returns:
            Kural tabanli yanit.
        """
        prompt_lower = prompt.lower()

        for keyword, response in _RULE_RESPONSES.items():
            if keyword in prompt_lower:
                return response

        return _RULE_RESPONSES["general"]

    async def _cached_generate(
        self,
        prompt: str,
        context: dict[str, Any] | None = None,
    ) -> str | None:
        """Cache'den yanit dondurur.

        Args:
            prompt: Giris metni.
            context: Ek baglam bilgisi (su an kullanilmiyor).

        Returns:
            Cache'deki yanit veya None.
        """
        prompt_hash = self._hash_prompt(prompt)
        return await self.get_cached_response(prompt_hash)

    def get_fallback_action(self, risk: str, urgency: str) -> str:
        """Risk ve aciliyete gore fallback aksiyon dondurur.

        Cevrimdisi modda muhafazakar davranir:
        auto_fix ve immediate yerine notify kullanir.

        Args:
            risk: Risk seviyesi (low/medium/high).
            urgency: Aciliyet seviyesi (low/medium/high).

        Returns:
            Aksiyon tipi (log/notify).
        """
        return FALLBACK_RULES.get((risk, urgency), "notify")

    async def cache_response(self, prompt_hash: str, response: str) -> None:
        """Yaniti cache'e yazar.

        Args:
            prompt_hash: Prompt hash degeri.
            response: Yanit metni.
        """
        self._response_cache[prompt_hash] = response

    async def get_cached_response(self, prompt_hash: str) -> str | None:
        """Cache'den yanit okur.

        Args:
            prompt_hash: Prompt hash degeri.

        Returns:
            Cache'deki yanit veya None.
        """
        return self._response_cache.get(prompt_hash)

    async def is_available(self) -> bool:
        """Yerel LLM'in kullanilabilir olup olmadigini kontrol eder.

        Returns:
            LLM kullanilabilir ise True.
        """
        if self.provider == LocalLLMProvider.RULE_BASED:
            return True
        if self.provider == LocalLLMProvider.CACHED:
            return len(self._response_cache) > 0

        # Ollama kontrolu
        try:
            import httpx

            async with httpx.AsyncClient(timeout=3) as client:
                resp = await client.get(f"{self.ollama_url}/api/tags")
                return resp.status_code == 200
        except Exception:
            return False

    @staticmethod
    def _hash_prompt(prompt: str) -> str:
        """Prompt'u hash'ler.

        Args:
            prompt: Giris metni.

        Returns:
            SHA-256 hash degeri.
        """
        return hashlib.sha256(prompt.encode()).hexdigest()[:16]
