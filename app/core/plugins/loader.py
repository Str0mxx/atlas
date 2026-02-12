"""Plugin yukleme modulu.

Plugin'leri dosya sistemininden kesfeder, modul olarak import eder
ve sinif orneklerini olusturur.
"""

import importlib
import importlib.util
import logging
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

from app.core.plugins.manifest import discover_manifests
from app.core.plugins.validator import PluginValidator
from app.models.plugin import (
    AgentProvision,
    HookProvision,
    MonitorProvision,
    PluginManifest,
    PluginProvides,
    ToolProvision,
)

logger = logging.getLogger(__name__)


class PluginLoadError(Exception):
    """Plugin yukleme hatasi."""

    pass


class LoadedComponents:
    """Yuklenen plugin bilesenleri.

    Attributes:
        agents: (agent_instance, keywords) listesi.
        monitors: (monitor_class, check_interval) listesi.
        tools: tool_instance listesi.
        hooks: (HookEvent_str, async_handler, priority) listesi.
    """

    def __init__(self) -> None:
        """LoadedComponents'i baslatir."""
        self.agents: list[tuple[Any, list[str]]] = []
        self.monitors: list[tuple[type, int]] = []
        self.tools: list[Any] = []
        self.hooks: list[tuple[str, Any, int]] = []


