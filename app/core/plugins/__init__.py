"""ATLAS Plugin sistemi.

Plugin kesfi, yukleme, dogrulama, kayit ve hook
yonetimi alt modulleri.
"""

from app.core.plugins.hooks import HookManager
from app.core.plugins.loader import LoadedComponents, PluginLoader, PluginLoadError
from app.core.plugins.manager import PluginManager
from app.core.plugins.manifest import (
    discover_manifests,
    load_manifest_from_file,
    load_manifest_from_string,
)
from app.core.plugins.registry import PluginRegistry
from app.core.plugins.validator import PluginValidator

__all__ = [
    "HookManager",
    "LoadedComponents",
    "PluginLoadError",
    "PluginLoader",
    "PluginManager",
    "PluginRegistry",
    "PluginValidator",
    "discover_manifests",
    "load_manifest_from_file",
    "load_manifest_from_string",
]
