"""Gateway yapilandirma yoneticisi.

Hot-reload, guvenli birlestirme ve
dogrulama islemleri.
"""

import json
import logging
import os
import time
from typing import Any

logger = logging.getLogger(__name__)


class GatewayConfigManager:
    """Gateway yapilandirma yoneticisi.

    Attributes:
        _bindings: Aktif baglamalar.
        _config_path: Yapilandirma dosya yolu.
        _last_refresh: Son yenileme zamani.
    """

    def __init__(
        self,
        config_path: str = "",
    ) -> None:
        """GatewayConfigManager baslatir."""
        self._bindings: dict[str, Any] = {}
        self._config_path = config_path
        self._last_refresh: float = 0.0
        self._history: list[dict[str, Any]] = []

    def refresh_bindings(self) -> bool:
        """Baglamalari mesaj basina yeniler.

        Restart gerektirmez.

        Returns:
            Yenileme basarili ise True.
        """
        if not self._config_path:
            return False

        try:
            if os.path.isfile(self._config_path):
                with open(
                    self._config_path,
                    encoding="utf-8",
                ) as f:
                    new_config = json.load(f)

                self._bindings = new_config
                self._last_refresh = time.time()
                logger.info(
                    "Baglamalar yenilendi: %s",
                    self._config_path,
                )
                return True
        except (json.JSONDecodeError, OSError) as e:
            logger.error(
                "Baglama yenileme hatasi: %s", e,
            )
        return False

    @staticmethod
    def prevent_object_array_merge(
        base: Any,
        override: Any,
    ) -> Any:
        """Object-array merge fallback'i engeller.

        Dict'leri birlestirir, array'leri degistirir
        ama dict+array karisimini engeller.

        Args:
            base: Temel deger.
            override: Uzerine yazilacak deger.

        Returns:
            Birlesmis deger.
        """
        if isinstance(base, dict) and isinstance(
            override, dict,
        ):
            result = dict(base)
            for key, val in override.items():
                if key in result:
                    result[key] = (
                        GatewayConfigManager
                        .prevent_object_array_merge(
                            result[key], val,
                        )
                    )
                else:
                    result[key] = val
            return result

        if isinstance(base, dict) and isinstance(
            override, list,
        ):
            return base

        if isinstance(base, list) and isinstance(
            override, dict,
        ):
            return base

        return override

    @staticmethod
    def trim_proxy_whitespace(
        entries: list[str],
    ) -> list[str]:
        """Trusted proxy girislerindeki boslugu temizler.

        Args:
            entries: Proxy girisleri.

        Returns:
            Temizlenmis girisler.
        """
        return [
            e.strip()
            for e in entries
            if e.strip()
        ]

    def hot_reload(
        self,
        config_path: str = "",
    ) -> list[dict[str, str]]:
        """Config'i dosyadan yeniden yukler.

        Args:
            config_path: Yapilandirma dosya yolu.

        Returns:
            Degisiklik listesi.
        """
        path = config_path or self._config_path
        if not path or not os.path.isfile(path):
            return []

        try:
            with open(path, encoding="utf-8") as f:
                new_config = json.load(f)
        except (json.JSONDecodeError, OSError):
            return []

        old = dict(self._bindings)
        diffs: list[dict[str, str]] = []

        merged = self.prevent_object_array_merge(
            old, new_config,
        )
        if isinstance(merged, dict):
            for key in set(
                list(old.keys())
                + list(merged.keys())
            ):
                old_val = old.get(key)
                new_val = merged.get(key)
                if old_val != new_val:
                    action = "changed"
                    if key not in old:
                        action = "added"
                    elif key not in merged:
                        action = "removed"
                    diffs.append({
                        "key": key,
                        "old_value": str(old_val),
                        "new_value": str(new_val),
                        "action": action,
                    })

            self._bindings = merged
            self._config_path = path
            self._last_refresh = time.time()

        return diffs

    def get(
        self,
        key: str,
        default: Any = None,
    ) -> Any:
        """Nokta notasyonuyla config degeri getirir.

        Args:
            key: Ayar anahtari (orn: "auth.mode").
            default: Varsayilan deger.

        Returns:
            Config degeri.
        """
        parts = key.split(".")
        current: Any = self._bindings
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
                if current is None:
                    return default
            else:
                return default
        return current

    def set(
        self,
        key: str,
        value: Any,
    ) -> None:
        """Config degeri ayarlar.

        Args:
            key: Ayar anahtari.
            value: Deger.
        """
        parts = key.split(".")
        current = self._bindings
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        current[parts[-1]] = value

    def validate(self) -> list[str]:
        """Config'i dogrular.

        Returns:
            Uyari listesi.
        """
        warnings: list[str] = []

        if not self._bindings:
            warnings.append(
                "Yapilandirma bos",
            )

        proxies = self.get(
            "trusted_proxies", [],
        )
        if isinstance(proxies, list):
            for p in proxies:
                if isinstance(p, str) and (
                    p != p.strip()
                ):
                    warnings.append(
                        f"Proxy bosluk iceriyor: "
                        f"'{p}'",
                    )

        auth_mode = self.get("auth.mode", "token")
        if auth_mode not in (
            "token", "none", "basic",
        ):
            warnings.append(
                f"Gecersiz auth modu: {auth_mode}",
            )

        return warnings

    def _merge_configs(
        self,
        base: dict[str, Any],
        override: dict[str, Any],
    ) -> dict[str, Any]:
        """Derin birlestirme, array degistirme yok.

        Args:
            base: Temel config.
            override: Uzerine yazilacak config.

        Returns:
            Birlesmis config.
        """
        result = self.prevent_object_array_merge(
            base, override,
        )
        if isinstance(result, dict):
            return result
        return dict(base)
