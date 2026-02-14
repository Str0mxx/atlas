"""ATLAS Arac Adaptoru modulu.

CLI arac sarmalama, kutuphane sarmalama,
REST API sarmalama, fonksiyon cikarma ve dokumantasyon ayrıstirma.
"""

import logging
import re
from typing import Any

from app.models.github_integrator import (
    RepoAnalysis,
    WrapperConfig,
    WrapperType,
)

logger = logging.getLogger(__name__)


class ToolAdapter:
    """Arac adaptor sistemi.

    Harici araclari (CLI, library, API) ATLAS
    ile uyumlu hale getirir.

    Attributes:
        _adapters: Adaptor kayitlari.
    """

    def __init__(self) -> None:
        """Arac adaptorunu baslatir."""
        self._adapters: dict[str, dict[str, Any]] = {}
        logger.info("ToolAdapter baslatildi")

    def wrap_cli(
        self,
        tool_name: str,
        command: str,
        arguments: list[str] | None = None,
        description: str = "",
    ) -> dict[str, Any]:
        """CLI aracini sarmalar.

        Args:
            tool_name: Arac adi.
            command: Temel komut.
            arguments: Komut argumanlari.
            description: Aciklama.

        Returns:
            Adaptor konfigurasyonu.
        """
        adapter = {
            "name": tool_name,
            "type": WrapperType.CLI.value,
            "command": command,
            "arguments": arguments or [],
            "description": description,
            "invoke_template": self._generate_cli_template(command, arguments),
            "parse_output": "text",
        }

        self._adapters[tool_name] = adapter
        return adapter

    def wrap_library(
        self,
        tool_name: str,
        module_path: str,
        functions: list[str] | None = None,
        description: str = "",
    ) -> dict[str, Any]:
        """Kutuphaneyı sarmalar.

        Args:
            tool_name: Arac adi.
            module_path: Modul yolu.
            functions: Fonksiyon listesi.
            description: Aciklama.

        Returns:
            Adaptor konfigurasyonu.
        """
        adapter = {
            "name": tool_name,
            "type": WrapperType.LIBRARY.value,
            "module_path": module_path,
            "functions": functions or [],
            "description": description,
            "import_statement": f"from {module_path} import {', '.join(functions or ['*'])}",
        }

        self._adapters[tool_name] = adapter
        return adapter

    def wrap_api(
        self,
        tool_name: str,
        base_url: str,
        endpoints: list[dict[str, str]] | None = None,
        auth_type: str = "none",
        description: str = "",
    ) -> dict[str, Any]:
        """REST API'yi sarmalar.

        Args:
            tool_name: Arac adi.
            base_url: Temel URL.
            endpoints: Endpoint listesi.
            auth_type: Kimlik dogrulama tipi.
            description: Aciklama.

        Returns:
            Adaptor konfigurasyonu.
        """
        adapter = {
            "name": tool_name,
            "type": WrapperType.API.value,
            "base_url": base_url,
            "endpoints": endpoints or [],
            "auth_type": auth_type,
            "description": description,
            "client_config": {
                "timeout": 30,
                "retries": 3,
                "headers": {"Content-Type": "application/json"},
            },
        }

        self._adapters[tool_name] = adapter
        return adapter

    def extract_functions(self, source_code: str) -> list[dict[str, Any]]:
        """Kaynak koddan fonksiyonlari cikarir.

        Args:
            source_code: Kaynak kod.

        Returns:
            Fonksiyon bilgisi listesi.
        """
        functions: list[dict[str, Any]] = []

        # Python fonksiyon pattern
        pattern = r'(?:async\s+)?def\s+(\w+)\s*\(([^)]*)\)(?:\s*->\s*([^:]+))?\s*:'
        matches = re.finditer(pattern, source_code)

        for match in matches:
            name = match.group(1)
            params_str = match.group(2)
            return_type = match.group(3)

            if name.startswith("_"):
                continue

            params = self._parse_params(params_str)

            # Docstring cikar
            pos = match.end()
            docstring = self._extract_docstring(source_code[pos:])

            functions.append({
                "name": name,
                "params": params,
                "return_type": return_type.strip() if return_type else "None",
                "is_async": "async" in match.group(0),
                "docstring": docstring,
            })

        return functions

    def parse_documentation(self, doc_text: str) -> dict[str, Any]:
        """Dokumantasyonu ayrıstirir.

        Args:
            doc_text: Dokumantasyon metni.

        Returns:
            Ayristirilmis bilgi.
        """
        sections: dict[str, str] = {}
        current_section = "overview"
        current_content: list[str] = []

        for line in doc_text.split("\n"):
            # Baslik tespiti
            if line.startswith("# ") or line.startswith("## "):
                if current_content:
                    sections[current_section] = "\n".join(current_content).strip()
                current_section = line.lstrip("#").strip().lower().replace(" ", "_")
                current_content = []
            else:
                current_content.append(line)

        if current_content:
            sections[current_section] = "\n".join(current_content).strip()

        # Kod orneklerini cikar
        code_examples = re.findall(r'```(?:\w+)?\n(.*?)```', doc_text, re.DOTALL)

        return {
            "sections": sections,
            "code_examples": code_examples,
            "has_installation": "install" in doc_text.lower(),
            "has_usage": "usage" in doc_text.lower() or "example" in doc_text.lower(),
            "has_api_docs": "api" in doc_text.lower(),
        }

    def get_adapter(self, tool_name: str) -> dict[str, Any] | None:
        """Adaptoru getirir.

        Args:
            tool_name: Arac adi.

        Returns:
            Adaptor konfigurasyonu veya None.
        """
        return self._adapters.get(tool_name)

    def list_adapters(self) -> list[dict[str, Any]]:
        """Tum adaptorleri listeler.

        Returns:
            Adaptor listesi.
        """
        return list(self._adapters.values())

    def remove_adapter(self, tool_name: str) -> bool:
        """Adaptoru siler.

        Args:
            tool_name: Arac adi.

        Returns:
            Basarili ise True.
        """
        if tool_name in self._adapters:
            del self._adapters[tool_name]
            return True
        return False

    def _generate_cli_template(
        self, command: str, arguments: list[str] | None
    ) -> str:
        """CLI calistirma sablonu olusturur."""
        parts = [command]
        if arguments:
            for arg in arguments:
                parts.append(f"{{{arg}}}")
        return " ".join(parts)

    def _parse_params(self, params_str: str) -> list[dict[str, str]]:
        """Parametre string'ini ayrıstirir."""
        params: list[dict[str, str]] = []
        if not params_str.strip():
            return params

        for param in params_str.split(","):
            param = param.strip()
            if not param or param == "self" or param == "cls":
                continue

            if ":" in param:
                name, type_hint = param.split(":", 1)
                # Default deger varsa ayır
                if "=" in type_hint:
                    type_hint = type_hint.split("=")[0]
                params.append({
                    "name": name.strip(),
                    "type": type_hint.strip(),
                })
            else:
                name = param.split("=")[0].strip()
                params.append({"name": name, "type": "Any"})

        return params

    def _extract_docstring(self, code_after_def: str) -> str:
        """Docstring cikarir."""
        stripped = code_after_def.lstrip()
        if stripped.startswith('"""'):
            end = stripped.find('"""', 3)
            if end > 0:
                return stripped[3:end].strip()
        if stripped.startswith("'''"):
            end = stripped.find("'''", 3)
            if end > 0:
                return stripped[3:end].strip()
        return ""

    @property
    def adapter_count(self) -> int:
        """Adaptor sayisi."""
        return len(self._adapters)
