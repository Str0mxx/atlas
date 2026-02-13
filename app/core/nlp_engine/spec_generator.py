"""ATLAS Spesifikasyon Uretici modulu.

Dogal dilden teknik spesifikasyon, API tasarimi,
veri modeli tasarimi, mimari onerileri ve dokumantasyon.
"""

import logging
from typing import Any

from app.models.nlp_engine import (
    RequirementSet,
    SpecSection,
    SpecSectionType,
    TechnicalSpec,
)

logger = logging.getLogger(__name__)


class SpecGenerator:
    """Spesifikasyon uretici.

    Dogal dil gereksinimlerinden teknik spesifikasyon,
    API tasarimi, veri modeli ve mimari onerileri uretir.

    Attributes:
        _specs: Uretilen spesifikasyonlar (id -> TechnicalSpec).
    """

    def __init__(self) -> None:
        """Spesifikasyon ureticiyi baslatir."""
        self._specs: dict[str, TechnicalSpec] = {}

        logger.info("SpecGenerator baslatildi")

    def generate(self, title: str, requirements: RequirementSet | None = None, description: str = "") -> TechnicalSpec:
        """Teknik spesifikasyon uretir.

        Gereksinimlerden veya serbest metinden teknik
        spesifikasyon olusturur.

        Args:
            title: Spesifikasyon basligi.
            requirements: Gereksinim seti.
            description: Serbest metin aciklama.

        Returns:
            TechnicalSpec nesnesi.
        """
        sections: list[SpecSection] = []

        # Genel bakis
        overview_content = description or (
            f"{title} icin teknik spesifikasyon. "
            f"{len(requirements.requirements) if requirements else 0} gereksinim tanimlanmistir."
        )
        sections.append(SpecSection(
            section_type=SpecSectionType.OVERVIEW,
            title="Genel Bakis",
            content=overview_content,
        ))

        # Gereksinimlerden bolumler olustur
        if requirements:
            for req in requirements.requirements:
                section_type = self._map_requirement_to_section(req.requirement_type.value)
                sections.append(SpecSection(
                    section_type=section_type,
                    title=req.description[:60],
                    content=req.description,
                    subsections=[{"criteria": c} for c in req.acceptance_criteria],
                ))

        spec = TechnicalSpec(
            title=title,
            sections=sections,
        )
        self._specs[spec.id] = spec

        logger.info("Spesifikasyon uretildi: %s (%d bolum)", title, len(sections))
        return spec

    def design_api(self, spec_id: str, resource_name: str, operations: list[str] | None = None) -> list[dict[str, Any]]:
        """API tasarimi yapar.

        RESTful endpoint tanimlari olusturur.

        Args:
            spec_id: Spesifikasyon ID.
            resource_name: Kaynak adi.
            operations: Islem listesi (None ise CRUD).

        Returns:
            API endpoint tanimlari. Spesifikasyon bulunamazsa bos liste.
        """
        spec = self._specs.get(spec_id)
        if not spec:
            return []

        ops = operations or ["list", "get", "create", "update", "delete"]

        _OP_MAP: dict[str, tuple[str, str]] = {
            "list": ("GET", f"/{resource_name}"),
            "get": ("GET", f"/{resource_name}/{{id}}"),
            "create": ("POST", f"/{resource_name}"),
            "update": ("PUT", f"/{resource_name}/{{id}}"),
            "delete": ("DELETE", f"/{resource_name}/{{id}}"),
        }

        endpoints: list[dict[str, Any]] = []
        for op in ops:
            if op in _OP_MAP:
                method, path = _OP_MAP[op]
                endpoints.append({
                    "method": method,
                    "path": path,
                    "operation": op,
                    "description": f"{resource_name} {op} islemi",
                })

        spec.api_endpoints.extend(endpoints)
        logger.info("API tasarimi: %s -> %d endpoint", resource_name, len(endpoints))
        return endpoints

    def design_data_model(self, spec_id: str, model_name: str, fields: list[dict[str, str]]) -> dict[str, Any]:
        """Veri modeli tasarimi yapar.

        Args:
            spec_id: Spesifikasyon ID.
            model_name: Model adi.
            fields: Alan tanimlari (name, type, description).

        Returns:
            Model tanimi. Spesifikasyon bulunamazsa bos dict.
        """
        spec = self._specs.get(spec_id)
        if not spec:
            return {}

        model = {
            "name": model_name,
            "fields": fields,
            "field_count": len(fields),
        }
        spec.data_models.append(model)
        logger.info("Veri modeli tasarimi: %s (%d alan)", model_name, len(fields))
        return model

    def suggest_architecture(self, spec_id: str, context: str = "") -> list[str]:
        """Mimari onerileri olusturur.

        Spesifikasyonun icerigine gore mimari oneriler uretir.

        Args:
            spec_id: Spesifikasyon ID.
            context: Ek baglam bilgisi.

        Returns:
            Mimari onerileri listesi.
        """
        spec = self._specs.get(spec_id)
        if not spec:
            return []

        notes: list[str] = []

        # Endpoint sayisina gore oneri
        if len(spec.api_endpoints) > 5:
            notes.append("API Gateway katmani eklenmesi onerilir")

        if len(spec.data_models) > 3:
            notes.append("Veritabani normalizasyonu gozden gecirilmeli")

        # Genel oneriler
        notes.append("Async islemler icin Celery/Redis kullanilmali")
        notes.append("Hata yonetimi icin merkezi exception handler eklenmeli")

        if context:
            notes.append(f"Baglam notu: {context}")

        spec.architecture_notes.extend(notes)
        logger.info("Mimari onerileri: %d oneri", len(notes))
        return notes

    def generate_documentation(self, spec_id: str) -> str:
        """Spesifikasyondan dokumantasyon uretir.

        Args:
            spec_id: Spesifikasyon ID.

        Returns:
            Markdown formatinda dokumantasyon.
        """
        spec = self._specs.get(spec_id)
        if not spec:
            return ""

        lines: list[str] = [f"# {spec.title}", ""]

        for section in spec.sections:
            lines.append(f"## {section.title}")
            lines.append(section.content)
            for sub in section.subsections:
                for key, val in sub.items():
                    lines.append(f"- **{key}**: {val}")
            lines.append("")

        if spec.api_endpoints:
            lines.append("## API Endpoints")
            for ep in spec.api_endpoints:
                lines.append(f"- `{ep['method']} {ep['path']}` - {ep.get('description', '')}")
            lines.append("")

        if spec.data_models:
            lines.append("## Veri Modelleri")
            for model in spec.data_models:
                lines.append(f"### {model['name']}")
                for field in model.get("fields", []):
                    lines.append(f"- `{field.get('name', '')}`: {field.get('type', '')} - {field.get('description', '')}")
            lines.append("")

        if spec.architecture_notes:
            lines.append("## Mimari Notlari")
            for note in spec.architecture_notes:
                lines.append(f"- {note}")
            lines.append("")

        doc = "\n".join(lines)
        logger.info("Dokumantasyon uretildi: %d satir", len(lines))
        return doc

    def _map_requirement_to_section(self, req_type: str) -> SpecSectionType:
        """Gereksinim tipini spesifikasyon bolum tipine esler.

        Args:
            req_type: Gereksinim tipi degeri.

        Returns:
            Spesifikasyon bolum tipi.
        """
        mapping: dict[str, SpecSectionType] = {
            "functional": SpecSectionType.OVERVIEW,
            "non_functional": SpecSectionType.ARCHITECTURE,
            "constraint": SpecSectionType.SECURITY,
            "assumption": SpecSectionType.OVERVIEW,
        }
        return mapping.get(req_type, SpecSectionType.OVERVIEW)

    def get_spec(self, spec_id: str) -> TechnicalSpec | None:
        """Spesifikasyonu getirir.

        Args:
            spec_id: Spesifikasyon ID.

        Returns:
            TechnicalSpec nesnesi veya None.
        """
        return self._specs.get(spec_id)

    @property
    def spec_count(self) -> int:
        """Toplam spesifikasyon sayisi."""
        return len(self._specs)
