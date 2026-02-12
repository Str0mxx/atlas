"""Plugin manifest yukleme ve dogrulama yardimcilari.

plugin.json dosyalarini okuyup PluginManifest modeline donusturur.
"""

import json
import logging
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from app.models.plugin import PluginManifest

logger = logging.getLogger(__name__)

MANIFEST_FILENAME = "plugin.json"


def load_manifest_from_file(path: Path) -> PluginManifest:
    """plugin.json dosyasindan manifest yukler.

    Args:
        path: plugin.json dosya yolu.

    Returns:
        PluginManifest nesnesi.

    Raises:
        FileNotFoundError: Dosya bulunamazsa.
        json.JSONDecodeError: JSON parse hatasinda.
        ValidationError: Model dogrulama hatasinda.
    """
    raw = path.read_text(encoding="utf-8")
    data = json.loads(raw)
    return _parse_manifest_data(data)


def load_manifest_from_string(raw: str) -> PluginManifest:
    """JSON string'den manifest yukler.

    Args:
        raw: JSON icerik.

    Returns:
        PluginManifest nesnesi.

    Raises:
        json.JSONDecodeError: JSON parse hatasinda.
        ValidationError: Model dogrulama hatasinda.
    """
    data = json.loads(raw)
    return _parse_manifest_data(data)


def _parse_manifest_data(data: dict[str, Any]) -> PluginManifest:
    """Ham sozlukten PluginManifest olusturur.

    plugin.json 'type' alanini 'plugin_type' olarak esler
    ve 'provides' icindeki 'class' alanlarini 'class_name' olarak esler.

    Args:
        data: Ham manifest sozlugu.

    Returns:
        PluginManifest nesnesi.
    """
    # 'type' -> 'plugin_type' esleme (Pydantic alan adi ile json farkli)
    if "type" in data and "plugin_type" not in data:
        data["plugin_type"] = data.pop("type")

    # provides icindeki 'class' -> 'class_name' esleme
    provides = data.get("provides", {})

    for agent in provides.get("agents", []):
        if "class" in agent and "class_name" not in agent:
            agent["class_name"] = agent.pop("class")

    for monitor in provides.get("monitors", []):
        if "class" in monitor and "class_name" not in monitor:
            monitor["class_name"] = monitor.pop("class")

    for tool in provides.get("tools", []):
        if "class" in tool and "class_name" not in tool:
            tool["class_name"] = tool.pop("class")

    return PluginManifest(**data)


def discover_manifests(plugins_dir: Path) -> list[tuple[Path, PluginManifest]]:
    """Plugin dizinini tarayarak manifest'leri kesfeder.

    Alt cizgi veya nokta ile baslayan dizinleri atlar.

    Args:
        plugins_dir: Plugin ana dizini.

    Returns:
        (plugin_dizin_yolu, manifest) ciftlerinin listesi.
    """
    results: list[tuple[Path, PluginManifest]] = []

    if not plugins_dir.exists():
        logger.warning("Plugin dizini bulunamadi: %s", plugins_dir)
        return results

    for child in sorted(plugins_dir.iterdir()):
        if not child.is_dir():
            continue

        # _ veya . ile baslayan dizinleri atla
        if child.name.startswith(("_", ".")):
            continue

        manifest_file = child / MANIFEST_FILENAME
        if not manifest_file.exists():
            logger.debug("Manifest bulunamadi: %s", manifest_file)
            continue

        try:
            manifest = load_manifest_from_file(manifest_file)
            results.append((child, manifest))
            logger.debug("Manifest kesfedildi: %s (%s)", manifest.name, child)
        except (json.JSONDecodeError, ValidationError, OSError) as exc:
            logger.warning(
                "Manifest okunamadi (%s): %s", manifest_file, exc
            )

    return results