class PluginLoader:
    """Plugin yukleyici.

    Dizin tarama, manifest okuma, Python modulu import etme
    ve sinif dogrulama islemlerini yonetir.

    Attributes:
        _plugins_dir: Plugin ana dizini.
        _validator: Plugin dogrulayici.
        _loaded_modules: Yuklenen modul referanslari.
    """

    def __init__(
        self,
        plugins_dir: str | Path,
        validator: PluginValidator | None = None,
    ) -> None:
        """PluginLoader'i baslatir.

        Args:
            plugins_dir: Plugin ana dizini.
            validator: Plugin dogrulayici (None ise yeni olusturur).
        """
        self._plugins_dir = Path(plugins_dir)
        self._validator = validator or PluginValidator()
        self._loaded_modules: dict[str, list[ModuleType]] = {}

        logger.info("PluginLoader olusturuldu: %s", self._plugins_dir)

    def discover(self) -> list[tuple[Path, PluginManifest]]:
        """Plugin dizinini tarar ve manifest'leri kesfeder.

        Returns:
            (plugin_dizin_yolu, manifest) ciftlerinin listesi.
        """
        return discover_manifests(self._plugins_dir)

    def load_plugin(
        self,
        plugin_dir: Path,
        manifest: PluginManifest,
    ) -> LoadedComponents:
        """Plugin'i yukler: modulleri import eder, sinif orneklerini olusturur.

        Args:
            plugin_dir: Plugin dizin yolu.
            manifest: Plugin manifest verisi.

        Returns:
            Yuklenen bilesenler.

        Raises:
            PluginLoadError: Yukleme hatasi.
        """
        # Manifest dogrula
        manifest_errors = self._validator.validate_manifest(manifest)
        if manifest_errors:
            raise PluginLoadError(
                f"Manifest dogrulama hatasi ({manifest.name}): "
                + "; ".join(manifest_errors)
            )

        components = LoadedComponents()
        modules: list[ModuleType] = []

        try:
            # Agent'lari yukle
            for agent_prov in manifest.provides.agents:
                mod = self._import_module(plugin_dir, manifest.name, agent_prov.module)
                modules.append(mod)
                agent_cls = self._get_class(mod, agent_prov.class_name)

                errors = self._validator.validate_agent_class(agent_cls)
                if errors:
                    raise PluginLoadError(
                        f"Agent dogrulama hatasi ({agent_prov.class_name}): "
                        + "; ".join(errors)
                    )

                instance = agent_cls()
                components.agents.append((instance, agent_prov.keywords))

            # Monitor'lari yukle
            for mon_prov in manifest.provides.monitors:
                mod = self._import_module(plugin_dir, manifest.name, mon_prov.module)
                modules.append(mod)
                monitor_cls = self._get_class(mod, mon_prov.class_name)

                errors = self._validator.validate_monitor_class(monitor_cls)
                if errors:
                    raise PluginLoadError(
                        f"Monitor dogrulama hatasi ({mon_prov.class_name}): "
                        + "; ".join(errors)
                    )

                components.monitors.append((monitor_cls, mon_prov.check_interval))

            # Tool'lari yukle
            for tool_prov in manifest.provides.tools:
                mod = self._import_module(plugin_dir, manifest.name, tool_prov.module)
                modules.append(mod)
                tool_cls = self._get_class(mod, tool_prov.class_name)

                errors = self._validator.validate_tool_class(tool_cls)
                if errors:
                    raise PluginLoadError(
                        f"Tool dogrulama hatasi ({tool_prov.class_name}): "
                        + "; ".join(errors)
                    )

                instance = tool_cls()
                components.tools.append(instance)

            # Hook handler'lari yukle
            for hook_prov in manifest.provides.hooks:
                handler = self._resolve_handler(
                    plugin_dir, manifest.name, hook_prov.handler
                )

                errors = self._validator.validate_hook_handler(handler)
                if errors:
                    raise PluginLoadError(
                        f"Hook handler dogrulama hatasi ({hook_prov.handler}): "
                        + "; ".join(errors)
                    )

                components.hooks.append(
                    (hook_prov.event, handler, hook_prov.priority)
                )

        except PluginLoadError:
            raise
        except Exception as exc:
            raise PluginLoadError(
                f"Plugin yukleme hatasi ({manifest.name}): {exc}"
            ) from exc

        self._loaded_modules[manifest.name] = modules
        logger.info(
            "Plugin yuklendi: %s (agents=%d, monitors=%d, tools=%d, hooks=%d)",
            manifest.name,
            len(components.agents),
            len(components.monitors),
            len(components.tools),
            len(components.hooks),
        )
        return components

    def unload_plugin(self, plugin_name: str) -> None:
        """Plugin modullerini hafizadan temizler.

        Args:
            plugin_name: Plugin adi.
        """
        modules = self._loaded_modules.pop(plugin_name, [])
        for mod in modules:
            mod_name = getattr(mod, "__name__", None)
            if mod_name and mod_name in sys.modules:
                del sys.modules[mod_name]

        logger.debug("Plugin modulleri temizlendi: %s", plugin_name)

    def _import_module(
        self, plugin_dir: Path, plugin_name: str, module_name: str
    ) -> ModuleType:
        """Plugin modulunu import eder.

        Args:
            plugin_dir: Plugin dizin yolu.
            plugin_name: Plugin adi.
            module_name: Modul dosya adi (uzantisiz).

        Returns:
            Import edilen modul.

        Raises:
            PluginLoadError: Import hatasi.
        """
        module_file = plugin_dir / f"{module_name}.py"
        if not module_file.exists():
            raise PluginLoadError(
                f"Modul dosyasi bulunamadi: {module_file}"
            )

        full_module_name = f"atlas_plugin_{plugin_name}_{module_name}"

        spec = importlib.util.spec_from_file_location(
            full_module_name, str(module_file)
        )
        if spec is None or spec.loader is None:
            raise PluginLoadError(
                f"Modul spec olusturulamadi: {module_file}"
            )

        module = importlib.util.module_from_spec(spec)
        sys.modules[full_module_name] = module

        try:
            spec.loader.exec_module(module)
        except Exception as exc:
            del sys.modules[full_module_name]
            raise PluginLoadError(
                f"Modul import hatasi ({module_file}): {exc}"
            ) from exc

        return module

    def _get_class(self, module: ModuleType, class_name: str) -> type:
        """Modulden sinif alir.

        Args:
            module: Python modulu.
            class_name: Sinif adi.

        Returns:
            Sinif referansi.

        Raises:
            PluginLoadError: Sinif bulunamazsa.
        """
        cls = getattr(module, class_name, None)
        if cls is None:
            raise PluginLoadError(
                f"Sinif bulunamadi: '{class_name}' modulde '{module.__name__}'"
            )
        return cls

    def _resolve_handler(
        self, plugin_dir: Path, plugin_name: str, dotted_path: str
    ) -> Any:
        """Dotted path'ten hook handler cozumler.

        Ornek: 'hooks.on_task_completed' -> hooks.py'deki on_task_completed fonksiyonu.

        Args:
            plugin_dir: Plugin dizin yolu.
            plugin_name: Plugin adi.
            dotted_path: 'modul.fonksiyon' formati.

        Returns:
            Handler fonksiyonu.

        Raises:
            PluginLoadError: Handler cozumlenemezse.
        """
        parts = dotted_path.rsplit(".", 1)
        if len(parts) != 2:
            raise PluginLoadError(
                f"Gecersiz handler yolu: '{dotted_path}' "
                "(modul.fonksiyon formati bekleniyor)"
            )

        module_name, func_name = parts
        mod = self._import_module(plugin_dir, plugin_name, module_name)
        handler = getattr(mod, func_name, None)
        if handler is None:
            raise PluginLoadError(
                f"Handler bulunamadi: '{func_name}' modulde '{module_name}'"
            )

        return handler

    @property
    def loaded_plugin_names(self) -> list[str]:
        """Yuklenen plugin adlari."""
        return list(self._loaded_modules.keys())
