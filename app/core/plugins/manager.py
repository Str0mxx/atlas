"""Plugin yoneticisi (facade).

Tum plugin alt sistemlerini orkestrasyonu yapar:
PluginLoader, PluginRegistry, PluginValidator ve HookManager.
"""

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.plugins.hooks import HookManager
from app.core.plugins.loader import LoadedComponents, PluginLoader, PluginLoadError
from app.core.plugins.registry import PluginRegistry
from app.core.plugins.validator import PluginValidator
from app.models.plugin import HookEvent, PluginInfo, PluginState

logger = logging.getLogger(__name__)


class PluginManager:
    """Plugin sistemi ana yoneticisi.

    Loader, Registry, Validator ve HookManager'i birlestirerek
    plugin yasam dongusunu yonetir.

    Attributes:
        registry: Plugin kayit defteri.
        hooks: Hook olay yoneticisi.
    """

    def __init__(
        self,
        master_agent: Any = None,
        plugins_dir: str | Path | None = None,
    ) -> None:
        """PluginManager'i baslatir.

        Args:
            master_agent: MasterAgent referansi (agent kaydi icin).
            plugins_dir: Plugin dizini (None ise config'den alinir).
        """
        if plugins_dir is None:
            try:
                from app.config import settings
                plugins_dir = settings.plugins_dir
            except Exception:
                plugins_dir = "app/plugins"

        self._master_agent = master_agent
        self._plugins_dir = Path(plugins_dir)

        self.registry = PluginRegistry()
        self.hooks = HookManager()
        self._validator = PluginValidator()
        self._loader = PluginLoader(self._plugins_dir, self._validator)

        # Plugin bazinda yuklenen bilesenler (rollback icin)
        self._plugin_components: dict[str, LoadedComponents] = {}

        logger.info("PluginManager olusturuldu: %s", self._plugins_dir)

    async def initialize(self) -> int:
        """Plugin sistemini baslatir, mevcut plugin'leri kesfeder.

        Returns:
            Kesfedilen plugin sayisi.
        """
        discovered = self._loader.discover()

        for plugin_dir, manifest in discovered:
            info = PluginInfo(
                manifest=manifest,
                state=PluginState.DISCOVERED,
                plugin_dir=str(plugin_dir),
            )
            info.set_defaults()
            try:
                self.registry.register(info)
            except ValueError:
                logger.warning("Tekrar eden plugin adi: %s", manifest.name)

        count = len(discovered)
        logger.info("%d plugin kesfedildi", count)
        return count

    async def load_all(self) -> dict[str, PluginInfo]:
        """Tum kesfedilen plugin'leri yukler ve etkinlestirir.

        Returns:
            {plugin_adi: PluginInfo} sonuc sozlugu.
        """
        results: dict[str, PluginInfo] = {}
        discovered = self.registry.list_by_state(PluginState.DISCOVERED)

        # Bagimlilik sirasina gore sirala
        ordered = self._sort_by_dependencies(discovered)

        for info in ordered:
            name = info.manifest.name
            try:
                await self.load_plugin(name)
                await self.enable_plugin(name)
            except Exception as exc:
                logger.error("Plugin yuklenemedi (%s): %s", name, exc)
                self.registry.update_state(
                    name, PluginState.ERROR, str(exc)
                )
            results[name] = self.registry.get(name)  # type: ignore[assignment]

        return results

    async def load_plugin(self, name: str) -> PluginInfo:
        """Tek plugin'i yukler (modulleri import eder, dogrular).

        Args:
            name: Plugin adi.

        Returns:
            Guncellenen PluginInfo.

        Raises:
            ValueError: Plugin bulunamazsa.
            PluginLoadError: Yukleme hatasi.
        """
        info = self.registry.get(name)
        if info is None:
            raise ValueError(f"Plugin bulunamadi: '{name}'")

        plugin_dir = Path(info.plugin_dir)
        components = self._loader.load_plugin(plugin_dir, info.manifest)
        self._plugin_components[name] = components

        info.state = PluginState.LOADED
        info.load_time = datetime.now(timezone.utc)
        info.error_message = None

        logger.info("Plugin yuklendi: %s", name)
        await self.hooks.emit(HookEvent.PLUGIN_LOADED, plugin_name=name)
        return info

    async def enable_plugin(self, name: str) -> PluginInfo:
        """Plugin'i etkinlestirir, agent/monitor/hook kayitlarini yapar.

        Args:
            name: Plugin adi.

        Returns:
            Guncellenen PluginInfo.

        Raises:
            ValueError: Plugin bulunamazsa veya yuklu degilse.
        """
        info = self.registry.get(name)
        if info is None:
            raise ValueError(f"Plugin bulunamadi: '{name}'")

        if info.state not in (PluginState.LOADED, PluginState.DISABLED):
            raise ValueError(
                f"Plugin etkinlestirilemez (durum: {info.state.value}): '{name}'"
            )

        components = self._plugin_components.get(name)
        if components is None:
            raise ValueError(f"Plugin bilesenleri bulunamadi: '{name}'")

        try:
            # Agent'lari kaydet
            for agent_instance, keywords in components.agents:
                if self._master_agent is not None:
                    self._master_agent.register_agent(agent_instance)
                    if keywords:
                        self._master_agent.register_agent_keywords(
                            agent_instance.name.lower(), keywords
                        )

            # Hook'lari kaydet
            for event_str, handler, priority in components.hooks:
                try:
                    event = HookEvent(event_str)
                except ValueError:
                    logger.warning("Gecersiz hook olayi: %s", event_str)
                    continue
                self.hooks.register(event, name, handler, priority)

            info.state = PluginState.ENABLED
            info.error_message = None
            logger.info("Plugin etkinlestirildi: %s", name)
            await self.hooks.emit(HookEvent.PLUGIN_ENABLED, plugin_name=name)

        except Exception as exc:
            # Rollback: kayitlari geri al
            self._rollback_enable(name, components)
            info.state = PluginState.ERROR
            info.error_message = str(exc)
            raise

        return info

    async def disable_plugin(self, name: str) -> PluginInfo:
        """Plugin'i devre disi birakir, kayitlari geri alir.

        Args:
            name: Plugin adi.

        Returns:
            Guncellenen PluginInfo.

        Raises:
            ValueError: Plugin bulunamazsa.
        """
        info = self.registry.get(name)
        if info is None:
            raise ValueError(f"Plugin bulunamadi: '{name}'")

        components = self._plugin_components.get(name)
        if components:
            self._rollback_enable(name, components)

        info.state = PluginState.DISABLED
        info.error_message = None

        logger.info("Plugin devre disi birakildi: %s", name)
        await self.hooks.emit(HookEvent.PLUGIN_DISABLED, plugin_name=name)
        return info

    async def reload_plugin(self, name: str) -> PluginInfo:
        """Plugin'i yeniden yukler (disable -> unload -> load -> enable).

        Args:
            name: Plugin adi.

        Returns:
            Guncellenen PluginInfo.
        """
        info = self.registry.get(name)
        if info is None:
            raise ValueError(f"Plugin bulunamadi: '{name}'")

        # Devre disi birak
        if info.state == PluginState.ENABLED:
            await self.disable_plugin(name)

        # Bosalt
        self._loader.unload_plugin(name)
        self._plugin_components.pop(name, None)

        # Yeniden yukle ve etkinlestir
        info.state = PluginState.DISCOVERED
        await self.load_plugin(name)
        return await self.enable_plugin(name)

    async def shutdown(self) -> None:
        """Tum plugin'leri devre disi birakir ve temizlik yapar."""
        enabled = self.registry.list_by_state(PluginState.ENABLED)
        for info in enabled:
            try:
                await self.disable_plugin(info.manifest.name)
            except Exception as exc:
                logger.error(
                    "Plugin kapatma hatasi (%s): %s",
                    info.manifest.name,
                    exc,
                )

        # Tum modulleri temizle
        for name in list(self._plugin_components.keys()):
            self._loader.unload_plugin(name)

        self._plugin_components.clear()
        self.hooks.clear()
        logger.info("Plugin sistemi kapatildi")

    def get_plugin_config(self, plugin_name: str, key: str, default: Any = None) -> Any:
        """Plugin yapilandirma degeri dondurur.

        Args:
            plugin_name: Plugin adi.
            key: Yapilandirma anahtari.
            default: Varsayilan deger.

        Returns:
            Yapilandirma degeri.
        """
        return self.registry.get_config_value(plugin_name, key, default)

    def _rollback_enable(self, name: str, components: LoadedComponents) -> None:
        """Plugin etkinlestirme kayitlarini geri alir.

        Args:
            name: Plugin adi.
            components: Geri alinacak bilesenler.
        """
        # Agent'lari kaldir
        for agent_instance, _ in components.agents:
            if self._master_agent is not None:
                self._master_agent.unregister_agent(agent_instance.name)

        # Hook'lari kaldir
        self.hooks.unregister_plugin(name)

    def _sort_by_dependencies(
        self, plugins: list[PluginInfo]
    ) -> list[PluginInfo]:
        """Plugin'leri bagimlilik sirasina gore siralar.

        Basit topolojik siralama. Dairesel bagimliliklari atlar.

        Args:
            plugins: Siralanacak plugin listesi.

        Returns:
            Sirali plugin listesi.
        """
        name_map = {p.manifest.name: p for p in plugins}
        visited: set[str] = set()
        result: list[PluginInfo] = []

        def visit(name: str) -> None:
            if name in visited or name not in name_map:
                return
            visited.add(name)
            info = name_map[name]
            for dep in info.manifest.dependencies:
                visit(dep)
            result.append(info)

        for p in plugins:
            visit(p.manifest.name)

        return result
