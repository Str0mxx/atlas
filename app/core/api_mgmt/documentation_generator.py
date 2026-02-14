"""ATLAS API Dokumantasyon Ureticisi modulu.

OpenAPI/Swagger uretimi, otomatik
dokumantasyon, ornek uretimi,
playground ve export formatlari.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class DocumentationGenerator:
    """API dokumantasyon ureticisi.

    API dokumantasyonunu otomatik
    olusturur ve yonetir.

    Attributes:
        _specs: OpenAPI spesifikasyonlari.
        _examples: Ornek istek/yanitlar.
    """

    def __init__(
        self,
        title: str = "ATLAS API",
        version: str = "1.0.0",
    ) -> None:
        """Dokumantasyon ureticisini baslatir.

        Args:
            title: API basligi.
            version: API surumu.
        """
        self._title = title
        self._version = version
        self._endpoints: dict[
            str, dict[str, Any]
        ] = {}
        self._schemas: dict[
            str, dict[str, Any]
        ] = {}
        self._examples: dict[
            str, list[dict[str, Any]]
        ] = {}
        self._tags: dict[str, str] = {}

        logger.info(
            "DocumentationGenerator baslatildi",
        )

    def add_endpoint(
        self,
        path: str,
        method: str = "GET",
        summary: str = "",
        description: str = "",
        parameters: list[dict[str, Any]] | None = None,
        responses: dict[str, Any] | None = None,
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        """Endpoint dokumantasyonu ekler.

        Args:
            path: Endpoint yolu.
            method: HTTP metodu.
            summary: Ozet.
            description: Aciklama.
            parameters: Parametreler.
            responses: Yanitlar.
            tags: Etiketler.

        Returns:
            Endpoint bilgisi.
        """
        key = f"{method.upper()}:{path}"
        doc = {
            "path": path,
            "method": method.upper(),
            "summary": summary,
            "description": description,
            "parameters": parameters or [],
            "responses": responses or {},
            "tags": tags or [],
            "added_at": time.time(),
        }
        self._endpoints[key] = doc
        return doc

    def add_schema(
        self,
        name: str,
        properties: dict[str, Any],
        required: list[str] | None = None,
        description: str = "",
    ) -> dict[str, Any]:
        """Sema ekler.

        Args:
            name: Sema adi.
            properties: Ozellikler.
            required: Zorunlu alanlar.
            description: Aciklama.

        Returns:
            Sema bilgisi.
        """
        schema = {
            "name": name,
            "type": "object",
            "properties": properties,
            "required": required or [],
            "description": description,
        }
        self._schemas[name] = schema
        return schema

    def add_example(
        self,
        endpoint_key: str,
        request: dict[str, Any] | None = None,
        response: dict[str, Any] | None = None,
        description: str = "",
    ) -> dict[str, Any]:
        """Ornek ekler.

        Args:
            endpoint_key: Endpoint anahtari.
            request: Ornek istek.
            response: Ornek yanit.
            description: Aciklama.

        Returns:
            Ornek bilgisi.
        """
        example = {
            "request": request or {},
            "response": response or {},
            "description": description,
        }
        if endpoint_key not in self._examples:
            self._examples[endpoint_key] = []
        self._examples[endpoint_key].append(
            example,
        )
        return example

    def add_tag(
        self,
        name: str,
        description: str = "",
    ) -> None:
        """Etiket ekler.

        Args:
            name: Etiket adi.
            description: Aciklama.
        """
        self._tags[name] = description

    def generate_openapi(
        self,
    ) -> dict[str, Any]:
        """OpenAPI spesifikasyonu uretir.

        Returns:
            OpenAPI 3.0 spesifikasyonu.
        """
        paths: dict[str, Any] = {}
        for doc in self._endpoints.values():
            path = doc["path"]
            method = doc["method"].lower()

            if path not in paths:
                paths[path] = {}

            operation: dict[str, Any] = {
                "summary": doc["summary"],
                "description": doc["description"],
            }

            if doc["parameters"]:
                operation["parameters"] = doc[
                    "parameters"
                ]

            if doc["responses"]:
                operation["responses"] = doc[
                    "responses"
                ]
            else:
                operation["responses"] = {
                    "200": {
                        "description": "Basarili",
                    },
                }

            if doc["tags"]:
                operation["tags"] = doc["tags"]

            paths[path][method] = operation

        # Schemas
        components: dict[str, Any] = {}
        if self._schemas:
            components["schemas"] = {
                name: {
                    "type": s["type"],
                    "properties": s["properties"],
                    "required": s["required"],
                }
                for name, s in self._schemas.items()
            }

        spec: dict[str, Any] = {
            "openapi": "3.0.0",
            "info": {
                "title": self._title,
                "version": self._version,
            },
            "paths": paths,
        }

        if components:
            spec["components"] = components

        if self._tags:
            spec["tags"] = [
                {"name": n, "description": d}
                for n, d in self._tags.items()
            ]

        return spec

    def generate_markdown(
        self,
    ) -> str:
        """Markdown dokumantasyonu uretir.

        Returns:
            Markdown metni.
        """
        lines = [
            f"# {self._title}",
            f"\nVersion: {self._version}\n",
        ]

        if self._tags:
            lines.append("## Tags\n")
            for name, desc in self._tags.items():
                lines.append(f"- **{name}**: {desc}")
            lines.append("")

        lines.append("## Endpoints\n")
        for doc in self._endpoints.values():
            lines.append(
                f"### {doc['method']} {doc['path']}",
            )
            if doc["summary"]:
                lines.append(f"\n{doc['summary']}\n")
            if doc["description"]:
                lines.append(doc["description"])
            if doc["parameters"]:
                lines.append("\n**Parameters:**\n")
                for p in doc["parameters"]:
                    name = p.get("name", "")
                    ptype = p.get("type", "string")
                    lines.append(
                        f"- `{name}` ({ptype})",
                    )
            lines.append("")

        if self._schemas:
            lines.append("## Schemas\n")
            for name, s in self._schemas.items():
                lines.append(f"### {name}\n")
                if s["description"]:
                    lines.append(s["description"])
                for pname, pinfo in s[
                    "properties"
                ].items():
                    ptype = pinfo.get(
                        "type", "string",
                    )
                    lines.append(
                        f"- `{pname}` ({ptype})",
                    )
                lines.append("")

        return "\n".join(lines)

    def get_playground_config(
        self,
        endpoint_key: str,
    ) -> dict[str, Any]:
        """Playground yapisi dondurur.

        Args:
            endpoint_key: Endpoint anahtari.

        Returns:
            Playground yapisi.
        """
        doc = self._endpoints.get(endpoint_key)
        if not doc:
            return {"found": False}

        examples = self._examples.get(
            endpoint_key, [],
        )
        return {
            "found": True,
            "endpoint": doc,
            "examples": examples,
            "try_it": True,
        }

    def search_endpoints(
        self,
        query: str,
    ) -> list[dict[str, Any]]:
        """Endpoint arar.

        Args:
            query: Arama sorgusu.

        Returns:
            Eslesen endpointler.
        """
        query_lower = query.lower()
        results = []
        for doc in self._endpoints.values():
            if (
                query_lower in doc["path"].lower()
                or query_lower
                in doc["summary"].lower()
                or query_lower
                in doc["description"].lower()
            ):
                results.append(doc)
        return results

    def get_endpoint(
        self,
        key: str,
    ) -> dict[str, Any] | None:
        """Endpoint bilgisi getirir.

        Args:
            key: Endpoint anahtari.

        Returns:
            Endpoint bilgisi veya None.
        """
        return self._endpoints.get(key)

    @property
    def endpoint_count(self) -> int:
        """Endpoint sayisi."""
        return len(self._endpoints)

    @property
    def schema_count(self) -> int:
        """Sema sayisi."""
        return len(self._schemas)

    @property
    def example_count(self) -> int:
        """Ornek sayisi."""
        return sum(
            len(v) for v in self._examples.values()
        )

    @property
    def tag_count(self) -> int:
        """Etiket sayisi."""
        return len(self._tags)
