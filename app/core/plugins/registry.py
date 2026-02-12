"""Plugin kayit defteri.

Tum yuklenen plugin'lerin durumlarini ve meta verilerini
merkezi olarak yonetir.
"""

import logging
from typing import Any

from app.models.plugin import PluginInfo, PluginState, PluginType

logger = logging.getLogger(__name__)


class PluginRegistry:
    """Merkezi plugin kayit defteri.

    Plugin'lerin durumlarini takip eder, CRUD islemleri saglar
    ve tip/durum bazli filtreleme yapar.

    Attributes:
        _plugins: Plugin adi -> PluginInfo eslesmesi.
    """

    def __init__(self) -> None:
        """PluginRegistry'yi baslatir."""
        self._plugins: dict[str, PluginInfo] = {}
        logger.info("PluginRegistry olusturuldu")

    def register(self, info: PluginInfo) -> None:
        """Plugin'i kayit defterine ekler.

        Args:
            info: Plugin bilgisi.

        Raises:
            ValueError: Ayni isimde plugin zaten kayitliysa.
        """
        name = info.manifest.name
        if name in self._plugins:
            raise ValueError(f"Plugin zaten kayitli: '{name}'")
        self._plugins[name] = info
        logger.debug("Plugin kaydedildi: %s", name)

    def unregister(self, name: str) -> PluginInfo | None:
        """Plugin'i kayit defterinden kaldirir.

        Args:
            name: Plugin adi.

        Returns:
            Kaldirilan PluginInfo veya None.
        """
        info = self._plugins.pop(name, None)
        if info:
            logger.debug("Plugin kaydi silindi: %s", name)
        return info

    def get(self, name: str) -> PluginInfo | None:
        """Plugin bilgisi dondurur.

        Args:
            name: Plugin adi.

        Returns:
            PluginInfo veya None.
        """
        return self._plugins.get(name)

    def has(self, name: str) -> bool:
        """Plugin kayitli mi kontrol eder.

        Args:
            name: Plugin adi.

        Returns:
            Kayitli ise True.
        """
        return name in self._plugins

    def list_all(self) -> list[PluginInfo]:
        """Tum plugin'leri dondurur.

        Returns:
            PluginInfo listesi.
        """
        return list(self._plugins.values())

    def list_by_state(self, state: PluginState) -> list[PluginInfo]:
        """Belirli durumdaki plugin'leri dondurur.

        Args:
            state: Filtrelenecek durum.

        Returns:
            PluginInfo listesi.
        """
        return [p for p in self._plugins.values() if p.state == state]

    def list_by_type(self, plugin_type: PluginType) -> list[PluginInfo]:
        """Belirli tipteki plugin'leri dondurur.

        Args:
            plugin_type: Filtrelenecek tip.

        Returns:
            PluginInfo listesi.
        """
        return [
            p for p in self._plugins.values()
            if p.manifest.plugin_type == plugin_type
        ]

    def update_state(
        self,
        name: str,
        state: PluginState,
        error_message: str | None = None,
    ) -> PluginInfo | None:
        """Plugin durumunu gunceller.

        Args:
            name: Plugin adi.
            state: Yeni durum.
            error_message: Hata mesaji (sadece ERROR durumunda).

        Returns:
            Guncellenen PluginInfo veya None.
        """
        info = self._plugins.get(name)
        if info is None:
            return None

        info.state = state
        if error_message is not None:
            info.error_message = error_message
        elif state != PluginState.ERROR:
            info.error_message = None

        logger.debug("Plugin durumu guncellendi: %s -> %s", name, state.value)
        return info

    def count_total(self) -> int:
        """Toplam plugin sayisi."""
        return len(self._plugins)

    def count_enabled(self) -> int:
        """Etkin plugin sayisi."""
        return sum(
            1 for p in self._plugins.values() if p.state == PluginState.ENABLED
        )

    def count_by_state(self) -> dict[str, int]:
        """Durum bazinda plugin sayilari.

        Returns:
            {durum: sayi} sozlugu.
        """
        counts: dict[str, int] = {}
        for plugin in self._plugins.values():
            state_val = plugin.state.value
            counts[state_val] = counts.get(state_val, 0) + 1
        return counts

    def get_names(self) -> list[str]:
        """Tum plugin adlarini dondurur."""
        return list(self._plugins.keys())

    def clear(self) -> None:
        """Tum kayitlari temizler."""
        self._plugins.clear()
        logger.debug("Plugin kayit defteri temizlendi")

    def set_config_value(self, name: str, key: str, value: Any) -> bool:
        """Plugin yapilandirma degerini ayarlar.

        Args:
            name: Plugin adi.
            key: Yapilandirma anahtari.
            value: Yeni deger.

        Returns:
            Basarili ise True.
        """
        info = self._plugins.get(name)
        if info is None:
            return False
        info.config_values[key] = value
        return True

    def get_config_value(self, name: str, key: str, default: Any = None) -> Any:
        """Plugin yapilandirma degeri dondurur.

        Args:
            name: Plugin adi.
            key: Yapilandirma anahtari.
            default: Varsayilan deger.

        Returns:
            Yapilandirma degeri.
        """
        info = self._plugins.get(name)
        if info is None:
            return default
        return info.config_values.get(key, default)
