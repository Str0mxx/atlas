"""Sistem prompt garantisi.

Her zaman sistem prompt dahil etme,
alan rezervasyonu ve oncelik yonetimi.
"""

import logging
import time
from typing import Any

from app.models.contextwindow_models import (
    SystemPromptConfig,
)

logger = logging.getLogger(__name__)

# Varsayilan ayarlar
_DEFAULT_RESERVE = 2000
_MAX_RESERVE = 50000
_MAX_PROMPTS = 100
_MAX_VERSIONS = 50


class SystemPromptGuarantee:
    """Sistem prompt garantisi.

    Her zaman sistem prompt dahil etme,
    alan rezervasyonu ve oncelik yonetimi.

    Attributes:
        _prompts: Kayitli promptlar.
        _active_id: Aktif prompt ID.
        _reserve_tokens: Rezerve token.
    """

    def __init__(
        self,
        reserve_tokens: int = (
            _DEFAULT_RESERVE
        ),
    ) -> None:
        """SystemPromptGuarantee baslatir.

        Args:
            reserve_tokens: Rezerve token.
        """
        self._reserve_tokens: int = min(
            reserve_tokens, _MAX_RESERVE,
        )
        self._prompts: dict[
            str, SystemPromptConfig
        ] = {}
        self._active_id: str = ""
        self._versions: list[
            dict[str, Any]
        ] = []
        self._total_injections: int = 0
        self._total_fallbacks: int = 0

        logger.info(
            "SystemPromptGuarantee "
            "baslatildi",
        )

    # ---- Prompt Yonetimi ----

    def register_prompt(
        self,
        prompt_text: str,
        reserved_tokens: int = 0,
        fallback_text: str = "",
        is_protected: bool = True,
    ) -> SystemPromptConfig | None:
        """Sistem promptu kaydeder.

        Args:
            prompt_text: Prompt metni.
            reserved_tokens: Ozel rezerv.
            fallback_text: Yedek metin.
            is_protected: Korunuyor mu.

        Returns:
            Config veya None.
        """
        if not prompt_text:
            return None

        if (
            len(self._prompts) >= _MAX_PROMPTS
        ):
            return None

        token_count = self._estimate_tokens(
            prompt_text,
        )
        fb_tokens = (
            self._estimate_tokens(
                fallback_text,
            )
            if fallback_text
            else 0
        )

        config = SystemPromptConfig(
            prompt_text=prompt_text,
            token_count=token_count,
            reserved_tokens=(
                reserved_tokens
                if reserved_tokens > 0
                else token_count + 100
            ),
            is_protected=is_protected,
            fallback_text=fallback_text,
            fallback_tokens=fb_tokens,
        )

        self._prompts[config.config_id] = (
            config
        )

        # Ilk prompt aktif olur
        if not self._active_id:
            self._active_id = config.config_id

        self._record_version(
            config.config_id, "register",
        )

        return config

    def get_prompt(
        self, config_id: str,
    ) -> SystemPromptConfig | None:
        """Prompt dondurur.

        Args:
            config_id: Config ID.

        Returns:
            Config veya None.
        """
        return self._prompts.get(config_id)

    def get_active_prompt(
        self,
    ) -> SystemPromptConfig | None:
        """Aktif promptu dondurur.

        Returns:
            Aktif config veya None.
        """
        if not self._active_id:
            return None
        return self._prompts.get(
            self._active_id,
        )

    def set_active(
        self, config_id: str,
    ) -> bool:
        """Aktif promptu degistirir.

        Args:
            config_id: Config ID.

        Returns:
            Degistirildi ise True.
        """
        if config_id not in self._prompts:
            return False
        self._active_id = config_id
        self._record_version(
            config_id, "activate",
        )
        return True

    def update_prompt(
        self,
        config_id: str,
        prompt_text: str | None = None,
        fallback_text: str | None = None,
        is_protected: bool | None = None,
    ) -> bool:
        """Promptu gunceller.

        Args:
            config_id: Config ID.
            prompt_text: Yeni metin.
            fallback_text: Yeni yedek.
            is_protected: Yeni koruma.

        Returns:
            Guncellendi ise True.
        """
        config = self._prompts.get(config_id)
        if not config:
            return False

        if prompt_text is not None:
            config.prompt_text = prompt_text
            config.token_count = (
                self._estimate_tokens(
                    prompt_text,
                )
            )
            config.reserved_tokens = (
                config.token_count + 100
            )
            config.version += 1

        if fallback_text is not None:
            config.fallback_text = (
                fallback_text
            )
            config.fallback_tokens = (
                self._estimate_tokens(
                    fallback_text,
                )
            )

        if is_protected is not None:
            config.is_protected = is_protected

        self._record_version(
            config_id, "update",
        )
        return True

    def remove_prompt(
        self, config_id: str,
    ) -> bool:
        """Promptu siler.

        Args:
            config_id: Config ID.

        Returns:
            Silindi ise True.
        """
        if config_id not in self._prompts:
            return False

        del self._prompts[config_id]

        if self._active_id == config_id:
            self._active_id = ""
            # Ilk mevcut promptu aktif yap
            if self._prompts:
                self._active_id = next(
                    iter(self._prompts),
                )

        return True

    def list_prompts(
        self,
    ) -> list[SystemPromptConfig]:
        """Promptlari listeler.

        Returns:
            Config listesi.
        """
        return list(self._prompts.values())

    # ---- Garanti Mekanizmasi ----

    def inject_system_prompt(
        self,
        messages: list[dict[str, str]],
        max_tokens: int = 0,
    ) -> list[dict[str, str]]:
        """Sistem promptunu enjekte eder.

        Args:
            messages: Mesaj listesi.
            max_tokens: Maks token.

        Returns:
            Prompt eklenmis mesajlar.
        """
        active = self.get_active_prompt()
        if not active:
            return list(messages)

        # Zaten var mi kontrol
        for m in messages:
            if (
                m.get("role") == "system"
                and m.get("content")
                == active.prompt_text
            ):
                self._total_injections += 1
                return list(messages)

        # Token butcesi kontrol
        prompt_text = active.prompt_text
        prompt_tokens = active.token_count

        if max_tokens > 0:
            msg_tokens = sum(
                self._estimate_tokens(
                    m.get("content", ""),
                )
                for m in messages
            )

            if (
                msg_tokens + prompt_tokens
                > max_tokens
            ):
                # Yedek dene
                if active.fallback_text:
                    prompt_text = (
                        active.fallback_text
                    )
                    prompt_tokens = (
                        active.fallback_tokens
                    )
                    self._total_fallbacks += 1

                    if (
                        msg_tokens
                        + prompt_tokens
                        > max_tokens
                    ):
                        return list(messages)

        # Sistem promptu en basa ekle
        result = [
            {
                "role": "system",
                "content": prompt_text,
            },
        ]

        # Mevcut sistem mesajlarini atla
        for m in messages:
            if m.get("role") != "system":
                result.append(m)

        self._total_injections += 1
        return result

    def calculate_available(
        self,
        max_tokens: int,
    ) -> int:
        """Kullanilabilir token sayisi.

        Args:
            max_tokens: Maks token.

        Returns:
            Kullanilabilir token.
        """
        active = self.get_active_prompt()
        reserve = self._reserve_tokens

        if active:
            reserve = max(
                reserve,
                active.reserved_tokens,
            )

        return max(0, max_tokens - reserve)

    def fits_with_prompt(
        self,
        message_tokens: int,
        max_tokens: int,
    ) -> bool:
        """Prompt ile birlikte sigar mi.

        Args:
            message_tokens: Mesaj tokenlari.
            max_tokens: Maks token.

        Returns:
            Sigar ise True.
        """
        available = (
            self.calculate_available(
                max_tokens,
            )
        )
        return message_tokens <= available

    def get_prompt_tokens(self) -> int:
        """Aktif prompt token sayisi.

        Returns:
            Token sayisi.
        """
        active = self.get_active_prompt()
        if not active:
            return 0
        return active.token_count

    # ---- Rezervasyon ----

    def set_reserve(
        self, tokens: int,
    ) -> None:
        """Rezerve token ayarlar.

        Args:
            tokens: Token sayisi.
        """
        self._reserve_tokens = min(
            max(0, tokens), _MAX_RESERVE,
        )

    def get_reserve(self) -> int:
        """Rezerve token dondurur.

        Returns:
            Token sayisi.
        """
        return self._reserve_tokens

    # ---- Versiyon ----

    def _record_version(
        self,
        config_id: str,
        action: str,
    ) -> None:
        """Versiyon kaydeder.

        Args:
            config_id: Config ID.
            action: Aksiyon.
        """
        self._versions.append(
            {
                "config_id": config_id,
                "action": action,
                "timestamp": time.time(),
            },
        )
        if len(self._versions) > _MAX_VERSIONS:
            self._versions = (
                self._versions[-_MAX_VERSIONS:]
            )

    def get_version_history(
        self, limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Versiyon gecmisini dondurur.

        Args:
            limit: Maks sonuc.

        Returns:
            Gecmis listesi.
        """
        return list(
            reversed(
                self._versions[-limit:],
            ),
        )

    # ---- Yardimci ----

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        """Token tahmin eder.

        Args:
            text: Metin.

        Returns:
            Tahmini token.
        """
        if not text:
            return 0
        return max(1, len(text) // 4)

    # ---- Istatistikler ----

    def get_stats(
        self,
    ) -> dict[str, Any]:
        """Istatistikleri dondurur.

        Returns:
            Istatistik sozlugu.
        """
        active = self.get_active_prompt()
        return {
            "reserve_tokens": (
                self._reserve_tokens
            ),
            "total_prompts": len(
                self._prompts,
            ),
            "active_prompt": (
                self._active_id or None
            ),
            "active_tokens": (
                active.token_count
                if active
                else 0
            ),
            "total_injections": (
                self._total_injections
            ),
            "total_fallbacks": (
                self._total_fallbacks
            ),
        }
