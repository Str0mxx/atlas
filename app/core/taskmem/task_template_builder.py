"""ATLAS Görev Şablonu Oluşturucu modülü.

Şablon çıkarma, değişken tespiti,
parametreleme, versiyon, kullanım takibi.
"""

import logging
import re
import time
from typing import Any

logger = logging.getLogger(__name__)


class TaskTemplateBuilder:
    """Görev şablonu oluşturucu.

    Tekrarlayan görevlerden şablon çıkarır.

    Attributes:
        _templates: Şablon kayıtları.
    """

    def __init__(self) -> None:
        """Oluşturucuyu başlatır."""
        self._templates: dict[
            str, dict[str, Any]
        ] = {}
        self._counter = 0
        self._stats = {
            "templates_created": 0,
            "templates_used": 0,
            "variables_detected": 0,
        }

        logger.info(
            "TaskTemplateBuilder baslatildi",
        )

    def create_template(
        self,
        name: str,
        pattern: str,
        variables: list[str] | None = None,
        description: str = "",
        category: str = "general",
    ) -> dict[str, Any]:
        """Şablon oluşturur.

        Args:
            name: Şablon adı.
            pattern: Şablon kalıbı.
            variables: Değişkenler.
            description: Açıklama.
            category: Kategori.

        Returns:
            Şablon bilgisi.
        """
        self._counter += 1
        tid = f"tmpl_{self._counter}"

        # Otomatik değişken tespiti
        detected_vars = variables or []
        if not detected_vars:
            detected_vars = (
                self._detect_variables(
                    pattern,
                )
            )

        template = {
            "template_id": tid,
            "name": name,
            "pattern": pattern,
            "variables": detected_vars,
            "description": description,
            "category": category,
            "version": 1,
            "usage_count": 0,
            "status": "active",
            "created_at": time.time(),
        }
        self._templates[tid] = template
        self._stats["templates_created"] += 1
        self._stats[
            "variables_detected"
        ] += len(detected_vars)

        return {
            "template_id": tid,
            "name": name,
            "variables": detected_vars,
            "created": True,
        }

    def extract_template(
        self,
        examples: list[str],
        name: str = "",
    ) -> dict[str, Any]:
        """Örneklerden şablon çıkarır.

        Args:
            examples: Örnek görevler.
            name: Şablon adı.

        Returns:
            Çıkarma bilgisi.
        """
        if not examples:
            return {"error": "no_examples"}

        if len(examples) == 1:
            return self.create_template(
                name=name or "auto_template",
                pattern=examples[0],
            )

        # Ortak parçaları bul
        words_list = [
            e.split() for e in examples
        ]
        min_len = min(
            len(w) for w in words_list
        )

        pattern_parts = []
        variables = []
        var_count = 0

        for i in range(min_len):
            column = [
                w[i] for w in words_list
            ]
            if len(set(column)) == 1:
                pattern_parts.append(
                    column[0],
                )
            else:
                var_count += 1
                var_name = f"var_{var_count}"
                pattern_parts.append(
                    f"{{{var_name}}}",
                )
                variables.append(var_name)

        pattern = " ".join(pattern_parts)

        return self.create_template(
            name=name or "extracted_template",
            pattern=pattern,
            variables=variables,
        )

    def apply_template(
        self,
        template_id: str,
        values: dict[str, str],
    ) -> dict[str, Any]:
        """Şablonu uygular.

        Args:
            template_id: Şablon ID.
            values: Değişken değerleri.

        Returns:
            Uygulama bilgisi.
        """
        tmpl = self._templates.get(
            template_id,
        )
        if not tmpl:
            return {
                "error": "template_not_found",
            }

        result = tmpl["pattern"]
        for key, val in values.items():
            result = result.replace(
                f"{{{key}}}", val,
            )

        tmpl["usage_count"] += 1
        self._stats["templates_used"] += 1

        return {
            "template_id": template_id,
            "result": result,
            "variables_filled": len(values),
            "applied": True,
        }

    def update_version(
        self,
        template_id: str,
        new_pattern: str,
    ) -> dict[str, Any]:
        """Şablon versiyonunu günceller.

        Args:
            template_id: Şablon ID.
            new_pattern: Yeni kalıp.

        Returns:
            Güncelleme bilgisi.
        """
        tmpl = self._templates.get(
            template_id,
        )
        if not tmpl:
            return {
                "error": "template_not_found",
            }

        tmpl["version"] += 1
        tmpl["pattern"] = new_pattern
        tmpl["variables"] = (
            self._detect_variables(
                new_pattern,
            )
        )

        return {
            "template_id": template_id,
            "version": tmpl["version"],
            "updated": True,
        }

    def get_template(
        self,
        template_id: str,
    ) -> dict[str, Any]:
        """Şablonu getirir."""
        tmpl = self._templates.get(
            template_id,
        )
        if not tmpl:
            return {
                "error": "template_not_found",
            }
        return dict(tmpl)

    def get_templates(
        self,
        category: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Şablonları getirir."""
        results = list(
            self._templates.values(),
        )
        if category:
            results = [
                t for t in results
                if t["category"] == category
            ]
        return results[:limit]

    def _detect_variables(
        self,
        pattern: str,
    ) -> list[str]:
        """Değişkenleri tespit eder."""
        return re.findall(
            r"\{(\w+)\}", pattern,
        )

    @property
    def template_count(self) -> int:
        """Şablon sayısı."""
        return len(self._templates)

    @property
    def usage_count(self) -> int:
        """Kullanım sayısı."""
        return self._stats[
            "templates_used"
        ]
