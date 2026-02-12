"""Plugin dogrulama modulu.

Plugin'lerin gerekli arayuzleri dogru implement edip etmedigini,
yapilandirma anahtarlarinin cakisip cakismadigini kontrol eder.
"""

import inspect
import logging
from typing import Any

from app.models.plugin import HookEvent, PluginManifest

logger = logging.getLogger(__name__)


class PluginValidator:
    """Plugin dogrulayici.

    Agent, monitor ve tool siniflarinin gerekli interface'leri
    implement edip etmedigini kontrol eder.
    """

    def validate_manifest(self, manifest: PluginManifest) -> list[str]:
        """Manifest yapisal dogrulamasi.

        Args:
            manifest: Dogrulanacak manifest.

        Returns:
            Hata mesajlari listesi (bos = gecerli).
        """
        errors: list[str] = []

        if not manifest.name or not manifest.name.strip():
            errors.append("Plugin adi bos olamaz")

        if not manifest.version or not manifest.version.strip():
            errors.append("Plugin surumu bos olamaz")

        # Manifest adi sadece alfanumerik, tire ve alt cizgi icermeli
        if manifest.name and not all(
            c.isalnum() or c in "-_" for c in manifest.name
        ):
            errors.append(
                f"Gecersiz plugin adi: '{manifest.name}' "
                "(sadece harf, rakam, tire ve alt cizgi)"
            )

        # Hook olaylari gecerli olmali
        valid_events = {e.value for e in HookEvent}
        for hook in manifest.provides.hooks:
            if hook.event not in valid_events:
                errors.append(f"Gecersiz hook olayi: '{hook.event}'")

        # Handler dotted path formati kontrolu
        for hook in manifest.provides.hooks:
            if "." not in hook.handler:
                errors.append(
                    f"Gecersiz handler yolu: '{hook.handler}' "
                    "(modul.fonksiyon formati bekleniyor)"
                )

        return errors

    def validate_agent_class(self, agent_cls: type) -> list[str]:
        """Agent sinifinin BaseAgent interface'ini implement edip etmedigini kontrol eder.

        Args:
            agent_cls: Dogrulanacak sinif.

        Returns:
            Hata mesajlari listesi.
        """
        errors: list[str] = []
        cls_name = getattr(agent_cls, "__name__", str(agent_cls))

        # BaseAgent'dan miras kontrolu
        from app.agents.base_agent import BaseAgent

        if not (isinstance(agent_cls, type) and issubclass(agent_cls, BaseAgent)):
            errors.append(f"'{cls_name}' BaseAgent'dan miras almiyor")
            return errors

        # Soyut metotlarin implement edilip edilmedigini kontrol et
        required_methods = ["execute", "analyze", "report"]
        for method_name in required_methods:
            method = getattr(agent_cls, method_name, None)
            if method is None:
                errors.append(f"'{cls_name}' '{method_name}' metodunu tanimlamiyor")
            elif getattr(method, "__isabstractmethod__", False):
                errors.append(f"'{cls_name}' '{method_name}' metodu hala soyut")
            elif not inspect.iscoroutinefunction(method):
                errors.append(
                    f"'{cls_name}.{method_name}' async olmali"
                )

        return errors

    def validate_monitor_class(self, monitor_cls: type) -> list[str]:
        """Monitor sinifinin BaseMonitor interface'ini implement edip etmedigini kontrol eder.

        Args:
            monitor_cls: Dogrulanacak sinif.

        Returns:
            Hata mesajlari listesi.
        """
        errors: list[str] = []
        cls_name = getattr(monitor_cls, "__name__", str(monitor_cls))

        from app.monitors.base_monitor import BaseMonitor

        if not (isinstance(monitor_cls, type) and issubclass(monitor_cls, BaseMonitor)):
            errors.append(f"'{cls_name}' BaseMonitor'dan miras almiyor")
            return errors

        check_method = getattr(monitor_cls, "check", None)
        if check_method is None:
            errors.append(f"'{cls_name}' 'check' metodunu tanimlamiyor")
        elif getattr(check_method, "__isabstractmethod__", False):
            errors.append(f"'{cls_name}' 'check' metodu hala soyut")
        elif not inspect.iscoroutinefunction(check_method):
            errors.append(f"'{cls_name}.check' async olmali")

        return errors

    def validate_tool_class(self, tool_cls: type) -> list[str]:
        """Tool sinifinin gecerli olup olmadigini kontrol eder.

        Tool'lar icin sabit bir base class yok, sadece sinif olmasi yeterli.

        Args:
            tool_cls: Dogrulanacak sinif.

        Returns:
            Hata mesajlari listesi.
        """
        errors: list[str] = []
        cls_name = getattr(tool_cls, "__name__", str(tool_cls))

        if not isinstance(tool_cls, type):
            errors.append(f"'{cls_name}' bir sinif degil")

        return errors

    def validate_config_keys(
        self,
        plugin_name: str,
        config: dict[str, Any],
        existing_keys: set[str],
    ) -> list[str]:
        """Plugin config anahtarlarinin mevcut ayarlarla cakisip cakismadigini kontrol eder.

        Args:
            plugin_name: Plugin adi.
            config: Plugin yapilandirma alanlari.
            existing_keys: Mevcut yapilandirma anahtar kumeleri.

        Returns:
            Hata mesajlari listesi.
        """
        errors: list[str] = []
        for key in config:
            if key in existing_keys:
                errors.append(
                    f"Config anahtari cakismasi: '{key}' zaten kullaniliyor "
                    f"(plugin: {plugin_name})"
                )
        return errors

    def validate_hook_handler(self, handler: Any) -> list[str]:
        """Hook handler fonksiyonunun gecerli olup olmadigini kontrol eder.

        Args:
            handler: Dogrulanacak handler.

        Returns:
            Hata mesajlari listesi.
        """
        errors: list[str] = []

        if not callable(handler):
            errors.append("Hook handler callable degil")
            return errors

        if not inspect.iscoroutinefunction(handler):
            errors.append("Hook handler async olmali")

        return errors
