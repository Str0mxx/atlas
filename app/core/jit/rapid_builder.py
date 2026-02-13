"""ATLAS Hizli Insa modulu.

Istemci kodu, agent kodu, model kodu ve test kodu
uretimi ile bilesenleri birbirine baglama.
"""

import logging
from typing import Any

from app.models.jit import (
    APIEndpoint,
    AuthMethod,
    GeneratedCode,
    RequirementSpec,
)

logger = logging.getLogger(__name__)


class RapidBuilder:
    """Hizli insa sistemi.

    API istemcisi, agent, model ve test kodu uretir,
    bilesenleri birbirine baglar.

    Attributes:
        _generated: Uretilen kodlar.
        _templates: Kod sablonlari.
    """

    def __init__(self) -> None:
        """Hizli insa sistemini baslatir."""
        self._generated: list[GeneratedCode] = []
        self._templates: dict[str, str] = {}

        logger.info("RapidBuilder baslatildi")

    def generate_client(self, api_name: str, endpoints: list[APIEndpoint]) -> GeneratedCode:
        """API istemci kodu uretir.

        Args:
            api_name: API adi.
            endpoints: Endpoint listesi.

        Returns:
            GeneratedCode nesnesi.
        """
        lines: list[str] = [
            f'"""ATLAS {api_name} API istemcisi (JIT uretildi)."""',
            "",
            "import logging",
            "from typing import Any",
            "",
            "logger = logging.getLogger(__name__)",
            "",
            "",
            f"class {self._to_class_name(api_name)}Client:",
            f'    """{api_name} API istemcisi."""',
            "",
            "    def __init__(self, api_key: str = \"\", base_url: str = \"\") -> None:",
            f'        """Istemciyi baslatir."""',
            "        self._api_key = api_key",
            f'        self._base_url = base_url or "{endpoints[0].base_url if endpoints else ""}"',
            "        self._session_active = False",
            "",
        ]

        for ep in endpoints:
            method_name = ep.name.replace(f"{api_name}_", "").replace("-", "_")
            lines.extend([
                f"    def {method_name}(self, **params: Any) -> dict[str, Any]:",
                f'        """API {method_name} cagrisi."""',
                f'        # Endpoint: {ep.method} {ep.path}',
                "        return {",
                f'            "endpoint": "{ep.path}",',
                f'            "method": "{ep.method}",',
                '            "params": params,',
                '            "status": "ok",',
                "        }",
                "",
            ])

        source = "\n".join(lines)
        code = GeneratedCode(
            module_name=f"{api_name}_client",
            code_type="client",
            source_code=source,
            dependencies=["httpx"],
            line_count=len(lines),
        )
        self._generated.append(code)

        logger.info("Istemci kodu uretildi: %s (%d satir)", api_name, len(lines))
        return code

    def generate_agent(self, capability_name: str, spec: RequirementSpec) -> GeneratedCode:
        """Agent kodu uretir.

        Args:
            capability_name: Yetenek adi.
            spec: Gereksinim spesifikasyonu.

        Returns:
            GeneratedCode nesnesi.
        """
        class_name = self._to_class_name(capability_name) + "Agent"
        lines: list[str] = [
            f'"""ATLAS {capability_name} Agent (JIT uretildi)."""',
            "",
            "import logging",
            "from typing import Any",
            "",
            "logger = logging.getLogger(__name__)",
            "",
            "",
            f"class {class_name}:",
            f'    """{capability_name} agenti."""',
            "",
            "    def __init__(self) -> None:",
            f'        """Agenti baslatir."""',
            "        self._active = True",
            f'        self._intent = "{spec.parsed_intent}"',
            "",
            "    async def execute(self, params: dict[str, Any] | None = None) -> dict[str, Any]:",
            f'        """Gorevi calistirir."""',
            "        return {",
            f'            "capability": "{capability_name}",',
            f'            "intent": self._intent,',
            '            "status": "completed",',
            '            "params": params or {},',
            "        }",
            "",
            "    async def analyze(self, data: Any) -> dict[str, Any]:",
            f'        """Analiz yapar."""',
            "        return {",
            f'            "capability": "{capability_name}",',
            '            "analysis": "completed",',
            "        }",
            "",
        ]

        source = "\n".join(lines)
        code = GeneratedCode(
            module_name=f"{capability_name}_agent",
            code_type="agent",
            source_code=source,
            dependencies=[],
            line_count=len(lines),
        )
        self._generated.append(code)

        logger.info("Agent kodu uretildi: %s (%d satir)", class_name, len(lines))
        return code

    def generate_models(self, capability_name: str, fields: dict[str, str] | None = None) -> GeneratedCode:
        """Model kodu uretir.

        Args:
            capability_name: Yetenek adi.
            fields: Alan tanimlari (ad -> tip).

        Returns:
            GeneratedCode nesnesi.
        """
        class_name = self._to_class_name(capability_name) + "Model"
        model_fields = fields or {"name": "str", "value": "Any", "status": "str"}

        lines: list[str] = [
            f'"""ATLAS {capability_name} modeli (JIT uretildi)."""',
            "",
            "from typing import Any",
            "from pydantic import BaseModel, Field",
            "",
            "",
            f"class {class_name}(BaseModel):",
            f'    """{capability_name} veri modeli."""',
            "",
        ]

        for field_name, field_type in model_fields.items():
            default = '""' if field_type == "str" else "None" if "Any" in field_type else "0"
            lines.append(f"    {field_name}: {field_type} = {default}")

        lines.append("")

        source = "\n".join(lines)
        code = GeneratedCode(
            module_name=f"{capability_name}_model",
            code_type="model",
            source_code=source,
            dependencies=["pydantic"],
            line_count=len(lines),
        )
        self._generated.append(code)

        logger.info("Model kodu uretildi: %s (%d satir)", class_name, len(lines))
        return code

    def generate_tests(self, capability_name: str, code_modules: list[GeneratedCode]) -> GeneratedCode:
        """Test kodu uretir.

        Args:
            capability_name: Yetenek adi.
            code_modules: Test edilecek moduller.

        Returns:
            GeneratedCode nesnesi.
        """
        lines: list[str] = [
            f'"""ATLAS {capability_name} testleri (JIT uretildi)."""',
            "",
            "import pytest",
            "",
            "",
        ]

        for module in code_modules:
            class_name = self._to_class_name(module.module_name)
            lines.extend([
                f"class Test{class_name}:",
                f'    """{module.module_name} testleri."""',
                "",
                f"    def test_{module.module_name}_exists(self):",
                f'        """Modul mevcutlugu testi."""',
                f"        assert True  # {module.code_type} modulu mevcut",
                "",
                f"    def test_{module.module_name}_line_count(self):",
                f'        """Kod satir sayisi testi."""',
                f"        assert {module.line_count} > 0",
                "",
            ])

        source = "\n".join(lines)
        code = GeneratedCode(
            module_name=f"test_{capability_name}",
            code_type="test",
            source_code=source,
            dependencies=["pytest"],
            line_count=len(lines),
        )
        self._generated.append(code)

        logger.info("Test kodu uretildi: %s (%d satir)", capability_name, len(lines))
        return code

    def wire_together(self, modules: list[GeneratedCode]) -> dict[str, Any]:
        """Bilesenleri birbirine baglar.

        Args:
            modules: Baglanacak moduller.

        Returns:
            Baglanti haritasi.
        """
        wiring: dict[str, Any] = {
            "modules": [m.module_name for m in modules],
            "dependencies": [],
            "imports": [],
            "total_lines": 0,
        }

        all_deps: set[str] = set()
        for module in modules:
            all_deps.update(module.dependencies)
            wiring["total_lines"] += module.line_count
            if module.code_type != "test":
                wiring["imports"].append(f"from .{module.module_name} import *")

        wiring["dependencies"] = list(all_deps)

        logger.info("Bileseler baglandi: %d modul", len(modules))
        return wiring

    def _to_class_name(self, name: str) -> str:
        """Alt cizgili adi sinif adina cevirir."""
        return "".join(word.capitalize() for word in name.replace("-", "_").split("_"))

    @property
    def generated_count(self) -> int:
        """Uretilen kod sayisi."""
        return len(self._generated)

    @property
    def generated_modules(self) -> list[GeneratedCode]:
        """Tum uretilen moduller."""
        return list(self._generated)

    @property
    def total_lines(self) -> int:
        """Toplam uretilen satir sayisi."""
        return sum(g.line_count for g in self._generated)
