"""ATLAS yetenek olusturma modulu.

Dinamik agent, plugin, tool ve API istemci sablonlari
olusturur. Scaffold uretimi ve bagimliliklari yonetir.
"""

import logging
from typing import Any

from app.models.bootstrap import (
    CapabilityCategory,
    CapabilityTemplate,
    ScaffoldResult,
)

logger = logging.getLogger(__name__)

# Kategori bazli temel siniflar
BASE_CLASSES: dict[CapabilityCategory, str] = {
    CapabilityCategory.AGENT: "BaseAgent",
    CapabilityCategory.TOOL: "object",
    CapabilityCategory.MONITOR: "BaseMonitor",
    CapabilityCategory.API_CLIENT: "object",
    CapabilityCategory.PLUGIN: "object",
}

# Agent icin varsayilan metotlar
DEFAULT_AGENT_METHODS = ["execute", "analyze", "report"]

# Monitor icin varsayilan metotlar
DEFAULT_MONITOR_METHODS = ["check", "evaluate", "alert"]


class CapabilityBuilder:
    """Yetenek olusturucu.

    Agent, tool, monitor, plugin sablonu uretir
    ve scaffold (iskele) kodu olusturur.

    Attributes:
        templates: Mevcut sablonlar (id -> CapabilityTemplate).
    """

    def __init__(self) -> None:
        """CapabilityBuilder baslatir."""
        self.templates: dict[str, CapabilityTemplate] = {}
        logger.info("CapabilityBuilder olusturuldu")

    def create_agent_template(
        self,
        name: str,
        keywords: list[str] | None = None,
        methods: list[str] | None = None,
        description: str = "",
    ) -> CapabilityTemplate:
        """Agent sablonu olusturur.

        Args:
            name: Agent adi.
            keywords: Agent anahtar kelimeleri.
            methods: Agent metotlari. None ise varsayilan metotlar.
            description: Aciklama.

        Returns:
            Olusturulan sablon.
        """
        method_list = methods or list(DEFAULT_AGENT_METHODS)
        method_defs = [
            {"name": m, "async": True, "args": "self, task: dict[str, Any]"}
            for m in method_list
        ]

        template = CapabilityTemplate(
            name=name,
            category=CapabilityCategory.AGENT,
            description=description or f"{name} agent sablonu",
            base_class=BASE_CLASSES[CapabilityCategory.AGENT],
            methods=method_defs,
            dependencies=["app.agents.base_agent"],
        )
        if keywords:
            template.dependencies.append(f"keywords:{','.join(keywords)}")

        self.templates[template.id] = template
        logger.info("Agent sablonu olusturuldu: %s", name)
        return template

    def create_tool_template(
        self,
        name: str,
        methods: list[str] | None = None,
        dependencies: list[str] | None = None,
        description: str = "",
    ) -> CapabilityTemplate:
        """Tool sablonu olusturur.

        Args:
            name: Tool adi.
            methods: Tool metotlari.
            dependencies: Gerekli paketler.
            description: Aciklama.

        Returns:
            Olusturulan sablon.
        """
        method_list = methods or ["run", "validate"]
        method_defs = [
            {"name": m, "async": True, "args": "self, **kwargs"}
            for m in method_list
        ]

        template = CapabilityTemplate(
            name=name,
            category=CapabilityCategory.TOOL,
            description=description or f"{name} tool sablonu",
            base_class=BASE_CLASSES[CapabilityCategory.TOOL],
            methods=method_defs,
            dependencies=dependencies or [],
        )
        self.templates[template.id] = template
        logger.info("Tool sablonu olusturuldu: %s", name)
        return template

    def create_monitor_template(
        self,
        name: str,
        check_interval: int = 300,
        description: str = "",
    ) -> CapabilityTemplate:
        """Monitor sablonu olusturur.

        Args:
            name: Monitor adi.
            check_interval: Kontrol araligi (saniye).
            description: Aciklama.

        Returns:
            Olusturulan sablon.
        """
        method_defs = [
            {"name": m, "async": True, "args": "self"}
            for m in DEFAULT_MONITOR_METHODS
        ]
        method_defs[0]["args"] = "self"  # check

        template = CapabilityTemplate(
            name=name,
            category=CapabilityCategory.MONITOR,
            description=description or f"{name} monitor sablonu",
            base_class=BASE_CLASSES[CapabilityCategory.MONITOR],
            methods=method_defs,
            dependencies=["app.monitors.base_monitor"],
        )
        self.templates[template.id] = template
        logger.info("Monitor sablonu olusturuldu: %s (interval=%d)", name, check_interval)
        return template

    def create_api_client_template(
        self,
        name: str,
        base_url: str = "",
        endpoints: list[dict[str, str]] | None = None,
        description: str = "",
    ) -> CapabilityTemplate:
        """API istemci sablonu olusturur.

        Args:
            name: Istemci adi.
            base_url: API temel URL.
            endpoints: Endpoint tanimlari.
            description: Aciklama.

        Returns:
            Olusturulan sablon.
        """
        method_defs = []
        for ep in endpoints or []:
            method_defs.append({
                "name": ep.get("name", "request"),
                "async": True,
                "args": "self",
                "method": ep.get("method", "GET"),
                "path": ep.get("path", "/"),
            })

        if not method_defs:
            method_defs = [
                {"name": "get", "async": True, "args": "self, path: str"},
                {"name": "post", "async": True, "args": "self, path: str, data: dict"},
            ]

        template = CapabilityTemplate(
            name=name,
            category=CapabilityCategory.API_CLIENT,
            description=description or f"{name} API istemci sablonu",
            base_class="object",
            methods=method_defs,
            dependencies=["httpx"],
        )
        self.templates[template.id] = template
        logger.info("API istemci sablonu olusturuldu: %s", name)
        return template

    def create_plugin_scaffold(
        self,
        name: str,
        plugin_type: str = "tool",
        description: str = "",
    ) -> CapabilityTemplate:
        """Plugin iskele sablonu olusturur.

        Args:
            name: Plugin adi.
            plugin_type: Plugin tipi (agent, tool, monitor).
            description: Aciklama.

        Returns:
            Olusturulan sablon.
        """
        template = CapabilityTemplate(
            name=name,
            category=CapabilityCategory.PLUGIN,
            description=description or f"{name} plugin sablonu",
            base_class="Plugin",
            methods=[
                {"name": "on_load", "async": True, "args": "self"},
                {"name": "on_enable", "async": True, "args": "self"},
                {"name": "on_disable", "async": True, "args": "self"},
            ],
            dependencies=[],
        )
        self.templates[template.id] = template
        logger.info("Plugin sablonu olusturuldu: %s (tip=%s)", name, plugin_type)
        return template

    def generate_class_code(
        self,
        template: CapabilityTemplate,
    ) -> str:
        """Sinif kodunu uretir (string olarak).

        Args:
            template: Kaynak sablon.

        Returns:
            Python sinif kodu.
        """
        lines: list[str] = []
        class_name = "".join(
            part.capitalize() for part in template.name.split("_")
        )

        # Import
        if template.category == CapabilityCategory.AGENT:
            lines.append("from app.agents.base_agent import BaseAgent, TaskResult")
            lines.append("")
        elif template.category == CapabilityCategory.MONITOR:
            lines.append("from app.monitors.base_monitor import BaseMonitor")
            lines.append("")

        # Sinif tanimi
        base = template.base_class
        lines.append(f"class {class_name}({base}):")
        lines.append(f'    """{template.description}."""')
        lines.append("")

        # __init__
        lines.append("    def __init__(self) -> None:")
        lines.append(f'        """{{class_name}} baslatir."""')
        if template.category == CapabilityCategory.AGENT:
            lines.append(f'        super().__init__(name="{class_name}")')
        elif template.category == CapabilityCategory.MONITOR:
            lines.append(f'        super().__init__(name="{class_name}")')
        lines.append("")

        # Metotlar
        for method in template.methods:
            name = method["name"]
            is_async = method.get("async", False)
            args = method.get("args", "self")
            prefix = "async " if is_async else ""
            lines.append(f"    {prefix}def {name}({args}):")
            lines.append(f'        """{name} islemi."""')
            lines.append("        pass")
            lines.append("")

        return "\n".join(lines)

    def generate_test_code(
        self,
        template: CapabilityTemplate,
    ) -> str:
        """Test kodu uretir (string olarak).

        Args:
            template: Kaynak sablon.

        Returns:
            Python test kodu.
        """
        class_name = "".join(
            part.capitalize() for part in template.name.split("_")
        )

        lines: list[str] = [
            f'"""Test {template.name} modulu."""',
            "",
            "import pytest",
            "",
            "",
            f"class Test{class_name}Init:",
            f'    """{class_name} init testleri."""',
            "",
            "    def test_create(self) -> None:",
            f'        """Olusturma testi."""',
            "        pass",
            "",
        ]

        for method in template.methods:
            name = method["name"]
            is_async = method.get("async", False)
            prefix = "async " if is_async else ""
            lines.extend([
                f"class Test{class_name}{name.capitalize()}:",
                f'    """{name} testleri."""',
                "",
                f"    {prefix}def test_{name}_basic(self) -> None:",
                f'        """{name} temel testi."""',
                "        pass",
                "",
            ])

        return "\n".join(lines)

    def generate_manifest(
        self,
        template: CapabilityTemplate,
    ) -> dict[str, Any]:
        """Plugin manifest icerigi uretir.

        Args:
            template: Kaynak sablon.

        Returns:
            Manifest sozlugu.
        """
        class_name = "".join(
            part.capitalize() for part in template.name.split("_")
        )

        manifest: dict[str, Any] = {
            "name": template.name,
            "version": "1.0.0",
            "description": template.description,
            "type": template.category.value,
            "provides": {},
        }

        if template.category == CapabilityCategory.AGENT:
            manifest["provides"]["agents"] = [
                {
                    "class": class_name,
                    "module": template.name,
                    "keywords": [],
                }
            ]
        elif template.category == CapabilityCategory.TOOL:
            manifest["provides"]["tools"] = [
                {
                    "class": class_name,
                    "module": template.name,
                }
            ]

        return manifest

    def get_template(
        self,
        template_id: str,
    ) -> CapabilityTemplate | None:
        """Sablonu ID ile dondurur.

        Args:
            template_id: Sablon kimlik numarasi.

        Returns:
            Sablon veya None.
        """
        return self.templates.get(template_id)

    def list_templates(
        self,
        category: CapabilityCategory | None = None,
    ) -> list[CapabilityTemplate]:
        """Sablonlari listeler.

        Args:
            category: Filtreleme kategorisi. None ise tumu.

        Returns:
            Sablon listesi.
        """
        if category is None:
            return list(self.templates.values())
        return [
            t for t in self.templates.values() if t.category == category
        ]
